import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.domains.secretary.turn import process_turn
from app.infrastructure.memory.patient_cache import InMemoryPatientCache
from app.infrastructure.observability.turn_log import log_turn, mask_number


def test_number_is_masked():
    assert mask_number("5546999887766") == "46*****7766"
    assert mask_number("123") == "***"


def test_trace_explains_each_decision():
    turn = process_turn("quanto custa o botox?", "5546999887766", store=InMemoryPatientCache())
    steps = {item["step"] for item in turn["trace"]}
    assert {"classificar", "unidade", "fora do mapa"} <= steps
    assert all(item["why"] for item in turn["trace"])


def test_jsonl_has_trace_and_no_message_text_by_default(tmp_path, monkeypatch):
    log = tmp_path / "turns.jsonl"
    monkeypatch.setenv("TURN_LOG_PATH", str(log))
    monkeypatch.delenv("LOG_MESSAGE_TEXT", raising=False)
    turn = process_turn("estou com dor no rosto", "5546999887766", store=InMemoryPatientCache())
    log_turn(number="5546999887766", message="estou com dor no rosto", message_type="text", turn=turn, source="test", duration_ms=1.2)
    record = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert record["patient"] == "46*****7766"
    assert record["message"] is None
    assert record["escalation"]["reason"] == "clinical"
    assert record["trace"]

    monkeypatch.setenv("LOG_MESSAGE_TEXT", "1")
    log_turn(number="5546999887766", message="oi", message_type="text", turn=turn, source="test", duration_ms=1.0)
    assert json.loads(log.read_text(encoding="utf-8").splitlines()[1])["message"] == "oi"
