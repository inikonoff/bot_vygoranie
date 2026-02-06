import asyncio
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from src.keyboards import builders
from src.services.llm import get_ai_response

router = Router()

class AIState(StatesGroup):
    waiting_for_query = State()

class AngerState(StatesGroup):
    venting = State()

# === ГЛАВНОЕ МЕНЮ РАЗДЕЛА ===
@router.message(F.text == "🆘 SOS / Я киплю")
@router.message(Command("sos"))
async def sos_menu(message: types.Message):
    await message.answer("Что чувствуешь? Выбери, чтобы я помог:", reply_markup=builders.sos_keyboard())

# === 1. ДЫХАНИЕ ===
@router.callback_query(F.data == "sos_breathe")
async def sos_breathe(callback: types.CallbackQuery):
    # Локальный файл надежнее всего.
    try:
        gif_file = FSInputFile("data/breathing.gif")
        await callback.message.answer_animation(
            animation=gif_file,
            caption=(
                "🌬 <b>Квадратное дыхание</b>\n\n"
                "1. 🟢 Вдох (4 сек)\n"
                "2. ✋ Задержка (4 сек)\n"
                "3. ⚪️ Выдох (4 сек)\n"
                "4. ✋ Задержка (4 сек)"
            ),
            parse_mode="HTML"
        )
    except:
        # Запасной вариант с ссылкой
        try:
            await callback.message.answer_animation(
                animation="https://i.gifer.com/7GCO.gif",
                caption="🌬 <b>Дыши вместе с квадратом</b>\nВдох - Пауза - Выдох - Пауза (по 4 сек).",
                parse_mode="HTML"
            )
        except:
            await callback.message.answer("Инструкция: Вдох 4 сек -> Задержка 4 сек -> Выдох 4 сек -> Задержка 4 сек.")
    
    await callback.answer()

# === 2. ВИДЕО ОТ АПАТИИ ===
@router.callback_query(F.data == "sos_apathy")
async def sos_video(callback: types.CallbackQuery):
    await callback.message.answer("Посмотри это видео от Татьяны Мужицкой, оно помогает:\nhttps://www.youtube.com/shorts/VxJfaGCRIvM")
    await callback.answer()

# === 3. СЖИГАНИЕ ГНЕВА ===
@router.callback_query(F.data == "sos_anger")
async def sos_anger(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🔥 <b>Техника сброса гнева</b>\n\n"
        "Напиши сюда всё, что тебя бесит. Не стесняйся в выражениях.\n"
        "Я приму это сообщение, и мы его ментально «сожжем».\n\n"
        "Пиши прямо сейчас:", 
        parse_mode="HTML"
    )
    await state.set_state(AngerState.venting)
    await callback.answer()

@router.message(AngerState.venting)
async def process_anger(message: types.Message, state: FSMContext):
    msg = await message.reply("🔥🔥🔥 Сжигаю этот негатив...")
    await asyncio.sleep(1.5) 
    await msg.edit_text("🗑 Пепел развеян.\n\nКак ты сейчас? Сделай глубокий вдох.")
    await state.clear()

# === 4. ЧАТ С ПСИХОЛОГОМ (AI) ===
@router.callback_query(F.data == "sos_ai_chat")
async def sos_ai_start(callback: types.CallbackQuery, state: FSMContext):
    # Очищаем историю при новом входе
    await state.update_data(history=[])
    
    await callback.message.answer(
        "🤖 <b>AI-Психолог на связи</b>\n\n"
        "Напиши, что тебя беспокоит. Я здесь, чтобы выслушать и поддержать.\n"
        "Мы можем общаться столько, сколько нужно.\n\n"
        "<i>Напиши 'Стоп' или нажми кнопку ниже, чтобы закончить.</i>",
        parse_mode="HTML"
    )
    await state.set_state(AIState.waiting_for_query)
    await callback.answer()

# Хендлер для ВЫХОДА из чата (кнопка)
@router.callback_query(F.data == "ai_stop", AIState.waiting_for_query)
async def sos_ai_stop_btn(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Диалог завершен. Береги себя! ❤️", reply_markup=builders.main_menu())
    await callback.answer()

# Хендлер для ОБЩЕНИЯ (ловит текст)
@router.message(AIState.waiting_for_query)
async def process_ai_query(message: types.Message, state: FSMContext):
    # 1. Проверяем, не нажал ли юзер кнопку меню (выход)
    if message.text in ["📊 Диагностика (MBI)", "📝 Дневник", "🆘 SOS / Я киплю", "🧠 Мои Эмоции", "🧘 Ресурсы", "📋 Тест Бойко"]:
        await state.clear()
        await message.answer("Выхожу из режима AI...", reply_markup=builders.main_menu())
        return

    # 2. Проверяем команду стоп текстом
    if message.text.lower().strip() in ["стоп", "stop", "хватит", "выход"]:
        await state.clear()
        await message.answer("Диалог завершен.", reply_markup=builders.main_menu())
        return

    # 3. Подготовка запроса
    wait_msg = await message.answer("⏳ ...")
    
    # Достаем историю из памяти
    data = await state.get_data()
    history = data.get("history", [])
    
    try:
        # Передаем текст и историю в LLM
        response = await get_ai_response(
            user_text=message.text, 
            conversation_history=history
        )
        
        # Обновляем историю (добавляем пару вопрос-ответ)
        history.append({"role": "user", "content": message.text})
        history.append({"role": "assistant", "content": response})
        
        # Ограничиваем историю последними 10 сообщениями (5 пар), чтобы не переполнять память
        if len(history) > 10:
            history = history[-10:]
            
        # Сохраняем обновленную историю в State
        await state.update_data(history=history)
        
        # Клавиатура для выхода
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛑 Закончить диалог", callback_data="ai_stop")]
        ])
        
        await wait_msg.edit_text(response, reply_markup=kb)
        
    except Exception as e:
        await wait_msg.edit_text("Ошибка связи с нейросетью. Попробуй позже.")
        print(f"AI Error: {e}")
        # Не сбрасываем state, чтобы можно было попробовать еще раз
