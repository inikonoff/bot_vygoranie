import asyncio
import logging
from typing import Any, Dict, Optional

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

from src.database.supabase_client import db

logger = logging.getLogger(__name__)


class SupabaseStorage(BaseStorage):
    """
    FSM-хранилище в таблице fsm_states (см. migrations/001_*.sql).

    Чтение идёт из памяти, запись — в память и в Supabase (write-through),
    так что состояния переживают перезапуск, а обычные обращения быстрые.
    Если Supabase недоступен, бот продолжает работать на кэше в памяти.
    """

    def __init__(self):
        self._cache: Dict[str, dict] = {}
        self._loaded: set[str] = set()
        self._locks: Dict[str, asyncio.Lock] = {}

    @staticmethod
    def _key(key: StorageKey) -> str:
        return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.thread_id or 0}:{key.destiny}"

    async def _load(self, k: str) -> dict:
        if k in self._cache:
            return self._cache[k]
        entry = {"state": None, "data": {}}
        if k not in self._loaded:
            self._loaded.add(k)
            try:
                row = await db.fsm_get(k)
                if row:
                    entry = {"state": row.get("state"), "data": row.get("data") or {}}
            except Exception as e:
                logger.warning(f"fsm load error: {e}")
        self._cache[k] = entry
        return entry

    async def _save(self, k: str):
        entry = self._cache[k]
        try:
            if entry["state"] is None and not entry["data"]:
                await db.fsm_delete(k)
            else:
                await db.fsm_set(k, entry["state"], entry["data"])
        except Exception as e:
            logger.warning(f"fsm save error: {e}")

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        k = self._key(key)
        entry = await self._load(k)
        entry["state"] = state.state if isinstance(state, State) else state
        await self._save(k)

    async def get_state(self, key: StorageKey) -> Optional[str]:
        return (await self._load(self._key(key)))["state"]

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        k = self._key(key)
        entry = await self._load(k)
        entry["data"] = dict(data)
        await self._save(k)

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        return dict((await self._load(self._key(key)))["data"])

    async def close(self) -> None:
        self._cache.clear()
