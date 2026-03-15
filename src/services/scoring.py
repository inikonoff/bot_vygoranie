def calculate_mbi(answers: dict) -> dict:
    ee_indices = [1, 2, 3, 6, 8, 13, 14, 16, 20]
    dp_indices = [5, 10, 11, 15, 22]
    pa_indices = [4, 7, 9, 12, 17, 18, 19, 21]

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
    s1_keys  = {1: True, 13: True, 25: True, 37: True, 49: True, 61: True, 73: False}
    s2_keys  = {2: False, 14: True, 26: True, 38: True, 50: True, 62: True, 74: True}
    s3_keys  = {3: True, 15: True, 27: True, 39: True, 51: True, 63: True, 75: False}
    s4_keys  = {4: True, 16: True, 28: True, 40: True, 52: True, 64: True, 76: False}
    s5_keys  = {5: False, 17: True, 29: True, 41: True, 53: True, 65: True, 77: True}
    s6_keys  = {6: False, 18: True, 30: True, 42: True, 54: True, 66: True, 78: True}
    s7_keys  = {7: True, 19: True, 31: True, 43: True, 55: True, 67: True, 79: False}
    s8_keys  = {8: True, 20: True, 32: True, 44: True, 56: True, 68: True, 80: False}
    s9_keys  = {9: True, 21: True, 33: True, 45: True, 57: True, 69: False, 81: True}
    s10_keys = {10: True, 22: True, 34: True, 46: True, 58: True, 70: True, 82: False}
    s11_keys = {11: True, 23: True, 35: True, 47: True, 59: True, 71: True, 83: False}
    s12_keys = {12: True, 24: True, 36: True, 48: True, 60: True, 72: True, 84: False}

    def score_symptom(keys: dict) -> int:
        total = 0
        for q_id, expect_yes in keys.items():
            given = answers.get(q_id, 0)
            if expect_yes and given == 1:
                total += 1
            elif not expect_yes and given == 0:
                total += 1
        return total * 3

    tension    = sum(score_symptom(k) for k in [s1_keys, s2_keys, s3_keys, s4_keys])
    resistance = sum(score_symptom(k) for k in [s5_keys, s6_keys, s7_keys, s8_keys])
    exhaustion = sum(score_symptom(k) for k in [s9_keys, s10_keys, s11_keys, s12_keys])

    def phase_status(score: int) -> str:
        if score < 36:   return "не сложилась"
        elif score <= 60: return "складывается"
        else:             return "сложилась"

    return {
        "tension":           tension,
        "tension_status":    phase_status(tension),
        "resistance":        resistance,
        "resistance_status": phase_status(resistance),
        "exhaustion":        exhaustion,
        "exhaustion_status": phase_status(exhaustion),
        "total":             tension + resistance + exhaustion,
    }


def calculate_phq9(answers: dict) -> dict:
    total = sum(answers.values())
    if total <= 4:    level, label = "minimal",          "Минимальная / отсутствует"
    elif total <= 9:  level, label = "mild",             "Лёгкая"
    elif total <= 14: level, label = "moderate",         "Умеренная"
    elif total <= 19: level, label = "moderately_severe","Умеренно тяжёлая"
    else:             level, label = "severe",           "Тяжёлая"
    return {"total": total, "level": level, "label": label}


def calculate_gad7(answers: dict) -> dict:
    total = sum(answers.values())
    if total <= 4:    level, label = "minimal",  "Минимальная / отсутствует"
    elif total <= 9:  level, label = "mild",     "Лёгкая"
    elif total <= 14: level, label = "moderate", "Умеренная"
    else:             level, label = "severe",   "Тяжёлая"
    return {"total": total, "level": level, "label": label}


def calculate_pss10(answers: dict) -> dict:
    positive_items = {4, 5, 7, 8}
    total = 0
    for q_id, value in answers.items():
        if int(q_id) in positive_items:
            total += (4 - value)
        else:
            total += value
    if total <= 13:   level, label = "low",      "Низкий уровень стресса"
    elif total <= 26: level, label = "moderate", "Умеренный уровень стресса"
    else:             level, label = "high",     "Высокий уровень стресса"
    return {"total": total, "level": level, "label": label}


