import os
import sys
import signal
import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import settings
from src.handlers import start, testing, sos, tracker, emotions, resources, chat
from src.database.supabase_client import db
from src.scheduler import run_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

# Глобальные переменные
bot = None
dp = None
shutdown_event = asyncio.Event()
polling_task = None
keep_alive_task = None
scheduler_task = None
is_shutting_down = False


# ============================================================================
# ОБРАБОТКА СИГНАЛОВ
# ============================================================================

def handle_sigterm(signum, frame):
    """Обработчик сигнала SIGTERM от Render"""
    global is_shutting_down
    if is_shutting_down:
        return
    
    logger.info("📡 Received SIGTERM signal, initiating graceful shutdown...")
    is_shutting_down = True
    
    loop = asyncio.get_running_loop()
    loop.call_soon_threadsafe(lambda: asyncio.create_task(trigger_shutdown()))


async def trigger_shutdown():
    """Триггер для graceful shutdown"""
    shutdown_event.set()


# ============================================================================
# НАСТРОЙКА БОТА
# ============================================================================

async def setup_bot_commands(bot_instance: Bot):
    """Устанавливает меню команд бота"""
    bot_commands = [
        BotCommand(command="/start", description="🔄 Главное меню"),
        BotCommand(command="/sos", description="🆘 Срочная помощь"),
        BotCommand(command="/diary", description="📝 Дневник"),
        BotCommand(command="/help", description="📖 О боте")
    ]
    await bot_instance.set_my_commands(bot_commands)
    logger.info("✅ Bot commands menu installed")


# ============================================================================
# ВЕБ-СЕРВЕР ДЛЯ RENDER
# ============================================================================

async def health_check(request):
    """Health check endpoint"""
    return web.json_response({
        "status": "healthy",
        "service": "mental-health-bot",
        "timestamp": datetime.utcnow().isoformat()
    })


async def ping(request):
    """Ping endpoint"""
    return web.json_response({"pong": True, "timestamp": datetime.utcnow().isoformat()})


