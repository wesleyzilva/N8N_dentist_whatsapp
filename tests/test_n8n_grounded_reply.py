import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.domains.secretary.turn import process_turn
from scripts.n8n_grounded_reply import map_turn_to_webhook_response


def test_availability_without_calendar_asks_not_slot():
    turn = process_turn("Quero ver disponibilidade", "5546999887766")
    mapped = map_turn_to_webhook_response(turn)
    assert mapped["next"] == "ask"
    assert mapped["can_assert_facts"] is False
    assert mapped["availability_evidence"] == "missing"
    assert "14h" not in mapped["reply_text"]
    assert "09:00" not in mapped["reply_text"]
    assert mapped["reply_text"] == turn["reply_text"]


def test_clinical_handoff_uses_reply_text():
    turn = process_turn("Estou com dor no rosto depois do preenchimento", "5516988887777")
    mapped = map_turn_to_webhook_response(turn)
    assert mapped["next"] == "handoff"
    assert mapped["escalation"]["needed"] is True
    assert mapped["reply_text"]
