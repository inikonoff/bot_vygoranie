from aiogram import Router, types
from aiogram.filters import CommandStart
from src.database.supabase_client import db
from src.keyboards import builders

router = Router()

@router.message(CommandStart())
async def command_start(message: types.Message):
    user = message.from_user
    # Регистрируем юзера в БД
    await db.add_user(user.id, user.first_name, user.username)
    
    txt = (
        f"Привет, {user.first_name}! 👋\n\n"
        "Я твой помощник по ментальному здоровью. Я не заменяю врача, "
        "но помогу отследить выгорание, найти ресурс и успокоиться.\n\n"
        "С чего начнем?"
    )
    
    await message.answer(txt, reply_markup=builders.main_menu())
