import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.database.supabase_client import db
from src.keyboards import builders
from src.states import TrackerStates
from src.services.llm import generate_weekly_narrative, generate_cross_test_comment

logger = logging.getLogger(__name__)
router = Router()


# ── СТАРТ ДНЕВНИКА ────────────────────────────────────────────────────────────

@router.message(F.text == "📝 Дневник")
async def start_tracker(message: types.Message, state: FSMContext):
    await state.set_state(TrackerStates.energy)

    b = InlineKeyboardBuilder()
    for i in range(1, 11):
        b.button(text=str(i), callback_data=f"energy_{i}")
    b.adjust(5)

    await message.answer(
        "⚡️ <b>Как твой уровень энергии прямо сейчас?</b>\n\n"
        "1 — пустой, 10 — на подъёме",
        reply_markup=b.as_markup(),
        parse_mode="HTML"
    )


# ── ЭНЕРГИЯ ───────────────────────────────────────────────────────────────────

@router.callback_query(TrackerStates.energy, F.data.startswith("energy_"))
async def save_energy(callback: types.CallbackQuery, state: FSMContext):
    energy_level = int(callback.data.split("_")[1])
    await state.update_data(energy=energy_level)
    await state.set_state(TrackerStates.emotion)

    emotions = ["Радость", "Доверие", "Страх", "Удивление", "Грусть", "Неудовольствие", "Гнев", "Ожидание"]
    b = InlineKeyboardBuilder()
    for emo in emotions:
        b.button(text=emo, callback_data=f"emo_{emo}")
    b.adjust(2)

    await callback.message.edit_text(
        f"Записал: <b>{energy_level}/10</b>.\n\n"
        f"Теперь выбери <b>главную эмоцию</b> момента:",
        reply_markup=b.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# ── ЭМОЦИЯ ───────────────────────────────────────────────────────────────────

@router.callback_query(TrackerStates.emotion, F.data.startswith("emo_"))
async def save_emotion(callback: types.CallbackQuery, state: FSMContext):
    emotion = callback.data.split("_", 1)[1]
    await state.update_data(emotion=emotion)
    await state.set_state(TrackerStates.gratitude)

    await callback.message.edit_text(
        f"Эмоция: <b>{emotion}</b> ✓\n\n"
        f"💛 <b>Последний вопрос:</b> назови одно хорошее, что произошло сегодня.\n"
        f"Это может быть совсем мелочь — вкусный кофе, улыбка прохожего, минута тишины.\n\n"
        f"<i>Просто напиши — или пропусти.</i>",
        reply_markup=builders.tracker_skip_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ── БЛАГОДАРНОСТЬ (текст) ─────────────────────────────────────────────────────

@router.message(TrackerStates.gratitude)
async def save_gratitude(message: types.Message, state: FSMContext):
    menu_buttons = {"📊 Диагностика", "📝 Дневник", "🆘 SOS / Я киплю",
                    "🧠 Мои Эмоции", "🧘 Ресурсы", "📈 Моя динамика"}
    if message.text in menu_buttons:
        await state.clear()
        return

    data = await state.get_data()
    await state.clear()

    gratitude = message.text.strip()
    await db.save_daily_log(
        tg_id=message.from_user.id,
        energy=data["energy"],
        emotion=data["emotion"],
        gratitude=gratitude
    )

    await _send_tracker_result(message, data["energy"], data["emotion"], gratitude)
    await _check_energy_pattern(message, data["energy"])


# ── БЛАГОДАРНОСТЬ (пропуск) ───────────────────────────────────────────────────

@router.callback_query(TrackerStates.gratitude, F.data == "tracker_skip_gratitude")
async def skip_gratitude(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    await db.save_daily_log(
        tg_id=callback.from_user.id,
        energy=data["energy"],
        emotion=data["emotion"],
        gratitude=None
    )

    await _send_tracker_result(callback.message, data["energy"], data["emotion"], None)
    await _check_energy_pattern(callback.message, data["energy"])
    await callback.answer()


async def _send_tracker_result(message, energy: int, emotion: str, gratitude):
    text = (
        f"✅ <b>Запись сохранена!</b>\n\n"
        f"⚡ Энергия: <b>{energy}/10</b>\n"
        f"😶 Эмоция: <b>{emotion}</b>\n"
    )
    if gratitude:
        text += f"💛 Хорошее: {gratitude}\n"

    text += "\nНаблюдаем дальше."
    await message.answer(text, parse_mode="HTML", reply_markup=builders.main_menu())


async def _check_energy_pattern(message, current_energy: int):
    """Если 3+ дня подряд энергия ≤ 3 — предложить помощь."""
    if current_energy > 3:
        return
    try:
        recent = await db.get_recent_energy(message.chat.id, days=3)
        if recent and len(recent) >= 3 and all(e <= 3 for e in recent):
            await message.answer(
                "💙 Замечаю, что несколько дней тебе тяжело.\n\n"
                "Это важный сигнал. Хочешь — поговори с AI или пройди короткий тест.",
                reply_markup=builders.sos_prolonged_keyboard()
            )
    except Exception as e:
        logger.warning(f"Energy pattern check failed: {e}")


# ── ДИНАМИКА ─────────────────────────────────────────────────────────────────

@router.message(F.text == "📈 Моя динамика")
async def show_dynamics(message: types.Message):
    try:
        logs = await db.get_recent_logs(message.from_user.id, days=7)
    except Exception as e:
        logger.error(f"get_recent_logs error: {e}")
        await message.answer("Не удалось загрузить данные. Попробуй позже.")
        return

    if not logs:
        await message.answer(
            "📈 Пока нет записей.\n\nЗаполни дневник — это займёт 20 секунд.",
            reply_markup=builders.main_menu()
        )
        return

    # Базовая статистика
    energies = [r["energy_level"] for r in logs if r.get("energy_level")]
    emotions = [r["emotion"] for r in logs if r.get("emotion")]
    avg_energy = round(sum(energies) / len(energies), 1) if energies else "—"
    top_emotion = max(set(emotions), key=emotions.count) if emotions else "—"

    lines = [f"📈 <b>Динамика за 7 дней</b>\n"]
    lines.append(f"⚡ Средняя энергия: <b>{avg_energy}/10</b>")
    lines.append(f"😶 Чаще всего: <b>{top_emotion}</b>\n")

    for row in logs[:7]:
        date = str(row.get("created_at", ""))[:10]
        e = row.get("energy_level", "?")
        emo = row.get("emotion", "?")
        grat = row.get("gratitude", "")
        line = f"• {date} — {e}/10, {emo}"
        if grat:
            line += f" 💛 {grat[:40]}"
        lines.append(line)

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=builders.main_menu())

    # Недельный нарратив от LLM — отдельным сообщением
    if len(logs) >= 3:
        wait_msg = await message.answer("🔍 <i>Анализирую твою неделю...</i>", parse_mode="HTML")
        try:
            narrative = await generate_weekly_narrative(logs)
            if narrative:
                await wait_msg.edit_text(
                    f"🧠 <b>Наблюдение недели:</b>\n\n{narrative}",
                    parse_mode="HTML"
                )
            else:
                await wait_msg.delete()
        except Exception as e:
            logger.warning(f"Weekly narrative error: {e}")
            await wait_msg.delete()

    # Кросс-тест паттерн
    try:
        pattern = await db.get_cross_test_pattern(message.from_user.id)
        if pattern:
            latest_tests = await db.get_latest_test_results(message.from_user.id)
            comment = await generate_cross_test_comment(pattern, latest_tests)
            if comment:
                await message.answer(
                    f"📊 <b>Общая картина по тестам:</b>\n\n{comment}",
                    parse_mode="HTML"
                )
    except Exception as e:
        logger.warning(f"Cross-test pattern error: {e}")
