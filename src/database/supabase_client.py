import logging
from datetime import datetime, timedelta
from supabase import create_client, Client
from config import config

logger = logging.getLogger(__name__)


class DBClient:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> Client:
        """Создаём клиент лениво — только при первом обращении.
        К этому моменту Render уже точно передал переменные окружения."""
        if self._client is None:
            self._client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
            logger.info("✅ Supabase client initialized")
        return self._client

    # ── ПОЛЬЗОВАТЕЛИ ─────────────────────────────────────────────────────────

    async def add_user(self, tg_id: int, first_name: str, username: str):
        data = {
            "telegram_id": tg_id,
            "first_name": first_name,
            "username": username,
        }
        try:
            self.client.table("users").upsert(data).execute()
        except Exception as e:
            logger.error(f"add_user error: {e}")

    # ── ТЕСТЫ ────────────────────────────────────────────────────────────────

    async def save_test_result(self, tg_id: int, test_type: str, scores: dict) -> str:
        """
        Универсальное сохранение результата любого теста.
        Возвращает risk_level (green/yellow/red) для MBI, пустую строку для остальных.
        """
        risk = self._calc_risk(test_type, scores)

        # Обновляем risk_group пользователя только для MBI
        if test_type == "mbi" and risk:
            try:
                self.client.table("users").update({"risk_group": risk}) \
                    .eq("telegram_id", tg_id).execute()
            except Exception as e:
                logger.error(f"update risk_group error: {e}")

        total_score = scores.get("total", sum(v for v in scores.values() if isinstance(v, (int, float))))
        data = {
            "user_id": tg_id,
            "test_type": test_type,
            "total_score": total_score,
            "details": scores,
        }
        try:
            self.client.table("assessments").insert(data).execute()
        except Exception as e:
            logger.error(f"save_test_result error: {e}")

        return risk

    def _calc_risk(self, test_type: str, scores: dict) -> str:
        if test_type == "mbi":
            if scores.get("ee", 0) > 25 or scores.get("dp", 0) > 15:
                return "red"
            elif scores.get("ee", 0) > 15:
                return "yellow"
            return "green"
        return ""

    async def get_test_history(self, tg_id: int, limit: int = 10) -> list:
        try:
            result = (
                self.client.table("assessments")
                .select("test_type, total_score, created_at")
                .eq("user_id", tg_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"get_test_history error: {e}")
            return []

    # ── ДНЕВНИК ───────────────────────────────────────────────────────────────

    async def save_daily_log(self, tg_id: int, energy: int, emotion: str, gratitude: str = None):
        data = {
            "user_id": tg_id,
            "energy_level": energy,
            "emotion": emotion,
        }
        if gratitude is not None:
            data["gratitude"] = gratitude
        try:
            self.client.table("daily_logs").insert(data).execute()
        except Exception as e:
            logger.error(f"save_daily_log error: {e}")

    async def get_recent_logs(self, tg_id: int, days: int = 7) -> list:
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        try:
            result = (
                self.client.table("daily_logs")
                .select("energy_level, emotion, gratitude, created_at")
                .eq("user_id", tg_id)
                .gte("created_at", since)
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"get_recent_logs error: {e}")
            return []

    async def get_recent_energy(self, tg_id: int, days: int = 3) -> list:
        """Возвращает список значений энергии за последние N дней."""
        logs = await self.get_recent_logs(tg_id, days=days)
        return [r["energy_level"] for r in logs if r.get("energy_level") is not None]


db = DBClient()
