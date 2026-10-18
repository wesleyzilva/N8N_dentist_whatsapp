import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.domains.locations.resolver import resolve_unit


def test_ddd_46_hypothesis():
    result = resolve_unit(whatsapp_number="5546999887766")
    assert result["unit_id"] == "pato-branco"
    assert result["source"] == "ddd_hypothesis"
    assert result["is_presence"] is False
    assert result["needs_confirmation"] is True


def test_ddd_16_hypothesis():
    result = resolve_unit(whatsapp_number="5516999887766")
    assert result["unit_id"] == "sao-carlos"
    assert result["is_presence"] is False


def test_text_overrides_conflicting_ddd():
    result = resolve_unit(
        message="Prefiro atendimento em Pato Branco",
        whatsapp_number="5516981122334",
    )
    assert result["unit_id"] == "pato-branco"
    assert result["conflict"] is True
    assert result["source"] == "message_overrides_ddd"


def test_unknown_ddd_asks():
    result = resolve_unit(whatsapp_number="5511999887766")
    assert result["unit_id"] is None
    assert result["needs_confirmation"] is True
