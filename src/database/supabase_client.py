import asyncio
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
            self._client = create_client(
                supabase_url=config.SUPABASE_URL,
                supabase_key=config.SUPABASE_KEY,
            )
            logger.info("✅ Supabase client initialized")
        return self._client

    @staticmethod
    async def _x(query):
        """Выполняет синхронный запрос supabase-py в потоке, не блокируя event loop."""
        return await asyncio.to_thread(query.execute)

    async def ping(self):
        await self._x(self.client.table("users").select("telegram_id").limit(1))

    # ── ПОЛЬЗОВАТЕЛИ ─────────────────────────────────────────────────────────

    async def add_user(self, tg_id: int, first_name: str, username: str):
        data = {"telegram_id": tg_id, "first_name": first_name, "username": username}
        try:
            await self._x(self.client.table("users").upsert(data))
        except Exception as e:
            logger.error(f"add_user error: {e}")

    # ── ТЕСТЫ ────────────────────────────────────────────────────────────────

    async def save_test_result(self, tg_id: int, test_type: str, scores: dict) -> str:
        """
        Универсальное сохранение результата любого теста.
        Возвращает risk_level (green/yellow/red) для MBI, пустую строку для остальных.
        """
        risk = self._calc_risk(test_type, scores)

        if test_type == "mbi" and risk:
            try:
                await self._x(
                    self.client.table("users").update({"risk_group": risk})
                    .eq("telegram_id", tg_id)
                )
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
            await self._x(self.client.table("assessments").insert(data))
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
            result = await self._x(
                self.client.table("assessments")
                .select("test_type, total_score, created_at")
                .eq("user_id", tg_id)
                .order("created_at", desc=True)
                .limit(limit)
            )
            return result.data or []
        except Exception as e:
            logger.error(f"get_test_history error: {e}")
            return []

    # ── ДНЕВНИК ───────────────────────────────────────────────────────────────

    async def save_daily_log(self, tg_id: int, energy: int, emotion: str, gratitude: str = None):
        data = {"user_id": tg_id, "energy_level": energy, "emotion": emotion}
        if gratitude is not None:
            data["gratitude"] = gratitude
        try:
            await self._x(self.client.table("daily_logs").insert(data))
        except Exception as e:
            logger.error(f"save_daily_log error: {e}")

    async def get_recent_logs(self, tg_id: int, days: int = 7) -> list:
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        try:
            result = await self._x(
                self.client.table("daily_logs")
                .select("energy_level, emotion, gratitude, created_at")
                .eq("user_id", tg_id)
                .gte("created_at", since)
                .order("created_at", desc=True)
            )
            return result.data or []
        except Exception as e:
            logger.error(f"get_recent_logs error: {e}")
            return []

    async def get_daily_logs_range(self, tg_id: int, start: datetime, end: datetime) -> list:
        try:
            result = await self._x(
                self.client.table("daily_logs")
                .select("energy_level, emotion, gratitude, created_at")
                .eq("user_id", tg_id)
                .gte("created_at", start.isoformat())
                .lte("created_at", end.isoformat())
                .order("created_at", desc=True)
            )
            return result.data or []
        except Exception as e:
            logger.error(f"get_daily_logs_range error: {e}")
            return []

    async def get_recent_energy(self, tg_id: int, days: int = 3) -> list:
        """Возвращает список значений энергии за последние N дней."""
        logs = await self.get_recent_logs(tg_id, days=days)
        return [r["energy_level"] for r in logs if r.get("energy_level") is not None]

    # ── ОНБОРДИНГ ─────────────────────────────────────────────────────────────

    async def is_onboarded(self, tg_id: int) -> bool:
        try:
            result = await self._x(
                self.client.table("users").select("is_onboarded").eq("telegram_id", tg_id)
            )
            if result.data:
                return bool(result.data[0].get("is_onboarded", False))
            return False
        except Exception as e:
            logger.error(f"is_onboarded error: {e}")
            return False

    async def set_onboarded(self, tg_id: int):
        try:
            await self._x(
                self.client.table("users").update({"is_onboarded": True}).eq("telegram_id", tg_id)
            )
        except Exception as e:
            logger.error(f"set_onboarded error: {e}")

    async def save_onboarding(self, tg_id: int, sphere: str, main_request: str):
        try:
            await self._x(
                self.client.table("users").update({
                    "sphere": sphere,
                    "main_request": main_request,
                    "is_onboarded": True,
                }).eq("telegram_id", tg_id)
            )
            logger.info(f"User {tg_id} onboarding saved")
        except Exception as e:
            logger.error(f"save_onboarding error: {e}")

    # ── ДАЙДЖЕСТ ──────────────────────────────────────────────────────────────

    async def get_digest_enabled(self, tg_id: int) -> bool:
        try:
            result = await self._x(
                self.client.table("users").select("digest_enabled").eq("telegram_id", tg_id)
            )
            return bool(result.data and result.data[0].get("digest_enabled"))
        except Exception as e:
            logger.error(f"get_digest_enabled error: {e}")
            return False

    async def set_digest_enabled(self, tg_id: int, enabled: bool) -> bool:
        try:
            await self._x(
                self.client.table("users").update({"digest_enabled": enabled}).eq("telegram_id", tg_id)
            )
            return True
        except Exception as e:
            logger.error(f"set_digest_enabled error: {e}")
            return False

    async def get_digest_users(self) -> list:
        """Пользователи, давшие согласие на еженедельный дайджест."""
        try:
            result = await self._x(
                self.client.table("users").select("telegram_id").eq("digest_enabled", True)
            )
            return result.data or []
        except Exception as e:
            logger.error(f"get_digest_users error: {e}")
            return []

    # ── БАЗА ЗНАНИЙ (RAG) ─────────────────────────────────────────────────────

    async def search_knowledge(self, query: str, limit: int = 3) -> list[str]:
        """Полнотекстовый поиск по knowledge_base (RPC search_knowledge). При ошибке — []."""
        if not query or not query.strip():
            return []
        try:
            result = await self._x(
                self.client.rpc("search_knowledge", {"query_text": query, "match_count": limit})
            )
            return [r["content"] for r in (result.data or []) if r.get("content")]
        except Exception as e:
            logger.warning(f"search_knowledge error: {e}")
            return []

    # ── FSM-ХРАНИЛИЩЕ ─────────────────────────────────────────────────────────

    async def fsm_get(self, key: str) -> dict | None:
        result = await self._x(
            self.client.table("fsm_states").select("state, data").eq("key", key)
        )
        return result.data[0] if result.data else None

    async def fsm_set(self, key: str, state: str | None, data: dict):
        await self._x(
            self.client.table("fsm_states").upsert({
                "key": key,
                "state": state,
                "data": data,
                "updated_at": datetime.utcnow().isoformat(),
            })
        )

    async def fsm_delete(self, key: str):
        await self._x(self.client.table("fsm_states").delete().eq("key", key))

    # ── КОНТЕКСТ ДЛЯ LLM ─────────────────────────────────────────────────────

    async def build_user_context(self, tg_id: int) -> dict:
        """Собирает контекст пользователя для LLM: данные пользователя и последние записи."""
        try:
            user_result = await self._x(
                self.client.table("users")
                .select("first_name, sphere, main_request")
                .eq("telegram_id", tg_id)
            )
            user_data = user_result.data[0] if user_result.data else {}
            logs = await self.get_recent_logs(tg_id, days=7)
            tests = await self.get_test_history(tg_id, limit=3)
            return {
                "user": user_data,
                "recent_logs": logs[:3] if logs else [],
                "recent_tests": tests,
            }
        except Exception as e:
            logger.error(f"build_user_context error: {e}")
            return {"user": {}, "recent_logs": [], "recent_tests": []}

    # ── АДМИНКА ───────────────────────────────────────────────────────────────

    async def get_admin_stats(self) -> dict:
        """Статистика для админ-панели."""
        try:
            now = datetime.utcnow()
            today = (now - timedelta(days=1)).isoformat()
            week = (now - timedelta(days=7)).isoformat()
            t = self.client.table

            async def count(q):
                return (await self._x(q)).count or 0

            test_types = ["mbi", "boyko", "phq9", "gad7", "pss10"]
            results = await asyncio.gather(
                count(t("users").select("telegram_id", count="exact")),
                count(t("users").select("telegram_id", count="exact").gte("created_at", today)),
                count(t("users").select("telegram_id", count="exact").gte("created_at", week)),
                count(t("daily_logs").select("user_id", count="exact").gte("created_at", week)),
                count(t("users").select("telegram_id", count="exact").eq("risk_group", "red")),
                count(t("users").select("telegram_id", count="exact").eq("risk_group", "yellow")),
                count(t("users").select("telegram_id", count="exact").eq("risk_group", "green")),
                *[count(t("assessments").select("id", count="exact").eq("test_type", tt)) for tt in test_types],
                count(t("daily_logs").select("id", count="exact")),
            )
            energies = (await self._x(
                t("daily_logs").select("energy_level").gte("created_at", week)
            )).data or []
            values = [r["energy_level"] for r in energies if r.get("energy_level") is not None]
            avg_energy = sum(values) / len(values) if values else 0

            return {
                "total_users": results[0],
                "new_today": results[1],
                "new_week": results[2],
                "active_week": results[3],
                "risk_red": results[4],
                "risk_yellow": results[5],
                "risk_green": results[6],
                "tests_mbi": results[7],
                "tests_boyko": results[8],
                "tests_phq9": results[9],
                "tests_gad7": results[10],
                "tests_pss10": results[11],
                "total_logs": results[12],
                "avg_energy": avg_energy,
            }
        except Exception as e:
            logger.error(f"get_admin_stats error: {e}")
            return {}

    async def get_all_users(self, limit: int = 100) -> list:
        try:
            result = await self._x(
                self.client.table("users")
                .select("telegram_id, first_name, username, risk_group, created_at")
                .order("created_at", desc=True)
                .limit(limit)
            )
            return result.data or []
        except Exception as e:
            logger.error(f"get_all_users error: {e}")
            return []

    async def get_all_user_ids(self) -> list:
        try:
            result = await self._x(self.client.table("users").select("telegram_id"))
            return [r["telegram_id"] for r in (result.data or [])]
        except Exception as e:
            logger.error(f"get_all_user_ids error: {e}")
            return []

    async def get_user_card(self, tg_id: int) -> dict:
        try:
            user_result = await self._x(
                self.client.table("users")
                .select("telegram_id, first_name, username, risk_group, sphere, main_request, created_at")
                .eq("telegram_id", tg_id)
            )
            user = user_result.data[0] if user_result.data else {}
            tests = await self.get_test_history(tg_id, limit=3)
            logs = await self.get_recent_logs(tg_id, days=14)
            return {"user": user, "recent_tests": tests, "recent_logs": logs[:5]}
        except Exception as e:
            logger.error(f"get_user_card error: {e}")
            return {}


db = DBClient()
