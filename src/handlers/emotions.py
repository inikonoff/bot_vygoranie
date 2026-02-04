from aiogram import Router, F, types
from aiogram.types import URLInputFile
from src.keyboards import builders

router = Router()

@router.message(F.text == "🧠 Мои Эмоции")
async def emotions_menu(message: types.Message):
    # Ссылка на картинку колеса Плутчика (можно заменить на свою)
    photo_url = "https://www.odbtomsk.ru/images/useful-information/thewheelofemotions/fckremnmuvi.jpg"
    
    txt = (
        "<b>Колесо эмоций Роберта Плутчика</b>\n\n"
        "Посмотри на картинку. Где ты сейчас?\n"
        "Понимание своей эмоции — первый шаг к управлению ею."
    )
    
    await message.answer_photo(
        photo=URLInputFile(photo_url),
        caption=txt,
        reply_markup=builders.main_menu() # Возвращаем меню
    )
    
    # Добавляем упражнение "Азбука"
    await message.answer(
        "💡 <b>Упражнение:</b> Попробуй назвать 3 оттенка того, что ты чувствуешь.\n"
        "Например: не просто «Гнев», а «Раздражение», «Досада», «Бешенство»."
    )
