import logging
from groq import AsyncGroq
from config import config

# Настраиваем логгер
logger = logging.getLogger(__name__)

# Инициализация клиента
if not config.GROQ_API_KEY:
    logger.error("❌ GROQ_API_KEY не найден в переменных окружения!")
    client = None
else:
    # Используем асинхронный клиент для высокой производительности
    client = AsyncGroq(api_key=config.GROQ_API_KEY)

SYSTEM_PROMPT = """
Ты — эмпатичный, профессиональный психолог-консультант. 
Твоя цель — снизить тревогу пользователя, валидировать его чувства (показать, что они нормальны) и предложить конструктивное действие.

Правила:
1. Будь краток (максимум 4-5 предложений).
2. Не используй сложные термины без объяснения.
3. Не ставь диагнозы.
4. Если ситуация выглядит как кризисная (суицид, насилие), настоятельно рекомендуй обратиться к врачу и дай понять, что ты всего лишь бот.
5. Стиль общения: теплый, поддерживающий, на "вы".
"""

async def get_ai_response(user_text: str, context: str = "") -> str:
    """
    Отправляет запрос в Groq API (модель Llama 3 или Mixtral).
    user_text: сообщение пользователя.
    context: найденные через RAG куски из методичек (пока может быть пустым).
    """
    if not client:
        return "⚠️ Ошибка конфигурации: Отсутствует ключ API нейросети."

    # Формируем историю сообщений
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    
    # Если мы нашли релевантную информацию в базе знаний (RAG)
    if context:
        messages.append({
            "role": "system", 
            "content": f"Используй следующую информацию из проверенных методичек для ответа, если она подходит:\n{context}"
        })
        
    messages.append({"role": "user", "content": user_text})

    try:
        completion = await client.chat.completions.create(
            model="llama3-8b-8192", # Быстрая и умная модель
            messages=messages,
            temperature=0.6,        # Баланс между креативностью и точностью
            max_tokens=400,         # Ограничение длины ответа
        )
        
        return completion.choices[0].message.content

    except Exception as e:
        logger.error(f"Groq API Error: {e}")
        return (
            "Извините, сейчас я чувствую перегрузку сетей. "
            "Попробуйте выполнить дыхательное упражнение из меню SOS, пока я восстанавливаюсь."
        )
