from aiogram.fsm.state import State, StatesGroup


class TestStates(StatesGroup):
    """Состояния для всех тестов"""
    mbi_q = State()
    boyko_q = State()
    phq9_q = State()
    gad7_q = State()
    pss10_q = State()
    combined_phq_gad = State()


class SOSStates(StatesGroup):
    """Состояния для SOS-раздела"""
    ai_chat = State()
    anger_venting = State()
    defusion = State()
    stop_technique = State()


class TrackerStates(StatesGroup):
    """Состояния для дневника"""
    energy = State()
    emotion = State()
    gratitude = State()
