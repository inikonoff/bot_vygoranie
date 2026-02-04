def calculate_mbi(answers: dict):
    # Ключи из PDF 1 стр 2
    # Ответы приходят 0-6
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


def calculate_boyko(answers: dict):
    """
    answers: словарь {номер_вопроса: 1 (Да) или 0 (Нет)}
    В реальности здесь должны быть ключи (номера вопросов) для каждой фазы.
    Для старта мы просто посчитаем общее количество "Да".
    """

    # В будущем сюда надо вписать точные номера вопросов из PDF для каждой фазы
    # Пока считаем упрощенно:
    total_yes = sum(answers.values())

    # Примерная интерпретация (заглушка для логики)
    # В реальности макс балл = 84.
    result = {
        "tension": 0,      # Напряжение
        "resistance": 0,   # Резистенция
        "exhaustion": 0,   # Истощение
        "total": total_yes
    }

    # Простая логика распределения (примерная!)
    # Допустим, вопросы 1-28 это напряжение, 29-56 резистенция, 57-84 истощение
    # Это нужно будет сверить с ключами из PDF, если нужна медицинская точность
    for q_id, val in answers.items():
        q_id_int = int(q_id)
        if val == 1:
            if q_id_int <= 28:
                result["tension"] += 1
            elif q_id_int <= 56:
                result["resistance"] += 1
            else:
                result["exhaustion"] += 1

    return result
