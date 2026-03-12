import asyncio
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.database.supabase_client import db
from src.config import config

logger = logging.getLogger(__name__)
router = Router()

ADMIN_IDS = [7201211546]


class AdminState(StatesGroup):
    waiting_broadcast = State()


# ── ФИЛЬТР АДМИНА ─────────────────────────────────────────────────────────────

class IsAdmin(types.base.TelegramObject):
    pass

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def check_admin(event) -> bool:
    uid = event.from_user.id if hasattr(event, "from_user") else None
    return uid in ADMIN_IDS


# ── КЛАВИАТУРЫ ────────────────────────────────────────────────────────────────

def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика",    callback_data="admin_stats")
    builder.button(text="👥 Пользователи",  callback_data="admin_users")
    builder.button(text="📣 Рассылка",      callback_data="admin_broadcast")
    builder.button(text="🚫 Бан-лист",      callback_data="admin_bans")
    builder.button(text="🧪 Тест Groq",     callback_data="admin_test_groq")
    builder.adjust(2)
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить", callback_data="admin_stats")
    builder.button(text="← Назад",    callback_data="admin_panel")
    builder.adjust(2)
    return builder.as_markup()


def get_users_keyboard(users: list, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * per_page
    end = start + per_page

    for u in users[start:end]:
        uid = u.get("telegram_id", 0)
        name = u.get("first_name") or u.get("username") or str(uid)
        username = u.get("username")
        risk = u.get("risk_group", "green")
        risk_emoji = {"red": "🔴", "yellow": "🟡", "green": "🟢"}.get(risk, "⚪")
        label = f"{risk_emoji} {name}" + (f" @{username}" if username else "")
        builder.button(text=label[:60], callback_data=f"admin_user_{uid}")

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_users_page_{page-1}"))
    if end < len(users):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_users_page_{page+1}"))
    if nav:
        builder.row(*nav)

    builder.button(text="← Назад", callback_data="admin_panel")
    builder.adjust(1)
    return builder.as_markup()


def get_user_card_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="← К списку",  callback_data="admin_users")
    builder.button(text="🚫 Забанить", callback_data=f"admin_ban_{telegram_id}")
    builder.adjust(2)
    return builder.as_markup()


def get_bans_keyboard(banned: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for uid in banned[:10]:
        builder.button(text=f"✅ Разбанить {uid}", callback_data=f"admin_unban_{uid}")
    builder.button(text="← Назад", callback_data="admin_panel")
    builder.adjust(1)
    return builder.as_markup()


# ── КОМАНДА /admin ─────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_command(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\nВыберите раздел:",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML"
    )


# ── ГЛАВНОЕ МЕНЮ ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await callback.message.edit_text(
        "🔧 <b>Админ-панель</b>\n\nВыберите раздел:",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ── СТАТИСТИКА ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    stats = await db.get_admin_stats()
    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{stats.get('total_users', 0)}</b>\n"
        f"🆕 Новых сегодня: <b>{stats.get('new_today', 0)}</b>\n"
        f"📅 Новых за неделю: <b>{stats.get('new_week', 0)}</b>\n"
        f"✨ Активных за неделю: <b>{stats.get('active_week', 0)}</b>\n\n"
        f"📋 <b>Группы риска (MBI):</b>\n"
        f"🔴 Красная: {stats.get('risk_red', 0)}\n"
        f"🟡 Жёлтая: {stats.get('risk_yellow', 0)}\n"
        f"🟢 Зелёная: {stats.get('risk_green', 0)}\n\n"
        f"📝 <b>Тесты пройдено:</b>\n"
        f"• MBI: {stats.get('tests_mbi', 0)}\n"
        f"• Бойко: {stats.get('tests_boyko', 0)}\n"
        f"• PHQ-9: {stats.get('tests_phq9', 0)}\n"
        f"• GAD-7: {stats.get('tests_gad7', 0)}\n"
        f"• PSS-10: {stats.get('tests_pss10', 0)}\n\n"
        f"📓 <b>Дневник:</b>\n"
        f"• Всего записей: {stats.get('total_logs', 0)}\n"
        f"• Средняя энергия: {stats.get('avg_energy', 0):.1f}/10\n"
    )
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()


