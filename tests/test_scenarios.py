import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.interfaces.http.intent_service import IntentRequestHandler
from scripts.run_scenarios import evaluate, load_scenarios, run_scenario

SCENARIOS = load_scenarios()


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_scenario_in_process(scenario):
    result = run_scenario(scenario)
    failures = [
        (turn["say"], check)
        for turn in result["turns"]
        for check in turn["checks"]
        if not check["ok"]
    ]
    assert result["status"] == "passed", failures or result.get("error")


def test_every_scenario_points_to_a_problem_and_phase():
    for scenario in SCENARIOS:
        assert scenario["problems"], scenario["id"]
        assert all(p.startswith("P") for p in scenario["problems"]), scenario["id"]
        assert scenario.get("phase") is not None, scenario["id"]


def test_mandatory_antihallucination_gates_are_present():
    ids = {s["id"] for s in SCENARIOS}
    assert "S05-calendario-vazio-nao-sugere-horario" in ids
    assert "S07-presenca-sem-evento" in ids
    assert "S09-qualquer-horario-amanha" in ids
    assert "S06-calendario-erro-nao-sugere-horario" in ids


def test_evaluator_catches_invented_time():
    fake_turn = {
        "intent": "AVAILABILITY",
        "reply_text": "Tenho amanhã às 14:30!",
        "availability_evidence": "missing",
        "escalation": {"needed": False},
    }
    checks = evaluate({"reply_no_clock_time": True, "reply_excludes": ["amanhã"]}, fake_turn)
    assert [c["ok"] for c in checks] == [False, False]


def _serve():
    server = ThreadingHTTPServer(("127.0.0.1", 0), IntentRequestHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_scenarios_over_http_simulate_endpoint(monkeypatch):
    monkeypatch.setenv("SIMULATION_ENABLED", "1")
    server = _serve()
    try:
        host, port = server.server_address
        url = f"http://{host}:{port}/simulate/turn"
        for scenario in SCENARIOS:
            result = run_scenario(scenario, url)
            assert result["status"] == "passed", (scenario["id"], result)
    finally:
        server.shutdown()


def test_simulate_endpoint_is_disabled_by_default(monkeypatch):
    import json
    from http.client import HTTPConnection

    monkeypatch.delenv("SIMULATION_ENABLED", raising=False)
    server = _serve()
    try:
        host, port = server.server_address
        conn = HTTPConnection(host, port, timeout=5)
        conn.request(
            "POST",
            "/simulate/turn",
            body=json.dumps({"message": "oi", "calendar_mode": "fixture"}),
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        response.read()
        assert response.status == 403
    finally:
        server.shutdown()
