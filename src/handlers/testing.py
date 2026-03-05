import json
import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.keyboards import builders
from src.services.scoring import (
    calculate_mbi, calculate_boyko, calculate_phq9, 
    calculate_gad7, calculate_pss10
)
from src.database.supabase_client import db
from src.states import TestStates
from src.services.llm import client, MODEL_NAME

logger = logging.getLogger(__name__)
router = Router()

# Загрузка вопросов
try:
    with open("data/mbi_test.json", "r", encoding="utf-8") as f:
        MBI_QUESTIONS = json.load(f)
except:
    MBI_QUESTIONS = []
    logger.error("Failed to load mbi_test.json")

try:
    with open("data/boyko_test.json", "r", encoding="utf-8") as f:
        BOYKO_QUESTIONS = json.load(f)
except:
    BOYKO_QUESTIONS = []
    logger.error("Failed to load boyko_test.json")

try:
    with open("data/phq9_test.json", "r", encoding="utf-8") as f:
        PHQ9_QUESTIONS = json.load(f)
except:
    PHQ9_QUESTIONS = []
    logger.error("Failed to load phq9_test.json")

try:
    with open("data/gad7_test.json", "r", encoding="utf-8") as f:
        GAD7_QUESTIONS = json.load(f)
except:
    GAD7_QUESTIONS = []
    logger.error("Failed to load gad7_test.json")

try:
    with open("data/pss10_test.json", "r", encoding="utf-8") as f:
        PSS10_QUESTIONS = json.load(f)
except:
    PSS10_QUESTIONS = []
    logger.error("Failed to load pss10_test.json")


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

async def analyze_test_result_with_llm(test_type: str, scores: dict, user_id: int) -> str:
    """Отправляет результаты теста в LLM для получения развернутого анализа"""
    
    if not client:
        return "Анализ временно недоступен."
    
    prompts = {
        "mbi": f"""
        Проанализируй результаты теста MBI (Maslach Burnout Inventory) и дай развернутый ответ из 3-4 абзацев.
        
        Результаты:
        - Эмоциональное истощение (EE): {scores['ee']} баллов (норма < 16)
        - Деперсонализация/Цинизм (DP): {scores['dp']} баллов (норма < 9)
        - Редукция достижений (PA): {scores['pa']} баллов (норма > 30)
        
        В ответе:
        1. Объясни простым языком, что означают эти цифры
        2. На что обратить внимание в первую очередь
        3. Дай 2-3 конкретных совета, что делать дальше
        """,
        
        "boyko": f"""
        Проанализируй результаты теста Бойко на эмоциональное выгорание.
        
        Результаты по фазам:
        - Фаза напряжения: {scores['tension']} баллов
        - Фаза резистенции (сопротивления): {scores['resistance']} баллов
        - Фаза истощения: {scores['exhaustion']} баллов
        
        Дай развернутый анализ:
        1. Что показывает каждая фаза
        2. Какие симптомы характерны для этих значений
        3. Что делать в первую очередь
        """,
        
        "phq9": f"""
        Проанализируй результаты теста PHQ-9 (скрининг депрессии).
        
        Общий балл: {scores['total']}
        Уровень: {scores['level']}
        
        Дай развернутый анализ и рекомендации.
        """,
        
        "gad7": f"""
        Проанализируй результаты теста GAD-7 (скрининг тревоги).
        
        Общий балл: {scores['total']}
        Уровень: {scores['level']}
        
        Дай развернутый анализ и рекомендации.
        """,
        
        "pss10": f"""
        Проанализируй результаты теста PSS-10 (шкала воспринимаемого стресса).
        
        Общий балл: {scores['total']}
        Уровень: {scores['level']}
        
        Дай развернутый анализ и рекомендации по снижению стресса.
        """
    }
    
    if test_type not in prompts:
        return "Неизвестный тип теста."
    
    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Ты - психолог, который дает развернутые, понятные и поддерживающие анализы результатов тестов. Используй теплый, эмпатичный тон."},
                {"role": "user", "content": prompts[test_type]}
            ],
            temperature=0.7,
            max_tokens=700  # Для развернутого ответа
        )
        
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM analysis error: {e}")
        return "Не удалось получить развернутый анализ. Пожалуйста, попробуйте позже."


# ============================================================================
# МЕНЮ ДИАГНОСТИКИ
# ============================================================================

@router.message(F.text == "📊 Диагностика")
async def diagnostic_menu_handler(message: types.Message):
    """Показывает меню выбора теста"""
    await message.answer(
        "📋 **Выберите тип диагностики**\n\n"
        "• **MBI** - профессиональное выгорание (22 вопроса)\n"
        "• **PHQ-9** - скрининг депрессии (9 вопросов)\n"
        "• **GAD-7** - скрининг тревоги (7 вопросов)\n"
        "• **PSS-10** - уровень стресса (10 вопросов)\n"
        "• **Тест Бойко** - глубокая диагностика выгорания (84 вопроса)",
        reply_markup=builders.diagnostic_menu(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("diag_"))
async def process_diagnostic_choice(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора теста из меню"""
    test_type = callback.data.split("_")[1]
    
    if test_type == "mbi":
        await start_mbi(callback.message, state)
    elif test_type == "boyko":
        await start_boyko(callback.message, state)
    elif test_type == "phq9":
        await start_phq9(callback.message, state)
    elif test_type == "gad7":
        await start_gad7(callback.message, state)
    elif test_type == "pss10":
        await start_pss10(callback.message, state)
    elif test_type == "my_results":
        await show_my_results(callback.message)
    
    await callback.answer()


# ============================================================================
# MBI (Maslach Burnout Inventory)
# =========================================================================
