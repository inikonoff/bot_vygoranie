import json
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.keyboards import builders
from src.services.scoring import calculate_mbi
from src.database.supabase_client import db

router = Router()

class TestStates(StatesGroup):
    mbi_q = State()

# Загрузка вопросов
with open("data/mbi_test.json", "r", encoding="utf-8") as f:
    MBI_QUESTIONS = json.load(f)

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
