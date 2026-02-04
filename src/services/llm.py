import logging
from groq import AsyncGroq
from config import config

logger = logging.getLogger(__name__)

if not config.GROQ_API_KEY:
    logger.error("❌ GROQ_API_KEY не найден!")
    client = None
else:
    client = AsyncGroq(api_key=config.GROQ_API_KEY)

# Базовая инструкция
BASE_PROMPT = """
Ты — эмпатичный психолог-консультант.
Твоя цель — снизить тревогу, валидировать чувства и предложить действие.
Правила:
1. Будь краток (3-4 предложения).
2. Без сложных терминов.
3. Не ставь диагнозы.
4. Стиль: теплый, на "вы".
"""

async def get_ai_response(user_text: str, context: str = "") -> str:
    if not client:
        return "⚠️ Ошибка: нет ключа API."

    # --- ИСПРАВЛЕНИЕ ОШИБКИ 400 ---
    # Объединяем инструкцию и контекст в ОДНО системное сообщение.
    # Llama 3 не любит, когда system messages идут списком.
    
    full_system_content = BASE_PROMPT
    
    if context:
        full_system_content += f"\n\nИСПОЛЬЗУЙ ЭТУ ИНФОРМАЦИЮ ДЛЯ ОТВЕТА:\n{context}"

    messages = [
        {"role": "system", "content": full_system_content},
        {"role": "user", "content": user_text}
    ]

    try:
        completion = await client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.6,
            max_tokens=400,
        )
        return completion.choices[0].message.content

    except Exception as e:
        logger.error(f"Groq API Error: {e}")
        # Возвращаем заглушку, чтобы бот не молчал
        return "Сейчас я немного перегружен мыслями. Попробуйте дыхательную практику из меню SOS, это поможет успокоиться."
