from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import URLInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.keyboards import builders
from src.states import TrackerStates

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
async def go_to_diary(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(TrackerStates.energy)

    b = InlineKeyboardBuilder()
    for i in range(1, 11):
        b.button(text=str(i), callback_data=f"energy_{i}")
    b.adjust(5)

    await callback.message.answer(
        "⚡️ <b>Как твой уровень энергии прямо сейчас?</b>\n\n"
        "1 — пустой, 10 — на подъёме",
        reply_markup=b.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()
