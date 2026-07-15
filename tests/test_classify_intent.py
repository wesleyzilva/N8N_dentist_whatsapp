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
