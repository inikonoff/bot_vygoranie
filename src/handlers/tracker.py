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
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )


@router.message(TrackerStates.gratitude)
async def save_gratitude(message: types.Message, state: FSMContext):
    """Сохранение благодарности и завершение"""
    gratitude = message.text.strip()
    if len(gratitude) > 200:
        gratitude = gratitude[:200] + "..."
    
    await state.update_data(gratitude=gratitude)
    await finish_tracker(message, state)


@router.callback_query(TrackerStates.gratitude, F.data == "skip_gratitude")
async def skip_gratitude(callback: types.CallbackQuery, state: FSMContext):
    """Пропуск благодарности"""
    await state.update_data(gratitude=None)
    await finish_tracker(callback.message, state, is_callback=True)
    await callback.answer()


async def finish_tracker(message: types.Message, state: FSMContext, is_callback: bool = False):
    """Завершение дневника и сохранение"""
    data = await state.get_data()
    
    # Сохраняем в Supabase
    await db.save_daily_log(
        tg_id=message.from_user.id if not is_callback else message.chat.id,
        energy=data['energy'],
        emotion=data['emotion'],
        gratitude=data.get('gratitude')
    )
    
    response = (
        f"✅ **Запись сохранена!**\n\n"
        f"🔋 Энергия: {data['energy']}/10\n"
        f"😶 Эмоция: {data['emotion']}\n"
    )
    
    if data.get('gratitude'):
        response += f"✨ Благодарность: {data['gratitude']}\n\n"
    else:
        response += "\n"
    
    response += "Продолжаем наблюдение. Завтра будет новый день!"
    
    if is_callback:
        await message.edit_text(response, parse_mode="Markdown")
        await message.edit_reply_markup(reply_markup=None)
    else:
        await message.answer(response, parse_mode="Markdown", reply_markup=builders.main_menu())
    
    await state.clear()


# ============================================================================
# ИСТОРИЯ ДНЕВНИКА
# ============================================================================

@router.message(F.text == "📈 Моя динамика")
async def show_diary_history(message: types.Message):
    """Показать историю дневника"""
    logs = await db.get_recent_daily_logs(message.from_user.id, limit=14)
    
    if not logs:
        await message.answer(
            "📭 Пока нет записей в дневнике.\n"
            "Начни с **📝 Дневник**, чтобы отслеживать состояние.",
            reply_markup=builders.main_menu()
        )
        return
    
    # Статистика за последние 7 дней
    recent_logs = logs[:7]
    avg_energy = sum(log['energy_level'] for log in recent_logs) / len(recent_logs)
    
    emotions = [log['emotion'] for log in recent_logs if log.get('emotion')]
    emotion_stats = ""
    if emotions:
        top_emotions = Counter(emotions).most_common(3)
        emotion_stats = "🎭 **Топ эмоций:**\n"
        for emo, count in top_emotions:
            percentage = (count / len(recent_logs)) * 100
            emotion_stats += f"  • {emo}: {count} раз ({percentage:.0f}%)\n"
    
    gratitude_count = sum(1 for log in recent_logs if log.get('gratitude'))
    
    text = f"📊 **Динамика за {len(recent_logs)} дней**\n\n"
    text += f"📈 Средняя энергия: {avg_energy:.1f}/10\n"
    text += emotion_stats
    text += f"✨ Дней с благодарностью: {gratitude_count}\n\n"
    
    text += "📅 **Последние записи:**\n"
    for log in recent_logs[:7]:
        date = log.get('created_at', '')[:10] if log.get('created_at') else 'недавно'
        gratitude_mark = " ✨" if log.get('gratitude') else ""
        text += f"• {date}: {log['energy_level']}/10, {log.get('emotion', '—')}{gratitude_mark}\n"
    
    # Проверка на паттерн: 3 дня подряд энергия ≤ 3
    low_energy_days = sum(1 for log in logs[:3] if log['energy_level'] <= 3)
    if low_energy_days >= 3:
        text += "\n⚠️ **Замечаю, что несколько дней тебе тяжело.**\n"
        text += "Хочешь поговорить или пройти короткий тест?"
        
        kb = InlineKeyboardBuilder()
        kb.button(text="🤖 Поговорить с AI", callback_data="sos_ai_chat")
        kb.button(text="🧠 PHQ-9 (депрессия)", callback_data="diag_phq9")
        kb.adjust(1)
        
        await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    else:
        await message.answer(text, parse_mode="Markdown")
