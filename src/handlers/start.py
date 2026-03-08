from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from src.database.supabase_client import db
from src.keyboards import builders
from src.states import OnboardingStates

router = Router()

# Сферы для онбординга
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

    # Новый пользователь — запускаем онбординг
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
    sphere = message.text.strip()
    await state.update_data(sphere=sphere)
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
        "Вот что я умею:",
        reply_markup=builders.main_menu()
    )
    await message.answer(
        "📊 <b>Диагностика</b> — тесты MBI, Бойко, PHQ-9, GAD-7, PSS-10\n"
        "📝 <b>Дневник</b> — отслеживай энергию и эмоции каждый день\n"
        "🆘 <b>SOS</b> — техники быстрой помощи при тревоге и стрессе\n"
        "🧠 <b>Мои Эмоции</b> — колесо эмоций и упражнения\n"
        "📈 <b>Моя динамика</b> — анализ твоей недели\n"
        "🤖 <b>AI-психолог</b> — поговорить, когда нужна поддержка\n\n"
        "<i>Я не заменяю специалиста, но всегда рядом.</i>",
        parse_mode="HTML"
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
