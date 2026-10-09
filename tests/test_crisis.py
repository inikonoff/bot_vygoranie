from src.services.crisis import is_crisis


def test_detects_crisis_phrases():
    for t in ["Я не хочу жить", "думаю о самоубийстве", "хочу умереть", "Хочу ИСЧЕЗНУТЬ"]:
        assert is_crisis(t), t


def test_ignores_ordinary_text():
    for t in ["устал на работе", "хочу в отпуск", "", None]:
        assert not is_crisis(t), t
