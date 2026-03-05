import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from src.services.llm import get_ai_response
from src.keyboards import builders

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text, ~F.text.startswith("/"))
async def chat_logic(message: types.Message, state: FSMContext):
    """
    Ловит любое текстовое сообщение, которое не является командой,
    ТОЛЬКО если пользователь не находится ни в каком FSM состоянии.
    """
    # Проверяем, не в состоянии ли пользователь
    current_state = await state.get_state()
    
    if current_state is not None:
        logger.debug(f"User in state {current_state}, skipping chat handler")
        return
    
    user_text = message.text
    
    # Проверяем, не нажал ли юзер кнопку меню
    menu_buttons = [
        "📊 Диагностика", "📝 Дневник", "🆘 SOS / Я киплю", 
        "🧠 Мои Эмоции", "🧘 Ресурсы", "📋 Тест Бойко", "📈 Моя динамика"
    ]
    
    if user_text in menu_buttons:
        return
    
    # Отправляем "печатает..."
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # Отправляем запрос в LLM
        response_text = await get_ai_response(user_text)
        
        # Если ответ слишком длинный, разбиваем на части
        if len(response_text) > 4000:
            parts = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    await message.answer(part)
                else:
                    await message.answer(part + "\n\n(продолжение следует...)")
        else:
            await message.answer(response_text)
            
    except Exception as e:
        logger.error(f"AI Error in chat: {e}", exc_info=True)
        await message.answer(
            "Извини, сейчас не могу ответить. Попробуй позже или воспользуйся меню.",
            reply_markup=builders.main_menu()
        )
