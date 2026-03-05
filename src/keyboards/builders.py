from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu():
    """Главное меню бота"""
    kb = [
        [KeyboardButton(text="📊 Диагностика"), KeyboardButton(text="📝 Дневник")],
        [KeyboardButton(text="🧠 Мои Эмоции"), KeyboardButton(text="🆘 SOS / Я киплю")],
        [KeyboardButton(text="🧘 Ресурсы"), KeyboardButton(text="📈 Моя динамика")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def scale_keyboard():
    """Клавиатура для MBI (0-6)"""
    builder = InlineKeyboardBuilder()
    for i in range(7):
        builder.button(text=str(i), callback_data=f"mbi_{i}")
    builder.adjust(7)
    return builder.as_markup()


def yes_no_keyboard():
    """Клавиатура для теста Бойко (Да/Нет)"""
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data="boyko_yes")
    builder.button(text="Нет", callback_data="boyko_no")
    builder.adjust(2)
    return builder.as_markup()


def phq9_scale_keyboard():
    """Клавиатура для PHQ-9 и GAD-7 (0-3)"""
    builder = InlineKeyboardBuilder()
    options = [
        ("0 - Никогда", "phq9_0"),
        ("1 - Несколько дней", "phq9_1"),
        ("2 - Более половины дней", "phq9_2"),
        ("3 - Почти каждый день", "phq9_3")
    ]
    for text, callback in options:
        builder.button(text=text, callback_data=callback)
    builder.adjust(1)
    return builder.as_markup()


def pss10_scale_keyboard():
    """Клавиатура для PSS-10 (0-4)"""
    builder = InlineKeyboardBuilder()
    options = [
        ("0 - Никогда", "pss10_0"),
        ("1 - Почти никогда", "pss10_1"),
        ("2 - Иногда", "pss10_2"),
        ("3 - Довольно часто", "pss10_3"),
        ("4 - Очень часто", "pss10_4")
    ]
    for text, callback in options:
        builder.button(text=text, callback_data=callback)
    builder.adjust(1)
    return builder.as_markup()


def diagnostic_menu():
    """Меню выбора диагностики"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔥 MBI (выгорание)", callback_data="diag_mbi")
    builder.button(text="😔 PHQ-9 (депрессия)", callback_data="diag_phq9")
    builder.button(text="😰 GAD-7 (тревога)", callback_data="diag_gad7")
    builder.button(text="📊 PSS-10 (стресс)", callback_data="diag_pss10")
    builder.button(text="📋 Тест Бойко", callback_data="diag_boyko")
    builder.button(text="📈 Мои результаты", callback_data="my_results")
    builder.adjust(2)
    return builder.as_markup()


def smart_sos_keyboard():
    """Умная клавиатура SOS с уточняющим вопросом"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🌪 Накрыло внезапно", callback_data="sos_sudden")
    builder.button(text="⚡️ Конфликт или злость", callback_data="sos_anger")
    builder.button(text="🌧 Уже долго плохо", callback_data="sos_prolonged")
    builder.button(text="🤖 Нужен совет AI", callback_data="sos_ai_chat")
    builder.adjust(1)
    return builder.as_markup()


def sos_keyboard():
    """Оригинальная клавиатура SOS (для обратной совместимости)"""
    builder = InlineKeyboardBuilder()
    builder.button(text="Тревога (Дыхание)", callback_data="sos_breathe")
    builder.button(text="Гнев (Стоп-мысль)", callback_data="sos_anger")
    builder.button(text="Апатия (Видео)", callback_data="sos_apathy")
    builder.button(text="Нужен совет AI", callback_data="sos_ai_chat")
    builder.adjust(1)
    return builder.as_markup()


def skip_keyboard():
    """Кнопка пропуска"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить", callback_data="skip")
    return builder.as_markup()


def gratitude_keyboard():
    """Клавиатура для шага благодарности в дневнике"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✨ Написать", callback_data="write_gratitude")
    builder.button(text="⏭ Пропустить", callback_data="skip_gratitude")
    builder.adjust(2)
    return builder.as_markup()
