import asyncio
import logging
import os
import sys
import signal
from datetime import datetime

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from config import config
from src.handlers import start, testing, sos, tracker, emotions, resources, chat
from src.database.supabase_client import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

bot = None
dp = None
shutdown_event = asyncio.Event()


# ── SIGTERM ───────────────────────────────────────────────────────────────────

def handle_sigterm(signum, frame):
    logger.info("📡 Received SIGTERM, initiating graceful shutdown...")
    asyncio.create_task(trigger_shutdown())


async def trigger_shutdown():
    shutdown_event.set()


# ── BOT COMMANDS ──────────────────────────────────────────────────────────────

async def setup_bot_commands(bot_instance: Bot):
    commands = [
        BotCommand(command="/start", description="🔄 Главное меню"),
        BotCommand(command="/sos", description="🆘 Срочная помощь"),
        BotCommand(command="/diary", description="📝 Заполнить дневник"),
        BotCommand(command="/mbi", description="📊 Тест на выгорание"),
        BotCommand(command="/help", description="📖 О боте"),
    ]
    await bot_instance.set_my_commands(commands)
    logger.info("✅ Bot commands set up")


# ── WEB SERVER ────────────────────────────────────────────────────────────────

async def health_check(request):
    return web.json_response({
        "status": "healthy",
        "service": "mental-health-bot",
        "timestamp": datetime.utcnow().isoformat()
    })


async def ping(request):
    return web.json_response({"pong": True, "timestamp": datetime.utcnow().isoformat()})


async def status(request):
    global bot
    try:
        if bot:
            bot_info = await bot.get_me()
            return web.json_response({
                "status": "running",
                "bot": {"username": bot_info.username, "id": bot_info.id},
                "timestamp": datetime.utcnow().isoformat()
            })
        return web.json_response({"status": "initializing"})
    except Exception as e:
        return web.json_response({"status": "error", "error": str(e)}, status=500)


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    app.router.add_get("/ping", ping)
    app.router.add_get("/status", status)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"✅ Web server started on port {port}")
    return runner


# ── KEEP-ALIVE (ИСПРАВЛЕННЫЙ) ─────────────────────────────────────────────────

async def keep_alive_ping():
    """
    Самопинг каждые 5 минут.
    Использует aiohttp.ClientSession (не aiohttp.web.ClientSession — это разные вещи).
    """
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        logger.debug("RENDER_EXTERNAL_URL не задан, самопинг отключён")
        return

    logger.info("🔄 Self-ping task started")

    while True:
        try:
            await asyncio.sleep(300)  # 5 минут

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"{url}/ping",
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            if response.status == 200:
                                logger.debug("✅ Self-ping successful")
                            else:
                                logger.warning(f"⚠️ Self-ping returned {response.status}")
                    break  # успех — выходим из retry-цикла
                except Exception as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(10)
                    else:
                        logger.debug(f"Self-ping failed after {max_retries} attempts: {e}")

        except asyncio.CancelledError:
            logger.info("🛑 Self-ping task stopped")
            break
        except Exception as e:
            logger.debug(f"Self-ping outer error: {e}")


# ── DATABASE HEALTH CHECK ─────────────────────────────────────────────────────

async def database_health_check():
    logger.info("🔄 Database health check task started")
    while True:
        try:
            await asyncio.sleep(900)  # 15 минут
            if db and hasattr(db, "client"):
                db.client.table("users").select("telegram_id").limit(1).execute()
                logger.debug("✅ Database ping successful")
        except asyncio.CancelledError:
            logger.info("🛑 Database health check stopped")
            break
        except Exception as e:
            logger.error(f"❌ Database ping failed: {e}")


# ── STARTUP / SHUTDOWN ────────────────────────────────────────────────────────

async def startup():
    global bot, dp

    logger.info("=" * 50)
    logger.info("🚀 Starting Mental Health Bot...")
    logger.info("=" * 50)

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(testing.router)
    dp.include_router(sos.router)
    dp.include_router(tracker.router)
    dp.include_router(emotions.router)
    dp.include_router(resources.router)
    dp.include_router(chat.router)   # chat — ПОСЛЕДНИМ, он ловит всё остальное

    await setup_bot_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)

    bot_info = await bot.get_me()
    logger.info(f"🤖 Bot: @{bot_info.username}")
    logger.info("=" * 50)
    logger.info("✅ Bot started successfully!")
    logger.info("=" * 50)


async def run_polling():
    global bot, dp
    try:
        logger.info("📡 Starting polling...")
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("🛑 Polling cancelled")
    except Exception as e:
        logger.error(f"❌ Polling error: {e}", exc_info=True)


async def shutdown(web_runner):
    global bot

    logger.info("🛑 Shutting down...")
    await asyncio.sleep(5)

    if web_runner:
        await web_runner.cleanup()

    if bot:
        await bot.session.close()

    logger.info("👋 Goodbye!")


# ── MAIN ──────────────────────────────────────────────────────────────────────

async def main():
    signal.signal(signal.SIGTERM, handle_sigterm)

    web_runner = None
    tasks = []

    try:
        web_runner = await start_web_server()
        await startup()

        if os.environ.get("ENABLE_SELF_PING", "false").lower() == "true":
            tasks.append(asyncio.create_task(keep_alive_ping()))

        if os.environ.get("ENABLE_DB_HEALTH_CHECK", "false").lower() == "true":
            tasks.append(asyncio.create_task(database_health_check()))

        await run_polling()

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)

    finally:
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await shutdown(web_runner)


if __name__ == "__main__":
    try:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped manually")
    except Exception as e:
        logger.error(f"💥 Unhandled exception: {e}", exc_info=True)
