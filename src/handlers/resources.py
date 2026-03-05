import asyncio
import logging
from aiogram import Router, F, types
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.keyboards import builders

logger = logging.getLogger(__name__)
router = Router()

# Тексты для запасного варианта
SAFE_PLACE_TEXT = """
Сделайте несколько глубоких вдохов и выдохов. На каждом выдохе отпускайте напряжение.

Представьте, что вы можете найти или создать место, где вы чувствуете себя абсолютно спокойно и безопасно.

Это может быть реальное место на природе — лес, пляж, горы. Или уютная комната.

Осмотритесь вокруг. Что вы видите? Какие цвета?

Что вы слышите? Пение птиц, шум прибоя или тишину?

Побудьте в этом месте. Почувствуйте, как здесь спокойно.

Запомните это ощущение безопасности. Вы можете вернуться сюда в любой момент.
"""

RELAX_TEXT = """
Сядьте удобно. Закройте глаза.

Сожмите крепко кулаки. Держите напряжение... Еще сильнее... И резко расслабьте.

Почувствуйте разницу между напряжением и покоем.

Теперь поднимите плечи к ушам. Тяните сильно-сильно... И бросьте их вниз. Расслабьтесь.

Зажмурьте глаза изо всех сил... И расслабьте лицо. Пусть челюсть станет тяжелой.

Сделайте глубокий вдох... и медленный выдох. 

Ваше тело расслаблено. Наслаждайтесь этим состоянием.
"""


@router.callback_query(F.data == "resources_menu")
@router.message(F.text == "🧘 Ресурсы")
async def resources_menu(message: types.Message):
    """Показывает ресурсы для самопомощи"""
    
    # 1. Отправляем аудио Безопасное место
    try:
        audio = FSInputFile("data/safe_place.mp3")
        await message.answer_audio(
            audio, 
            caption="🎧 **Практика: Безопасное место**\nСлушай, когда нужно быстро успокоиться.", 
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Safe place audio not found: {e}")
        await message.answer(
            f"🔇 **Безопасное место** (текстовая версия):\n{SAFE_PLACE_TEXT}",
            parse_mode="Markdown"
        )
    
    # 2. Отправляем аудио Прогрессивная релаксация
    try:
        audio = FSInputFile("data/relaxation.mp3")
        await message.answer_audio(
            audio, 
            caption="🧘 **Прогрессивная релаксация**\nПомогает снять мышечное напряжение.", 
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Relaxation audio not found: {e}")
        await message.answer(
            f"🔇 **Прогрессивная релаксация** (текстовая версия):\n{RELAX_TEXT}",
            parse_mode="Markdown"
        )
    
    # 3. Техника "Наблюдатель"
    kb = InlineKeyboardBuilder()
    kb.button(text="👁 Техника «Наблюдатель»", callback_data="technique_observer")
    kb.button(text="📞 Контакты помощи", callback_data="help_contacts")
    kb.adjust(1)
    
    await message.answer(
        "🧘 **Доступные практики:**\n\n"
        "• **Наблюдатель** - отделиться от эмоций\n"
        "• **Контакты помощи** - если нужна живая поддержка",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "technique_observer")
async def observer_technique(callback: types.CallbackQuery):
    """Техника Наблюдатель - guided-медитация"""
    
    steps = [
        "👁 **Шаг 1**\n\nПредставь, что ты — сторонний наблюдатель.\nТы смотришь на свою жизнь со стороны, как на фильм.",
        "🌍 **Шаг 2**\n\nПосмотри на ситуацию, которая вызывает стресс. Ты просто наблюдаешь, не оценивая. Ты не участник, ты зритель.",
        "💭 **Шаг 3**\n\nЗаметь свои эмоции — но ты не эмоции. Ты тот, кто их наблюдает. Эмоции приходят и уходят, а ты остаешься.",
        "🕊 **Шаг 4**\n\nВ этом состоянии наблюдателя есть спокойствие. Ты можешь вернуться сюда в любой момент."
    ]
    
    msg = await callback.message.edit_text(steps[0], parse_mode="Markdown")
    
    for step in steps[1:]:
        await asyncio.sleep(4)
        msg = await msg.edit_text(step, parse_mode="Markdown")
    
    await asyncio.sleep(2)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🧘 Еще техники", callback_data="resources_menu")
    kb.button(text="🏠 Главное меню", callback_data="main_menu")
    
    await msg.edit_text(
        "🧘 Ты снова в настоящем моменте. Как себя чувствуешь?",
        reply_markup=kb.as_markup()
    )
    
    await callback.answer()


@router.callback_query(F.data == "help_contacts")
async def help_contacts(callback: types.CallbackQuery):
    """Показать контакты помощи"""
    await callback.message.edit_text(
        "📞 **Куда обратиться за помощью**\n\n"
        "🇧🇾 **Беларусь:**\n"
        "• Для взрослых: `8-017-352-44-44` (Минск, круглосуточно)\n"
        "• Для подростков: `8-801-100-16-11`\n\n"
        "🇷🇺 **Россия:**\n"
        "• Экстренная психологическая помощь МЧС: `+7-495-989-50-50`\n"
        "• Телефон доверия: `8-800-2000-122`\n\n"
        "🌐 **Онлайн-помощь:**\n"
        "• Чат поддержки: pomogi.online\n"
        "• Сайт помощи: ya-ne-odin.ru\n\n"
        "👇 Помни: обращаться за помощью — это признак силы, а не слабости.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardBuilder().button(
            text="◀️ Назад", callback_data="resources_menu"
        ).as_markup()
    )
    await callback.answer()
