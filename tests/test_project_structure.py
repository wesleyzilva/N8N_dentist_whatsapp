import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.domains.appointments.intent_classifier import classify_intent
from app.infrastructure.config.config_loader import load_guardrails


def test_domain_modules_are_importable():
    result = classify_intent("Quero cancelar minha consulta")
    assert result["intent"] == "CANCEL"


def test_config_module_is_importable():
    config = load_guardrails()
    assert config["default_intent"] == "UNKNOWN"
