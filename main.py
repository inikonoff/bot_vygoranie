import os
import sys
import signal
import logging
import asyncio
import time
import json
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Dict, Any

import aiohttp
import psutil
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from src.config import config
from src.handlers import start, testing, sos, tracker, emotions, resources, chat
from src.database.supabase_client import db
from src.rate_limit import RateLimitMiddleware, BannedUsersMiddleware, LoggingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

# ── ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ────────────────────────────────────────────────────

bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# Middleware инстансы — доступны глобально для управления (например, бан через API)
rate_limit_mw  = RateLimitMiddleware()
banned_users_mw = BannedUsersMiddleware()
logging_mw     = LoggingMiddleware()

shutdown_event = asyncio.Event()
start_time = time.time()
polling_task = None
is_shutting_down = False

request_stats: Dict[str, int] = {"total": 0, "success": 0, "errors": 0}


# ── BOT COMMANDS ──────────────────────────────────────────────────────────────

async def setup_bot_commands():
    commands = [
        BotCommand(command="/start",  description="🔄 Главное меню"),
        BotCommand(command="/sos",    description="🆘 Срочная помощь"),
        BotCommand(command="/diary",  description="📝 Заполнить дневник"),
        BotCommand(command="/mbi",    description="📊 Тест на выгорание"),
        BotCommand(command="/help",   description="📖 О боте"),
    ]
    await bot.set_my_commands(commands)
    logger.info("✅ Bot commands set up")


# ── SIGTERM ───────────────────────────────────────────────────────────────────

def handle_sigterm(signum, frame):
    global is_shutting_down
    if is_shutting_down:
        return
    logger.info("📡 Received SIGTERM, initiating graceful shutdown...")
    is_shutting_down = True
    loop = asyncio.get_running_loop()
    loop.call_soon_threadsafe(lambda: asyncio.create_task(trigger_shutdown()))


async def trigger_shutdown():
    shutdown_event.set()


# ── POLLING ───────────────────────────────────────────────────────────────────

async def run_polling_with_auto_restart():
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
            logger.error(f"❌ Polling error: {e}. Restarting in 5s...")
            request_stats["errors"] += 1
            await asyncio.sleep(5)
    logger.info("📡 Polling stopped")


# ── KEEP-ALIVE ────────────────────────────────────────────────────────────────

