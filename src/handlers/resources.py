import logging
from aiogram import Router, F, types
from aiogram.types import FSInputFile
from src.keyboards import builders

logger = logging.getLogger(__name__)
router = Router()

RELAX_TEXT = (
    "🧘 <b>Прогрессивная мышечная релаксация</b>\n\n"
    "Сядь удобно.\n\n"
    "Сожми крепко кулаки. Ещё сильнее... И резко расслабь.\n"
    "Почувствуй разницу между напряжением и покоем.\n\n"
    "Теперь подними плечи к ушам. Тяни сильно... И бросай вниз. Расслабься.\n\n"
    "Зажмурь глаза изо всех сил... И расслабь лицо. Пусть челюсть станет тяжёлой.\n\n"
    "Глубокий вдох... и медленный выдох.\n\n"
    "<i>Тело расслаблено. Оставайся в этом состоянии столько, сколько нужно.</i>"
)

OBSERVER_TEXT = (
    "👁 <b>Техника «Наблюдатель»</b>\n\n"
    "Используй, когда ситуация захлёстывает или чужая критика выбивает из колеи.\n\n"
    "<b>Шаг 1.</b> Закрой глаза. Представь, что смотришь на ситуацию сверху — как режиссёр, "
    "который видит всю сцену целиком.\n\n"
    "<b>Шаг 2.</b> Посмотри на себя со стороны. Что делает этот человек? Что чувствует? "
    "Что ему сейчас нужно?\n\n"
    "<b>Шаг 3.</b> Посмотри на других участников ситуации. Что происходит с ними? "
    "Почему они ведут себя так?\n\n"
    "<b>Шаг 4.</b> Вернись в своё тело. Что изменилось в восприятии?\n\n"
    "<i>Эта дистанция не отстранённость — это ясность. Ты видишь больше, реагируешь точнее.</i>"
)


@router.message(F.text == "🧘 Ресурсы")
async def resources_menu(message: types.Message):
    # 1. Аудио — безопасное место
    try:
        audio = FSInputFile("data/safe_place.mp3")
        await message.answer_audio(
            audio,
            caption="🎧 <b>Практика: Безопасное место</b>\nСлушай, когда нужно быстро успокоиться.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"safe_place.mp3 не найден: {e}")
        await message.answer(
            "🎧 <b>Практика: Безопасное место</b>\n\n"
            "Закрой глаза. Представь место, где тебе абсолютно спокойно.\n"
            "Что ты видишь? Какие цвета? Что слышишь?\n"
            "Побудь здесь несколько минут.",
            parse_mode="HTML"
        )

    # 2. Аудио — релаксация
    try:
        relax_audio = FSInputFile("data/relaxation.mp3")
        await message.answer_audio(
            relax_audio,
            caption="🧘 <b>Практика: Прогрессивная релаксация</b>\nСнимает мышечное напряжение за 5 минут.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"relaxation.mp3 не найден: {e}")
        await message.answer(RELAX_TEXT, parse_mode="HTML")

    # 3. Техника Наблюдатель
    await message.answer(OBSERVER_TEXT, parse_mode="HTML")

    # 4. Контакты
    await message.answer(
        "📞 <b>Куда обратиться за живой помощью</b>\n\n"
        "🇧🇾 <b>Беларусь:</b>\n"
        "• Взрослым: <code>8-017-352-44-44</code>\n"
        "• Подросткам: <code>8-801-100-16-11</code>\n\n"
        "🇷🇺 <b>Россия:</b>\n"
        "• Телефон доверия: <code>8-800-2000-122</code> (бесплатно, 24/7)\n\n"
        "<i>Обращаться за помощью — это признак силы, а не слабости.</i>",
        parse_mode="HTML",
        reply_markup=builders.main_menu()
    )
