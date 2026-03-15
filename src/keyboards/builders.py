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

DIAGNOSTICS_DESCRIPTION = (
    "🧪 <b>Диагностика</b>\n\n"
    "Выбери тему — пройдёшь связанные тесты один за другим и получишь общий анализ.\n\n"
    "🔥 <b>Выгорание</b>\n"
    "MBI + Бойко — два взгляда на одно явление. MBI даёт количественную картину, "
    "Бойко показывает в какой фазе ты находишься.\n\n"
    "⚡ <b>Энергия и ресурс</b>\n"
    "UWES + PSS-10 — где у тебя ещё есть силы и насколько стресс их съедает.\n\n"
    "😔 <b>Тревога и настроение</b>\n"
    "PHQ-9 + GAD-7 — скрининг депрессии и тревоги. 16 вопросов, клинически валидированные шкалы.\n\n"
    "🏢 <b>Рабочая среда</b>\n"
    "Осипов — что именно в организации создаёт стресс: нагрузка, контроль, поддержка, роль.\n\n"
    "📊 <b>Полная диагностика</b>\n"
    "Все тесты подряд. Занимает 25–30 минут. В конце — сводный анализ всей картины."
)


def diagnostics_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔥 Выгорание",           callback_data="bundle_burnout")
    builder.button(text="⚡ Энергия и ресурс",     callback_data="bundle_energy")
    builder.button(text="😔 Тревога и настроение", callback_data="bundle_anxiety")
    builder.button(text="🏢 Рабочая среда",        callback_data="bundle_work")
    builder.button(text="📊 Полная диагностика",   callback_data="bundle_full")
    builder.button(text="📈 Мои результаты",       callback_data="test_history")
    builder.adjust(1)
    return builder.as_markup()


def scale_keyboard_mbi():
    builder = InlineKeyboardBuilder()
    labels = ["0", "1", "2", "3", "4", "5", "6"]
    for i, label in enumerate(labels):
        builder.button(text=label, callback_data=f"mbi_{i}")
    builder.adjust(7)
    return builder.as_markup()


def scale_keyboard_03():
    builder = InlineKeyboardBuilder()
    labels = ["0 — Никогда", "1 — Несколько дней", "2 — Больше половины дней", "3 — Почти каждый день"]
    for i, label in enumerate(labels):
        builder.button(text=label, callback_data=f"scale03_{i}")
    builder.adjust(1)
    return builder.as_markup()


def scale_keyboard_04():
    builder = InlineKeyboardBuilder()
    labels = ["0 — Никогда", "1 — Почти никогда", "2 — Иногда", "3 — Довольно часто", "4 — Очень часто"]
    for i, label in enumerate(labels):
        builder.button(text=label, callback_data=f"scale04_{i}")
    builder.adjust(1)
    return builder.as_markup()


def scale_keyboard_uwes():
    """Шкала 0–6 для UWES."""
    builder = InlineKeyboardBuilder()
    labels = [
        "0 — Никогда",
        "1 — Почти никогда",
        "2 — Редко",
        "3 — Иногда",
        "4 — Часто",
        "5 — Очень часто",
        "6 — Всегда",
    ]
    for i, label in enumerate(labels):
        builder.button(text=label, callback_data=f"uwes_{i}")
    builder.adjust(1)
    return builder.as_markup()


def scale_keyboard_osipov():
    """Шкала 1–5 для Осипова."""
    builder = InlineKeyboardBuilder()
    labels = [
        "1 — Совсем не согласен",
        "2 — Скорее не согласен",
        "3 — Затрудняюсь ответить",
        "4 — Скорее согласен",
        "5 — Полностью согласен",
    ]
    for i, label in enumerate(labels, start=1):
        builder.button(text=label, callback_data=f"osipov_{i}")
    builder.adjust(1)
    return builder.as_markup()


def yes_no_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data="boyko_yes")
    builder.button(text="❌ Нет", callback_data="boyko_no")
    builder.adjust(2)
    return builder.as_markup()


# ── SOS ──────────────────────────────────────────────────────────────────────

def sos_situation_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="⚡ Накрыло внезапно / паника", callback_data="sos_sudden")
    builder.button(text="🔥 Конфликт или злость",       callback_data="sos_anger")
    builder.button(text="🌑 Уже долго плохо / апатия",  callback_data="sos_prolonged")
    builder.button(text="🤖 Поговорить с AI",            callback_data="sos_ai_chat")
    builder.adjust(1)
    return builder.as_markup()


def sos_sudden_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🌬 Квадратное дыхание",    callback_data="sos_breathe")
    builder.button(text="🧭 Техника 5-4-3-2-1",     callback_data="sos_grounding")
    builder.button(text="⏸ Техника STOP (30 сек)",  callback_data="sos_stop_technique")
    builder.adjust(1)
    return builder.as_markup()


def sos_prolonged_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎧 Медитация: безопасное место", callback_data="sos_safe_place")
    builder.button(text="💙 Пройти PHQ-9 + GAD-7",        callback_data="bundle_anxiety")
    builder.button(text="🤖 Поговорить с AI",              callback_data="sos_ai_chat")
    builder.adjust(1)
    return builder.as_markup()


def sos_after_anger_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🧠 Разобрать мысль (дефьюзинг)", callback_data="sos_defusion")
    builder.button(text="🌬 Успокоиться (дыхание)",        callback_data="sos_breathe")
    builder.button(text="🏠 В главное меню",               callback_data="sos_main_menu")
    builder.adjust(1)
    return builder.as_markup()


# ── ОБЩИЕ ────────────────────────────────────────────────────────────────────

def back_to_main():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data="go_main")
    return builder.as_markup()


def back_to_diagnostics():
    builder = InlineKeyboardBuilder()
    builder.button(text="🧪 К диагностике", callback_data="go_diagnostics")
    builder.button(text="🏠 Главное меню",  callback_data="go_main")
    builder.adjust(1)
    return builder.as_markup()


def ai_chat_stop_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🛑 Закончить диалог", callback_data="ai_stop")
    return builder.as_markup()


def offer_phq9_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="💙 Да, пройти PHQ-9 + GAD-7", callback_data="bundle_anxiety")
    builder.button(text="Не сейчас",                    callback_data="go_main")
    builder.adjust(1)
    return builder.as_markup()


def offer_sos_after_test_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🆘 Попробовать технику сейчас", callback_data="sos_sudden")
    builder.button(text="🤖 Поговорить с AI",             callback_data="sos_ai_chat")
    builder.button(text="Позже",                          callback_data="go_main")
    builder.adjust(1)
    return builder.as_markup()


def offer_work_env_keyboard():
    """После выгорания предложить пройти тест рабочей среды."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏢 Да, проверить рабочую среду", callback_data="bundle_work")
    builder.button(text="Не сейчас",                      callback_data="go_main")
    builder.adjust(1)
    return builder.as_markup()


def tracker_skip_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить", callback_data="tracker_skip_gratitude")
    return builder.as_markup()
