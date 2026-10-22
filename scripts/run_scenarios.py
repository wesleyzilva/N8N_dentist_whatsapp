"""Executa a suite de conversas (tests/scenarios/conversations.json).

Uso:
    python -m scripts.run_scenarios                      # em processo, texto
    python -m scripts.run_scenarios --json               # saída para o TPM Console
    python -m scripts.run_scenarios --only S05 S09
    python -m scripts.run_scenarios --url http://localhost:8001/simulate/turn
    python -m scripts.run_scenarios --url http://localhost:5678/webhook/intent-webhook

Com `--url` a suite roda de ponta a ponta (HTTP). Cenários que dependem de
`calendar_mode` diferente de `missing` só rodam contra /simulate/turn; nos demais
alvos ficam `skipped`.
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCENARIOS_PATH = ROOT / "tests" / "scenarios" / "conversations.json"
CITY_NAMES = ("pato branco", "são carlos", "sao carlos")
CLOCK_TIME = re.compile(r"\b\d{1,2}\s*(?::\d{2}|h\b|h\d{2})", re.IGNORECASE)

TurnFn = Callable[[str, Dict[str, Any]], Dict[str, Any]]


def load_scenarios(path: Path = SCENARIOS_PATH) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)["scenarios"]


def _present(value: Any) -> str:
    return "missing" if value in (None, "", "missing", [], {}) else "present"


def evaluate(expect: Dict[str, Any], turn: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compara a resposta de um turno com as expectativas. Retorna uma lista de checagens."""
    reply = str(turn.get("reply_text") or "")
    lowered = reply.casefold()
    unit = turn.get("unit_hypothesis") or {}
    session = turn.get("session") or {}
    tools = turn.get("tool_status") or {}
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, expected: Any, actual: Any) -> None:
        checks.append({"name": name, "ok": bool(ok), "expected": expected, "actual": actual})

    exact = {
        "intent": turn.get("intent"),
        "unit_id": unit.get("unit_id"),
        "unit_conflict": unit.get("conflict"),
        "unit_needs_confirmation": unit.get("needs_confirmation"),
        "unit_confirmed": session.get("unit_confirmed"),
        "opt_out": session.get("opt_out"),
        "can_assert_facts": turn.get("can_assert_facts"),
        "freebusy": tools.get("freebusy"),
        "presence_tool": tools.get("presence"),
    }
    for key, actual in exact.items():
        if key in expect:
            add(key, actual == expect[key], expect[key], actual)

    if "escalation" in expect:
        actual = bool((turn.get("escalation") or {}).get("needed"))
        add("escalation", actual == expect["escalation"], expect["escalation"], actual)
    if "presence" in expect:
        actual = _present(turn.get("presence_evidence"))
        add("presence_evidence", actual == expect["presence"], expect["presence"], actual)
    if "availability" in expect:
        actual = _present(turn.get("availability_evidence"))
        add("availability_evidence", actual == expect["availability"], expect["availability"], actual)

    if "reply_includes_any" in expect:
        options = expect["reply_includes_any"]
        ok = any(item.casefold() in lowered for item in options)
        add("reply_includes_any", ok, options, reply)
    if "reply_includes_all" in expect:
        options = expect["reply_includes_all"]
        missing = [item for item in options if item.casefold() not in lowered]
        add("reply_includes_all", not missing, options, missing or "ok")
    if "reply_excludes" in expect:
        found = [item for item in expect["reply_excludes"] if item.casefold() in lowered]
        add("reply_excludes", not found, expect["reply_excludes"], found or "ok")
    if expect.get("reply_excludes_cities"):
        found = [city for city in CITY_NAMES if city in lowered]
        add("reply_excludes_cities", not found, "nenhuma cidade na resposta", found or "ok")
    if expect.get("reply_no_clock_time"):
        found = CLOCK_TIME.findall(reply)
        add("reply_no_clock_time", not found, "nenhum horário na resposta", found or "ok")
    if "reply_max_chars" in expect:
        add("reply_max_chars", len(reply) <= expect["reply_max_chars"], expect["reply_max_chars"], len(reply))
    return checks


