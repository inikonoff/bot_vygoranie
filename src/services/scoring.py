
def calculate_mbi(answers: dict):
    # Ключи из PDF 1 стр 2
    # Ответы приходят 0-6
    ee_indices = [1, 2, 3, 6, 8, 13, 14, 16, 20] # Эмоциональное истощение
    dp_indices = [5, 10, 11, 15, 22]             # Деперсонализация
    pa_indices = [4, 7, 9, 12, 17, 18, 19, 21]   # Редукция достижений (обратная шкала)

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
