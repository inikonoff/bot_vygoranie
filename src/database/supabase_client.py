from supabase import create_client, Client
from config import config

class DBClient:
    def __init__(self):
        self.client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

    async def add_user(self, tg_id: int, first_name: str, username: str):
        data = {"telegram_id": tg_id, "first_name": first_name, "username": username}
        try:
            self.client.table("users").upsert(data).execute()
        except Exception as e:
            print(f"Error adding user: {e}")

    async def save_mbi_result(self, tg_id: int, scores: dict):
        # MBI логика оценки риска
        # Истощение > 30 или Цинизм > 20 -> RED
        risk = "green"
        if scores['ee'] > 25 or scores['dp'] > 15:
            risk = "red"
        elif scores['ee'] > 15:
            risk = "yellow"
            
        # Обновляем статус юзера
        self.client.table("users").update({"risk_group": risk}).eq("telegram_id", tg_id).execute()
        
        # Сохраняем результат
        data = {
            "user_id": tg_id,
            "test_type": "mbi",
            "total_score": sum(scores.values()),
            "details": scores
        }
        self.client.table("assessments").insert(data).execute()
        return risk

    async def save_daily_log(self, tg_id: int, energy: int, emotion: str):
        data = {"user_id": tg_id, "energy_level": energy, "emotion": emotion}
        self.client.table("daily_logs").insert(data).execute()

    async def search_knowledge_base(self, query_vector: list, limit=3):
        # Вызов RPC функции Supabase (нужно создать в SQL, см ниже) или прямой запрос
        # Для простоты используем прямой запрос, если библиотека поддерживает, 
        # но правильнее через rpc match_documents.
        # Пока вернем заглушку, так как векторизация требует настройки на стороне Supabase
        return []

db = DBClient()
