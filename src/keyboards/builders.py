from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu():
    kb = [
        # Добавили кнопку для Бойко
        [KeyboardButton(text="📊 Диагностика (MBI)"), KeyboardButton(text="📋 Тест Бойко")],
        [KeyboardButton(text="📝 Дневник"), KeyboardButton(text="🧠 Мои Эмоции")],
        [KeyboardButton(text="🆘 SOS / Я киплю"), KeyboardButton(text="🧘 Ресурсы")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Клавиатура для MBI (0-6)
def scale_keyboard():
    builder = InlineKeyboardBuilder()
    for i in range(7):
        builder.button(text=str(i), callback_data=f"mbi_{i}")
    builder.adjust(7)
    return builder.as_markup()

# НОВАЯ: Клавиатура для Бойко (Да/Нет)
def yes_no_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data="boyko_yes")
    builder.button(text="Нет", callback_data="boyko_no")
    builder.adjust(2)
    return builder.as_markup()

def sos_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Тревога (Дыхание)", callback_data="sos_breathe")
    builder.button(text="Гнев (Стоп-мысль)", callback_data="sos_anger")
    builder.button(text="Апатия (Видео)", callback_data="sos_apathy")
    builder.button(text="Нужен совет AI", callback_data="sos_ai_chat")
    builder.adjust(1)
    return builder.as_markup()