def calculate_uwes(answers: dict, questions: list) -> dict:
    """
    UWES-9. Ответы 0–6.
    Три шкалы: vigor (энергичность), dedication (энтузиазм), absorption (поглощённость).
    Средний балл по каждой шкале и общий.
    Уровни: 0–2.9 низкий, 3–4.9 средний, 5–6 высокий.
    """
    scale_sums = {"vigor": 0, "dedication": 0, "absorption": 0}
    scale_counts = {"vigor": 0, "dedication": 0, "absorption": 0}

    for q in questions:
        q_id = q["id"]
        scale = q["scale"]
        value = answers.get(q_id, 0)
        scale_sums[scale] += value
        scale_counts[scale] += 1

    def avg(scale):
        count = scale_counts[scale]
        return round(scale_sums[scale] / count, 2) if count else 0

    def level(score):
        if score < 3:   return "низкий"
        elif score < 5: return "средний"
        else:           return "высокий"

    vigor      = avg("vigor")
    dedication = avg("dedication")
    absorption = avg("absorption")
    total_avg  = round((vigor + dedication + absorption) / 3, 2)

    return {
        "vigor":            vigor,
        "vigor_level":      level(vigor),
        "dedication":       dedication,
        "dedication_level": level(dedication),
        "absorption":       absorption,
        "absorption_level": level(absorption),
        "total":            total_avg,
        "total_level":      level(total_avg),
    }


def calculate_osipov(answers: dict, questions: list) -> dict:
    """
    Опросник организационного стресса Осипова.
    Ответы 1–5.
    Шесть шкал: demands, control, manager_support, peer_support, role, change, reward.
    Обратные вопросы (негативные утверждения) инвертируются: 6 - value.
    Средний балл по шкале: 1–2.4 критично, 2.5–3.4 умеренно, 3.5–5 хорошо.
    """
    # Негативные утверждения — инвертируем
    reversed_items = {1, 2, 3, 4, 5, 6, 7, 12, 13, 18, 23, 28, 29, 34, 39}

    scale_sums   = {"demands": 0, "control": 0, "manager_support": 0,
                    "peer_support": 0, "role": 0, "change": 0, "reward": 0}
    scale_counts = {k: 0 for k in scale_sums}

    for q in questions:
        q_id  = q["id"]
        scale = q["scale"]
        value = answers.get(q_id, 3)
        if q_id in reversed_items:
            value = 6 - value
        scale_sums[scale]   += value
        scale_counts[scale] += 1

    def avg(scale):
        count = scale_counts[scale]
        return round(scale_sums[scale] / count, 2) if count else 0

    def level(score):
        if score < 2.5:  return "критично"
        elif score < 3.5: return "умеренно"
        else:             return "хорошо"

    SCALE_NAMES = {
        "demands":         "Рабочая нагрузка",
        "control":         "Контроль над работой",
        "manager_support": "Поддержка руководства",
        "peer_support":    "Поддержка коллег",
        "role":            "Ясность роли",
        "change":          "Управление изменениями",
        "reward":          "Вознаграждение и признание",
    }

    scales = {}
    for key in scale_sums:
        score = avg(key)
        scales[key] = {
            "name":  SCALE_NAMES[key],
            "score": score,
            "level": level(score),
        }

    all_scores = [scales[k]["score"] for k in scales]
    total_avg  = round(sum(all_scores) / len(all_scores), 2)

    # Находим самую проблемную шкалу
    worst_key   = min(scales, key=lambda k: scales[k]["score"])
    worst_scale = scales[worst_key]

    return {
        "scales":      scales,
        "total":       total_avg,
        "total_level": level(total_avg),
        "worst_scale": worst_scale["name"],
        "worst_score": worst_scale["score"],
    }
