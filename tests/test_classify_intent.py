import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.domains.appointments.intent_classifier import classify_intent


def test_confirm():
    result = classify_intent("Vou confirmar minha consulta")
    assert result["intent"] == "CONFIRM"


def test_reschedule():
    result = classify_intent("Preciso reagendar para outro dia")
    assert result["intent"] == "RESCHEDULE"


def test_cancel():
    result = classify_intent("Quero cancelar")
    assert result["intent"] == "CANCEL"


def test_availability():
    result = classify_intent("Quero ver disponibilidade")
    assert result["intent"] == "AVAILABILITY"


def test_location():
    result = classify_intent("Atende em São Carlos hoje")
    assert result["intent"] == "LOCATION"


def test_question_about_hof():
    result = classify_intent("Vocês fazem harmonização orofacial?")
    assert result["intent"] == "QUESTION"
