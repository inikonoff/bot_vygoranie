def calculate_mbi(answers: dict):
    """
    Расчет MBI (Maslach Burnout Inventory)
    Ключи из PDF 1 стр 2
    Ответы приходят 0-6
    """
    ee_indices = [1, 2, 3, 6, 8, 13, 14, 16, 20]  # Эмоциональное истощение
    dp_indices = [5, 10, 11, 15, 22]              # Деперсонализация
    pa_indices = [4, 7, 9, 12, 17, 18, 19, 21]    # Редукция достижений (обратная шкала)

    scores = {"ee": 0, "dp": 0, "pa": 0}

    for q_id, value in answers.items():
        q_id = int(q_id)
        if q_id in ee_indices:
            scores["ee"] += value
        elif q_id in dp_indices:
            scores["dp"] += value
        elif q_id in pa_indices:
            scores["pa"] += value

    return scores


# ПРАВИЛЬНЫЕ КЛЮЧИ ДЛЯ ТЕСТА БОЙКО (на основе методики)
BOYKO_KEYS = {
    "tension": {
        "переживание_психотравмирующих_обстоятельств": [1, 13, 25, 37, 49, 61, 73],
        "неудовлетворенность_собой": [2, 14, 26, 38, 50, 62, 74],
        "загнанность_в_клетку": [3, 15, 27, 39, 51, 63, 75],
        "тревога_и_депрессия": [4, 16, 28, 40, 52, 64, 76]
    },
    "resistance": {
        "неадекватное_эмоциональное_реагирование": [5, 17, 29, 41, 53, 65, 77],
        "эмоционально_нравственная_дезориентация": [6, 18, 30, 42, 54, 66, 78],
        "расширение_сферы_экономии_эмоций": [7, 19, 31, 43, 55, 67, 79],
        "редукция_профессиональных_обязанностей": [8, 20, 32, 44, 56, 68, 80]
    },
    "exhaustion": {
        "эмоциональный_дефицит": [9, 21, 33, 45, 57, 69, 81],
        "эмоциональная_отстраненность": [10, 22, 34, 46, 58, 70, 82],
        "личностная_отстраненность_деперсонализация": [11, 23, 35, 47, 59, 71, 83],
        "психосоматические_и_вегетативные_нарушения": [12, 24, 36, 48, 60, 72, 84]
    }
}


def calculate_boyko(answers: dict):
    """
    Расчет теста Бойко с правильными ключами
    answers: словарь {номер_вопроса: 1 (Да) или 0 (Нет)}
    
    Возвращает словарь с баллами по фазам и общий балл.
    """
    result = {
        "tension": 0,
        "resistance": 0,
        "exhaustion": 0,
        "total": sum(answers.values())
    }
    
    # Собираем все вопросы для каждой фазы
    tension_questions = []
    for symptom_list in BOYKO_KEYS["tension"].values():
        tension_questions.extend(symptom_list)
    
    resistance_questions = []
    for symptom_list in BOYKO_KEYS["resistance"].values():
        resistance_questions.extend(symptom_list)
    
    exhaustion_questions = []
    for symptom_list in BOYKO_KEYS["exhaustion"].values():
        exhaustion_questions.extend(symptom_list)
    
    # Суммируем баллы
    for q_id, val in answers.items():
        q_id = int(q_id)
        if val == 1:
            if q_id in tension_questions:
                result["tension"] += 1
            elif q_id in resistance_questions:
                result["resistance"] += 1
            elif q_id in exhaustion_questions:
                result["exhaustion"] += 1
    
    return result


def calculate_phq9(answers: dict):
    """
    Расчет PHQ-9 (скрининг депрессии)
    Шкала 0-3: 
    0 = Никогда
    1 = Несколько дней
    2 = Более половины дней
    3 = Почти каждый день
    
    Итоговый балл 0-27
    """
    total = sum(answers.values())
    
    if total <= 4:
        level = "минимальная или отсутствует"
    elif total <= 9:
        level = "легкая депрессия"
    elif total <= 14:
        level = "умеренная депрессия"
    elif total <= 19:
        level = "умеренно тяжелая депрессия"
    else:
        level = "тяжелая депрессия"
    
    return {
        "total": total,
        "level": level,
        "scores": answers
    }


def calculate_gad7(answers: dict):
    """
    Расчет GAD-7 (скрининг тревоги)
    Шкала 0-3: 
    0 = Никогда
    1 = Несколько дней
    2 = Более половины дней
    3 = Почти каждый день
    
    Итоговый балл 0-21
    """
    total = sum(answers.values())
    
    if total <= 4:
        level = "минимальная тревога"
    elif total <= 9:
        level = "легкая тревога"
    elif total <= 14:
        level = "умеренная тревога"
    else:
        level = "тяжелая тревога"
    
    return {
        "total": total,
        "level": level,
        "scores": answers
    }


def calculate_pss10(answers: dict):
    """
    Расчет PSS-10 (шкала воспринимаемого стресса)
    Вопросы 4,5,7,8 - обратная шкала (0-4)
    
    Шкала ответов:
    0 = Никогда
    1 = Почти никогда
    2 = Иногда
    3 = Довольно часто
    4 = Очень часто
    
    Итоговый балл 0-40
    """
    reverse_items = [4, 5, 7, 8]
    total = 0
    
    for q_id, value in answers.items():
        q_id = int(q_id)
        if q_id in reverse_items:
            total += (4 - value)  # инвертируем для вопросов с положительной формулировкой
        else:
            total += value
    
    # Интерпретация
    if total <= 13:
        level = "низкий уровень стресса"
    elif total <= 26:
        level = "средний уровень стресса"
    else:
        level = "высокий уровень стресса"
    
    return {
        "total": total,
        "level": level,
        "scores": answers
    }
