import asyncio
import logging
import os
import sys
import signal
from contextlib import asynccontextmanager
from datetime import datetime

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

# Импорт конфигурации
from config import config

# Импорт хендлеров
from src.handlers import start, testing, sos, tracker, emotions, resources, chat

# Импорт БД
from src.database.supabase_client import db

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


# ============================================================================
# ОБРАБОТКА СИГНАЛОВ (SIGTERM) ДЛЯ RENDER
# ============================================================================

def handle_sigterm(signum, frame):
    """Обработчик сигнала SIGTERM от Render"""
    logger.info("📡 Received SIGTERM signal, initiating graceful shutdown...")
    asyncio.create_task(trigger_shutdown())


async def trigger_shutdown():
    """Триггер для graceful shutdown"""
    shutdown_event.set()


# ============================================================================
# ФУНКЦИИ ДЛЯ НАСТРОЙКИ БОТА
# ============================================================================

async def setup_bot_commands(bot_instance: Bot):
    """
    Устанавливает меню команд бота, которые видны пользователям.
    """
    bot_commands = [
        BotCommand(command="/start", description="🔄 Рестарт (Главное меню)"),
        BotCommand(command="/sos", description="🆘 Срочная помощь"),
        BotCommand(command="/diary", description="📝 Заполнить дневник"),
        BotCommand(command="/mbi", description="📊 Тест на выгорание"),
        BotCommand(command="/help", description="📖 О боте")
    ]
    await bot_instance.set_my_commands(bot_commands)
    logger.info("✅ Bot commands menu has been set up")


# ============================================================================
# ВЕБ-СЕРВЕР ДЛЯ RENDER (Health Check)
# ============================================================================

async def health_check(request):
    """Health check endpoint для Render/UptimeRobot"""
    return web.json_response({
        "status": "healthy",
        "service": "mental-health-bot",
        "timestamp": datetime.utcnow().isoformat()
    })


async def ping(request):
    """Простой ping endpoint"""
    return web.json_response({
        "pong": True,
        "timestamp": datetime.utcnow().isoformat()
    })


async def status(request):
    """Детальный статус бота"""
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
                "database": "connected" if db and hasattr(db, '_is_connected') and db._is_connected else "disconnected",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return web.json_response({
                "status": "initializing",
                "message": "Bot is starting up",
                "timestamp": datetime.utcnow().isoformat()
            })
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return web.json_response({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, status=500)


async def start_web_server():
    """
    Запускает веб-сервер с несколькими endpoints для мониторинга.
    """
    app = web.Application()
    
    # Регистрируем endpoints
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/ping', ping)
    app.router.add_get('/status', status)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render передает порт через переменную окружения PORT
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"✅ Web server started on port {port}")
    logger.info(f"📌 Available endpoints: /, /health, /ping, /status")
    
    return runner


# ============================================================================
# ПЕРИОДИЧЕСКИЕ ЗАДАЧИ
# ============================================================================

# В main.py нужно заменить функцию keep_alive_ping на эту:

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
    
    while True:
        try:
            await asyncio.sleep(300)  # 5 минут
            
            # Retry logic: 3 попытки с экспоненциальной задержкой
            for attempt in range(3):
                try:
                    # ИСПРАВЛЕНО: используем aiohttp напрямую, не из web
                    import aiohttp
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
            logger.info("🛑 Self-ping task stopped")
            break
        except Exception as e:
            logger.debug(f"Self-ping error: {e}")

# Также в main.py нужно добавить переменную ENABLE_SELF_PING в startup
# и создать задачу:
if os.environ.get("ENABLE_SELF_PING", "false").lower() == "true":
    asyncio.create_task(keep_alive_ping())


async def database_health_check():
    """
    Периодическая проверка соединения с БД (каждые 15 минут)
    """
    logger.info("🔄 Database health check task started")
    
    while True:
        try:
            await asyncio.sleep(900)  # 15 минут
            
            if db and hasattr(db, 'health_check'):
                result = await db.health_check()
                if result:
                    logger.debug("✅ Database connection is healthy")
                else:
                    logger.warning("⚠️ Database health check failed, attempting reconnect...")
                    if hasattr(db, 'connect'):
                        await db.connect()
            else:
                # Простой ping БД
                try:
                    await db.execute("SELECT 1")
                    logger.debug("✅ Database ping successful")
                except Exception as e:
                    logger.error(f"❌ Database ping failed: {e}")
                    
        except asyncio.CancelledError:
            logger.info("🛑 Database health check stopped")
            break
        except Exception as e:
            logger.error(f"❌ Error in database health check: {e}")