def in_process_turn_fn(scenario: Dict[str, Any]) -> TurnFn:
    from app.domains.secretary.turn import process_turn
    from app.infrastructure.mcp.calendar import build_calendar_gateway
    from app.infrastructure.memory.patient_cache import InMemoryPatientCache

    gateway = build_calendar_gateway(
        scenario.get("calendar_mode", "missing"), scenario.get("fixture_city", "São Carlos")
    )
    store = InMemoryPatientCache()

    def turn(message: str, scenario_ctx: Dict[str, Any]) -> Dict[str, Any]:
        return process_turn(message, scenario_ctx["number"], calendar=gateway, store=store)

    return turn


def http_turn_fn(url: str, scenario: Dict[str, Any], timeout: float = 15.0) -> TurnFn:
    def turn(message: str, scenario_ctx: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "message": message,
            "from": scenario_ctx["number"],
            "whatsapp_number": scenario_ctx["number"],
            "calendar_mode": scenario.get("calendar_mode", "missing"),
            "fixture_city": scenario.get("fixture_city"),
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    return turn


def _reset_remote(url: str, number: str) -> None:
    if not url.rstrip("/").endswith("/simulate/turn"):
        return
    reset_url = url.rstrip("/")[: -len("/turn")] + "/reset"
    request = urllib.request.Request(
        reset_url,
        data=json.dumps({"whatsapp_number": number}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(request, timeout=10).read()


def run_scenario(scenario: Dict[str, Any], url: Optional[str] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "id": scenario["id"],
        "title": scenario["title"],
        "problems": scenario.get("problems", []),
        "phase": scenario.get("phase"),
        "calendar_mode": scenario.get("calendar_mode", "missing"),
        "number": scenario["number"],
        "status": "passed",
        "turns": [],
    }
    supports_modes = url is None or url.rstrip("/").endswith("/simulate/turn")
    if not supports_modes and result["calendar_mode"] != "missing":
        result["status"] = "skipped"
        result["reason"] = "alvo não aceita calendar_mode"
        return result

    try:
        if url:
            _reset_remote(url, scenario["number"])
            turn_fn = http_turn_fn(url, scenario)
        else:
            turn_fn = in_process_turn_fn(scenario)
        for step in scenario["turns"]:
            response = turn_fn(step["say"], scenario)
            checks = evaluate(step.get("expect", {}), response)
            ok = all(check["ok"] for check in checks)
            result["turns"].append(
                {
                    "say": step["say"],
                    "reply": response.get("reply_text"),
                    "ok": ok,
                    "checks": checks,
                    "response": response,
                }
            )
            if not ok:
                result["status"] = "failed"
    except Exception as exc:
        result["status"] = "error"
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def run_all(only: Optional[List[str]] = None, url: Optional[str] = None) -> Dict[str, Any]:
    scenarios = load_scenarios()
    if only:
        scenarios = [s for s in scenarios if any(s["id"].startswith(prefix) for prefix in only)]
    results = [run_scenario(s, url) for s in scenarios]
    summary = {"total": len(results)}
    for status in ("passed", "failed", "error", "skipped"):
        summary[status] = sum(1 for r in results if r["status"] == status)
    return {"target": url or "in-process", "summary": summary, "scenarios": results}


def _print_text(report: Dict[str, Any]) -> None:
    print(f"Alvo: {report['target']}")
    for item in report["scenarios"]:
        print(f"[{item['status'].upper():7}] {item['id']} — {item['title']}")
        if item.get("error"):
            print(f"    erro: {item['error']}")
        for turn in item["turns"]:
            if turn["ok"]:
                continue
            print(f"    > {turn['say']}")
            print(f"    < {turn['reply']}")
            for check in turn["checks"]:
                if not check["ok"]:
                    print(f"      falhou {check['name']}: esperado={check['expected']!r} obtido={check['actual']!r}")
    s = report["summary"]
    print(f"\nTotal {s['total']} | ok {s['passed']} | falhou {s['failed']} | erro {s['error']} | pulados {s['skipped']}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="saída JSON completa")
    parser.add_argument("--only", nargs="*", help="prefixos de id (ex.: S05 S09)")
    parser.add_argument("--url", help="alvo HTTP; padrão = em processo")
    args = parser.parse_args(argv)

    report = run_all(args.only, args.url)
    if args.json:
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
    else:
        _print_text(report)
    summary = report["summary"]
    return 0 if summary["failed"] == 0 and summary["error"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
