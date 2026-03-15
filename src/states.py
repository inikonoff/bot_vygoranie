from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    sphere = State()
    request = State()


class TestStates(StatesGroup):
    mbi_q = State()
    boyko_q = State()
    phq9_q = State()
    gad7_q = State()
    pss10_q = State()
    uwes_q = State()
    osipov_q = State()


class TrackerStates(StatesGroup):
    energy = State()
    emotion = State()
    gratitude = State()


class AIState(StatesGroup):
    waiting_for_query = State()


class AngerState(StatesGroup):
    venting = State()


class DefusionState(StatesGroup):
    waiting_for_thought = State()
