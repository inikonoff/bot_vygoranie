import json
import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from src.keyboards import builders
from src.services.scoring import calculate_mbi, calculate_boyko, calculate_phq9, calculate_gad7, calculate_pss10
from src.services.llm import analyze_mbi, analyze_boyko, analyze_phq9_gad7, analyze_pss10, generate_cross_test_comment
from src.database.supabase_client import db
from src.states import TestStates

logger = logging.getLogger(__name__)
router = Router()


# ── ЗАГРУЗКА ВОПРОСОВ ────────────────────────────────────────────────────────

def _load_json(path: str) -> list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Не удалось загрузить {path}: {e}")
        return []


MBI_QUESTIONS   = _load_json("data/mbi_test.json")
BOYKO_QUESTIONS = _load_json("data/boyko_test.json")
PHQ9_QUESTIONS  = _load_json("data/phq9_test.json")
GAD7_QUESTIONS  = _load_json("data/gad7_test.json")
PSS10_QUESTIONS = _load_json("data/pss10_test.json")


async def _maybe_show_cross_pattern(message_or_callback, user_id: int):
    """
    После сохранения любого теста проверяем общий паттерн.
    Если есть тревожное пересечение — показываем сводный комментарий.
    """
    try:
        pattern = await db.get_cross_test_pattern(user_id)
        if not pattern:
            return
        latest_tests = await db.get_latest_test_results(user_id)
        # Нужно минимум 2 разных теста чтобы был смысл в сводке
        if len(latest_tests) < 2:
            return
        comment = await generate_cross_test_comment(pattern, latest_tests)
        if not comment:
            return

        send = (
            message_or_callback.message.answer
            if hasattr(message_or_callback, "message")
            else message_or_callback.answer
        )
        await send(
            f"📊 <b>Общая картина:</b>\n\n{comment}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Cross-pattern check error: {e}")


# ── ВХОД В ДИАГНОСТИКУ ───────────────────────────────────────────────────────

@router.message(F.text == "📊 Диагностика")
@router.message(Command("mbi"))
async def diagnostics_menu(message: types.Message):
    await message.answer(
        "🧪 <b>Диагностика</b>\n\n"
        "Выбери тест. Все результаты сохраняются — ты сможешь отслеживать динамику.",
        reply_markup=builders.diagnostics_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "go_main")
async def go_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Главное меню:", reply_markup=builders.main_menu())
    await callback.answer()


