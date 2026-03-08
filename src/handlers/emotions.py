from aiogram import Router, F, types
from aiogram.types import URLInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from src.keyboards import builders

router = Router()


@router.message(F.text == "🧠 Мои Эмоции")
async def emotions_menu(message: types.Message):
    photo_url = "https://www.odbtomsk.ru/images/useful-information/thewheelofemotions/fckremnmuvi.jpg"

    await message.answer_photo(
        photo=URLInputFile(photo_url),
        caption=(
            "<b>Колесо эмоций Роберта Плутчика</b>\n\n"
            "Посмотри на картинку. Где ты сейчас?\n"
            "Понимание своей эмоции — первый шаг к управлению ею."
        ),
        parse_mode="HTML"
    )

    await message.answer(
        "💡 <b>Упражнение «Азбука»:</b>\n\n"
        "Попробуй назвать 3 оттенка того, что ты чувствуешь.\n"
        "Например: не просто «Гнев», а «Раздражение», «Досада», «Бешенство».\n\n"
        "Чем точнее назовёшь — тем легче управлять.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Записать эту эмоцию в дневник", callback_data="go_diary")]
        ])
    )


@router.callback_query(F.data == "go_diary")
async def go_to_diary(callback: types.CallbackQuery):
    await callback.message.answer(
        "Открываю дневник — выбери уровень энергии:",
        reply_markup=builders.main_menu()
    )
    # Имитируем нажатие кнопки дневника — пользователь сам нажмёт 📝 Дневник
    await callback.answer("Нажми «📝 Дневник» в меню ниже")
