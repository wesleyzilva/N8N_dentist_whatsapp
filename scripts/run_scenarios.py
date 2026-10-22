"""Executa a suite de conversas (tests/scenarios/conversations.json).

Uso:
    python -m scripts.run_scenarios                      # em processo, texto
    python -m scripts.run_scenarios --json               # saída para o TPM Console
    python -m scripts.run_scenarios --suite corpus --quiet   # corpus simulado (tests/scenarios/corpus.json)
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
CORPUS_PATH = ROOT / "tests" / "scenarios" / "corpus.json"
CITY_NAMES = ("pato branco", "são carlos", "sao carlos")
CLOCK_TIME = re.compile(r"\b\d{1,2}\s*(?::\d{2}|h\b|h\d{2})", re.IGNORECASE)
PRICE = re.compile(r"R\$\s*\d|\b\d+[.,]?\d*\s*(?:reais|real)\b", re.IGNORECASE)

TurnFn = Callable[..., Dict[str, Any]]


def load_scenarios(path: Path = SCENARIOS_PATH) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)["scenarios"]


def load_corpus(path: Path = CORPUS_PATH) -> List[Dict[str, Any]]:
    """Expande o corpus: um cenário de um turno por mensagem + as jornadas de vários turnos."""
    with path.open("r", encoding="utf-8") as handle:
        corpus = json.load(handle)
    invariants = corpus.get("invariants", {})
    scenarios: List[Dict[str, Any]] = []
    for group in corpus["groups"]:
        numbers = group["numbers"]
        for index, item in enumerate(group["messages"]):
            say, kind = (item, "text") if isinstance(item, str) else (item["say"], item.get("type", "text"))
            step: Dict[str, Any] = {"say": say, "expect": {**group["expect"], **invariants}}
            if kind != "text":
                step["type"] = kind
            scenarios.append(
                {
                    "id": f"C-{group['id']}-{index + 1:02d}",
                    "title": f"{group['title']}: {say or '[' + kind + ']'}",
                    "group": group["id"],
                    "problems": group["problems"],
                    "phase": group["phase"],
                    "number": numbers[index % len(numbers)],
                    "calendar_mode": group.get("calendar_mode", "missing"),
                    "turns": [step],
                }
            )
    for journey in corpus.get("journeys", []):
        journey = dict(journey)
        journey["group"] = "jornadas"
        journey["turns"] = [{**s, "expect": {**invariants, **s["expect"]}} for s in journey["turns"]]
        scenarios.append(journey)
    return scenarios


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
    if "escalation_reason" in expect:
        actual = (turn.get("escalation") or {}).get("reason")
        add("escalation_reason", actual == expect["escalation_reason"], expect["escalation_reason"], actual)
    if "fallback_state" in expect:
        actual = (turn.get("fallback") or {}).get("state")
        add("fallback_state", actual == expect["fallback_state"], expect["fallback_state"], actual)
    if "handoff_mode" in expect:
        actual = (turn.get("handoff") or {}).get("mode")
        add("handoff_mode", actual == expect["handoff_mode"], expect["handoff_mode"], actual)
    if "pending" in expect:
        actual = session.get("pending")
        add("pending", actual == expect["pending"], expect["pending"], actual)
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
    if expect.get("reply_no_price"):
        found = PRICE.findall(reply)
        add("reply_no_price", not found, "nenhum valor em reais", found or "ok")
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

    def turn(message: str, scenario_ctx: Dict[str, Any], message_type: str = "text") -> Dict[str, Any]:
        return process_turn(message, scenario_ctx["number"], calendar=gateway, store=store, message_type=message_type)

    return turn


def http_turn_fn(url: str, scenario: Dict[str, Any], timeout: float = 15.0) -> TurnFn:
    def turn(message: str, scenario_ctx: Dict[str, Any], message_type: str = "text") -> Dict[str, Any]:
        payload = {
            "message_type": message_type,
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
        "group": scenario.get("group"),
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
            response = turn_fn(step["say"], scenario, step.get("type", "text"))
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


def run_all(only: Optional[List[str]] = None, url: Optional[str] = None, suite: str = "conversations") -> Dict[str, Any]:
    scenarios: List[Dict[str, Any]] = []
    if suite in ("conversations", "all"):
        scenarios += load_scenarios()
    if suite in ("corpus", "all"):
        scenarios += load_corpus()
    if only:
        scenarios = [s for s in scenarios if any(s["id"].startswith(prefix) for prefix in only)]
    results = [run_scenario(s, url) for s in scenarios]
    summary = {"total": len(results)}
    for status in ("passed", "failed", "error", "skipped"):
        summary[status] = sum(1 for r in results if r["status"] == status)
    groups: Dict[str, Dict[str, int]] = {}
    for item in results:
        if not item.get("group"):
            continue
        bucket = groups.setdefault(item["group"], {"total": 0, "passed": 0})
        bucket["total"] += 1
        bucket["passed"] += item["status"] == "passed"
    return {"target": url or "in-process", "suite": suite, "summary": summary, "groups": groups, "scenarios": results}


def _print_text(report: Dict[str, Any], quiet: bool = False) -> None:
    print(f"Alvo: {report['target']}")
    for item in report["scenarios"]:
        if quiet and item["status"] == "passed":
            continue
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
    if report.get("groups"):
        print("\nPor grupo (acertos / total):")
        for name, bucket in report["groups"].items():
            print(f"  {name:28} {bucket['passed']:3} / {bucket['total']:3}")
    s = report["summary"]
    print(f"\nTotal {s['total']} | ok {s['passed']} | falhou {s['failed']} | erro {s['error']} | pulados {s['skipped']}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="saída JSON completa")
    parser.add_argument("--only", nargs="*", help="prefixos de id (ex.: S05 S09)")
    parser.add_argument("--url", help="alvo HTTP; padrão = em processo")
    parser.add_argument("--suite", choices=["conversations", "corpus", "all"], default="conversations", help="qual suíte rodar")
    parser.add_argument("--list", action="store_true", help="lista os cenários da suíte (JSON) sem executar")
    parser.add_argument("--quiet", action="store_true", help="só falhas e totais (útil no corpus)")
    args = parser.parse_args(argv)

    if args.list:
        sys.stdout.reconfigure(encoding="utf-8")
        scenarios: List[Dict[str, Any]] = []
        if args.suite in ("conversations", "all"):
            scenarios += load_scenarios()
        if args.suite in ("corpus", "all"):
            scenarios += load_corpus()
        print(json.dumps({"scenarios": scenarios}, ensure_ascii=False))
        return 0
    report = run_all(args.only, args.url, args.suite)
    if args.json:
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
    else:
        _print_text(report, args.quiet)
    summary = report["summary"]
    return 0 if summary["failed"] == 0 and summary["error"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
