from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from src.services.llm import get_ai_response

router = Router()


@router.message(StateFilter(default_state), F.text)
async def chat_logic(message: types.Message):
    """
    Ловит текстовые сообщения ТОЛЬКО когда пользователь не находится
    ни в каком FSM State (не проходит тест, не заполняет дневник и т.д.)
    """
    # Игнорируем кнопки главного меню
    menu_buttons = {"📊 Диагностика", "📝 Дневник", "🆘 SOS / Я киплю",
                    "🧠 Мои Эмоции", "🧘 Ресурсы", "📈 Моя динамика"}
    if message.text in menu_buttons:
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        response_text = await get_ai_response(message.text)
        await message.answer(response_text)
    except Exception as e:
        await message.answer("Произошла ошибка при обращении к нейросети. Попробуй позже.")
