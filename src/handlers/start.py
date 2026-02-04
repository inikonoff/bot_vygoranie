from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.database.supabase_client import db
from src.keyboards import builders

router = Router()

@router.message(CommandStart())
async def command_start(message: types.Message):
    user = message.from_user
    
    # Регистрируем юзера в БД (если он новый - добавится, если старый - обновится инфо)
    await db.add_user(user.id, user.first_name, user.username)
    
    txt = (
        f"Привет, {user.first_name}! 👋\n\n"
        "Я твой помощник по ментальному здоровью. Я не заменяю врача, "
        "но помогу отследить выгорание, найти ресурс и успокоиться.\n\n"
        "С чего начнем?"
    )
    
    # Отправляем приветствие и клавиатуру главного меню (снизу)
    await message.answer(txt, reply_markup=builders.main_menu())

@router.message(Command("help"))
async def help_command(message: types.Message):
    # Создаем инлайн-кнопку со ссылкой
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Читать инструкцию", url="https://telegra.ph/Gajd-po-Mental-Health-Bot-02-03")]
    ])
    
    await message.answer(
        "<b>Гайд по использованию бота</b>\n\n"
        "Нажмите на кнопку ниже, чтобы открыть подробную статью с картинками, контактами помощи и описанием методик.",
        reply_markup=kb,
        parse_mode="HTML"
    )
