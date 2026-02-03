from groq import Groq
from config import config

client = Groq(api_key=config.GROQ_API_KEY)

SYSTEM_PROMPT = """
Ты — эмпатичный помощник по ментальному здоровью. 
Твоя задача — поддержать пользователя и дать рекомендацию на основе предоставленного контекста.
Не ставь диагнозы. Если ситуация критическая, советуй обратиться к врачу.
Будь краток и вежлив.
"""

async def get_ai_response(user_text: str, context: str = ""):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    
    if context:
        messages.append({"role": "system", "content": f"Используй эту информацию из методички: {context}"})
        
    messages.append({"role": "user", "content": user_text})

    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192", # Или mixtral-8x7b-32768
            messages=messages,
            temperature=0.6,
            max_tokens=500
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Groq Error: {e}")
        return "Извини, я сейчас немного перегружен. Попробуй позже или выбери упражнение из меню."
