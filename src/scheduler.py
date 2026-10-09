import asyncio
import html
import logging
from collections import Counter
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.database.supabase_client import db

logger = logging.getLogger(__name__)

# Часовой пояс рассылки (РФ/РБ — UTC+3)
TIMEZONE = "Europe/Moscow"

scheduler = AsyncIOScheduler(timezone=TIMEZONE)


def build_digest(logs: list, start: datetime, end: datetime) -> str:
    """Текст дайджеста (HTML) по записям дневника за период."""
    energies = [l["energy_level"] for l in logs if l.get("energy_level") is not None]
    avg_energy = sum(energies) / len(energies) if energies else 0

    emotions = [l["emotion"] for l in logs if l.get("emotion")]
    emotion_stats = ""
    if emotions:
        emotion_stats = "🎭 <b>Топ эмоций:</b>\n"
        for emo, count in Counter(emotions).most_common(3):
            emotion_stats += f"  • {html.escape(emo)}: {count}\n"

    gratitude_count = sum(1 for l in logs if l.get("gratitude"))

    digest = (
        f"📊 <b>Твой еженедельный дайджест</b>\n\n"
        f"📅 {start.strftime('%d.%m')} — {end.strftime('%d.%m')}\n\n"
        f"📈 <b>Средняя энергия:</b> {avg_energy:.1f}/10\n"
        f"{emotion_stats}"
        f"✨ <b>Хорошего отмечено:</b> {gratitude_count}\n\n"
    )
    if avg_energy < 4:
        digest += ("⚠️ Энергия ниже среднего. Может, стоит отдохнуть?\n"
                   "Загляни в раздел 🧘 Ресурсы.")
    elif avg_energy > 7:
        digest += "🌟 Отличная энергия! Так держать!"
    else:
        digest += "🌿 Держись, всё идёт своим чередом."
    digest += "\n\n<i>Отключить дайджест: /digest</i>"
    return digest


async def send_weekly_digest(bot):
    """Отправляет еженедельный дайджест тем, кто включил его через /digest."""
    users = await db.get_digest_users()
    if not users:
        logger.info("Digest: no subscribers")
        return

    end = datetime.utcnow()
    start = end - timedelta(days=7)
    sent = 0
    for user in users:
        tg_id = user["telegram_id"]
        try:
            logs = await db.get_daily_logs_range(tg_id, start, end)
            if not logs:
                text = ("📝 <b>Напоминание</b>: на этой неделе не было записей в дневнике. "
                        "Это займёт 20 секунд и помогает замечать тенденции.\n\n"
                        "<i>Отключить дайджест: /digest</i>")
            else:
                text = build_digest(logs, start, end)
            await bot.send_message(tg_id, text, parse_mode="HTML")
            sent += 1
        except Exception as e:
            logger.error(f"Digest to {tg_id} failed: {e}")
        await asyncio.sleep(0.1)  # лимиты Telegram
    logger.info(f"✅ Weekly digest sent to {sent}/{len(users)}")


def start_scheduler(bot):
    scheduler.add_job(
        send_weekly_digest,
        CronTrigger(day_of_week="mon", hour=10, minute=0, timezone=TIMEZONE),
        args=[bot],
        id="weekly_digest",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("✅ Scheduler started: weekly_digest (Mon 10:00 %s)", TIMEZONE)


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
