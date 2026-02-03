import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import config
from src.handlers import start, testing, sos, tracker
from src.database.supabase_client import db

async def keep_alive():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="I am alive"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()
    
async def main():
    logging.basicConfig(level=logging.INFO)
    await keep_alive()
    
    print("Bot started...")
    await dp.start_polling(bot)
    
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
