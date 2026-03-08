import time
import logging
from typing import Any, Callable, Awaitable
from collections import defaultdict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)

# ── НАСТРОЙКИ ────────────────────────────────────────────────────────────────

RATE_LIMIT_MESSAGES = 30        # макс сообщений в окне
RATE_LIMIT_WINDOW = 60          # окно в секундах
FLOOD_THRESHOLD = 5             # сообщений за 3 секунды = флуд
FLOOD_WINDOW = 3                # секунд для детекции флуда
FLOOD_MUTE_SECONDS = 30         # бан на N секунд после флуда


class RateLimitMiddleware(BaseMiddleware):
    """
    Защита от спама и флуда.

    Два уровня:
    1. Мягкий rate-limit: не более RATE_LIMIT_MESSAGES сообщений
       за RATE_LIMIT_WINDOW секунд. При превышении — предупреждение.
    2. Жёсткий anti-flood: если за FLOOD_WINDOW секунд пришло
       FLOOD_THRESHOLD+ сообщений — временный мут на FLOOD_MUTE_SECONDS.

    Callback-запросы считаются отдельно от сообщений, но тоже ограничиваются.
    """

    def __init__(self):
        # {user_id: [(timestamp, ...), ...]}
        self._message_timestamps: dict[int, list[float]] = defaultdict(list)
        self._callback_timestamps: dict[int, list[float]] = defaultdict(list)
        # {user_id: mute_until_timestamp}
        self._muted_until: dict[int, float] = {}
        # {user_id: warned} — флаг "уже предупрежден в этом окне"
        self._warned: dict[int, bool] = defaultdict(bool)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:

        user_id, is_callback = self._extract_user(event)
        if user_id is None:
            return await handler(event, data)

        now = time.monotonic()

        # ── Проверка мута ────────────────────────────────────────────────────
        mute_until = self._muted_until.get(user_id, 0)
        if now < mute_until:
            remaining = int(mute_until - now)
            if is_callback:
                await event.answer(
                    f"⏳ Слишком быстро. Подожди {remaining} сек.", show_alert=True
                )
            else:
                await event.answer(
                    f"⏳ Слишком много сообщений. Подожди {remaining} сек."
                )
            logger.debug(f"User {user_id} muted, {remaining}s left")
            return  # блокируем

        # ── Выбираем нужный хранилище временных меток ────────────────────────
        store = self._callback_timestamps if is_callback else self._message_timestamps

        # Очищаем старые метки за пределами длинного окна
        store[user_id] = [t for t in store[user_id] if now - t < RATE_LIMIT_WINDOW]
        store[user_id].append(now)

        timestamps = store[user_id]

        # ── Anti-flood: проверяем короткое окно ──────────────────────────────
        recent = [t for t in timestamps if now - t < FLOOD_WINDOW]
        if len(recent) >= FLOOD_THRESHOLD:
            self._muted_until[user_id] = now + FLOOD_MUTE_SECONDS
            self._warned[user_id] = False  # сбрасываем предупреждение
            logger.warning(f"User {user_id} flood-muted for {FLOOD_MUTE_SECONDS}s")
            if is_callback:
                await event.answer(
                    f"🚫 Флуд обнаружен. Пауза {FLOOD_MUTE_SECONDS} сек.",
                    show_alert=True
                )
            else:
                await event.answer(
                    f"🚫 Пожалуйста, не спамь. Пауза {FLOOD_MUTE_SECONDS} сек."
                )
            return

        # ── Rate-limit: проверяем длинное окно ───────────────────────────────
        if len(timestamps) > RATE_LIMIT_MESSAGES:
            if not self._warned[user_id]:
                self._warned[user_id] = True
                logger.info(f"User {user_id} rate-limited ({len(timestamps)} msgs/min)")
                if is_callback:
                    await event.answer(
                        "⚠️ Ты отправляешь слишком много запросов. Немного помедленнее.",
                        show_alert=True
                    )
                else:
                    await event.answer(
                        "⚠️ Ты отправляешь слишком много сообщений. Немного помедленнее."
                    )
            return  # блокируем без мута

        # Сбрасываем флаг предупреждения если окно очистилось
        if len(timestamps) <= RATE_LIMIT_MESSAGES // 2:
            self._warned[user_id] = False

        return await handler(event, data)

    @staticmethod
    def _extract_user(event: TelegramObject) -> tuple[int | None, bool]:
        """Возвращает (user_id, is_callback)."""
        if isinstance(event, Message):
            return (event.from_user.id if event.from_user else None), False
        if isinstance(event, CallbackQuery):
            return (event.from_user.id if event.from_user else None), True
        return None, False


class BannedUsersMiddleware(BaseMiddleware):
    """
    Блокирует конкретных пользователей по user_id.
    Список можно менять на лету через add/remove без перезапуска бота.

    Использование:
        banned_mw = BannedUsersMiddleware()
        banned_mw.ban(123456789)
        dp.message.middleware(banned_mw)
    """

    def __init__(self, banned_ids: set[int] | None = None):
        self._banned: set[int] = banned_ids or set()

    def ban(self, user_id: int):
        self._banned.add(user_id)
        logger.info(f"User {user_id} banned")

    def unban(self, user_id: int):
        self._banned.discard(user_id)
        logger.info(f"User {user_id} unbanned")

    @property
    def banned_list(self) -> frozenset[int]:
        return frozenset(self._banned)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id and user_id in self._banned:
            logger.debug(f"Blocked banned user {user_id}")
            return  # тихо игнорируем

        return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
    """
    Логирует входящие сообщения и callback-запросы.
    Удобно для дебага и мониторинга активности.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            uid = event.from_user.id
            uname = event.from_user.username or "no_username"
            text = (event.text or "")[:60]
            logger.info(f"MSG uid={uid} @{uname}: {text!r}")

        elif isinstance(event, CallbackQuery) and event.from_user:
            uid = event.from_user.id
            uname = event.from_user.username or "no_username"
            logger.info(f"CBQ uid={uid} @{uname}: data={event.data!r}")

        return await handler(event, data)
