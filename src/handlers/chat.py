from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

from src.services.llm import get_ai_response
from src.database.supabase_client import db

logger = logging.getLogger(__name__)
router = Router()

SESSION_MODE_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🗣 Выговориться", callback_data="mode_support")],
    [InlineKeyboardButton(text="🔍 Разобраться в ситуации", callback_data="mode_understand")],
    [InlineKeyboardButton(text="🛠 Получить конкретные техники", callback_data="mode_tools")],
])

MENU_BUTTONS = {
    "📊 Диагностика", "📝 Дневник", "🆘 SOS / Я киплю",
    "🧠 Мои Эмоции", "🧘 Ресурсы", "📈 Моя динамика",
}


@router.message(StateFilter(default_state), F.text)
async def chat_logic(message: types.Message, state: FSMContext):
    if message.text in MENU_BUTTONS:
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # Читаем режим сессии из FSM
    fsm_data = await state.get_data()
    session_mode = fsm_data.get("session_mode", "")

    # Если режим ещё не выбран — предлагаем выбрать (один раз)
    if not session_mode and not fsm_data.get("mode_prompted"):
        await state.update_data(mode_prompted=True)
        await message.answer(
            "Как ты хочешь работать сегодня?",
            reply_markup=SESSION_MODE_KB,
        )
        return

    try:
        user_context = await db.build_user_context(message.from_user.id)
        response_text = await get_ai_response(
            user_text=message.text,
            user_context=user_context,
            session_mode=session_mode,
        )
        await message.answer(response_text)
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        await message.answer("Что-то пошло не так. Попробуй ещё раз.")
