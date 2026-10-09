import asyncio
from datetime import datetime

from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.state import State, StatesGroup

from src import fsm_storage
from src.scheduler import build_digest


class FakeDB:
    def __init__(self):
        self.rows = {}

    async def fsm_get(self, k):
        return self.rows.get(k)

    async def fsm_set(self, k, state, data):
        self.rows[k] = {"state": state, "data": data}

    async def fsm_delete(self, k):
        self.rows.pop(k, None)


class S(StatesGroup):
    a = State()


def test_storage_persists_across_instances(monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(fsm_storage, "db", fake)
    key = StorageKey(bot_id=1, chat_id=2, user_id=3)

    async def run():
        st1 = fsm_storage.SupabaseStorage()
        await st1.set_state(key, S.a)
        await st1.update_data(key, {"q_index": 3, "answers": {"1": 2}})
        st2 = fsm_storage.SupabaseStorage()  # «перезапуск»
        assert await st2.get_state(key) == S.a.state
        assert (await st2.get_data(key))["answers"] == {"1": 2}
        await st2.set_state(key, None)
        await st2.set_data(key, {})
        assert fake.rows == {}

    asyncio.run(run())


def test_storage_survives_db_failure(monkeypatch):
    class Broken(FakeDB):
        async def fsm_get(self, k):
            raise RuntimeError("down")

        async def fsm_set(self, k, state, data):
            raise RuntimeError("down")

    monkeypatch.setattr(fsm_storage, "db", Broken())
    key = StorageKey(bot_id=1, chat_id=2, user_id=3)

    async def run():
        st = fsm_storage.SupabaseStorage()
        await st.set_data(key, {"x": 1})
        assert await st.get_data(key) == {"x": 1}

    asyncio.run(run())


def test_build_digest_is_html_and_escapes():
    logs = [
        {"energy_level": 2, "emotion": "<b>Гнев</b>", "gratitude": "кофе"},
        {"energy_level": 3, "emotion": "Грусть", "gratitude": None},
    ]
    text = build_digest(logs, datetime(2026, 10, 1), datetime(2026, 10, 8))
    assert "&lt;b&gt;" in text and "**" not in text
    assert "2.5/10" in text and "/digest" in text
