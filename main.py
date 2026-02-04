import asyncio
import logging
import os
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand  # <--- Добавил импорт BotCommand

# Импорт конфигурации
from config import config

# Импорт хендлеров
# ВАЖНО: Убедись, что все эти файлы существуют в папке src/handlers
from src.handlers import start, testing, sos, tracker, emotions, resources  # <--- Добавил недостающие импорты

# Импорт БД (если нужно инициализировать подключение)
from src.database.supabase_client import db

# --- ФУНКЦИЯ ДЛЯ НАСТРОЙКИ КОМАНД БОТА ---
async def setup_bot_commands(bot: Bot):
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
    await bot.set_my_commands(bot_commands)
    logging.info("Bot commands menu has been set up")

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (Health Check) ---
async def keep_alive():
    """
    Запускает маленький веб-сервер, чтобы Render считал сервис активным.
    """
    app = web.Application()
    # Простой роут, который возвращает 200 OK
    app.router.add_get('/', lambda r: web.Response(text="I am alive"))
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render передает порт через переменную окружения PORT
    # Если переменной нет (локальный запуск), используем 8080
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server started on port {port}")

# --- ОСНОВНАЯ ФУНКЦИЯ ---
async def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    # 1. Создаем экземпляры Бота и Диспетчера
    # ParseMode.HTML позволяет использовать форматирование в сообщениях
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # 2. Регистрируем роутеры (подключаем логику)
    dp.include_router(start.router)
    dp.include_router(testing.router)
    dp.include_router(sos.router)
    dp.include_router(tracker.router)      # <--- Добавил роутер tracker
    dp.include_router(emotions.router)     # <--- Добавил роутер emotions
    dp.include_router(resources.router)    # <--- Добавил роутер resources

    # 3. Настраиваем меню команд бота
    await setup_bot_commands(bot)

    # 4. Запускаем веб-сервер (фоновая задача)
    await keep_alive()

    # 5. Удаляем вебхук (полезно при переходе на поллинг, чтобы не ловить старые апдейты)
    await bot.delete_webhook(drop_pending_updates=True)

    # 6. Запускаем бота
    logging.info("Bot started and polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error during polling: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        # Запуск асинхронного цикла
        if sys.platform == 'win32':
            # Исправление для Windows (если запускаешь локально)
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped manually")
