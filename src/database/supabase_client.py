import logging
from datetime import datetime, timedelta
from supabase import create_client, Client
from src.config import config

logger = logging.getLogger(__name__)


class DBClient:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> Client:
        """Создаём клиент лениво — только при первом обращении.
        К этому моменту Render уже точно передал переменные окружения."""
        if self._client is None:
            # Явно передаём API ключ в заголовках
            self._client = create_client(
                supabase_url=config.SUPABASE_URL,
                supabase_key=config.SUPABASE_KEY
            )
            logger.info(f"✅ Supabase client initialized with URL: {config.SUPABASE_URL}")
            logger.info(f"✅ Supabase key length: {len(config.SUPABASE_KEY)}")
        return self._client

    # ── ПОЛЬЗОВАТЕЛИ ─────────────────────────────────────────────────────────

    async def add_user(self, tg_id: int, first_name: str, username: str):
        data = {
            "telegram_id": tg_id,
            "first_name": first_name,
            "username": username,
        }
        try:
            # Добавляем явную авторизацию в запрос
            response = self.client.table("users").upsert(data).execute()
            logger.debug(f"add_user response: {response}")
        except Exception as e:
            logger.error(f"add_user error: {e}")
            # Пробуем альтернативный способ с явными заголовками
            try:
                import httpx
                headers = {
                    "apikey": config.SUPABASE_KEY,
                    "Authorization": f"Bearer {config.SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates"
                }
                url = f"{config.SUPABASE_URL}/rest/v1/users"
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        headers=headers,
                        json=data
                    )
                    logger.debug(f"Alternative add_user response: {response.status_code}")
            except Exception as e2:
                logger.error(f"Alternative add_user error: {e2}")

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

    # ── ОНБОРДИНГ ─────────────────────────────────────────────────────────────

    async def is_onboarded(self, tg_id: int) -> bool:
        """Проверяет, прошёл ли пользователь онбординг."""
        try:
            result = (
                self.client.table("users")
                .select("is_onboarded")
                .eq("telegram_id", tg_id)
                .execute()
            )
            if result.data and len(result.data) > 0:
                return bool(result.data[0].get("is_onboarded", False))
            return False
        except Exception as e:
            logger.error(f"is_onboarded error: {e}")
            return False

    async def set_onboarded(self, tg_id: int):
        """Помечает пользователя как прошедшего онбординг."""
        try:
            self.client.table("users").update({"is_onboarded": True}) \
                .eq("telegram_id", tg_id).execute()
        except Exception as e:
            logger.error(f"set_onboarded error: {e}")

    async def save_onboarding(self, tg_id: int, sphere: str, main_request: str):
        """Сохраняет данные онбординга и помечает пользователя как прошедшего онбординг."""
        try:
            # Обновляем данные пользователя
            self.client.table("users").update({
                "sphere": sphere,
                "main_request": main_request,
                "is_onboarded": True
            }).eq("telegram_id", tg_id).execute()
            
            logger.info(f"User {tg_id} onboarding saved")
        except Exception as e:
            logger.error(f"save_onboarding error: {e}")

    # ── КОНТЕКСТ ДЛЯ LLM ─────────────────────────────────────────────────────

    async def build_user_context(self, tg_id: int) -> dict:
        """Собирает контекст пользователя для LLM: данные пользователя и последние записи."""
        try:
            # Получаем данные пользователя
            user_result = self.client.table("users") \
                .select("first_name, sphere, main_request") \
                .eq("telegram_id", tg_id) \
                .execute()
            
            user_data = user_result.data[0] if user_result.data else {}
            
            # Получаем последние 3 записи из дневника
            logs = await self.get_recent_logs(tg_id, days=7)
            
            # Получаем последние результаты тестов
            tests = await self.get_test_history(tg_id, limit=3)
            
            context = {
                "user": user_data,
                "recent_logs": logs[:3] if logs else [],
                "recent_tests": tests
            }
            
            return context
        except Exception as e:
            logger.error(f"build_user_context error: {e}")
            return {"user": {}, "recent_logs": [], "recent_tests": []}


db = DBClient()
