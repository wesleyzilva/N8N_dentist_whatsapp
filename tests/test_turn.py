import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.domains.secretary.turn import process_turn
from app.infrastructure.mcp.calendar import MissingCalendarGateway


def test_confirm_round_trip_has_contract_and_human_reply():
    result = process_turn("Vou confirmar minha consulta", "5546999887766")
    assert result["intent"] == "CONFIRM"
    assert result["unit_hypothesis"]["unit_id"] == "pato-branco"
    assert result["unit_hypothesis"]["is_presence"] is False
    assert result["presence_evidence"] == "missing"
    assert result["availability_evidence"] == "missing"
    assert result["reply_text"]
    assert result["escalation"]["needed"] is False


def test_availability_with_empty_calendar_does_not_invent_slots():
    result = process_turn(
        "Tem horário essa semana",
        "5516999887766",
        calendar=MissingCalendarGateway(),
    )
    assert result["intent"] == "AVAILABILITY"
    assert result["availability_evidence"] == "missing"
    assert result["allowed_claims"]["can_assert_facts"] is False
    assert "availability_slots" in result["allowed_claims"]["blocked"]
    reply = result["reply_text"].lower()
    assert "14:" not in reply
    assert "14h" not in reply
    assert "amanhã às" not in reply
    assert "agenda" in reply


def test_location_with_empty_calendar_does_not_assert_city():
    result = process_turn("A dra está em Pato Branco", calendar=MissingCalendarGateway())
    assert result["intent"] == "LOCATION"
    assert result["presence_evidence"] == "missing"
    assert result["can_assert_facts"] is False
    assert "pato branco" not in result["reply_text"].lower()


def test_clinical_escalates():
    result = process_turn("Estou com dor urgente no dente")
    assert result["escalation"]["needed"] is True
    assert result["escalation"]["reason"] == "clinical"
    assert "encaminhar" in result["reply_text"].lower()