# ── MBI ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "test_mbi")
async def start_mbi(callback: types.CallbackQuery, state: FSMContext):
    if not MBI_QUESTIONS:
        await callback.message.answer("⚠️ Файл с вопросами MBI не найден.")
        await callback.answer()
        return

    await state.set_state(TestStates.mbi_q)
    await state.update_data(q_index=0, answers={})
    q = MBI_QUESTIONS[0]
    await callback.message.edit_text(
        f"<b>Тест MBI — вопрос 1/{len(MBI_QUESTIONS)}</b>\n\n"
        f"{q['text']}\n\n<i>0 — Никогда, 6 — Каждый день</i>",
        reply_markup=builders.scale_keyboard_mbi(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(TestStates.mbi_q, F.data.startswith("mbi_"))
async def process_mbi(callback: types.CallbackQuery, state: FSMContext):
    score = int(callback.data.split("_")[1])
    data = await state.get_data()
    idx = data["q_index"]
    answers = data["answers"]
    answers[idx + 1] = score
    next_idx = idx + 1

    if next_idx < len(MBI_QUESTIONS):
        await state.update_data(q_index=next_idx, answers=answers)
        q = MBI_QUESTIONS[next_idx]
        await callback.message.edit_text(
            f"<b>Тест MBI — вопрос {next_idx + 1}/{len(MBI_QUESTIONS)}</b>\n\n"
            f"{q['text']}\n\n<i>0 — Никогда, 6 — Каждый день</i>",
            reply_markup=builders.scale_keyboard_mbi(),
            parse_mode="HTML"
        )
    else:
        await state.clear()
        result = calculate_mbi(answers)
        risk = await db.save_test_result(callback.from_user.id, "mbi", result)

        summary = (
            f"🏁 <b>MBI завершён</b>\n\n"
            f"🔥 Истощение: <b>{result['ee']}</b>/54 (норма &lt; 16)\n"
            f"😐 Деперсонализация: <b>{result['dp']}</b>/30 (норма &lt; 6)\n"
            f"📉 Редукция: <b>{result['pa']}</b>/48 (норма &gt; 36)\n\n"
            f"⏳ <i>Готовлю развёрнутый анализ...</i>"
        )
        msg = await callback.message.edit_text(summary, parse_mode="HTML")

        analysis = await analyze_mbi(result)
        if analysis:
            await msg.edit_text(
                f"🏁 <b>MBI завершён</b>\n\n"
                f"🔥 Истощение: <b>{result['ee']}</b>/54 · "
                f"😐 Деперсонализация: <b>{result['dp']}</b>/30 · "
                f"📉 Редукция: <b>{result['pa']}</b>/48\n\n"
                f"──────────────────\n\n{analysis}",
                parse_mode="HTML",
                reply_markup=builders.offer_phq9_keyboard() if risk == "red" else builders.back_to_main()
            )
        else:
            await msg.edit_text(
                summary.replace("⏳ <i>Готовлю развёрнутый анализ...</i>", ""),
                parse_mode="HTML",
                reply_markup=builders.offer_phq9_keyboard() if risk == "red" else builders.back_to_main()
            )

        await _maybe_show_cross_pattern(callback, callback.from_user.id)

    await callback.answer()


# ── БОЙКО ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "test_boyko")
async def start_boyko(callback: types.CallbackQuery, state: FSMContext):
    if not BOYKO_QUESTIONS:
        await callback.message.answer("⚠️ Файл с вопросами теста Бойко не найден.")
        await callback.answer()
        return

    await state.set_state(TestStates.boyko_q)
    await state.update_data(q_index=0, answers={})
    q = BOYKO_QUESTIONS[0]
    await callback.message.edit_text(
        f"<b>Тест Бойко — вопрос 1/{len(BOYKO_QUESTIONS)}</b>\n\n{q['text']}",
        reply_markup=builders.yes_no_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(TestStates.boyko_q, F.data.startswith("boyko_"))
async def process_boyko(callback: types.CallbackQuery, state: FSMContext):
    choice = 1 if callback.data == "boyko_yes" else 0
    data = await state.get_data()
    idx = data["q_index"]
    answers = data["answers"]
    answers[idx + 1] = choice
    next_idx = idx + 1

    if next_idx < len(BOYKO_QUESTIONS):
        await state.update_data(q_index=next_idx, answers=answers)
        q = BOYKO_QUESTIONS[next_idx]
        await callback.message.edit_text(
            f"<b>Тест Бойко — вопрос {next_idx + 1}/{len(BOYKO_QUESTIONS)}</b>\n\n{q['text']}",
            reply_markup=builders.yes_no_keyboard(),
            parse_mode="HTML"
        )
    else:
        await state.clear()
        result = calculate_boyko(answers)
        await db.save_test_result(callback.from_user.id, "boyko", result)

        summary = (
            f"🏁 <b>Тест Бойко завершён</b>\n\n"
            f"😬 Напряжение: <b>{result['tension']}</b> — {result['tension_status']}\n"
            f"🛡 Резистенция: <b>{result['resistance']}</b> — {result['resistance_status']}\n"
            f"🔋 Истощение: <b>{result['exhaustion']}</b> — {result['exhaustion_status']}\n\n"
            f"⏳ <i>Готовлю развёрнутый анализ...</i>"
        )
        msg = await callback.message.edit_text(summary, parse_mode="HTML")

        analysis = await analyze_boyko(result)
        if analysis:
            is_severe = result["exhaustion_status"] == "сложилась"
            await msg.edit_text(
                f"🏁 <b>Тест Бойко завершён</b>\n\n"
                f"😬 {result['tension']} · 🛡 {result['resistance']} · 🔋 {result['exhaustion']}\n\n"
                f"──────────────────\n\n{analysis}",
                parse_mode="HTML",
                reply_markup=builders.offer_sos_after_test_keyboard() if is_severe else builders.back_to_main()
            )

        await _maybe_show_cross_pattern(callback, callback.from_user.id)

    await callback.answer()


# ── PHQ-9 + GAD-7 ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "test_phq9_gad7")
async def start_phq9(callback: types.CallbackQuery, state: FSMContext):
    if not PHQ9_QUESTIONS:
        await callback.message.answer("⚠️ Файл с вопросами PHQ-9 не найден.")
        await callback.answer()
        return

    await state.set_state(TestStates.phq9_q)
    await state.update_data(q_index=0, answers={})
    q = PHQ9_QUESTIONS[0]
    await callback.message.edit_text(
        f"<b>PHQ-9 (депрессия) — вопрос 1/{len(PHQ9_QUESTIONS)}</b>\n\n"
        f"За последние <b>2 недели</b>, как часто вас беспокоило следующее?\n\n"
        f"{q['text']}",
        reply_markup=builders.scale_keyboard_03(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(TestStates.phq9_q, F.data.startswith("scale03_"))
async def process_phq9(callback: types.CallbackQuery, state: FSMContext):
    score = int(callback.data.split("_")[1])
    data = await state.get_data()
    idx = data["q_index"]
    answers = data["answers"]
    answers[idx + 1] = score
    next_idx = idx + 1

    if next_idx < len(PHQ9_QUESTIONS):
        await state.update_data(q_index=next_idx, answers=answers)
        q = PHQ9_QUESTIONS[next_idx]
        await callback.message.edit_text(
            f"<b>PHQ-9 — вопрос {next_idx + 1}/{len(PHQ9_QUESTIONS)}</b>\n\n{q['text']}",
            reply_markup=builders.scale_keyboard_03(),
            parse_mode="HTML"
        )
    else:
        phq9_answers = answers
        await state.set_state(TestStates.gad7_q)
        await state.update_data(phq9_answers=phq9_answers, q_index=0, answers={})

        if not GAD7_QUESTIONS:
            await _finish_phq9_only(callback, state, phq9_answers)
            return

        q = GAD7_QUESTIONS[0]
        await callback.message.edit_text(
            f"✅ PHQ-9 готов! Теперь GAD-7 — ещё 7 вопросов про тревогу.\n\n"
            f"<b>GAD-7 — вопрос 1/{len(GAD7_QUESTIONS)}</b>\n\n"
            f"За последние <b>2 недели</b>, как часто вас беспокоило следующее?\n\n"
            f"{q['text']}",
            reply_markup=builders.scale_keyboard_03(),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(TestStates.gad7_q, F.data.startswith("scale03_"))
async def process_gad7(callback: types.CallbackQuery, state: FSMContext):
    score = int(callback.data.split("_")[1])
    data = await state.get_data()
    idx = data["q_index"]
    answers = data["answers"]
    answers[idx + 1] = score
    next_idx = idx + 1

    if next_idx < len(GAD7_QUESTIONS):
        await state.update_data(q_index=next_idx, answers=answers)
        q = GAD7_QUESTIONS[next_idx]
        await callback.message.edit_text(
            f"<b>GAD-7 — вопрос {next_idx + 1}/{len(GAD7_QUESTIONS)}</b>\n\n{q['text']}",
            reply_markup=builders.scale_keyboard_03(),
            parse_mode="HTML"
        )
    else:
        await state.clear()
        phq9_result = calculate_phq9(data["phq9_answers"])
        gad7_result = calculate_gad7(answers)

        await db.save_test_result(callback.from_user.id, "phq9", phq9_result)
        await db.save_test_result(callback.from_user.id, "gad7", gad7_result)

        summary = (
            f"🏁 <b>Тесты завершены!</b>\n\n"
            f"💙 Депрессия (PHQ-9): <b>{phq9_result['total']}/27</b> — {phq9_result['label']}\n"
            f"💛 Тревога (GAD-7): <b>{gad7_result['total']}/21</b> — {gad7_result['label']}\n\n"
            f"⏳ <i>Готовлю развёрнутый анализ...</i>"
        )
        msg = await callback.message.edit_text(summary, parse_mode="HTML")

        analysis = await analyze_phq9_gad7(phq9_result, gad7_result)
        is_elevated = (
            phq9_result["level"] not in ("minimal",) or
            gad7_result["level"] not in ("minimal",)
        )

        if analysis:
            await msg.edit_text(
                f"🏁 <b>Тесты завершены</b>\n\n"
                f"💙 PHQ-9: <b>{phq9_result['total']}/27</b> — {phq9_result['label']}\n"
                f"💛 GAD-7: <b>{gad7_result['total']}/21</b> — {gad7_result['label']}\n\n"
                f"──────────────────\n\n{analysis}",
                parse_mode="HTML",
                reply_markup=builders.offer_sos_after_test_keyboard() if is_elevated else builders.back_to_main()
            )

        await _maybe_show_cross_pattern(callback, callback.from_user.id)

    await callback.answer()


async def _finish_phq9_only(callback, state, phq9_answers):
    await state.clear()
    result = calculate_phq9(phq9_answers)
    await db.save_test_result(callback.from_user.id, "phq9", result)
    await callback.message.edit_text(
        f"🏁 <b>PHQ-9 завершён</b>\n\n"
        f"💙 Депрессия: <b>{result['total']}/27</b> — {result['label']}",
        parse_mode="HTML",
        reply_markup=builders.back_to_main()
    )


# ── PSS-10 ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "test_pss10")
async def start_pss10(callback: types.CallbackQuery, state: FSMContext):
    if not PSS10_QUESTIONS:
        await callback.message.answer("⚠️ Файл с вопросами PSS-10 не найден.")
        await callback.answer()
        return

    await state.set_state(TestStates.pss10_q)
    await state.update_data(q_index=0, answers={})
    q = PSS10_QUESTIONS[0]
    await callback.message.edit_text(
        f"<b>PSS-10 — вопрос 1/{len(PSS10_QUESTIONS)}</b>\n\n"
        f"За последний <b>месяц</b>, как часто вы...\n\n{q['text']}",
        reply_markup=builders.scale_keyboard_04(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(TestStates.pss10_q, F.data.startswith("scale04_"))
async def process_pss10(callback: types.CallbackQuery, state: FSMContext):
    score = int(callback.data.split("_")[1])
    data = await state.get_data()
    idx = data["q_index"]
    answers = data["answers"]
    answers[idx + 1] = score
    next_idx = idx + 1

    if next_idx < len(PSS10_QUESTIONS):
        await state.update_data(q_index=next_idx, answers=answers)
        q = PSS10_QUESTIONS[next_idx]
        await callback.message.edit_text(
            f"<b>PSS-10 — вопрос {next_idx + 1}/{len(PSS10_QUESTIONS)}</b>\n\n{q['text']}",
            reply_markup=builders.scale_keyboard_04(),
            parse_mode="HTML"
        )
    else:
        await state.clear()
        result = calculate_pss10(answers)
        await db.save_test_result(callback.from_user.id, "pss10", result)

        summary = (
            f"🏁 <b>PSS-10 завершён</b>\n\n"
            f"🌡 Стресс: <b>{result['total']}/40</b> — {result['label']}\n\n"
            f"⏳ <i>Готовлю анализ...</i>"
        )
        msg = await callback.message.edit_text(summary, parse_mode="HTML")

        analysis = await analyze_pss10(result)
        if analysis:
            await msg.edit_text(
                f"🏁 <b>PSS-10 завершён</b>\n\n"
                f"🌡 Стресс: <b>{result['total']}/40</b> — {result['label']}\n\n"
                f"──────────────────\n\n{analysis}",
                parse_mode="HTML",
                reply_markup=builders.back_to_main()
            )

        await _maybe_show_cross_pattern(callback, callback.from_user.id)

    await callback.answer()


# ── ИСТОРИЯ ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "test_history")
async def show_test_history(callback: types.CallbackQuery):
    history = await db.get_test_history(callback.from_user.id)

    if not history:
        await callback.message.edit_text(
            "📋 Ты ещё не проходил ни одного теста.\n\nВыбери тест в меню диагностики:",
            reply_markup=builders.diagnostics_menu()
        )
        await callback.answer()
        return

    lines = ["📈 <b>Последние результаты</b>\n"]
    for row in history[:10]:
        test_type = row.get("test_type", "").upper()
        score = row.get("total_score", "?")
        created = row.get("created_at", "")[:10] if row.get("created_at") else ""
        lines.append(f"• {test_type}: <b>{score}</b> {f'({created})' if created else ''}")

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=builders.diagnostics_menu()
    )
    await callback.answer()