async def status(request):
    """Статус бота"""
    global bot
    
    try:
        if bot:
            bot_info = await bot.get_me()
            return web.json_response({
                "status": "running",
                "bot": {
                    "username": bot_info.username,
                    "id": bot_info.id,
                    "name": bot_info.first_name
                },
                "database": "connected" if db and db._is_connected else "disconnected",
                "polling": polling_task is not None and not polling_task.done(),
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return web.json_response({"status": "initializing"})
    except Exception as e:
        return web.json_response({"status": "error", "error": str(e)}, status=500)


async def start_web_server():
    """Запуск веб-сервера для мониторинга"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/ping', ping)
    app.router.add_get('/status', status)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"✅ Web server started on port {port}")
    return runner


# ============================================================================
# ФОНОВЫЕ ЗАДАЧИ
# ============================================================================

async def keep_alive_ping():
    """
    Самопинг для поддержания активности (каждые 5 минут)
    С retry-логикой и правильным импортом aiohttp
    """
    url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if not url:
        logger.debug("RENDER_EXTERNAL_URL not set, self-ping disabled")
        return
    
    logger.info("🔄 Self-ping task started")
    
    while not is_shutting_down:
        try:
            await asyncio.sleep(300)  # 5 минут
            
            import aiohttp
            # Retry logic: 3 попытки с экспоненциальной задержкой
            for attempt in range(3):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{url}/ping", timeout=5) as response:
                            if response.status == 200:
                                logger.debug("✅ Self-ping successful")
                                break
                            else:
                                logger.warning(f"⚠️ Self-ping returned {response.status}")
                except Exception as e:
                    if attempt < 2:  # не последняя попытка
                        wait_time = 2 ** attempt  # 1, 2, 4 секунды
                        logger.debug(f"Self-ping attempt {attempt+1} failed, retrying in {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.warning(f"⚠️ Self-ping failed after 3 attempts: {e}")
                        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"Self-ping error: {e}")
    
    logger.info("🛑 Self-ping task stopped")


async def database_keep_alive():
    """Пинг БД каждые 12 часов для предотвращения засыпания"""
    logger.info("🔄 Database keep-alive task started")
    
    while not is_shutting_down:
        try:
            await asyncio.sleep(43200)  # 12 часов
            await db.ping()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Database keep-alive error: {e}")
    
    logger.info("🛑 Database keep-alive task stopped")


# ============================================================================
# POLLING
# ============================================================================

async def run_polling_with_auto_restart():
    """Запуск polling с автоматическим перезапуском при ошибках"""
    global is_shutting_down
    
    while not is_shutting_down:
        try:
            logger.info("🚀 Starting polling...")
            await dp.start_polling(bot)
            logger.info("✅ Polling completed normally")
        except asyncio.CancelledError:
            break
        except Exception as e:
            if is_shutting_down:
                break
            logger.error(f"❌ Polling error: {e}", exc_info=True)
            await asyncio.sleep(5)
    
    logger.info("📡 Polling stopped")


# ============================================================================
# STARTUP / SHUTDOWN
# ============================================================================

async def startup():
    """Запуск всех компонентов"""
    global bot, dp, polling_task, keep_alive_task, scheduler_task
    
    logger.info("=" * 50)
    logger.info("🚀 Starting Mental Health Bot...")
    logger.info("=" * 50)
    
    try:
        # 1. Создаем бота и диспетчера
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
        dp = Dispatcher(storage=MemoryStorage())
        
        # 2. Подключаемся к БД
        logger.info("📦 Connecting to database...")
        try:
            await db.connect()
        except Exception as e:
            logger.warning(f"⚠️ Database connection issue: {e}")
        
        # 3. Регистрируем хендлеры
        logger.info("🔧 Registering handlers...")
        dp.include_router(start.router)
        dp.include_router(testing.router)
        dp.include_router(sos.router)
        dp.include_router(tracker.router)
        dp.include_router(emotions.router)
        dp.include_router(resources.router)
        dp.include_router(chat.router)
        logger.info("✅ Handlers registered")
        
        # 4. Настраиваем меню команд
        await setup_bot_commands(bot)
        
        # 5. Удаляем вебхук
        await bot.delete_webhook(drop_pending_updates=True)
        
        # 6. Информация о боте
        bot_info = await bot.get_me()
        logger.info(f"🤖 Bot: @{bot_info.username} (ID: {bot_info.id})")
        
        # 7. Запускаем фоновые задачи
        if os.environ.get("ENABLE_SELF_PING", "false").lower() == "true":
            keep_alive_task = asyncio.create_task(keep_alive_ping())
        
        # Запускаем пинг БД
        keep_alive_task = asyncio.create_task(database_keep_alive())
        
        # Запускаем планировщик
        scheduler_task = asyncio.create_task(run_scheduler(bot))
        
        # 8. Запускаем polling
        polling_task = asyncio.create_task(run_polling_with_auto_restart())
        
        logger.info("=" * 50)
        logger.info("✅ Bot started successfully!")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}", exc_info=True)
        raise


async def shutdown(web_runner):
    """Graceful shutdown"""
    global polling_task, keep_alive_task, scheduler_task, is_shutting_down
    
    logger.info("=" * 50)
    logger.info("🛑 Shutting down Mental Health Bot...")
    logger.info("=" * 50)
    
    is_shutting_down = True
    
    # Даем время на завершение текущих задач
    logger.info("⏳ Waiting for ongoing tasks (up to 10 seconds)...")
    await asyncio.sleep(10)
    
    # Отменяем задачи
    for task in [polling_task, keep_alive_task, scheduler_task]:
        if task and not task.done():
            task.cancel()
    
    # Ждем завершения задач
    tasks_to_wait = [t for t in [polling_task, keep_alive_task, scheduler_task] if t]
    if tasks_to_wait:
        await asyncio.gather(*tasks_to_wait, return_exceptions=True)
    
    # Останавливаем веб-сервер
    if web_runner:
        logger.info("🛑 Stopping web server...")
        await web_runner.cleanup()
        logger.info("✅ Web server stopped")
    
    # Закрываем соединение с БД
    if db:
        logger.info("🛑 Closing database connection...")
        await db.close()
    
    # Закрываем сессию бота
    if bot:
        logger.info("🛑 Closing bot session...")
        await bot.session.close()
    
    logger.info("👋 Goodbye!")
    logger.info("=" * 50)


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Главная функция"""
    # Регистрируем обработчик SIGTERM
    signal.signal(signal.SIGTERM, handle_sigterm)
    logger.info("✅ SIGTERM handler registered")
    
    web_runner = None
    
    try:
        # Запускаем веб-сервер
        web_runner = await start_web_server()
        
        # Запускаем бота
        await startup()
        
        # Ждем сигнала завершения
        await shutdown_event.wait()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        
    finally:
        await shutdown(web_runner)


if __name__ == "__main__":
    try:
        # Настройка для Windows (локальный запуск)
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped manually")
    except Exception as e:
        logger.error(f"💥 Unhandled exception: {e}", exc_info=True)
