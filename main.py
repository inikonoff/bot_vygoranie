import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher

# Импорты из твоего проекта
try:
    from config import config
    from src.handlers import start, testing, sos, tracker
    from src.database.supabase_client import db
except ImportError as e:
    print(f"Import warning: {e}")
    # Создаем заглушки для тестирования
    config = type('Config', (), {'BOT_TOKEN': os.environ.get('BOT_TOKEN', '')})()
    class RouterStub:
        router = None
    start = testing = sos = tracker = RouterStub()
    db = None

async def keep_alive():
    """Keep-alive сервер для Render/Heroku"""
    app = web.Application()
    
    # Простой health-check endpoint
    async def health_check(request):
        return web.Response(text="Bot is alive", status=200)
    
    app.router.add_get('/', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Получаем порт из переменных окружения (Render предоставляет PORT)
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    print(f"Starting keep-alive server on port {port}")
    await site.start()
    
    # Бесконечно ждем, чтобы сервер не закрывался
    await asyncio.Future()

async def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Запускаем keep-alive сервер в фоновой задаче
    keep_alive_task = asyncio.create_task(keep_alive())
    
    # Проверяем токен
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not found in config or environment variables!")
        return
    
    # Создаем бота и диспетчер
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрируем роутеры (если они есть)
    try:
        if start and start.router:
            dp.include_router(start.router)
        if testing and testing.router:
            dp.include_router(testing.router)
        if sos and sos.router:
            dp.include_router(sos.router)
        if tracker and tracker.router:
            dp.include_router(tracker.router)
    except Exception as e:
        logger.warning(f"Could not include some routers: {e}")
    
    # Информация о запуске
    logger.info("Starting bot...")
    print("=" * 50)
    print("Bot is starting...")
    print(f"Bot token present: {'Yes' if config.BOT_TOKEN else 'No'}")
    print("=" * 50)
    
    try:
        # Запускаем поллинг
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Polling error: {e}")
    finally:
        # Отменяем keep-alive задачу при остановке
        keep_alive_task.cancel()
        try:
            await keep_alive_task
        except asyncio.CancelledError:
            pass
        logger.info("Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
