import asyncio
import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.keyboards import builders
from src.services.llm import get_ai_response
from src.states import SOSStates

logger = logging.getLogger(__name__)
router = Router()


# ============================================================================
# ГЛАВНОЕ МЕНЮ РАЗДЕЛА SOS
# ============================================================================

@router.message(F.text == "🆘 SOS / Я киплю")
@router.message(Command("sos"))
async def sos_menu(message: types.Message):
    """Показывает меню SOS с уточняющим вопросом"""
    await message.answer(
        "🆘 **Что сейчас происходит?**\n\n"
        "Выбери вариант, который лучше всего описывает твое состояние:",
        reply_markup=builders.smart_sos_keyboard(),
        parse_mode="Markdown"
    )


# ============================================================================
# ОБРАБОТКА РАЗНЫХ ТИПОВ SOS
# ============================================================================

@router.callback_query(F.data == "sos_sudden")
async def handle_sudden(callback: types.CallbackQuery, state: FSMContext):
    """Обработка 'Накрыло внезапно' - техника STOP + дыхание"""
    await callback.message.edit_text("🌪 Понял. Давай сделаем технику STOP...")
    await asyncio.sleep(1)
    
    steps = [
        "🛑 **STOP** — Остановись. Замри на мгновение. Не реагируй автоматически.",
        "🌬 **Take a breath** — Сделай глубокий вдох... (4 секунды) ... и медленный выдох (6 секунд).",
        "👁 **Observe** — Заметь, что ты чувствуешь. Где в теле напряжение? Просто наблюдай.",
        "🚶 **Proceed** — А теперь продолжи. Что сейчас важно сделать?"
    ]
    
    msg = await callback.message.edit_text(steps[0], parse_mode="Markdown")
    for step in steps[1:]:
        await asyncio.sleep(3)
        msg = await msg.edit_text(step, parse_mode="Markdown")
    
    await asyncio.sleep(2)
    
    # Предлагаем дыхание
    kb = InlineKeyboardBuilder()
    kb.button(text="🌬 Квадратное дыхание", callback_data="sos_breathe")
    kb.button(text="✅ Уже легче", callback_data="sos_done")
    
    await msg.edit_text(
        "А теперь давай подышим вместе. Попробуй квадратное дыхание:",
        reply_markup=kb.as_markup()
    )
    
    await callback.answer()


@router.callback_query(F.data == "sos_anger")
async def handle_anger(callback: types.CallbackQuery):
    """Обработка конфликта/злости - выбор между сжиганием и дефьюзингом"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔥 Сжечь гнев", callback_data="sos_anger_vent")
    kb.button(text="🧠 Дефьюзинг (работа с мыслями)", callback_data="sos_defusion")
    kb.adjust(1)
    
    await callback.message.edit_text(
        "⚡️ **Что хочешь сделать с гневом?**\n\n"
        "• **Сжечь гнев** - выплеснуть всё наружу\n"
        "• **Дефьюзинг** - отделить себя от гневных мыслей",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "sos_prolonged")
async def handle_prolonged(callback: types.CallbackQuery):
    """Обработка 'Уже долго плохо' - предлагаем тест или разговор"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🧠 PHQ-9 (депрессия)", callback_data="diag_phq9")
    kb.button(text="🤖 Поговорить с AI", callback_data="sos_ai_chat")
    kb.button(text="🧘 Ресурсы", callback_data="resources_menu")
    kb.adjust(1)
    
    await callback.message.edit_text(
        "🌧 **Когда плохо долго**, важно понять причину.\n\n"
        "Что хочешь попробовать?\n"
        "• **PHQ-9** - проверить уровень депрессии\n"
        "• **AI-психолог** - просто поговорить\n"
        "• **Ресурсы** - техники самопомощи",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "sos_done")
async def handle_done(callback: types.CallbackQuery):
    """Завершение SOS-сессии"""
    await callback.message.edit_text(
        "✅ Хорошо. Я рядом, если понадоблюсь.",
        reply_markup=builders.main_menu()
    )
    await callback.answer()


