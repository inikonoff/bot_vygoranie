import asyncio
import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from src.keyboards import builders
from src.services.llm import get_ai_response
from src.database.supabase_client import db
from src.states import AIState, AngerState, DefusionState

logger = logging.getLogger(__name__)
router = Router()


# ── ВХОД В SOS ───────────────────────────────────────────────────────────────

@router.message(F.text == "🆘 SOS / Я киплю")
@router.message(Command("sos"))
async def sos_menu(message: types.Message):
    await message.answer(
        "🆘 <b>Что сейчас происходит?</b>\n\nВыбери — и я подберу подходящее:",
        reply_markup=builders.sos_situation_keyboard(),
        parse_mode="HTML"
    )


# ── МАРШРУТ: НАКРЫЛО ВНЕЗАПНО ────────────────────────────────────────────────

@router.callback_query(F.data == "sos_sudden")
async def sos_sudden(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⚡ <b>Накрыло — понял.</b>\n\nВыбери, что попробуем прямо сейчас:",
        reply_markup=builders.sos_sudden_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ── МАРШРУТ: ДОЛГО ПЛОХО ─────────────────────────────────────────────────────

@router.callback_query(F.data == "sos_prolonged")
async def sos_prolonged(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🌑 <b>Долго плохо — это важный сигнал.</b>\n\n"
        "Когда состояние затягивается, стоит разобраться глубже. Что выберешь?",
        reply_markup=builders.sos_prolonged_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ── ТЕХНИКА STOP ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "sos_stop_technique")
async def sos_stop_step1(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⏸ <b>Техника STOP</b>\n\n"
        "<b>S — Stop.</b>\n"
        "Остановись. Буквально — замри на секунду.\n"
        "Что бы ты ни делал — паузу.\n\n"
        "Готов? Нажми «Далее».",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее →", callback_data="stop_step2")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "stop_step2")
async def sos_stop_step2(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⏸ <b>Техника STOP</b>\n\n"
        "<b>T — Take a breath.</b>\n"
        "Один медленный вдох.\n"
        "Вдох на 4 счёта... задержи... выдох на 6.\n\n"
        "Сделай прямо сейчас, потом нажми «Далее».",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Сделал →", callback_data="stop_step3")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "stop_step3")
async def sos_stop_step3(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⏸ <b>Техника STOP</b>\n\n"
        "<b>O — Observe.</b>\n"
        "Посмотри, что происходит внутри — без оценки.\n"
        "Что чувствуешь в теле? Где напряжение?\n"
        "Просто заметь, не нужно ничего менять.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Заметил →", callback_data="stop_step4")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "stop_step4")
async def sos_stop_step4(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⏸ <b>Техника STOP</b>\n\n"
        "<b>P — Proceed.</b>\n"
        "Продолжи — но осознанно.\n"
        "Выбери наилучшее действие прямо сейчас.\n\n"
        "✅ Техника завершена. Как ты?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Лучше, спасибо", callback_data="sos_done")],
            [InlineKeyboardButton(text="Хочу ещё помощи", callback_data="sos_sudden")],
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "sos_done")
async def sos_done(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Хорошо. Береги себя ❤️",
        reply_markup=builders.back_to_main()
    )
    await callback.answer()


# ── ДЫХАНИЕ ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "sos_breathe")
async def sos_breathe(callback: types.CallbackQuery):
    try:
        gif_file = FSInputFile("data/breathing.gif")
        await callback.message.answer_animation(
            animation=gif_file,
            caption=(
                "🌬 <b>Квадратное дыхание</b>\n\n"
                "1. 🟢 Вдох — 4 сек\n"
                "2. ✋ Задержка — 4 сек\n"
                "3. ⚪️ Выдох — 4 сек\n"
                "4. ✋ Задержка — 4 сек\n\n"
                "<i>Повторяй 3–4 цикла. Это активирует парасимпатику и снижает тревогу.</i>"
            ),
            parse_mode="HTML"
        )
    except Exception:
        try:
            await callback.message.answer_animation(
                animation="https://i.gifer.com/7GCO.gif",
                caption="🌬 <b>Дыши вместе с квадратом</b>\nВдох — Пауза — Выдох — Пауза (по 4 сек).",
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                "🌬 <b>Квадратное дыхание</b>\n\n"
                "Вдох 4 сек → Задержка 4 сек → Выдох 4 сек → Задержка 4 сек.\n"
                "Повторяй 3–4 цикла.",
                parse_mode="HTML"
            )
    await callback.answer()


# ── ЗАЗЕМЛЕНИЕ 5-4-3-2-1 ─────────────────────────────────────────────────────

@router.callback_query(F.data == "sos_grounding")
async def sos_grounding(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🧭 <b>Техника 5-4-3-2-1</b>\n\n"
        "Возвращает тебя из тревоги в «здесь и сейчас».\n\n"
        "Прямо сейчас назови:\n\n"
        "👁 <b>5</b> вещей, которые <b>видишь</b>\n"
        "✋ <b>4</b> вещи, которые можешь <b>потрогать</b>\n"
        "👂 <b>3</b> звука, которые <b>слышишь</b>\n"
        "👃 <b>2</b> запаха, которые <b>чувствуешь</b>\n"
        "👅 <b>1</b> вкус во рту\n\n"
        "<i>Мозг переключается с режима «угроза» на режим «изучение» — тревога снижается.</i>",
        reply_markup=builders.back_to_main(),
        parse_mode="HTML"
    )
    await callback.answer()


