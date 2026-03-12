from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from src.services.llm import get_ai_response
from src.database.supabase_client import db
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(StateFilter(default_state), F.text)
async def chat_logic(message: types.Message):
    """
    Ловит текстовые сообщения когда пользователь не в FSM-состоянии.
    Подтягивает контекст пользователя из БД для персонализации.
    """
    menu_buttons = {"📊 Диагностика", "📝 Дневник", "🆘 SOS / Я киплю",
                    "🧠 Мои Эмоции", "🧘 Ресурсы", "📈 Моя динамика"}
    if message.text in menu_buttons:
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        user_context = await db.build_user_context(message.from_user.id)
        
        response_text = await get_ai_response(
            user_text=message.text,
            user_context=user_context,  # Передаём словарь с контекстом
        )
        await message.answer(response_text)
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обращении к нейросети. Попробуй позже.")
