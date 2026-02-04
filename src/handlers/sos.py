from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile  # <--- Используем FSInputFile вместо URLInputFile
import asyncio
from src.keyboards import builders
from src.services.llm import get_ai_response  # Убедись, что llm.py создан

router = Router()

class AIState(StatesGroup):
    waiting_for_query = State()

class AngerState(StatesGroup):
    venting = State()

@router.message(F.text == "🆘 SOS / Я киплю")
async def sos_menu(message: types.Message):
    await message.answer("Что чувствуешь? Выбери, чтобы я помог:", reply_markup=builders.sos_keyboard())

# --- ДЫХАНИЕ (С ЛОКАЛЬНОЙ ГИФКОЙ) ---
@router.callback_query(F.data == "sos_breathe")
async def sos_breathe(callback: types.CallbackQuery):
    try:
        # Используем локальный файл. Это 100% надежно.
        # Убедись, что файл data/sq_br.jpg существует в репозитории!
        gif_file = FSInputFile("data/sq_br.jpg")
        
        await callback.message.answer_animation(
            animation=gif_file,
            caption=(
                "🌬 <b>Квадратное дыхание</b>\n\n"
                "Синхронизируйся с анимацией:\n"
                "1. 🟢 Вдох (4 сек)\n"
                "2. ✋ Задержка (4 сек)\n"
                "3. ⚪️ Выдох (4 сек)\n"
                "4. ✋ Задержка (4 сек)"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.answer("Не удалось загрузить анимацию, но дышим так: 4 сек вдох - 4 пауза - 4 выдох - 4 пауза.")
        print(f"Ошибка GIF: {e}")
    
    await callback.answer()

# --- АПАТИЯ ---
@router.callback_query(F.data == "sos_apathy")
async def sos_video(callback: types.CallbackQuery):
    await callback.message.answer("Посмотри это видео от Татьяны Мужицкой, оно помогает:\nhttps://www.youtube.com/shorts/VxJfaGCRIvM")
    await callback.answer()

# --- ГНЕВ (Техника "Сжечь письмо") ---
@router.callback_query(F.data == "sos_anger")
async def sos_anger(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🔥 <b>Техника сброса гнева</b>\n\n"
        "Напиши сюда всё, что тебя бесит. Не стесняйся в выражениях. "
        "Я приму это сообщение и мы его ментально «сожжем».\n\n"
        "Пиши прямо сейчас:", 
        parse_mode="HTML"
    )
    await state.set_state(AngerState.venting)
    await callback.answer()

@router.message(AngerState.venting)
async def process_anger(message: types.Message, state: FSMContext):
    await message.reply("🔥🔥🔥 Сжигаю этот негатив...")
    await asyncio.sleep(1)  # Имитация работы
    await message.answer("Готово. Пепел развеян. Как ты сейчас? Сделай глубокий вдох.")
    await state.clear()

# --- AI СОВЕТЫ ---
@router.callback_query(F.data == "sos_ai_chat")
async def sos_ai_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🤖 <b>AI-Психолог</b>\n\n"
        "Опиши свою ситуацию одним предложением. "
        "Я поищу ответ в базе знаний или дам совет из общей практики.\n\n"
        "Например: <i>«Как успокоиться перед совещанием?»</i>",
        parse_mode="HTML"
    )
    await state.set_state(AIState.waiting_for_query)
    await callback.answer()

@router.message(AIState.waiting_for_query)
async def process_ai_query(message: types.Message, state: FSMContext):
    wait_msg = await message.answer("⏳ Думаю...")
    
    # Запрос к Groq (RAG)
    try:
        # Сначала ищем в базе знаний (если настроил RAG)
        # context = await db.search_knowledge_base(...) 
        # Пока без поиска, просто LLM
        response = await get_ai_response(message.text) 
        await wait_msg.edit_text(response)
    except Exception as e:
        await wait_msg.edit_text("Ошибка связи с нейросетью. Попробуй позже.")
        print(e)
        
    await state.clear()
