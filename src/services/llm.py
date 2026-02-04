from groq import Groq
from config import config

# Инициализация с проверкой ключа
if not config.GROQ_API_KEY:
    print("❌ ОШИБКА: Не найден GROQ_API_KEY в .env!")
    client = None
else:
    client = Groq(api_key=config.GROQ_API_KEY)

SYSTEM_PROMPT = """
Ты — эмпатичный психолог. Твоя задача — поддержать и успокоить.
Отвечай кратко (не более 3-4 предложений).
Не используй сложные термины.
"""

async def get_ai_response(user_text: str, context: str = ""):
    if not client:
        return "⚠️ Ошибка настройки: нет API ключа нейросети."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    
    # Если есть контекст из RAG
    if context:
        messages.append({"role": "system", "content": f"Опирайся на эту методичку: {context}"})
        
    messages.append({"role": "user", "content": user_text})

    try:
        print(f"📡 Отправляю запрос в Groq: {user_text[:50]}...") # Лог в консоль
        
        # Важно: используем асинхронный вызов, если библиотека позволяет, 
        # но стандартный клиент Groq синхронный. 
        # Чтобы не блокировать бота, лучше запускать его в executor, 
        # но для теста оставим так.
        
        completion = client.chat.completions.create(
            model="llama3-8b-8192", 
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        
        answer = completion.choices[0].message.content
        print("✅ Ответ от Groq получен!")
        return answer

    except Exception as e:
        error_msg = f"❌ Ошибка Groq: {str(e)}"
        print(error_msg) # Увидишь это в логах Render
        return "Извини, мои нейроны сейчас перегружены. Попробуй спросить позже."