# ============================================================================
# ТЕХНИКА СЖИГАНИЯ ГНЕВА
# ============================================================================

@router.callback_query(F.data == "sos_anger_vent")
async def start_anger_venting(callback: types.CallbackQuery, state: FSMContext):
    """Техника сжигания гнева"""
    await callback.message.edit_text(
        "🔥 **Техника сброса гнева**\n\n"
        "Напиши сюда всё, что тебя бесит. Не стесняйся в выражениях.\n"
        "Я приму это сообщение, и мы его ментально «сожжем».\n\n"
        "Пиши прямо сейчас:", 
        parse_mode="Markdown"
    )
    await state.set_state(SOSStates.anger_venting)
    await callback.answer()


@router.message(SOSStates.anger_venting)
async def process_anger_venting(message: types.Message, state: FSMContext):
    """Обработка сообщения с гневом"""
    msg = await message.reply("🔥🔥🔥 Сжигаю этот негатив...")
    await asyncio.sleep(1.5)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, стало легче", callback_data="sos_done")
    kb.button(text="🔄 Еще есть гнев", callback_data="sos_anger_vent")
    
    await msg.edit_text(
        "🗑 Пепел развеян.\n\n"
        "Как ты сейчас? Сделай глубокий вдох.\n"
        "Гнев ушел или остался?",
        reply_markup=kb.as_markup()
    )
    await state.clear()


# ============================================================================
# ТЕХНИКА ДЕФЬЮЗИНГ (КОГНИТИВНОЕ РАЗДЕЛЕНИЕ)
# ============================================================================

@router.callback_query(F.data == "sos_defusion")
async def start_defusion(callback: types.CallbackQuery, state: FSMContext):
    """Когнитивное разделение (дефьюзинг)"""
    await callback.message.edit_text(
        "🧠 **Когнитивное разделение**\n\n"
        "Напиши негативную мысль, которая тебя беспокоит "
        "(например: «я неудачник», «я тупой», «все плохо»):",
        parse_mode="Markdown"
    )
    await state.set_state(SOSStates.defusion)
    await callback.answer()


@router.message(SOSStates.defusion)
async def process_defusion(message: types.Message, state: FSMContext):
    """Обработка негативной мысли и переформулирование"""
    thought = message.text
    
    response = (
        f"Я замечаю, что у меня есть мысль: **«{thought}»**\n\n"
        "Почувствуй разницу — эта мысль больше не ты, это просто мысль.\n"
        "Ты — не твои мысли, ты тот, кто их наблюдает.\n\n"
        "Попробуй повторить:\n"
        f"«У меня есть мысль, что {thought.lower()}, и это всего лишь мысль».\n\n"
        "Заметил разницу?"
    )
    
    await message.answer(response, parse_mode="Markdown")
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, стало легче", callback_data="sos_done")
    kb.button(text="🔄 Попробовать еще", callback_data="sos_defusion")
    
    await message.answer(
        "Что чувствуешь теперь?",
        reply_markup=kb.as_markup()
    )
    await state.clear()


# ============================================================================
# ТЕХНИКА ДЫХАНИЯ
# ============================================================================

