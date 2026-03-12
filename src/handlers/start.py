from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from src.database.supabase_client import db
from src.keyboards import builders
from src.states import OnboardingStates

router = Router()

SPHERE_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏥 Медицина / здравоохранение")],
        [KeyboardButton(text="📚 Образование / воспитание")],
        [KeyboardButton(text="💼 Бизнес / менеджмент")],
        [KeyboardButton(text="💻 IT / технологии")],
        [KeyboardButton(text="🤝 Социальная работа / НКО")],
        [KeyboardButton(text="🎨 Творческая сфера")],
        [KeyboardButton(text="🔧 Другое")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

DISCLAIMER_KB = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Понял, начнём", callback_data="disclaimer_ok"),
        InlineKeyboardButton(text="Подробнее", callback_data="disclaimer_more"),
    ]
])

SESSION_MODE_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🗣 Выговориться", callback_data="mode_support")],
    [InlineKeyboardButton(text="🔍 Разобраться в ситуации", callback_data="mode_understand")],
    [InlineKeyboardButton(text="🛠 Получить конкретные техники", callback_data="mode_tools")],
])


@router.message(CommandStart())
async def command_start(message: types.Message, state: FSMContext):
    user = message.from_user
    await db.add_user(user.id, user.first_name, user.username)

    already_onboarded = await db.is_onboarded(user.id)

    if already_onboarded:
        await message.answer(
            f"С возвращением, {user.first_name}! 👋\n\nЧем могу помочь?",
            reply_markup=builders.main_menu()
        )
        return

    await state.set_state(OnboardingStates.sphere)
    await message.answer(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я помогу отслеживать выгорание, справляться с тревогой и находить ресурс.\n\n"
        "Пара вопросов, чтобы я мог помогать точнее — займёт 30 секунд.\n\n"
        "<b>В какой сфере ты работаешь?</b>",
        reply_markup=SPHERE_KB,
        parse_mode="HTML"
    )


@router.message(OnboardingStates.sphere)
async def onboarding_sphere(message: types.Message, state: FSMContext):
    await state.update_data(sphere=message.text.strip())
    await state.set_state(OnboardingStates.request)
    await message.answer(
        "Хорошо. Последний вопрос:\n\n"
        "<b>С чем тебе сейчас нужна помощь?</b>\n\n"
        "Можешь написать своими словами — одно предложение.",
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="HTML"
    )


@router.message(OnboardingStates.request)
async def onboarding_request(message: types.Message, state: FSMContext):
    main_request = message.text.strip()
    data = await state.get_data()
    sphere = data.get("sphere", "")

    await state.clear()
    await db.save_onboarding(message.from_user.id, sphere, main_request)

    await message.answer(
        "Записал. Теперь я буду понимать тебя лучше.\n\n"
        "📊 <b>Диагностика</b> — тесты MBI, Бойко, PHQ-9, GAD-7, PSS-10\n"
        "📝 <b>Дневник</b> — отслеживай энергию и эмоции каждый день\n"
        "🆘 <b>SOS</b> — техники быстрой помощи при тревоге и стрессе\n"
        "🧠 <b>Мои Эмоции</b> — колесо эмоций и упражнения\n"
        "📈 <b>Моя динамика</b> — анализ твоей недели\n"
        "🤖 <b>AI-психолог</b> — поговорить, когда нужна поддержка",
        reply_markup=builders.main_menu(),
        parse_mode="HTML"
    )

    await message.answer(
        "Когда захочешь поговорить с AI-психологом — важно понимать:\n\n"
        "Я работаю как психолог-практик: задаю вопросы, предлагаю техники, помогаю разобраться. "
        "Это <b>симуляция терапевтической беседы</b>, не живой специалист.\n\n"
        "Я не ставлю диагнозов и не заменяю реального психолога — "
        "но это настоящая работа, если ты готов к ней.\n\n"
        "Готов?",
        reply_markup=DISCLAIMER_KB,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "disclaimer_ok")
async def disclaimer_accepted(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Отлично. Когда будешь готов поговорить — просто напиши что-нибудь "
        "или выбери нужный раздел в меню.",
    )
    await callback.answer()


@router.callback_query(F.data == "disclaimer_more")
async def disclaimer_more(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Подробнее о том, как это работает:\n\n"
        "• Я — языковая модель, обученная на текстах по психологии и терапии\n"
        "• Я не помню предыдущие сессии между сеансами\n"
        "• Я не могу ставить диагнозы и не назначаю лечение\n"
        "• В кризисных ситуациях я всегда даю контакты живой помощи\n\n"
        "Если тебе нужна помощь прямо сейчас:\n"
        "📞 Телефон доверия: <b>8-800-2000-122</b> (бесплатно, 24/7)\n"
        "💬 Онлайн-чат: <b>pomogi.online</b>\n\n"
        "Готов начать?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да, начнём", callback_data="disclaimer_ok")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mode_"))
async def session_mode_selected(callback: types.CallbackQuery, state: FSMContext):
    mode_map = {
        "mode_support":    ("support",    "Хорошо. Говори — я слушаю."),
        "mode_understand": ("understand", "Хорошо. Расскажи что происходит — будем разбираться."),
        "mode_tools":      ("tools",      "Хорошо. Опиши ситуацию — дам конкретные техники."),
    }
    mode_key, reply_text = mode_map.get(callback.data, ("", "Хорошо, начнём."))
    await state.update_data(session_mode=mode_key)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(reply_text)
    await callback.answer()


@router.message(Command("chat"))
async def start_chat_session(message: types.Message, state: FSMContext):
    await state.update_data(session_mode="")
    await message.answer(
        "Как ты хочешь работать сегодня?",
        reply_markup=SESSION_MODE_KB,
    )


@router.message(Command("help"))
async def help_command(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📖 Читать инструкцию",
            url="https://telegra.ph/Gajd-po-Mental-Health-Bot-02-03"
        )]
    ])
    await message.answer(
        "<b>Гайд по использованию бота</b>\n\n"
        "Нажми на кнопку ниже — там описание всех функций, методик и контакты помощи.",
        reply_markup=kb,
        parse_mode="HTML"
    )
