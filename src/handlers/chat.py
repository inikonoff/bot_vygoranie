# src/handlers/chat.py
from aiogram import Router, F, types
from aiogram.types import Message
from src.services.llm import get_groq_response # Предполагаем, что у тебя есть этот файл
# Если llm.py нет, ниже я дам его код

router = Router()

@router.message(F.text)
async def chat_logic(message: Message):
    """
    Ловит любое текстовое сообщение, которое не является командой.
    """
    user_text = message.text
    
    # Отправляем "печатает...", чтобы юзер видел активность
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # Отправляем запрос в Groq (LLM)
        # Если у тебя нет RAG (базы знаний), просто шлем текст
        response_text = await get_groq_response(user_text) 
        await message.answer(response_text)
    except Exception as e:
        await message.answer(f"Произошла ошибка при обращении к нейросети: {e}")
