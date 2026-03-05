import logging
from collections import Counter
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.database.supabase_client import db
from src.states import TrackerStates
from src.keyboards import builders

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "📝 Дневник")
@router.message(Command("diary"))
async def start_tracker(message: types.Message, state: FSMContext):
    """Начало заполнения дневника"""
    await state.set_state(TrackerStates.energy)
    
    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.button(text=str(i), callback_data=f"energy_{i}")
    builder.adjust(5)
    
    await message.answer(
        "⚡️ **Оцени свой уровень энергии**\n"
        "1 - Совсем нет сил\n"
        "10 - Готов свернуть горы",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )


@router.callback_query(TrackerStates.energy, F.data.startswith("energy_"))
async def save_energy(callback: types.CallbackQuery, state: FSMContext):
    """Сохранение энергии и запрос эмоции"""
    energy_level = int(callback.data.split("_")[1])
    await state.update_data(energy=energy_level)
    
    await state.set_state(TrackerStates.emotion)
    
    emotions = ["😊 Радость", "🤝 Доверие", "😨 Страх", "😲 Удивление", 
                "😢 Грусть", "😠 Неудовольствие", "😤 Гнев", "🤔 Ожидание"]
    
    builder = InlineKeyboardBuilder()
    for emo in emotions:
        clean_emo = emo.split()[1] if ' ' in emo else emo
        builder.button(text=emo, callback_data=f"emo_{clean_emo}")
    builder.adjust(2)
    
    await callback.message.edit_text(
        f"Записал: {energy_level}/10.\n\nТеперь выбери **ключевую эмоцию** момента:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )


@router.callback_query(TrackerStates.emotion, F.data.startswith("emo_"))
async def save_emotion(callback: types.CallbackQuery, state: FSMContext):
    """Сохранение эмоции и запрос благодарности"""
    emotion = callback.data.split("_")[1]
    await state.update_data(emotion=emotion)
    
    await state.set_state(TrackerStates.gratitude)
    
    # Кнопка пропуска
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить", callback_data="skip_gratitude")
    
    await callback.message.edit_text(
        "✨ **Благодарность**\n\n"
        "Назови **одно хорошее**, что произошло сегодня:\n\n"
        "Это может быть что угодно:\n"
        "• вкусный кофе\n"
        "• солнце за окном\n"
        "• чья-то улыбка\n"
        "• сделанное дело\n\n"
        "Нейробиологически доказано: фиксация позитивного снижает тревогу.",
        reply_markup=builder.as