@router.callback_query(F.data == "sos_breathe")
async def sos_breathe(callback: types.CallbackQuery):
    """Техника квадратного дыхания с GIF"""
    try:
        gif_file = FSInputFile("data/breathing.gif")
        await callback.message.answer_animation(
            animation=gif_file,
            caption=(
                "🌬 **Квадратное дыхание**\n\n"
                "1. 🟢 Вдох (4 сек)\n"
                "2. ✋ Задержка (4 сек)\n"
                "3. ⚪️ Выдох (4 сек)\n"
                "4. ✋ Задержка (4 сек)\n\n"
                "Повтори 5-10 раз"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Breathing GIF not found: {e}")
        # Запасной вариант с текстом
        await callback.message.answer(
            "🌬 **Квадратное дыхание**\n\n"
            "1. Вдох (4 сек)\n"
            "2. Задержка (4 сек)\n"
            "3. Выдох (4 сек)\n"
            "4. Задержка (4 сек)\n\n"
            "Повтори 5-10 раз. Это активирует парасимпатическую нервную систему и успокаивает.",
            parse_mode="Markdown"
        )
    
    await callback.answer()


# ============================================================================
# ВИДЕО ОТ АПАТИИ
# ============================================================================

@router.callback_query(F.data == "sos_apathy")
async def sos_video(callback: types.CallbackQuery):
    """Видео от Татьяны Мужицкой при апатии"""
    await callback.message.answer(
        "🎬 **Видео от Татьяны Мужицкой**\n\n"
        "Посмотри это видео, оно помогает при апатии:\n"
        "https://www.youtube.com/shorts/VxJfaGCRIvM"
    )
    await callback.answer()


# ============================================================================
# ЧАТ С AI-ПСИХОЛОГОМ
# ============================================================================

@router.callback_query(F.data == "sos_ai_chat")
async def sos_ai_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало диалога с AI-психологом"""
    await state.update_data(history=[])
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛑 Закончить диалог", callback_data="ai_stop")]
    ])
    
    await callback.message.edit_text(
        "🤖 **AI-Психолог на связи**\n\n"
        "Напиши, что тебя беспокоит. Я здесь, чтобы выслушать и поддержать.\n"
        "Мы можем общаться столько, сколько нужно.\n\n"
        "_Напиши 'Стоп' или нажми кнопку ниже, чтобы закончить._",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await state.set_state(SOSStates.ai_chat)
    await callback.answer()


@router.callback_query(F.data == "ai_stop", SOSStates.ai_chat)
async def sos_ai_stop_btn(callback: types.CallbackQuery, state: FSMContext):
    """Завершение диалога с AI по кнопке"""
    await state.clear()
    await callback.message.edit_text(
        "💬 Диалог завершен. Береги себя! ❤️",
        reply_markup=builders.main_menu()
    )
    await callback.answer()


@router.message(SOSStates.ai_chat)
async def process_ai_query(message: types.Message, state: FSMContext):
    """Обработка сообщения в чате с AI"""
    # Проверка на выход
    if message.text.lower().strip() in ["стоп", "stop", "хватит", "выход"]:
        await state.clear()
        await message.answer(
            "💬 Диалог завершен.",
            reply_markup=builders.main_menu()
        )
        return

    # Проверка на кнопки меню
    menu_buttons = ["📊 Диагностика", "📝 Дневник", "🆘 SOS / Я киплю", 
                    "🧠 Мои Эмоции", "🧘 Ресурсы", "📋 Тест Бойко", "📈 Моя динамика"]
    
    if message.text in menu_buttons:
        await state.clear()
        await message.answer(
            "Выхожу из режима AI...",
            reply_markup=builders.main_menu()
        )
        return

    # Отправка запроса к AI
    wait_msg = await message.answer("⏳ ...")
    
    data = await state.get_data()
    history = data.get("history", [])
    
    try:
        response = await get_ai_response(
            user_text=message.text, 
            conversation_history=history
        )
        
        # Обновляем историю
        history.append({"role": "user", "content": message.text})
        history.append({"role": "assistant", "content": response})
        
        # Ограничиваем историю последними 10 сообщениями
        if len(history) > 10:
            history = history[-10:]
            
        await state.update_data(history=history)
        
        # Клавиатура для выхода
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛑 Закончить диалог", callback_data="ai_stop")]
        ])
        
        await wait_msg.edit_text(response, reply_markup=kb)
        
    except Exception as e:
        logger.error(f"AI Error: {e}")
        await wait_msg.edit_text(
            "Ошибка связи с нейросетью. Попробуй позже.",
            reply_markup=builders.main_menu()
        )
        await state.clear()
