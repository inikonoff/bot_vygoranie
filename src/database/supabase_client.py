from datetime import datetime, timedelta
import logging
from supabase import create_client, Client

from src.config import config

logger = logging.getLogger(__name__)


class DBClient:
    def __init__(self):
        self.client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        self._is_connected = True

    async def connect(self):
        """Проверка подключения к Supabase"""
        try:
            # Простой запрос для проверки соединения
            self.client.table("users").select("count", count="exact").limit(1).execute()
            self._is_connected = True
            logger.info("✅ Supabase connected")
            return True
        except Exception as e:
            self._is_connected = False
            logger.error(f"❌ Supabase connection error: {e}")
            return False

    async def close(self):
        """Закрытие соединения"""
        self._is_connected = False
        logger.info("✅ Supabase connection closed")

    async def ping(self):
        """Пинг для поддержания соединения"""
        try:
            self.client.table("users").select("count", count="exact").limit(1).execute()
            logger.debug("Database ping successful")
            self._is_connected = True
            return True
        except Exception as e:
            logger.error(f"Database ping failed: {e}")
            self._is_connected = False
            return False

    async def add_user(self, tg_id: int, first_name: str, username: str):
        """Добавление или обновление пользователя"""
        data = {
            "telegram_id": tg_id,
            "first_name": first_name,
            "username": username,
            "last_active": datetime.utcnow().isoformat()
        }
        try:
            self.client.table("users").upsert(data).execute()
            logger.info(f"User {tg_id} added/updated")
        except Exception as e:
            logger.error(f"Error adding user {tg_id}: {e}")

    async def save_test_result(self, tg_id: int, test_type: str, result: dict):
        """Универсальное сохранение результатов тестов"""
        # Вычисляем общий балл в зависимости от типа теста
        if test_type == "mbi":
            total_score = result['ee'] + result['dp'] + result['pa']
        elif test_type == "boyko":
            total_score = result.get('total', result['tension'] + result['resistance'] + result['exhaustion'])
        else:
            total_score = result.get('total', 0)
        
        data = {
            "user_id": tg_id,
            "test_type": test_type,
            "total_score": total_score,
            "details": result,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            self.client.table("assessments").insert(data).execute()
            logger.info(f"Saved {test_type} result for user {tg_id}: {total_score}")
            
            # Обновляем risk_group для MBI
            if test_type == "mbi":
                risk = "green"
                if result['ee'] > 25 or result['dp'] > 15:
                    risk = "red"
                elif result['ee'] > 15:
                    risk = "yellow"
                self.client.table("users").update({"risk_group": risk}).eq("telegram_id", tg_id).execute()
                
        except Exception as e:
            logger.error(f"Error saving test result for user {tg_id}: {e}")

    async def save_daily_log(self, tg_id: int, energy: int, emotion: str, gratitude: str = None):
        """Сохранение записи дневника"""
        data = {
            "user_id": tg_id,
            "energy_level": energy,
            "emotion": emotion,
            "gratitude": gratitude,
            "created_at": datetime.utcnow().isoformat()
        }
        try:
            self.client.table("daily_logs").insert(data).execute()
            
            # Обновляем last_active пользователя
            self.client.table("users").update({
                "last_active": datetime.utcnow().isoformat()
            }).eq("telegram_id", tg_id).execute()
            
            logger.info(f"Saved daily log for user {tg_id}: energy={energy}")
            
        except Exception as e:
            logger.error(f"Error saving daily log for user {tg_id}: {e}")

    async def get_recent_daily_logs(self, tg_id: int, limit: int = 7):
        """Получить последние записи дневника"""
        try:
            result = self.client.table("daily_logs")\
                .select("*")\
                .eq("user_id", tg_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting daily logs for user {tg_id}: {e}")
            return []

    async def get_daily_logs_range(self, tg_id: int, start_date: datetime, end_date: datetime):
        """Получить записи дневника за период"""
        try:
            result = self.client.table("daily_logs")\
                .select("*")\
                .eq("user_id", tg_id)\
                .gte("created_at", start_date.isoformat())\
                .lte("created_at", end_date.isoformat())\
                .order("created_at")\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting daily logs range for user {tg_id}: {e}")
            return []

    async def get_user_all_results(self, tg_id: int, limit: int = 10):
        """Получить все результаты тестов пользователя"""
        try:
            result = self.client.table("assessments")\
                .select("*")\
                .eq("user_id", tg_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting user results for {tg_id}: {e}")
            return []

    async def get_active_users(self, days: int = 7):
        """Получить активных пользователей за последние N дней"""
        try:
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            result = self.client.table("users")\
                .select("telegram_id, first_name")\
                .gte("last_active", cutoff)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []

    async def get_users_with_reminders(self):
        """Получить пользователей, включивших напоминания"""
        # Заглушка - в будущем можно добавить поле reminders_enabled в таблицу users
        return []


# СОЗДАЕМ ЭКЗЕМПЛЯР ДЛЯ ИМПОРТА - ЭТО ВАЖНО!
db = DBClient()
