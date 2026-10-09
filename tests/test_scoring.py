import json

from src.services import scoring as s


def test_mbi_scales():
    r = s.calculate_mbi({str(i): 6 for i in range(1, 23)})
    assert r == {"ee": 54, "dp": 30, "pa": 48}


def test_mbi_string_and_int_keys_equal():
    a = s.calculate_mbi({str(i): i % 7 for i in range(1, 23)})
    b = s.calculate_mbi({i: i % 7 for i in range(1, 23)})
    assert a == b


def test_phq9_and_gad7_levels():
    assert s.calculate_phq9({str(i): 0 for i in range(1, 10)})["level"] == "minimal"
    assert s.calculate_phq9({str(i): 3 for i in range(1, 10)})["level"] == "severe"
    assert s.calculate_gad7({str(i): 3 for i in range(1, 8)})["total"] == 21


def test_pss10_reverse_items():
    assert s.calculate_pss10({str(i): 4 for i in range(1, 11)})["total"] == 24
    assert s.calculate_pss10({str(i): 0 for i in range(1, 11)})["total"] == 16


def test_uwes_and_osipov_survive_json_roundtrip():
    uwes_q = json.load(open("data/uwes_test.json", encoding="utf-8"))
    osipov_q = json.load(open("data/osipov_test.json", encoding="utf-8"))
    answers_u = json.loads(json.dumps({i: 6 for i in range(1, 10)}))  # ключи -> str
    assert s.calculate_uwes(answers_u, uwes_q)["total"] == 6.0
    answers_o = json.loads(json.dumps({q["id"]: 5 for q in osipov_q}))
    r = s.calculate_osipov(answers_o, osipov_q)
    assert 1 <= r["total"] <= 5


def test_boyko_simplified_json_roundtrip():
    a = s._calculate_boyko_simplified({i: 1 for i in range(1, 85)})
    b = s._calculate_boyko_simplified(json.loads(json.dumps({i: 1 for i in range(1, 85)})))
    assert a == b and a["simplified"] is True


def _tiny_key():
    # синтетический ключ ТОЛЬКО для проверки механики, не методика Бойко
    symptoms = []
    q = 1
    for ph in ("tension", "resistance", "exhaustion"):
        for n in range(4):
            symptoms.append({
                "name": f"{ph}{n}", "phase": ph,
                "items": [{"q": q, "answer": "yes", "weight": 10}, {"q": q + 1, "answer": "no", "weight": 5}],
            })
            q += 2
    return {"symptoms": symptoms}


def test_boyko_weighted_thresholds():
    key = _tiny_key()
    # все «да»: набирают только yes-пункты -> 4 симптома * 10 = 40 на фазу
    answers = {i: (1 if i % 2 == 1 else 1) for i in range(1, 25)}
    r = s.calculate_boyko(answers, key=key)
    assert r["tension"] == 40 and r["tension_status"] == "складывается"
    assert r["simplified"] is False and len(r["symptoms"]) == 12
    # yes на нечётных, no на чётных -> 60 на фазу: ровно граница «складывается»
    answers = {i: (1 if i % 2 == 1 else 0) for i in range(1, 25)}
    r = s.calculate_boyko(answers, key=key)
    assert r["tension"] == 60 and r["tension_status"] == "складывается"
    # все «нет» -> по 20 -> не сложилась
    r = s.calculate_boyko({i: 0 for i in range(1, 25)}, key=key)
    assert r["tension_status"] == "не сложилась"


def test_boyko_key_validation(tmp_path):
    bad = tmp_path / "k.json"
    bad.write_text('{"symptoms": []}')
    assert s.load_boyko_key(str(bad)) is None
    assert s.load_boyko_key(str(tmp_path / "missing.json")) is None
    good = tmp_path / "g.json"
    good.write_text(json.dumps(_tiny_key()))
    assert s.load_boyko_key(str(good)) is not None
