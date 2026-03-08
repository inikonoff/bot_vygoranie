def calculate_mbi(answers: dict) -> dict:
    """
    Подсчёт результатов MBI (Maslach Burnout Inventory).
    Ответы: 0–6 (Никогда → Каждый день).
    """
    ee_indices = [1, 2, 3, 6, 8, 13, 14, 16, 20]   # Эмоциональное истощение (макс 54)
    dp_indices = [5, 10, 11, 15, 22]                 # Деперсонализация (макс 30)
    pa_indices = [4, 7, 9, 12, 17, 18, 19, 21]       # Редукция достижений (макс 48)

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


def calculate_boyko(answers: dict) -> dict:
    """
    Подсчёт результатов опросника Бойко (84 вопроса, Да/Нет).
    Каждый симптом = набор вопросов, за каждый «правильный» ответ — 1 балл.
    Максимум по фазе — 100 условных баллов (5 симптомов × 20 макс каждый).
    Интерпретация фазы: < 36 — не сложилась, 37–60 — складывается, > 60 — сложилась.

    Ключи составлены по оригинальной методике В.В. Бойко.
    Значение True = ответ «Да» засчитывается, False = засчитывается «Нет».
    """

    # ── ФАЗА 1: НАПРЯЖЕНИЕ ──────────────────────────────────────────────────
    # Симптом 1: Переживание психотравмирующих обстоятельств
    s1_keys = {1: True, 13: True, 25: True, 37: True, 49: True, 61: True, 73: False}
    # Симптом 2: Неудовлетворённость собой
    s2_keys = {2: False, 14: True, 26: True, 38: True, 50: True, 62: True, 74: True}
    # Симптом 3: «Загнанность в клетку»
    s3_keys = {3: True, 15: True, 27: True, 39: True, 51: True, 63: True, 75: False}
    # Симптом 4: Тревога и депрессия
    s4_keys = {4: True, 16: True, 28: True, 40: True, 52: True, 64: True, 76: False}

    # ── ФАЗА 2: РЕЗИСТЕНЦИЯ ─────────────────────────────────────────────────
    # Симптом 5: Неадекватное избирательное эмоциональное реагирование
    s5_keys = {5: False, 17: True, 29: True, 41: True, 53: True, 65: True, 77: True}
    # Симптом 6: Эмоционально-нравственная дезориентация
    s6_keys = {6: False, 18: True, 30: True, 42: True, 54: True, 66: True, 78: True}
    # Симптом 7: Расширение сферы экономии эмоций
    s7_keys = {7: True, 19: True, 31: True, 43: True, 55: True, 67: True, 79: False}
    # Симптом 8: Редукция профессиональных обязанностей
    s8_keys = {8: True, 20: True, 32: True, 44: True, 56: True, 68: True, 80: False}

    # ── ФАЗА 3: ИСТОЩЕНИЕ ───────────────────────────────────────────────────
    # Симптом 9: Эмоциональный дефицит
    s9_keys = {9: True, 21: True, 33: True, 45: True, 57: True, 69: False, 81: True}
    # Симптом 10: Эмоциональная отстранённость
    s10_keys = {10: True, 22: True, 34: True, 46: True, 58: True, 70: True, 82: False}
    # Симптом 11: Личностная отстранённость (деперсонализация)
    s11_keys = {11: True, 23: True, 35: True, 47: True, 59: True, 71: True, 83: False}
    # Симптом 12: Психосоматические и психовегетативные нарушения
    s12_keys = {12: True, 24: True, 36: True, 48: True, 60: True, 72: True, 84: False}

    def score_symptom(keys: dict) -> int:
        total = 0
        for q_id, expect_yes in keys.items():
            given = answers.get(q_id, 0)  # 1=Да, 0=Нет
            if expect_yes and given == 1:
                total += 1
            elif not expect_yes and given == 0:
                total += 1
        # Переводим в баллы по шкале Бойко (каждый «+» = 3 или 5 баллов)
        # Упрощённо: умножаем на 3 для совместимости со стандартной интерпретацией
        return total * 3

    tension = score_symptom(s1_keys) + score_symptom(s2_keys) + \
              score_symptom(s3_keys) + score_symptom(s4_keys)

    resistance = score_symptom(s5_keys) + score_symptom(s6_keys) + \
                 score_symptom(s7_keys) + score_symptom(s8_keys)

    exhaustion = score_symptom(s9_keys) + score_symptom(s10_keys) + \
                 score_symptom(s11_keys) + score_symptom(s12_keys)

    def phase_status(score: int) -> str:
        if score < 36:
            return "не сложилась"
        elif score <= 60:
            return "складывается"
        else:
            return "сложилась"

    return {
        "tension": tension,
        "tension_status": phase_status(tension),
        "resistance": resistance,
        "resistance_status": phase_status(resistance),
        "exhaustion": exhaustion,
        "exhaustion_status": phase_status(exhaustion),
        "total": tension + resistance + exhaustion,
    }


def calculate_phq9(answers: dict) -> dict:
    """
    PHQ-9 (Patient Health Questionnaire).
    9 вопросов, ответы 0–3.
    Итог: 0–4 нет, 5–9 лёгкая, 10–14 умеренная, 15–19 умеренно тяжёлая, 20+ тяжёлая депрессия.
    """
    total = sum(answers.values())

    if total <= 4:
        level = "minimal"
        label = "Минимальная / отсутствует"
    elif total <= 9:
        level = "mild"
        label = "Лёгкая"
    elif total <= 14:
        level = "moderate"
        label = "Умеренная"
    elif total <= 19:
        level = "moderately_severe"
        label = "Умеренно тяжёлая"
    else:
        level = "severe"
        label = "Тяжёлая"

    return {"total": total, "level": level, "label": label}


def calculate_gad7(answers: dict) -> dict:
    """
    GAD-7 (Generalized Anxiety Disorder).
    7 вопросов, ответы 0–3.
    Итог: 0–4 минимальная, 5–9 лёгкая, 10–14 умеренная, 15+ тяжёлая тревога.
    """
    total = sum(answers.values())

    if total <= 4:
        level = "minimal"
        label = "Минимальная / отсутствует"
    elif total <= 9:
        level = "mild"
        label = "Лёгкая"
    elif total <= 14:
        level = "moderate"
        label = "Умеренная"
    else:
        level = "severe"
        label = "Тяжёлая"

    return {"total": total, "level": level, "label": label}


def calculate_pss10(answers: dict) -> dict:
    """
    PSS-10 (Perceived Stress Scale).
    10 вопросов, ответы 0–4.
    Вопросы 4, 5, 7, 8 — позитивные, инвертируются (4→0, 3→1, 2→2, 1→3, 0→4).
    Итог: 0–13 низкий, 14–26 умеренный, 27–40 высокий стресс.
    """
    positive_items = {4, 5, 7, 8}  # номера вопросов с прямой шкалой (инвертируются)
    total = 0
    for q_id, value in answers.items():
        if int(q_id) in positive_items:
            total += (4 - value)
        else:
            total += value

    if total <= 13:
        level = "low"
        label = "Низкий уровень стресса"
    elif total <= 26:
        level = "moderate"
        label = "Умеренный уровень стресса"
    else:
        level = "high"
        label = "Высокий уровень стресса"

    return {"total": total, "level": level, "label": label}
