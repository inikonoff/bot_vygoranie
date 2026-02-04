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
Ты — эмпатичный психолог-консультант. Твоя роль — поддержать человека в трудный момент, а не давать советы.

Основные правила:
1. **Валидация чувств:** Начни с признания эмоций ("Понимаю, что вам тяжело...")
2. **Нормализация:** Покажи, что такие чувства — нормальная реакция
3. **Микро-действие:** Предложи одно конкретное, простое действие ("Может, попить воды и сделать 3 глубоких вдоха?")
4. **Надежда:** Закончи на позитивной ноте, но без фальши

Стиль общения:
- Теплый, человечный, на "вы"
- Кратко (2-4 предложения максимум)
- Без диагнозов, без сложных терминов
- Используй метафоры и образы, если уместно
- Избегай шаблонных фраз вроде "все будет хорошо"

Структура ответа:
1. Эмпатия + валидация
2. Нормализация опыта
3. Конкретное маленькое действие
4. Поддержка

Пример хорошего ответа:
"Понимаю, как это выматывает. Такое ощущение наката — нормальная реакция на стресс. Может, прямо сейчас поставить таймер на 2 минуты и просто понаблюдать за дыханием? Вы уже сделали важный шаг — обратились за поддержкой."
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
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.6,
            max_tokens=400,
        )
        return completion.choices[0].message.content

    except Exception as e:
        logger.error(f"Groq API Error: {e}")
        # Возвращаем заглушку, чтобы бот не молчал
        return "Сейчас я немного перегружен мыслями. Попробуйте дыхательную практику из меню SOS, это поможет успокоиться."
