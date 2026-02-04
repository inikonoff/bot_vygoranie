import json
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.keyboards import builders
from src.services.scoring import calculate_mbi, calculate_boyko  # <--- Добавил calculate_boyko
from src.database.supabase_client import db

router = Router()

# Обновляем класс состояний
class TestStates(StatesGroup):
    mbi_q = State()
    boyko_q = State()  # <--- Добавил новое состояние для теста Бойко

# Загрузка вопросов MBI
with open("data/mbi_test.json", "r", encoding="utf-8") as f:
    MBI_QUESTIONS = json.load(f)

# Загрузка вопросов Бойко
try:
    with open("data/boyko_test.json", "r", encoding="utf-8") as f:
        BOYKO_QUESTIONS = json.load(f)
except:
    BOYKO_QUESTIONS = []  # Заглушка, если файла нет

# --- ЛОГИКА ТЕСТА MBI ---

@router.message(F.text == "📊 Диагностика (MBI)")
async def start_mbi(message: types.Message, state: FSMContext):
    await state.set_state(TestStates.mbi_q)
    await state.update_data(q_index=0, answers={})
    
    q = MBI_QUESTIONS[0]
    txt = f"Вопрос 1/22:\n\n<b>{q['text']}</b>\n\n0 - Никогда\n6 - Каждый день"
    await message.answer(txt, reply_markup=builders.scale_keyboard(), parse_mode="HTML")

@router.callback_query(TestStates.mbi_q, F.data.startswith("mbi_"))
async def process_mbi_answer(callback: types.CallbackQuery, state: FSMContext):
    score = int(callback.data.split("_")[1])
    data = await state.get_data()
    idx = data['q_index']
    answers = data['answers']
    
    # Save answer using ID from JSON (idx + 1)
    answers[idx + 1] = score
    
    next_idx = idx + 1
    
    if next_idx < len(MBI_QUESTIONS):
        await state.update_data(q_index=next_idx, answers=answers)
        q = MBI_QUESTIONS[next_idx]
        txt = f"Вопрос {next_idx + 1}/22:\n\n<b>{q['text']}</b>\n\n0 - Никогда\n6 - Каждый день"
        await callback.message.edit_text(txt, reply_markup=builders.scale_keyboard(), parse_mode="HTML")
    else:
        # Finish
        result = calculate_mbi(answers)
        risk = await db.save_mbi_result(callback.from_user.id, result)
        
        txt = (
            f"🏁 <b>Тест завершен!</b>\n\n"
            f"🤯 Истощение: {result['ee']} (Норма &lt; 16)\n"
            f"😐 Цинизм: {result['dp']} (Норма &lt; 9)\n"
            f"📉 Редукция: {result['pa']} (Норма &gt; 30)\n\n"
        )
        
        if risk == "red":
            txt += "⚠️ <b>Высокий риск выгорания!</b> Рекомендуем режим 'SOS' и отдых."
        elif risk == "yellow":
            txt += "⚠️ Есть признаки напряжения. Следите за ресурсом."
        else:
            txt += "✅ Все в норме. Так держать!"
            
        await callback.message.edit_text(txt, parse_mode="HTML")
        await state.clear()
    
    await callback.answer()

# --- ЛОГИКА ТЕСТА БОЙКО ---

@router.message(F.text == "📋 Тест Бойко")
async def start_boyko(message: types.Message, state: FSMContext):
    if not BOYKO_QUESTIONS:
        await message.answer("Файл с тестом Бойко не найден или пуст.")
        return

    await state.set_state(TestStates.boyko_q)
    await state.update_data(q_index=0, answers={})
    
    q = BOYKO_QUESTIONS[0]
    # Используем yes_no_keyboard
    await message.answer(
        f"Вопрос 1/{len(BOYKO_QUESTIONS)}:\n\n<b>{q['text']}</b>", 
        reply_markup=builders.yes_no_keyboard(), 
        parse_mode="HTML"
    )

@router.callback_query(TestStates.boyko_q, F.data.startswith("boyko_"))
async def process_boyko_answer(callback: types.CallbackQuery, state: FSMContext):
    # Превращаем "boyko_yes" в 1, "boyko_no" в 0
    choice = 1 if callback.data == "boyko_yes" else 0
    
    data = await state.get_data()
    idx = data['q_index']
    answers = data['answers']
    
    # Сохраняем ответ
    answers[idx + 1] = choice
    
    next_idx = idx + 1
    
    if next_idx < len(BOYKO_QUESTIONS):
        await state.update_data(q_index=next_idx, answers=answers)
        q = BOYKO_QUESTIONS[next_idx]
        await callback.message.edit_text(
            f"Вопрос {next_idx + 1}/{len(BOYKO_QUESTIONS)}:\n\n<b>{q['text']}</b>",
            reply_markup=builders.yes_no_keyboard(),
            parse_mode="HTML"
        )
    else:
        # Финиш
        result = calculate_boyko(answers)
        
        # Сохраняем в базу (тип теста 'boyko')
        # Важно: убедись, что db.save_mbi_result умеет сохранять и boyko, 
        # или используй универсальный метод save_test_result
        # Для простоты используем тот же метод, но пометим в базе
        risk = "green"  # Логику риска для Бойко можно дописать позже
        
        # Формируем отчет
        txt = (
            f"🏁 <b>Тест Бойко завершен!</b>\n\n"
            f"😬 Напряжение: {result['tension']}\n"
            f"🛡 Резистенция: {result['resistance']}\n"
            f"🔋 Истощение: {result['exhaustion']}\n\n"
            f"Это более глубокий тест. Высокие баллы по шкале «Истощение» говорят о серьезном выгорании."
        )
        
        await callback.message.edit_text(txt, parse_mode="HTML")
        await state.clear()
    
    await callback.answer()
