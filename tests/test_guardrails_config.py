import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.infrastructure.config.config_loader import load_guardrails


def test_guardrails_config_loaded():
    config = load_guardrails()
    assert config["default_intent"] == "UNKNOWN"
    assert "CONFIRM" in config["intent_examples"]
    assert "guardrails" in config


def test_examples_are_not_empty():
    config = load_guardrails()
    assert config["intent_examples"]["CONFIRM"]
    assert config["intent_examples"]["QUESTION"]