# ── ПОЛЬЗОВАТЕЛИ ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_users")
async def show_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    users = await db.get_all_users(limit=100)
    await callback.message.edit_text(
        f"👥 <b>Пользователи</b> (всего: {len(users)})\n\n"
        "🔴🟡🟢 — группа риска по MBI",
        reply_markup=get_users_keyboard(users, 0),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_users_page_"))
async def show_users_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    page = int(callback.data.split("_")[-1])
    users = await db.get_all_users(limit=100)
    await callback.message.edit_text(
        f"👥 <b>Пользователи</b> (всего: {len(users)})\n\n"
        "🔴🟡🟢 — группа риска по MBI",
        reply_markup=get_users_keyboard(users, page),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_user_\d+$"))
async def show_user_card(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    telegram_id = int(callback.data.split("_")[-1])
    card = await db.get_user_card(telegram_id)

    if not card:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    user = card.get("user", {})
    tests = card.get("recent_tests", [])
    logs = card.get("recent_logs", [])
    risk_emoji = {"red": "🔴", "yellow": "🟡", "green": "🟢"}.get(user.get("risk_group"), "⚪")

    text = (
        f"{risk_emoji} <b>Карточка пользователя</b>\n\n"
        f"ID: <code>{telegram_id}</code>\n"
        f"Имя: {user.get('first_name', '—')}\n"
        f"Username: @{user.get('username', '—')}\n"
        f"Зарегистрирован: {str(user.get('created_at', '—'))[:10]}\n"
        f"Группа риска: {user.get('risk_group', '—')}\n"
        f"Сфера: {user.get('sphere', '—')}\n"
        f"Запрос: {user.get('main_request', '—')}\n"
    )

    if tests:
        text += "\n<b>📊 Последние тесты:</b>\n"
        for t in tests[:3]:
            text += f"• {t.get('test_type','').upper()}: {t.get('total_score','?')} ({str(t.get('created_at',''))[:10]})\n"

    if logs:
        text += "\n<b>📝 Последние записи дневника:</b>\n"
        for l in logs[:5]:
            text += f"• {str(l.get('created_at',''))[:10]}: энергия {l.get('energy_level','?')}, {l.get('emotion','—')}\n"

    await callback.message.edit_text(
        text,
        reply_markup=get_user_card_keyboard(telegram_id),
        parse_mode="HTML"
    )
    await callback.answer()


# ── БАН ───────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_ban_"))
async def ban_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    from src.rate_limit import banned_users_mw
    user_id = int(callback.data.split("_")[-1])
    banned_users_mw.ban(user_id)
    await callback.answer(f"Пользователь {user_id} забанен", show_alert=True)


@router.callback_query(F.data == "admin_bans")
async def show_bans(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    from src.rate_limit import banned_users_mw
    banned = list(banned_users_mw.banned_list)
    if not banned:
        await callback.message.edit_text(
            "🚫 <b>Бан-лист</b>\n\nНет забаненных пользователей.",
            reply_markup=get_admin_panel_keyboard(),
            parse_mode="HTML"
        )
    else:
        text = "🚫 <b>Бан-лист</b>\n\n" + "\n".join(f"• <code>{uid}</code>" for uid in banned[:20])
        if len(banned) > 20:
            text += f"\n\n... и ещё {len(banned) - 20}"
        await callback.message.edit_text(
            text,
            reply_markup=get_bans_keyboard(banned),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_unban_"))
async def unban_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    from src.rate_limit import banned_users_mw
    user_id = int(callback.data.split("_")[-1])
    banned_users_mw.unban(user_id)
    await callback.answer(f"Пользователь {user_id} разбанен", show_alert=True)
    # Обновляем список
    banned = list(banned_users_mw.banned_list)
    if not banned:
        await callback.message.edit_text(
            "🚫 <b>Бан-лист</b>\n\nНет забаненных пользователей.",
            reply_markup=get_admin_panel_keyboard(),
            parse_mode="HTML"
        )
    else:
        text = "🚫 <b>Бан-лист</b>\n\n" + "\n".join(f"• <code>{uid}</code>" for uid in banned[:20])
        await callback.message.edit_text(
            text,
            reply_markup=get_bans_keyboard(banned),
            parse_mode="HTML"
        )


# ── РАССЫЛКА ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.set_state(AdminState.waiting_broadcast)
    await callback.message.edit_text(
        "📣 <b>Рассылка</b>\n\n"
        "Отправь сообщение для рассылки всем пользователям.\n"
        "Можно текст, фото, видео.\n\n"
        "Отправь /cancel для отмены.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminState.waiting_broadcast)
async def handle_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Рассылка отменена")
        return

    user_ids = await db.get_all_user_ids()
    status_msg = await message.answer(f"📤 Начинаю рассылку {len(user_ids)} пользователям...")

    sent_ok = 0
    sent_fail = 0

    for i, uid in enumerate(user_ids):
        try:
            await message.bot.copy_message(
                chat_id=uid,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            sent_ok += 1
        except Exception as e:
            logger.debug(f"Broadcast failed for {uid}: {e}")
            sent_fail += 1

        if i % 10 == 0:
            try:
                await status_msg.edit_text(f"📤 Рассылка: {i}/{len(user_ids)}...")
            except Exception:
                pass

        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"✅ Рассылка завершена\n"
        f"✓ Успешно: {sent_ok}\n"
        f"✗ Ошибок: {sent_fail}"
    )
    await state.clear()


# ── ТЕСТ GROQ ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_test_groq")
async def test_groq(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    from src.services.llm import get_client
    client = await get_client()
    if client:
        await callback.message.edit_text(
            "✅ <b>Groq API работает</b>\n\nКлиент успешно создан.",
            reply_markup=get_admin_panel_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "❌ <b>Groq API не работает</b>\n\nПроверьте GROQ_API_KEY.",
            reply_markup=get_admin_panel_keyboard(),
            parse_mode="HTML"
        )
    await callback.answer()
