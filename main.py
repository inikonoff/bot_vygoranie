import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import config
from src.handlers import start, testing, sos, tracker
from src.database.supabase_client import db

async def main():
    logging.basicConfig(level=logging.INFO)
    
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    
    # Register routers
    dp.include_router(start.router) # Нужно создать start.py (простой привет)
    dp.include_router(testing.router)
    dp.include_router(sos.router)
    dp.include_router(tracker.router)
    
    # Init DB check (optional)
    print("Bot started...")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
