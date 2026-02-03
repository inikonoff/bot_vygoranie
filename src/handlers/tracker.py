from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.database.supabase_client import db

router = Router()

class TrackerStates(StatesGroup):
    energy = State()
    emotion = State()

# 1. Нажатие на кнопку "Дневник"
@router.message(F.text == "📝 Дневник")
async def start_tracker(message: types.Message, state: FSMContext):
    await state.set_state(TrackerStates.energy)
    
    # Создаем инлайн кнопки 1-10
    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.button(text=str(i), callback_data=f"energy_{i}")
    builder.adjust(5) # По 5 кнопок в ряд
    
    await message.answer(
        "⚡️ <b>Оцени свой уровень энергии</b>\n"
        "1 - Труп\n10 - Готов свернуть горы",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

# 2. Обработка энергии и запрос эмоции
@router.callback_query(TrackerStates.energy, F.data.startswith("energy_"))
async def save_energy(callback: types.CallbackQuery, state: FSMContext):
    energy_level = int(callback.data.split("_")[1])
    await state.update_data(energy=energy_level)
    
    await state.set_state(TrackerStates.emotion)
    
    # Кнопки эмоций (базовые по Плутчику из твоих PDF)
    emotions = ["Радость", "Доверие", "Страх", "Удивление", "Грусть", "Неудовольствие", "Гнев", "Ожидание"]
    builder = InlineKeyboardBuilder()
    for emo in emotions:
        builder.button(text=emo, callback_data=f"emo_{emo}")
    builder.adjust(2)
    
    await callback.message.edit_text(
        f"Записал: {energy_level}/10.\nТеперь выбери <b>ключевую эмоцию</b> момента:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

# 3. Финиш
@router.callback_query(TrackerStates.emotion, F.data.startswith("emo_"))
async def save_emotion(callback: types.CallbackQuery, state: FSMContext):
    emotion = callback.data.split("_")[1]
    data = await state.get_data()
    
    # Сохраняем в Supabase
    await db.save_daily_log(
        tg_id=callback.from_user.id,
        energy=data['energy'],
        emotion=emotion
    )
    
    await callback.message.edit_text(
        f"✅ <b>Запись сохранена!</b>\n\n"
        f"🔋 Энергия: {data['energy']}\n"
        f"😶 Эмоция: {emotion}\n\n"
        f"Продолжаем наблюдение.",
        parse_mode="HTML"
    )
    await state.clear()
