from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu():
    kb = [
        [KeyboardButton(text="📊 Диагностика"), KeyboardButton(text="📝 Дневник")],
        [KeyboardButton(text="🧠 Мои Эмоции"), KeyboardButton(text="📈 Моя динамика")],
        [KeyboardButton(text="🆘 SOS / Я киплю"), KeyboardButton(text="🧘 Ресурсы")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ── ДИАГНОСТИКА ──────────────────────────────────────────────────────────────

def diagnostics_menu():
    """Подменю выбора теста."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 MBI — Выгорание (22 вопроса)", callback_data="test_mbi")
    builder.button(text="📋 Бойко — Выгорание детально (84 вопроса)", callback_data="test_boyko")
    builder.button(text="💙 PHQ-9 + GAD-7 — Депрессия и тревога (16 вопросов)", callback_data="test_phq9_gad7")
    builder.button(text="🌡 PSS-10 — Уровень стресса (10 вопросов)", callback_data="test_pss10")
    builder.button(text="📈 Мои последние результаты", callback_data="test_history")
    builder.adjust(1)
    return builder.as_markup()


def scale_keyboard_mbi():
    """Шкала 0–6 для MBI."""
    builder = InlineKeyboardBuilder()
    for i in range(7):
        builder.button(text=str(i), callback_data=f"mbi_{i}")
    builder.adjust(7)
    return builder.as_markup()


def scale_keyboard_03():
    """Шкала 0–3 для PHQ-9 и GAD-7."""
    builder = InlineKeyboardBuilder()
    labels = ["0 — Никогда", "1 — Несколько дней", "2 — Больше половины дней", "3 — Почти каждый день"]
    for i, label in enumerate(labels):
        builder.button(text=label, callback_data=f"scale03_{i}")
    builder.adjust(1)
    return builder.as_markup()


def scale_keyboard_04():
    """Шкала 0–4 для PSS-10."""
    builder = InlineKeyboardBuilder()
    labels = ["0 — Никогда", "1 — Почти никогда", "2 — Иногда", "3 — Довольно часто", "4 — Очень часто"]
    for i, label in enumerate(labels):
        builder.button(text=label, callback_data=f"scale04_{i}")
    builder.adjust(1)
    return builder.as_markup()


def yes_no_keyboard():
    """Да/Нет для теста Бойко."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data="boyko_yes")
    builder.button(text="❌ Нет", callback_data="boyko_no")
    builder.adjust(2)
    return builder.as_markup()


# ── SOS ──────────────────────────────────────────────────────────────────────

def sos_situation_keyboard():
    """Первый вопрос умного SOS: что сейчас происходит?"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚡ Накрыло внезапно / паника", callback_data="sos_sudden")
    builder.button(text="🔥 Конфликт или злость", callback_data="sos_anger")
    builder.button(text="🌑 Уже долго плохо / апатия", callback_data="sos_prolonged")
    builder.button(text="🤖 Поговорить с AI", callback_data="sos_ai_chat")
    builder.adjust(1)
    return builder.as_markup()


def sos_sudden_keyboard():
    """Варианты для острого состояния."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🌬 Квадратное дыхание", callback_data="sos_breathe")
    builder.button(text="🧭 Техника 5-4-3-2-1", callback_data="sos_grounding")
    builder.button(text="⏸ Техника STOP (30 сек)", callback_data="sos_stop_technique")
    builder.adjust(1)
    return builder.as_markup()


def sos_prolonged_keyboard():
    """Варианты при длительном плохом состоянии."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎧 Медитация: безопасное место", callback_data="sos_safe_place")
    builder.button(text="💙 Пройти PHQ-9 + GAD-7", callback_data="test_phq9_gad7")
    builder.button(text="🤖 Поговорить с AI", callback_data="sos_ai_chat")
    builder.adjust(1)
    return builder.as_markup()


def sos_after_anger_keyboard():
    """После выброса гнева."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🧠 Разобрать мысль (дефьюзинг)", callback_data="sos_defusion")
    builder.button(text="🌬 Успокоиться (дыхание)", callback_data="sos_breathe")
    builder.button(text="🏠 В главное меню", callback_data="sos_main_menu")
    builder.adjust(1)
    return builder.as_markup()


# ── ОБЩИЕ ────────────────────────────────────────────────────────────────────

def back_to_main():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data="go_main")
    return builder.as_markup()


def ai_chat_stop_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🛑 Закончить диалог", callback_data="ai_stop")
    return builder.as_markup()


def offer_phq9_keyboard():
    """Предложение пройти PHQ-9 после высокого MBI."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💙 Да, пройти PHQ-9 + GAD-7", callback_data="test_phq9_gad7")
    builder.button(text="Не сейчас", callback_data="go_main")
    builder.adjust(1)
    return builder.as_markup()


def offer_sos_after_test_keyboard():
    """Предложение попробовать технику после тревожного результата."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🆘 Попробовать технику сейчас", callback_data="sos_sudden")
    builder.button(text="🤖 Поговорить с AI", callback_data="sos_ai_chat")
    builder.button(text="Позже", callback_data="go_main")
    builder.adjust(1)
    return builder.as_markup()


def tracker_skip_keyboard():
    """Пропустить шаг благодарности в дневнике."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить", callback_data="tracker_skip_gratitude")
    return builder.as_markup()