# ============================================================================
# ОСНОВНАЯ ЛОГИКА
# ============================================================================

async def startup():
    """Запуск всех компонентов бота"""
    global bot, dp
    
    logger.info("=" * 50)
    logger.info("🚀 Starting Mental Health Bot...")
    logger.info("=" * 50)
    
    try:
        # 1. Создаем экземпляры Бота и Диспетчера
        bot = Bot(
            token=config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        dp = Dispatcher()
        
        # 2. Проверяем подключение к БД
        logger.info("📦 Checking database connection...")
        if db:
            try:
                await db.connect()
                logger.info("✅ Database connected")
            except Exception as e:
                logger.warning(f"⚠️ Database connection issue: {e}")
        
        # 3. Регистрируем роутеры (подключаем логику)
        logger.info("🔧 Registering handlers...")
        dp.include_router(start.router)
        dp.include_router(testing.router)
        dp.include_router(sos.router)
        dp.include_router(tracker.router)
        dp.include_router(emotions.router)
        dp.include_router(resources.router)
        dp.include_router(chat.router)
        logger.info("✅ Handlers registered")
        
        # 4. Настраиваем меню команд бота
        await setup_bot_commands(bot)
        
        # 5. Удаляем вебхук (полезно при переходе на поллинг)
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook deleted")
        
        # 6. Получаем информацию о боте
        bot_info = await bot.get_me()
        logger.info(f"🤖 Bot: @{bot_info.username} (ID: {bot_info.id})")
        
        logger.info("=" * 50)
        logger.info("✅ Bot started successfully!")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}", exc_info=True)
        raise


async def run_polling():
    """Запуск polling с обработкой завершения"""
    global bot, dp
    
    try:
        logger.info("📡 Starting polling...")
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("🛑 Polling task cancelled")
    except Exception as e:
        logger.error(f"❌ Polling error: {e}", exc_info=True)
    finally:
        logger.info("📡 Polling stopped")


async def shutdown(web_runner):
    """Graceful shutdown всех компонентов"""
    global bot
    
    logger.info("=" * 50)
    logger.info("🛑 Shutting down Mental Health Bot...")
    logger.info("=" * 50)
    
    # Даём время на завершение текущих задач
    logger.info("⏳ Waiting for ongoing tasks to complete (up to 10 seconds)...")
    await asyncio.sleep(10)
    
    # Останавливаем веб-сервер
    if web_runner:
        logger.info("🛑 Stopping web server...")
        await web_runner.cleanup()
        logger.info("✅ Web server stopped")
    
    # Закрываем соединение с БД
    if db and hasattr(db, 'close'):
        logger.info("🛑 Closing database connection...")
        await db.close()
        logger.info("✅ Database connection closed")
    
    # Закрываем сессию бота
    if bot:
        logger.info("🛑 Closing bot session...")
        await bot.session.close()
        logger.info("✅ Bot session closed")
    
    logger.info("👋 Goodbye!")
    logger.info("=" * 50)


async def main():
    """Главная функция"""
    # Регистрируем обработчик SIGTERM для Render
    signal.signal(signal.SIGTERM, handle_sigterm)
    logger.info("✅ SIGTERM handler registered")
    
    web_runner = None
    
    try:
        # Запускаем веб-сервер для мониторинга
        web_runner = await start_web_server()
        
        # Запускаем бота
        await startup()
        
        # Запускаем фоновые задачи
        tasks = []
        
        # Самопинг (опционально)
        if os.environ.get("ENABLE_SELF_PING", "false").lower() == "true":
            tasks.append(asyncio.create_task(keep_alive_ping()))
        
        # Проверка БД (если нужно)
        if os.environ.get("ENABLE_DB_HEALTH_CHECK", "false").lower() == "true":
            tasks.append(asyncio.create_task(database_health_check()))
        
        # Запускаем polling (блокирующая операция)
        await run_polling()
        
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}", exc_info=True)
        
    finally:
        # Отменяем фоновые задачи
        for task in tasks:
            task.cancel()
        
        # Дожидаемся завершения задач
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Graceful shutdown
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
