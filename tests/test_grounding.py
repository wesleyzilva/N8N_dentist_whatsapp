import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.domains.guardrails.grounding import allowed_claims


def test_blocks_availability_without_slots():
    result = allowed_claims(["availability_slots"], evidence={})
    assert "availability_slots" in result["blocked"]
    assert result["can_assert_facts"] is False
    assert result["action_if_blocked"] == "ask_or_escalate"


def test_allows_presence_only_with_evidence():
    blocked = allowed_claims(["doctor_presence_city"], evidence={})
    assert blocked["can_assert_facts"] is False

    allowed = allowed_claims(
        ["doctor_presence_city"],
        evidence={"doctor_presence_city": "Pato Branco"},
    )
    assert "doctor_presence_city" in allowed["allowed"]
    assert allowed["can_assert_facts"] is True


def test_blocks_procedure_details_without_evidence():
    result = allowed_claims(["procedure_details"], evidence={})
    assert "procedure_details" in result["blocked"]
    assert result["can_assert_facts"] is False


def test_empty_calendar_list_is_not_evidence():
    result = allowed_claims(
        ["availability_slots"],
        evidence={"availability_slots": []},
    )
    assert result["can_assert_facts"] is False
    assert "availability_slots" in result["blocked"]
