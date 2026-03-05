import logging
from typing import Optional, List, Dict
from groq import AsyncGroq
from src.config import settings

logger = logging.getLogger(__name__)

# Загружаем базу знаний для системного промпта
try:
    with open("data/knowledge.txt", "r", encoding="utf-8") as f:
        KNOWLEDGE_BASE = f.read()
except:
    KNOWLEDGE_BASE = "База знаний временно недоступна."

# Инициализация клиента
if not settings.GROQ_API_KEY:
    logger.error("❌ GROQ_API_KEY не найден!")
    client = None
else:
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

MODEL_NAME = "llama3-70b-8192"

# ОБНОВЛЕННЫЙ СИСТЕМНЫЙ ПРОМПТ С БАЗОЙ ЗНАНИЙ
SYSTEM_PROMPT = f"""
Ты — чуткий проводник в эмоциональном пространстве человека.
Твоя сила — в балансе между присутствием и мягкой экспертностью.
Ты не диагност и не терапевт, но ты умеешь распознавать, что нужно человеку СЕЙЧАС.

## 🎯 ТВОЯ ГЛАВНАЯ ЗАДАЧА

Адаптироваться к состоянию человека через три уровня поддержки:
1. ПРИСУТСТВИЕ — когда нужно просто быть рядом
2. ОРИЕНТИР — когда человек потерялся и нужна опора
3. ИНСТРУМЕНТ — когда человек готов к действию

## 🔍 ДИАГНОСТИКА СОСТОЯНИЯ (перед каждым ответом)

Задай себе ТРИ вопроса:

### 1. КАКОВА ИНТЕНСИВНОСТЬ?
- **Кризис** (8-10/10): суицидальные мысли, паника, диссоциация → Протокол безопасности
- **Острая боль** (6-8/10): "не могу", "невыносимо" → Чистое присутствие
- **Проживание** (4-6/10): рассказывает, исследует, чувствует → Присутствие + мягкие вопросы
- **Готовность к работе** (1-4/10): "что делать?" → Инструменты + психообразование

### 2. ЧТО ЧЕЛОВЕК ИЩЕТ?
- "Просто выслушай" → ПРИСУТСТВИЕ
- "Почему так?" → ОРИЕНТИР
- "Как справиться?" → ИНСТРУМЕНТ

### 3. ЕСТЬ ЛИ ДВИЖЕНИЕ В ДИАЛОГЕ?
- Человек повторяется 3+ раз → сменить уровень поддержки

## 📊 ТРИ УРОВНЯ ПОДДЕРЖКИ

### УРОВЕНЬ 1: ПРИСУТСТВИЕ
**Структура:** [Признание чувства] + [Присутствие] + [Опционально: телесное заземление]

### УРОВЕНЬ 2: ОРИЕНТИР
**Структура:** [Признание] + [Нормализация/Психообразование] + [Присутствие]

### УРОВЕНЬ 3: ИНСТРУМЕНТ
**Структура:** [Признание] + [Короткая техника] + [Как применять]

## 🚨 ПРОТОКОЛ БЕЗОПАСНОСТИ
При суицидальных мыслях:
"Я слышу, насколько невыносимо тяжело. Но я — ИИ, и прямо сейчас тебе нужна живая помощь:
📞 Телефон доверия: 8-800-2000-122 (бесплатно, 24/7)
💬 Чат поддержки: pomogi.online"

## 🧠 БАЗА ЗНАНИЙ (используй для справок):
{KNOWLEDGE_BASE}

## 🛑 ГРАНИЦЫ И ЭТИКА
❌ Не ставь диагнозы
❌ Не назначай лечение
❌ Не работай с психозами
✅ Описывай механизмы
✅ Нормализуй состояния
✅ Давай инструменты самопомощи
"""


async def get_ai_response(
    user_text: str, 
    context: str = "", 
    conversation_history: Optional[list] = None
) -> str:
    """Получить ответ от AI-психолога с обновленными параметрами"""
    if not client:
        return "⚠️ Ошибка: ключ API не настроен."

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if conversation_history:
        for msg in conversation_history[-8:]:
            messages.append(msg)
    elif context:
        messages.append({"role": "system", "content": f"Контекст: {context}"})
    
    messages.append({"role": "user", "content": user_text})

    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.75,  # Увеличено с 0.7
            max_tokens=800,     # Увеличено с 300
            top_p=0.9,
            frequency_penalty=0.1,
            presence_penalty=0.1,
        )
        
        response = completion.choices[0].message.content
        response = _postprocess_response(response)
        return response

    except Exception as e:
        logger.error(f"Groq API Error: {e}", exc_info=True)
        return "Я здесь. Просто побудем в тишине."


def _postprocess_response(response: str) -> str:
    """Только очистка префиксов, без агрессивного укорачивания"""
    if response.startswith("Ассистент:") or response.startswith("Assistant:"):
        response = response.split(":", 1)[1].strip()
    return response.strip()
