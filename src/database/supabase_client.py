import logging
from datetime import datetime, timedelta
from supabase import create_client, Client
from src.config import config

logger = logging.getLogger(__name__)


class DBClient:
    def __init__(self):
        self.client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

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

    async def get_user(self, tg_id: int) -> dict | None:
        try:
            result = (
                self.client.table("users")
                .select("*")
                .eq("telegram_id", tg_id)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"get_user error: {e}")
            return None

    async def save_onboarding(self, tg_id: int, sphere: str, main_request: str):
        """Сохраняет данные онбординга в профиль пользователя."""
        try:
            self.client.table("users").update({
                "sphere": sphere,
                "main_request": main_request,
                "onboarded": True,
            }).eq("telegram_id", tg_id).execute()
        except Exception as e:
            logger.error(f"save_onboarding error: {e}")

    async def is_onboarded(self, tg_id: int) -> bool:
        user = await self.get_user(tg_id)
        return bool(user and user.get("onboarded"))

    # ── ТЕСТЫ ────────────────────────────────────────────────────────────────

    async def save_test_result(self, tg_id: int, test_type: str, scores: dict) -> str:
        risk = self._calc_risk(test_type, scores)

        if test_type == "mbi" and risk:
            try:
                self.client.table("users").update({"risk_group": risk}) \
                    .eq("telegram_id", tg_id).execute()
            except Exception as e:
                logger.error(f"update risk_group error: {e}")

        total_score = scores.get("total", sum(
            v for v in scores.values() if isinstance(v, (int, float))
        ))
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
                .select("test_type, total_score, created_at, details")
                .eq("user_id", tg_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"get_test_history error: {e}")
            return []

    async def get_latest_test_results(self, tg_id: int) -> dict:
        """
        Возвращает последний результат по каждому типу теста.
        Используется для формирования контекста AI-чата.
        """
        history = await self.get_test_history(tg_id, limit=20)
        latest: dict = {}
        for row in history:
            t = row.get("test_type")
            if t and t not in latest:
                latest[t] = {
                    "total_score": row.get("total_score"),
                    "details": row.get("details", {}),
                    "date": str(row.get("created_at", ""))[:10],
                }
        return latest

    async def get_cross_test_pattern(self, tg_id: int) -> str | None:
        """
        Проверяет, есть ли тревожный паттерн по нескольким тестам.
        Возвращает строку-описание или None.
        """
        latest = await self.get_latest_test_results(tg_id)
        alerts = []

        mbi = latest.get("mbi", {}).get("details", {})
        if mbi.get("ee", 0) > 25:
            alerts.append("высокое эмоциональное истощение (MBI)")

        phq9 = latest.get("phq9", {}).get("details", {})
        if phq9.get("level") in ("moderate", "moderately_severe", "severe"):
            alerts.append(f"депрессия уровня «{phq9.get('label')}» (PHQ-9)")

        gad7 = latest.get("gad7", {}).get("details", {})
        if gad7.get("level") in ("moderate", "severe"):
            alerts.append(f"тревога уровня «{gad7.get('label')}» (GAD-7)")

        pss10 = latest.get("pss10", {}).get("details", {})
        if pss10.get("level") == "high":
            alerts.append("высокий воспринимаемый стресс (PSS-10)")

        if len(alerts) >= 2:
            return "⚠️ Несколько тестов указывают на одно: " + ", ".join(alerts) + "."
        return None

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
        logs = await self.get_recent_logs(tg_id, days=days)
        return [r["energy_level"] for r in logs if r.get("energy_level") is not None]

    async def build_user_context(self, tg_id: int) -> str:
        """
        Формирует строку контекста пользователя для системного промпта AI.
        Включает: профиль, последние тесты, последние записи дневника.
        """
        user = await self.get_user(tg_id)
        lines = []

        # Профиль
        if user:
            name = user.get("first_name", "")
            sphere = user.get("sphere", "")
            request = user.get("main_request", "")
            risk = user.get("risk_group", "")

            if name:
                lines.append(f"Имя пользователя: {name}.")
            if sphere:
                lines.append(f"Сфера работы: {sphere}.")
            if request:
                lines.append(f"Главный запрос при регистрации: «{request}».")
            if risk:
                risk_label = {"red": "высокий (красный)", "yellow": "умеренный (жёлтый)", "green": "низкий"}.get(risk, risk)
                lines.append(f"Уровень риска по MBI: {risk_label}.")

        # Последние результаты тестов
        latest_tests = await self.get_latest_test_results(tg_id)
        if latest_tests:
            lines.append("\nПоследние результаты тестов:")
            label_map = {
                "mbi": "MBI (выгорание)",
                "boyko": "Бойко (выгорание)",
                "phq9": "PHQ-9 (депрессия)",
                "gad7": "GAD-7 (тревога)",
                "pss10": "PSS-10 (стресс)",
            }
            for test_type, data in latest_tests.items():
                label = label_map.get(test_type, test_type.upper())
                score = data.get("total_score", "?")
                date = data.get("date", "")
                details = data.get("details", {})
                detail_str = ""
                if test_type == "mbi":
                    detail_str = f" (истощение={details.get('ee')}, деперс.={details.get('dp')}, редукция={details.get('pa')})"
                elif test_type in ("phq9", "gad7", "pss10"):
                    detail_str = f" — {details.get('label', '')}"
                elif test_type == "boyko":
                    detail_str = (
                        f" (напряжение={details.get('tension_status')}, "
                        f"резистенция={details.get('resistance_status')}, "
                        f"истощение={details.get('exhaustion_status')})"
                    )
                lines.append(f"  • {label}: {score}{detail_str} [{date}]")

        # Последние 5 записей дневника
        logs = await self.get_recent_logs(tg_id, days=7)
        if logs:
            lines.append("\nПоследние записи дневника (от новых к старым):")
            for row in logs[:5]:
                date = str(row.get("created_at", ""))[:10]
                e = row.get("energy_level", "?")
                emo = row.get("emotion", "?")
                grat = row.get("gratitude", "")
                entry = f"  • {date}: энергия {e}/10, эмоция «{emo}»"
                if grat:
                    entry += f", хорошее: «{grat[:60]}»"
                lines.append(entry)

        if not lines:
            return ""

        return (
            "=== КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ (используй для персонализации, не упоминай явно) ===\n"
            + "\n".join(lines)
            + "\n=== КОНЕЦ КОНТЕКСТА ==="
        )


db = DBClient()