# ── ГНЕВ ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "sos_anger")
async def sos_anger_menu(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔥 <b>Техника сброса гнева</b>\n\n"
        "Напиши сюда всё, что тебя бесит. Не стесняйся в выражениях.\n"
        "Я приму это — и мы его ментально «сожжём».\n\n"
        "Пиши прямо сейчас:",
        parse_mode="HTML"
    )
    await state.set_state(AngerState.venting)
    await callback.answer()


@router.message(AngerState.venting)
async def process_anger(message: types.Message, state: FSMContext):
    msg = await message.reply("🔥🔥🔥 Сжигаю этот негатив...")
    await asyncio.sleep(1.5)
    await msg.edit_text(
        "🗑 Пепел развеян.\n\n"
        "Сделай глубокий вдох. Как ты сейчас?\n\n"
        "Хочешь разобрать мысль, которая за этим стоит?",
        reply_markup=builders.sos_after_anger_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "sos_main_menu")
async def sos_to_main(callback: types.CallbackQuery):
    await callback.message.answer("Главное меню:", reply_markup=builders.main_menu())
    await callback.answer()


# ── КОГНИТИВНОЕ РАЗДЕЛЕНИЕ (ДЕФЬЮЗИНГ) ──────────────────────────────────────

@router.callback_query(F.data == "sos_defusion")
async def sos_defusion_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🧠 <b>Техника когнитивного разделения</b>\n\n"
        "Негативные мысли теряют власть, когда мы замечаем их со стороны.\n\n"
        "Напиши мысль, которая тебя мучает — одним предложением.\n"
        "<i>Например: «Я недостаточно хорош» или «Всё бессмысленно»</i>",
        parse_mode="HTML"
    )
    await state.set_state(DefusionState.waiting_for_thought)
    await callback.answer()


@router.message(DefusionState.waiting_for_thought)
async def process_defusion(message: types.Message, state: FSMContext):
    thought = message.text.strip()
    await state.clear()

    await message.answer(
        f"🧠 <b>Теперь попробуй сказать это так:</b>\n\n"
        f"<i>«Я замечаю, что у меня есть мысль, что {thought.lower()}»</i>\n\n"
        f"──────────────────\n\n"
        f"Почувствуй разницу.\n\n"
        f"Первая версия — это ты. Вторая — это просто мысль, которая пришла и уйдёт.\n"
        f"Ты не обязан с ней соглашаться или бороться. Просто заметь её — как облако на небе.",
        parse_mode="HTML",
        reply_markup=builders.back_to_main()
    )


# ── БЕЗОПАСНОЕ МЕСТО ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "sos_safe_place")
async def sos_safe_place(callback: types.CallbackQuery):
    try:
        audio = FSInputFile("data/safe_place.mp3")
        await callback.message.answer_audio(
            audio,
            caption=(
                "🎧 <b>Практика: Безопасное место</b>\n\n"
                "Найди тихое место, закрой глаза и слушай.\n"
                "Эта практика поможет снизить тревогу и восстановить внутреннюю опору."
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"safe_place.mp3 not found: {e}")
        await callback.message.edit_text(
            "🧘 <b>Практика: Безопасное место</b>\n\n"
            "Сделай несколько глубоких вдохов.\n\n"
            "Представь место, где тебе абсолютно спокойно и безопасно.\n\n"
            "Осмотрись: что ты видишь? Какие цвета вокруг?\n"
            "Что слышишь? Птицы, тишина, шум воды?\n\n"
            "Побудь здесь несколько минут. Запомни это ощущение.",
            parse_mode="HTML",
            reply_markup=builders.back_to_main()
        )
    await callback.answer()


# ── AI-ЧАТ ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "sos_ai_chat")
async def sos_ai_start(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    # Подгружаем контекст пользователя из БД
    user_context = await db.build_user_context(user_id)

    await state.update_data(history=[], user_context=user_context)
    await state.set_state(AIState.waiting_for_query)

    await callback.message.answer(
        "🤖 <b>AI-психолог на связи</b>\n\n"
        "Напиши, что тебя беспокоит. Я здесь, чтобы выслушать и поддержать.\n\n"
        "<i>Напиши «стоп» или нажми кнопку ниже, чтобы закончить.</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "ai_stop", AIState.waiting_for_query)
async def sos_ai_stop(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "Диалог завершён. Береги себя ❤️",
        reply_markup=builders.main_menu()
    )
    await callback.answer()


@router.message(AIState.waiting_for_query)
async def process_ai_query(message: types.Message, state: FSMContext):
    menu_buttons = {"📊 Диагностика", "📝 Дневник", "🆘 SOS / Я киплю",
                    "🧠 Мои Эмоции", "🧘 Ресурсы", "📈 Моя динамика"}
    if message.text in menu_buttons:
        await state.clear()
        await message.answer("Выхожу из режима AI...", reply_markup=builders.main_menu())
        return

    if message.text.lower().strip() in ("стоп", "stop", "хватит", "выход"):
        await state.clear()
        await message.answer("Диалог завершён.", reply_markup=builders.main_menu())
        return

    wait_msg = await message.answer("⏳ ...")
    data = await state.get_data()
    history = data.get("history", [])
    user_context = data.get("user_context", "")

    try:
        response = await get_ai_response(
            user_text=message.text,
            user_context=user_context,
            conversation_history=history
        )

        history.append({"role": "user", "content": message.text})
        history.append({"role": "assistant", "content": response})
        if len(history) > 20:
            history = history[-20:]

        await state.update_data(history=history)
        await wait_msg.edit_text(response, reply_markup=builders.ai_chat_stop_keyboard())

    except Exception as e:
        logger.error(f"AI chat error: {e}", exc_info=True)
        await wait_msg.edit_text("Ошибка связи с нейросетью. Попробуй позже.")
