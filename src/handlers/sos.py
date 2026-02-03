from aiogram import Router, F, types
from src.keyboards import builders
from aiogram.types import FSInputFile

router = Router()

@router.message(F.text == "🆘 SOS / Я киплю")
async def sos_menu(message: types.Message):
    await message.answer("Что чувствуешь? Выбери, чтобы я помог:", reply_markup=builders.sos_keyboard())

@router.callback_query(F.data == "sos_breathe")
async def sos_breathe(callback: types.CallbackQuery):
    await callback.message.answer("🌬 <b>Квадратное дыхание</b>\n\nВдох - 4 сек\nЗадержка - 4 сек\nВыдох - 4 сек\nЗадержка - 4 сек\n\nПовторяй за мной...", parse_mode="HTML")
    # Тут можно отправить GIF, если есть файл
    await callback.answer()

@router.callback_query(F.data == "sos_apathy")
async def sos_video(callback: types.CallbackQuery):
    await callback.message.answer("Посмотри это видео от Татьяны Мужицкой, оно помогает:\nhttps://www.youtube.com/shorts/VxJfaGCRIvM")
    await callback.answer()
    
@router.message(F.text == "🧘 Ресурсы")
async def send_audio_relax(message: types.Message):
    # Отправка сгенерированного аудио
    try:
        audio = FSInputFile("data/safe_place.mp3")
        await message.answer_audio(audio, caption="🎧 Техника «Безопасное место»")
    except:
        await message.answer("Аудиофайл еще не сгенерирован. Запустите скрипт генерации.")