async def keep_alive_ping():
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        return
    logger.info("🔄 Self-ping task started")
    while True:
        try:
            await asyncio.sleep(300)
            for attempt in range(3):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"{url}/ping",
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as resp:
                            if resp.status == 200:
                                logger.debug("✅ Self-ping OK")
                    break
                except Exception as e:
                    if attempt < 2:
                        await asyncio.sleep(10)
                    else:
                        logger.debug(f"Self-ping failed: {e}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"Self-ping outer error: {e}")


async def db_keep_alive():
    while True:
        try:
            await asyncio.sleep(43200)
            db.client.table("users").select("telegram_id").limit(1).execute()
            logger.debug("✅ Supabase keep-alive OK")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Supabase keep-alive error: {e}")


# ── МОНИТОРИНГ ────────────────────────────────────────────────────────────────

def get_system_stats() -> Dict[str, Any]:
    try:
        proc = psutil.Process()
        mem = proc.memory_info()
        return {
            "cpu_percent": proc.cpu_percent(interval=0.1),
            "memory_rss_mb": round(mem.rss / 1024 / 1024, 1),
            "threads": proc.num_threads(),
            "open_files": len(proc.open_files()),
        }
    except Exception as e:
        logger.error(f"psutil error: {e}")
        return {}


def check_services_health() -> Dict[str, bool]:
    return {
        "supabase": db is not None and hasattr(db, "client"),
        "bot": bot is not None,
    }


# ── LIFESPAN ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global polling_task, is_shutting_down

    logger.info("=" * 50)
    logger.info("🚀 Starting Mental Health Bot...")
    logger.info("=" * 50)

    # ── Middleware (порядок важен: logging → banned → rate_limit) ─────────────
    dp.message.middleware(logging_mw)
    dp.callback_query.middleware(logging_mw)

    dp.message.middleware(banned_users_mw)
    dp.callback_query.middleware(banned_users_mw)

    dp.message.middleware(rate_limit_mw)
    dp.callback_query.middleware(rate_limit_mw)

    # ── Роутеры (chat — последним) ────────────────────────────────────────────
    dp.include_router(start.router)
    dp.include_router(testing.router)
    dp.include_router(sos.router)
    dp.include_router(tracker.router)
    dp.include_router(emotions.router)
    dp.include_router(resources.router)
    dp.include_router(chat.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await setup_bot_commands()

    bot_info = await bot.get_me()
    logger.info(f"🤖 Bot: @{bot_info.username} (ID: {bot_info.id})")

    polling_task = asyncio.create_task(run_polling_with_auto_restart())
    ping_task    = asyncio.create_task(keep_alive_ping())
    db_keepalive = asyncio.create_task(db_keep_alive())

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_sigterm, sig, None)

    logger.info("=" * 50)
    logger.info("✅ Bot started successfully!")
    logger.info(f"🛡  Middleware: RateLimit({RATE_LIMIT_MESSAGES}/min), AntiFlood, Banned, Logging")
    logger.info("=" * 50)

    yield

    logger.info("🛑 Shutting down...")
    is_shutting_down = True

    for task in (polling_task, ping_task, db_keepalive):
        if task and not task.done():
            task.cancel()

    await asyncio.gather(polling_task, ping_task, db_keepalive, return_exceptions=True)

    try:
        await asyncio.wait_for(bot.session.close(), timeout=10)
    except Exception:
        pass

    logger.info("👋 Goodbye!")


# ── FASTAPI ───────────────────────────────────────────────────────────────────

from src.rate_limit import RATE_LIMIT_MESSAGES  # для лога

app = FastAPI(
    lifespan=lifespan,
    title="Mental Health Bot",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
)


@app.get("/")
async def root():
    return {
        "status": "alive",
        "service": "Mental Health Bot",
        "version": "2.0.0",
        "uptime": str(timedelta(seconds=int(time.time() - start_time))),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health")
@app.head("/health")
async def health_check():
    services = check_services_health()
    polling_ok = polling_task is not None and not polling_task.done()
    all_ok = all(services.values()) and polling_ok

    body = {
        "status": "healthy" if all_ok else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - start_time),
        "services": services,
        "polling": polling_ok,
    }
    return Response(
        content=json.dumps(body),
        media_type="application/json",
        status_code=200 if all_ok else 503,
    )


@app.get("/ping")
async def ping():
    return {"pong": True, "timestamp": datetime.utcnow().isoformat()}


@app.get("/status")
async def status():
    try:
        bot_info = await bot.get_me()
        return {
            "status": "running",
            "bot": {"username": bot_info.username, "id": bot_info.id},
            "system": get_system_stats(),
            "polling_active": polling_task is not None and not polling_task.done(),
            "uptime_seconds": int(time.time() - start_time),
            "requests": request_stats,
            "middleware": {
                "banned_users": len(banned_users_mw.banned_list),
                "rate_limit": f"{RATE_LIMIT_MESSAGES} msg/min",
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/metrics")
async def metrics():
    stats = get_system_stats()
    text = (
        f"# HELP bot_uptime_seconds Uptime\n"
        f"# TYPE bot_uptime_seconds gauge\n"
        f"bot_uptime_seconds {int(time.time() - start_time)}\n"
        f"# HELP bot_memory_rss_mb RSS memory in MB\n"
        f"# TYPE bot_memory_rss_mb gauge\n"
        f"bot_memory_rss_mb {stats.get('memory_rss_mb', 0)}\n"
        f"# HELP bot_requests_total Total HTTP requests\n"
        f"# TYPE bot_requests_total counter\n"
        f"bot_requests_total {request_stats['total']}\n"
        f"# HELP bot_errors_total Total errors\n"
        f"# TYPE bot_errors_total counter\n"
        f"bot_errors_total {request_stats['errors']}\n"
        f"# HELP bot_banned_users Banned users count\n"
        f"# TYPE bot_banned_users gauge\n"
        f"bot_banned_users {len(banned_users_mw.banned_list)}\n"
    )
    return Response(content=text, media_type="text/plain")


@app.middleware("http")
async def stats_middleware(request: Request, call_next):
    request_stats["total"] += 1
    try:
        response = await call_next(request)
        if response.status_code < 400:
            request_stats["success"] += 1
        else:
            request_stats["errors"] += 1
        return response
    except Exception:
        request_stats["errors"] += 1
        raise


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info", reload=False, workers=1)
