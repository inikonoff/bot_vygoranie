import json
import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from src.keyboards import builders
from src.services.scoring import (
    calculate_mbi, calculate_boyko,
    calculate_phq9, calculate_gad7,
    calculate_pss10, calculate_uwes, calculate_osipov,
)
from src.services.llm import (
    analyze_mbi, analyze_boyko,
    analyze_phq9_gad7, analyze_pss10,
    analyze_uwes_pss10, analyze_osipov,
    generate_cross_test_comment,
)
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


MBI_QUESTIONS    = _load_json("data/mbi_test.json")
BOYKO_QUESTIONS  = _load_json("data/boyko_test.json")
PHQ9_QUESTIONS   = _load_json("data/phq9_test.json")
GAD7_QUESTIONS   = _load_json("data/gad7_test.json")
PSS10_QUESTIONS  = _load_json("data/pss10_test.json")
UWES_QUESTIONS   = _load_json("data/uwes_test.json")
OSIPOV_QUESTIONS = _load_json("data/osipov_test.json")

# Связки: порядок тестов внутри каждой
BUNDLES = {
    "bundle_burnout": ["mbi", "boyko"],
    "bundle_energy":  ["uwes", "pss10"],
    "bundle_anxiety": ["phq9_gad7"],
    "bundle_work":    ["osipov"],
    "bundle_full":    ["mbi", "boyko", "uwes", "pss10", "phq9_gad7", "osipov"],
}


# ── ВХОД В ДИАГНОСТИКУ ───────────────────────────────────────────────────────

@router.message(F.text == "📊 Диагностика")
@router.message(Command("diagnostics"))
async def diagnostics_menu(message: types.Message):
    await message.answer(
        builders.DIAGNOSTICS_DESCRIPTION,
        reply_markup=builders.diagnostics_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "go_diagnostics")
async def go_diagnostics(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        builders.DIAGNOSTICS_DESCRIPTION,
        reply_markup=builders.diagnostics_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "go_main")
async def go_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Главное меню:", reply_markup=builders.main_menu())
    await callback.answer()


# ── ЗАПУСК СВЯЗКИ ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("bundle_"))
async def start_bundle(callback: types.CallbackQuery, state: FSMContext):
    bundle_key = callback.data
    tests = BUNDLES.get(bundle_key, [])
    if not tests:
        await callback.answer("Связка не найдена", show_alert=True)
        return

    await state.update_data(bundle=bundle_key, bundle_tests=tests, bundle_results={})
    await callback.answer()
    await _start_next_test(callback.message, state, edit=True)


async def _start_next_test(message, state: FSMContext, edit: bool = False):
    """Запускает следующий тест в очереди связки."""
    data = await state.get_data()
    tests = data.get("bundle_tests", [])

    if not tests:
        await _finish_bundle(message, state)
        return

    current = tests[0]
    await state.update_data(bundle_tests=tests[1:])

    starters = {
        "mbi":      _launch_mbi,
        "boyko":    _launch_boyko,
        "phq9_gad7": _launch_phq9,
        "pss10":    _launch_pss10,
        "uwes":     _launch_uwes,
        "osipov":   _launch_osipov,
    }
    launcher = starters.get(current)
    if launcher:
        await launcher(message, state, edit=edit)


# ── MBI ──────────────────────────────────────────────────────────────────────

