import asyncio
import logging
from datetime import datetime, timedelta
from collections import Counter

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.database.supabase_client import db

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def send_weekly_digest(bot):
    """Отправляет еженедельный дайджест всем активным пользователям"""
    logger.info("📊 Generating weekly digest...")
    
    # Получаем всех пользователей, у которых есть записи за последнюю неделю
    users = await db.get_active_users(days=7)
    
    if not users:
        logger.info("No active users for digest")
        return
    
    sent_count = 0
    for user in users:
        try:
            tg_id = user['telegram_id']
            
            # Получаем статистику за неделю
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            logs = await db.get_daily_logs_range(tg_id, start_date, end_date)
            
            if not logs:
                # Если нет записей - мягкое напоминание
                await bot.send_message(
                    tg_id,
                    "📝 **Напоминание**: Заполни дневник сегодня — это займёт 20 секунд.\n"
                    "Это помогает отслеживать состояние и замечать тенденции."
                )
                sent_count += 1
                continue
            
            # Считаем статистику
            avg_energy = sum(log['energy_level'] for log in logs) / len(logs)
            
            emotions = [log['emotion'] for log in logs if log.get('emotion')]
            emotion_stats = ""
            if emotions:
                top_emotions = Counter(emotions).most_common(3)
                emotion_stats = "🎭 **Топ эмоций:**\n"
                for emo, count in top_emotions:
                    emotion_stats += f"  • {emo}: {count} раз\n"
            
            gratitude_count = sum(1 for log in logs if log.get('gratitude'))
            
            digest = (
                f"📊 **Твой еженедельный дайджест**\n\n"
                f"📅 {start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m')}\n\n"
                f"📈 **Средняя энергия:** {avg_energy:.1f}/10\n"
                f"{emotion_stats}"
                f"✨ **Благодарностей:** {gratitude_count}\n\n"
            )
            
            if avg_energy < 4:
                digest += "⚠️ Заметил, что энергия ниже среднего. Может, стоит отдохнуть?\n"
                digest += "Попробуй раздел 🧘 Ресурсы для восстановления."
            elif avg_energy > 7:
                digest += "🌟 Отличная энергия! Так держать!"
            else:
                digest += "🌿 Держись, всё идёт своим чередом."
            
            await bot.send_message(tg_id, digest)
            sent_count += 1
            
            # Небольшая задержка между отправками
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error sending digest to user {user.get('telegram_id')}: {e}")
    
    logger.info(f"✅ Weekly digest sent to {sent_count} users")


async def send_daily_reminder(bot):
    """Отправляет ежедневные напоминания (заглушка)"""
    # В будущем здесь будет логика для пользователей с включенными напоминаниями
    pass


def setup_scheduler(bot):
    """Настройка планировщика задач"""
    # Еженедельный дайджест - каждый понедельник в 10:00
    scheduler.add_job(
        send_weekly_digest,
        CronTrigger(day_of_week='mon', hour=10, minute=0),
        args=[bot],
        id="weekly_digest",
        replace_existing=True
    )
    
    # Ежедневные напоминания - каждый день в 21:00
    scheduler.add_job(
        send_daily_reminder,
        CronTrigger(hour=21, minute=0),
        args=[bot],
        id="daily_reminder",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ Scheduler started with jobs: weekly_digest, daily_reminder")


async def run_scheduler(bot):
    """Запуск планировщика (для вызова из main)"""
    setup_scheduler(bot)
    
    # Держим задачу живой
    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        logger.info("Scheduler task cancelled")
        scheduler.shutdown()
