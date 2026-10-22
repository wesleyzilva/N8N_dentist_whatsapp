import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.interfaces.http.intent_service import IntentRequestHandler
from scripts.run_scenarios import load_corpus, run_all, run_scenario

CORPUS = load_corpus()


def test_corpus_has_breadth():
    groups = {item["group"] for item in CORPUS}
    assert len(CORPUS) >= 200
    assert {"saudacao", "clinico", "pergunta_sem_evidencia", "fora_do_mapa", "injecao", "midia", "jornadas"} <= groups
    ids = [item["id"] for item in CORPUS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("scenario", CORPUS, ids=[s["id"] for s in CORPUS])
def test_corpus_scenario_in_process(scenario):
    result = run_scenario(scenario)
    assert result["status"] == "passed", [
        (turn["say"], turn["reply"], [c for c in turn["checks"] if not c["ok"]]) for turn in result["turns"] if not turn["ok"]
    ] or result.get("error")


def test_corpus_report_has_group_totals():
    report = run_all(only=["C-saudacao"], suite="corpus")
    assert report["groups"]["saudacao"]["total"] == report["groups"]["saudacao"]["passed"] > 0


def test_corpus_over_http_simulate(monkeypatch):
    monkeypatch.setenv("SIMULATION_ENABLED", "1")
    server = ThreadingHTTPServer(("127.0.0.1", 0), IntentRequestHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        host, port = server.server_address
        url = f"http://{host}:{port}/simulate/turn"
        sample = [s for s in CORPUS if s["id"].startswith(("C-midia", "J02", "J03", "J07", "C-clinico-01", "C-injecao-01"))]
        assert sample
        for scenario in sample:
            assert run_scenario(scenario, url)["status"] == "passed", scenario["id"]
    finally:
        server.shutdown()