async def _launch_mbi(message, state: FSMContext, edit=False):
    if not MBI_QUESTIONS:
        await message.answer("⚠️ Файл MBI не найден.")
        return
    await state.set_state(TestStates.mbi_q)
    await state.update_data(q_index=0, answers={})
    q = MBI_QUESTIONS[0]
    text = (
        f"<b>MBI — вопрос 1/{len(MBI_QUESTIONS)}</b>\n\n"
        f"{q['text']}\n\n<i>0 — Никогда, 6 — Каждый день</i>"
    )
    if edit:
        await message.edit_text(text, reply_markup=builders.scale_keyboard_mbi(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=builders.scale_keyboard_mbi(), parse_mode="HTML")


@router.callback_query(TestStates.mbi_q, F.data.startswith("mbi_"))
async def process_mbi(callback: types.CallbackQuery, state: FSMContext):
    score = int(callback.data.split("_")[1])
    data = await state.get_data()
    idx = data["q_index"]
    answers = data["answers"]
    answers[str(idx + 1)] = score
    next_idx = idx + 1

    if next_idx < len(MBI_QUESTIONS):
        await state.update_data(q_index=next_idx, answers=answers)
        q = MBI_QUESTIONS[next_idx]
        await callback.message.edit_text(
            f"<b>MBI — вопрос {next_idx + 1}/{len(MBI_QUESTIONS)}</b>\n\n"
            f"{q['text']}\n\n<i>0 — Никогда, 6 — Каждый день</i>",
            reply_markup=builders.scale_keyboard_mbi(),
            parse_mode="HTML"
        )
    else:
        result = calculate_mbi(answers)
        risk = await db.save_test_result(callback.from_user.id, "mbi", result)

        bundle_results = data.get("bundle_results", {})
        bundle_results["mbi"] = result
        await state.update_data(answers={}, bundle_results=bundle_results)

        # Проверяем есть ли ещё тесты в связке
        remaining = data.get("bundle_tests", [])
        if remaining:
            summary = (
                f"✅ <b>MBI завершён</b>\n\n"
                f"🔥 Истощение: <b>{result['ee']}</b>/54 · "
                f"😐 Деперсонализация: <b>{result['dp']}</b>/30 · "
                f"📉 Редукция: <b>{result['pa']}</b>/48\n\n"
                f"⏳ <i>Следующий тест: Бойко...</i>"
            )
            msg = await callback.message.edit_text(summary, parse_mode="HTML")
            await _start_next_test(msg, state, edit=False)
        else:
            # Последний тест в связке — финальный анализ
            summary = (
                f"🏁 <b>MBI завершён</b>\n\n"
                f"🔥 Истощение: <b>{result['ee']}</b>/54 (норма &lt; 16)\n"
                f"😐 Деперсонализация: <b>{result['dp']}</b>/30 (норма &lt; 6)\n"
                f"📉 Редукция: <b>{result['pa']}</b>/48 (норма &gt; 36)\n\n"
                f"⏳ <i>Готовлю анализ...</i>"
            )
            msg = await callback.message.edit_text(summary, parse_mode="HTML")
            analysis = await analyze_mbi(result)
            if analysis:
                await msg.edit_text(
                    f"🏁 <b>MBI завершён</b>\n\n"
                    f"🔥 {result['ee']}/54 · 😐 {result['dp']}/30 · 📉 {result['pa']}/48\n\n"
                    f"──────────────────\n\n{analysis}",
                    parse_mode="HTML",
                    reply_markup=builders.offer_phq9_keyboard() if risk == "red" else builders.back_to_diagnostics()
                )

    await callback.answer()


# ── БОЙКО ────────────────────────────────────────────────────────────────────

async def _launch_boyko(message, state: FSMContext, edit=False):
    if not BOYKO_QUESTIONS:
        await message.answer("⚠️ Файл Бойко не найден.")
        return
    await state.set_state(TestStates.boyko_q)
    await state.update_data(q_index=0, answers={})
    q = BOYKO_QUESTIONS[0]
    text = f"<b>Бойко — вопрос 1/{len(BOYKO_QUESTIONS)}</b>\n\n{q['text']}"
    if edit:
        await message.edit_text(text, reply_markup=builders.yes_no_keyboard(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=builders.yes_no_keyboard(), parse_mode="HTML")


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
            f"<b>Бойко — вопрос {next_idx + 1}/{len(BOYKO_QUESTIONS)}</b>\n\n{q['text']}",
            reply_markup=builders.yes_no_keyboard(),
            parse_mode="HTML"
        )
    else:
        result = calculate_boyko(answers)
        await db.save_test_result(callback.from_user.id, "boyko", result)

        bundle_results = data.get("bundle_results", {})
        bundle_results["boyko"] = result
        await state.update_data(answers={}, bundle_results=bundle_results)

        remaining = data.get("bundle_tests", [])
        if remaining:
            summary = (
                f"✅ <b>Бойко завершён</b>\n\n"
                f"😬 {result['tension']} · 🛡 {result['resistance']} · 🔋 {result['exhaustion']}\n\n"
                f"⏳ <i>Продолжаем...</i>"
            )
            msg = await callback.message.edit_text(summary, parse_mode="HTML")
            await _start_next_test(msg, state, edit=False)
        else:
            await _finish_bundle(callback.message, state)

    await callback.answer()


# ── PHQ-9 → GAD-7 ────────────────────────────────────────────────────────────

async def _launch_phq9(message, state: FSMContext, edit=False):
    if not PHQ9_QUESTIONS:
        await message.answer("⚠️ Файл PHQ-9 не найден.")
        return
    await state.set_state(TestStates.phq9_q)
    await state.update_data(q_index=0, answers={})
    q = PHQ9_QUESTIONS[0]
    text = (
        f"<b>PHQ-9 — вопрос 1/{len(PHQ9_QUESTIONS)}</b>\n\n"
        f"За последние <b>2 недели</b>, как часто вас беспокоило следующее?\n\n{q['text']}"
    )
    if edit:
        await message.edit_text(text, reply_markup=builders.scale_keyboard_03(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=builders.scale_keyboard_03(), parse_mode="HTML")


@router.callback_query(TestStates.phq9_q, F.data.startswith("scale03_"))
async def process_phq9(callback: types.CallbackQuery, state: FSMContext):
    score = int(callback.data.split("_")[1])
    data = await state.get_data()
    idx = data["q_index"]
    answers = data["answers"]
    answers[str(idx + 1)] = score
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
        await state.set_state(TestStates.gad7_q)
        await state.update_data(phq9_answers=answers, q_index=0, answers={})
        q = GAD7_QUESTIONS[0]
        await callback.message.edit_text(
            f"✅ PHQ-9 готов! Теперь GAD-7 — ещё 7 вопросов.\n\n"
            f"<b>GAD-7 — вопрос 1/{len(GAD7_QUESTIONS)}</b>\n\n"
            f"За последние <b>2 недели</b>:\n\n{q['text']}",
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
    answers[str(idx + 1)] = score
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
        phq9_result = calculate_phq9(data["phq9_answers"])
        gad7_result = calculate_gad7(answers)
        await db.save_test_result(callback.from_user.id, "phq9", phq9_result)
        await db.save_test_result(callback.from_user.id, "gad7", gad7_result)

        bundle_results = data.get("bundle_results", {})
        bundle_results["phq9"] = phq9_result
        bundle_results["gad7"] = gad7_result
        await state.update_data(answers={}, bundle_results=bundle_results)

        remaining = data.get("bundle_tests", [])
        if remaining:
            summary = (
                f"✅ <b>PHQ-9 + GAD-7 завершены</b>\n\n"
                f"💙 {phq9_result['total']}/27 · 💛 {gad7_result['total']}/21\n\n"
                f"⏳ <i>Продолжаем...</i>"
            )
            msg = await callback.message.edit_text(summary, parse_mode="HTML")
            await _start_next_test(msg, state, edit=False)
        else:
            await _finish_bundle(callback.message, state)

    await callback.answer()


# ── PSS-10 ────────────────────────────────────────────────────────────────────

async def _launch_pss10(message, state: FSMContext, edit=False):
    if not PSS10_QUESTIONS:
        await message.answer("⚠️ Файл PSS-10 не найден.")
        return
    await state.set_state(TestStates.pss10_q)
    await state.update_data(q_index=0, answers={})
    q = PSS10_QUESTIONS[0]
    text = (
        f"<b>PSS-10 — вопрос 1/{len(PSS10_QUESTIONS)}</b>\n\n"
        f"За последний <b>месяц</b>, как часто вы...\n\n{q['text']}"
    )
    if edit:
        await message.edit_text(text, reply_markup=builders.scale_keyboard_04(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=builders.scale_keyboard_04(), parse_mode="HTML")


@router.callback_query(TestStates.pss10_q, F.data.startswith("scale04_"))
async def process_pss10(callback: types.CallbackQuery, state: FSMContext):
    score = int(callback.data.split("_")[1])
    data = await state.get_data()
    idx = data["q_index"]
    answers = data["answers"]
    answers[str(idx + 1)] = score
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
        result = calculate_pss10(answers)
        await db.save_test_result(callback.from_user.id, "pss10", result)

        bundle_results = data.get("bundle_results", {})
        bundle_results["pss10"] = result
        await state.update_data(answers={}, bundle_results=bundle_results)

        remaining = data.get("bundle_tests", [])
        if remaining:
            summary = (
                f"✅ <b>PSS-10 завершён</b>\n\n"
                f"🌡 {result['total']}/40 — {result['label']}\n\n"
                f"⏳ <i>Продолжаем...</i>"
            )
            msg = await callback.message.edit_text(summary, parse_mode="HTML")
            await _start_next_test(msg, state, edit=False)
        else:
            await _finish_bundle(callback.message, state)

    await callback.answer()


# ── UWES ─────────────────────────────────────────────────────────────────────

async def _launch_uwes(message, state: FSMContext, edit=False):
    if not UWES_QUESTIONS:
        await message.answer("⚠️ Файл UWES не найден.")
        return
    await state.set_state(TestStates.uwes_q)
    await state.update_data(q_index=0, answers={})
    q = UWES_QUESTIONS[0]
    text = (
        f"<b>UWES — вопрос 1/{len(UWES_QUESTIONS)}</b>\n\n"
        f"Как часто у тебя возникает это ощущение <b>на работе</b>?\n\n{q['text']}"
    )
    if edit:
        await message.edit_text(text, reply_markup=builders.scale_keyboard_uwes(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=builders.scale_keyboard_uwes(), parse_mode="HTML")


@router.callback_query(TestStates.uwes_q, F.data.startswith("uwes_"))
async def process_uwes(callback: types.CallbackQuery, state: FSMContext):
    score = int(callback.data.split("_")[1])
    data = await state.get_data()
    idx = data["q_index"]
    answers = data["answers"]
    answers[idx + 1] = score
    next_idx = idx + 1

    if next_idx < len(UWES_QUESTIONS):
        await state.update_data(q_index=next_idx, answers=answers)
        q = UWES_QUESTIONS[next_idx]
        await callback.message.edit_text(
            f"<b>UWES — вопрос {next_idx + 1}/{len(UWES_QUESTIONS)}</b>\n\n"
            f"Как часто у тебя возникает это ощущение <b>на работе</b>?\n\n{q['text']}",
            reply_markup=builders.scale_keyboard_uwes(),
            parse_mode="HTML"
        )
    else:
        result = calculate_uwes(answers, UWES_QUESTIONS)
        await db.save_test_result(callback.from_user.id, "uwes", result)

        bundle_results = data.get("bundle_results", {})
        bundle_results["uwes"] = result
        await state.update_data(answers={}, bundle_results=bundle_results)

        remaining = data.get("bundle_tests", [])
        if remaining:
            summary = (
                f"✅ <b>UWES завершён</b>\n\n"
                f"⚡ Энергичность: {result['vigor_level']} · "
                f"🔥 Энтузиазм: {result['dedication_level']} · "
                f"🎯 Поглощённость: {result['absorption_level']}\n\n"
                f"⏳ <i>Продолжаем...</i>"
            )
            msg = await callback.message.edit_text(summary, parse_mode="HTML")
            await _start_next_test(msg, state, edit=False)
        else:
            await _finish_bundle(callback.message, state)

    await callback.answer()


# ── ОСИПОВ ───────────────────────────────────────────────────────────────────

async def _launch_osipov(message, state: FSMContext, edit=False):
    if not OSIPOV_QUESTIONS:
        await message.answer("⚠️ Файл Осипова не найден.")
        return
    await state.set_state(TestStates.osipov_q)
    await state.update_data(q_index=0, answers={})
    q = OSIPOV_QUESTIONS[0]
    text = (
        f"<b>Рабочая среда — вопрос 1/{len(OSIPOV_QUESTIONS)}</b>\n\n"
        f"Оцени насколько это утверждение верно для твоей работы:\n\n{q['text']}"
    )
    if edit:
        await message.edit_text(text, reply_markup=builders.scale_keyboard_osipov(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=builders.scale_keyboard_osipov(), parse_mode="HTML")


@router.callback_query(TestStates.osipov_q, F.data.startswith("osipov_"))
async def process_osipov(callback: types.CallbackQuery, state: FSMContext):
    score = int(callback.data.split("_")[1])
    data = await state.get_data()
    idx = data["q_index"]
    answers = data["answers"]
    answers[idx + 1] = score
    next_idx = idx + 1

    if next_idx < len(OSIPOV_QUESTIONS):
        await state.update_data(q_index=next_idx, answers=answers)
        q = OSIPOV_QUESTIONS[next_idx]
        await callback.message.edit_text(
            f"<b>Рабочая среда — вопрос {next_idx + 1}/{len(OSIPOV_QUESTIONS)}</b>\n\n"
            f"Оцени насколько это утверждение верно для твоей работы:\n\n{q['text']}",
            reply_markup=builders.scale_keyboard_osipov(),
            parse_mode="HTML"
        )
    else:
        result = calculate_osipov(answers, OSIPOV_QUESTIONS)
        await db.save_test_result(callback.from_user.id, "osipov", result)

        bundle_results = data.get("bundle_results", {})
        bundle_results["osipov"] = result
        await state.update_data(answers={}, bundle_results=bundle_results)

        remaining = data.get("bundle_tests", [])
        if remaining:
            summary = (
                f"✅ <b>Рабочая среда завершена</b>\n\n"
                f"🏢 Общий уровень: {result['total_level']} · "
                f"⚠️ Слабое место: {result['worst_scale']}\n\n"
                f"⏳ <i>Продолжаем...</i>"
            )
            msg = await callback.message.edit_text(summary, parse_mode="HTML")
            await _start_next_test(msg, state, edit=False)
        else:
            await _finish_bundle(callback.message, state)

    await callback.answer()


# ── ФИНАЛ СВЯЗКИ ─────────────────────────────────────────────────────────────

async def _finish_bundle(message, state: FSMContext):
    """Собирает результаты всей связки и отдаёт сводный анализ LLM."""
    data = await state.get_data()
    bundle_key = data.get("bundle", "")
    results = data.get("bundle_results", {})
    await state.clear()

    wait_msg = await message.answer(
        "🏁 <b>Тестирование завершено!</b>\n\n⏳ <i>Готовлю анализ...</i>",
        parse_mode="HTML"
    )

    # Одиночные связки — специализированный анализ
    if bundle_key == "bundle_burnout" and "mbi" in results and "boyko" in results:
        mbi_text = await analyze_mbi(results["mbi"])
        boyko_text = await analyze_boyko(results["boyko"])
        r_mbi = results["mbi"]
        r_boyko = results["boyko"]
        full_text = (
            f"🏁 <b>Выгорание — анализ завершён</b>\n\n"
            f"<b>MBI:</b> истощение {r_mbi['ee']}/54 · деперсонализация {r_mbi['dp']}/30 · редукция {r_mbi['pa']}/48\n"
            f"<b>Бойко:</b> напряжение {r_boyko['tension']} · резистенция {r_boyko['resistance']} · истощение {r_boyko['exhaustion']}\n\n"
            f"──────────────────\n\n"
            f"<b>🔥 MBI:</b>\n{mbi_text}\n\n"
            f"──────────────────\n\n"
            f"<b>📋 Бойко:</b>\n{boyko_text}"
        )
        is_severe = r_mbi["ee"] > 25 or r_boyko["exhaustion_status"] == "сложилась"
        await wait_msg.edit_text(
            full_text, parse_mode="HTML",
            reply_markup=builders.offer_work_env_keyboard() if is_severe else builders.back_to_diagnostics()
        )

    elif bundle_key == "bundle_energy" and "uwes" in results and "pss10" in results:
        analysis = await analyze_uwes_pss10(results["uwes"], results["pss10"])
        r_u = results["uwes"]
        r_p = results["pss10"]
        await wait_msg.edit_text(
            f"🏁 <b>Энергия и ресурс — анализ завершён</b>\n\n"
            f"⚡ UWES: {r_u['total_level']} · 🌡 PSS-10: {r_p['label']}\n\n"
            f"──────────────────\n\n{analysis}",
            parse_mode="HTML",
            reply_markup=builders.back_to_diagnostics()
        )

    elif bundle_key == "bundle_anxiety" and "phq9" in results and "gad7" in results:
        analysis = await analyze_phq9_gad7(results["phq9"], results["gad7"])
        r_p = results["phq9"]
        r_g = results["gad7"]
        is_elevated = r_p["level"] != "minimal" or r_g["level"] != "minimal"
        await wait_msg.edit_text(
            f"🏁 <b>Тревога и настроение — анализ завершён</b>\n\n"
            f"💙 PHQ-9: {r_p['total']}/27 — {r_p['label']}\n"
            f"💛 GAD-7: {r_g['total']}/21 — {r_g['label']}\n\n"
            f"──────────────────\n\n{analysis}",
            parse_mode="HTML",
            reply_markup=builders.offer_sos_after_test_keyboard() if is_elevated else builders.back_to_diagnostics()
        )

    elif bundle_key == "bundle_work" and "osipov" in results:
        analysis = await analyze_osipov(results["osipov"])
        r = results["osipov"]
        scales_text = "\n".join(
            f"• {v['name']}: <b>{v['score']}</b> — {v['level']}"
            for v in r["scales"].values()
        )
        await wait_msg.edit_text(
            f"🏁 <b>Рабочая среда — анализ завершён</b>\n\n"
            f"{scales_text}\n\n"
            f"──────────────────\n\n{analysis}",
            parse_mode="HTML",
            reply_markup=builders.back_to_diagnostics()
        )

    else:
        # Полная диагностика — сводный кросс-анализ
        cross_comment = await generate_cross_test_comment(results)
        summary_lines = ["🏁 <b>Полная диагностика завершена</b>\n"]
        if "mbi" in results:
            r = results["mbi"]
            summary_lines.append(f"🔥 MBI: истощение {r['ee']}/54 · деперсонализация {r['dp']}/30")
        if "boyko" in results:
            r = results["boyko"]
            summary_lines.append(f"📋 Бойко: {r['tension']} / {r['resistance']} / {r['exhaustion']}")
        if "uwes" in results:
            r = results["uwes"]
            summary_lines.append(f"⚡ UWES: {r['total_level']} вовлечённость")
        if "pss10" in results:
            r = results["pss10"]
            summary_lines.append(f"🌡 PSS-10: {r['label']}")
        if "phq9" in results:
            r = results["phq9"]
            summary_lines.append(f"💙 PHQ-9: {r['label']}")
        if "gad7" in results:
            r = results["gad7"]
            summary_lines.append(f"💛 GAD-7: {r['label']}")
        if "osipov" in results:
            r = results["osipov"]
            summary_lines.append(f"🏢 Рабочая среда: {r['total_level']} (слабое место: {r['worst_scale']})")

        if cross_comment:
            summary_lines.append(f"\n──────────────────\n\n🧠 <b>Общая картина:</b>\n{cross_comment}")

        await wait_msg.edit_text(
            "\n".join(summary_lines),
            parse_mode="HTML",
            reply_markup=builders.back_to_diagnostics()
        )


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
