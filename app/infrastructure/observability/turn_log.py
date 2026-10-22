"""Log de cada turno: uma linha legível no terminal e um registro JSONL com o rastro de decisões.

Variáveis de ambiente:
  LOG_LEVEL          INFO (padrão) | DEBUG | WARNING
  TURN_LOG_PATH      caminho do .jsonl (vazio = não grava arquivo)
  LOG_MESSAGE_TEXT   1 grava o texto do paciente (só em desenvolvimento; padrão não grava, por LGPD)
O número do paciente sai sempre mascarado (DDD + últimos 4 dígitos).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("secretaria")
_write_lock = threading.Lock()
_configured = False


def configure() -> None:
    global _configured
    if _configured:
        return
    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    _configured = True


def mask_number(number: str) -> str:
    digits = "".join(ch for ch in (number or "") if ch.isdigit())
    if len(digits) < 8:
        return "***"
    return f"{digits[2:4]}*****{digits[-4:]}" if digits.startswith("55") else f"{digits[:2]}*****{digits[-4:]}"


def _short(text: Optional[str], limit: int = 90) -> str:
    text = (text or "").replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def summarize(turn: Dict[str, Any]) -> str:
    esc = turn.get("escalation") or {}
    fb = turn.get("fallback") or {}
    parts = [f"intent={turn.get('intent')}"]
    unit = (turn.get("unit_hypothesis") or {}).get("unit_id")
    if unit:
        parts.append(f"unidade={unit}")
    if fb.get("state"):
        parts.append(f"fallback={fb['state']}")
    if esc.get("needed"):
        parts.append(f"escalar={esc.get('reason')}")
    return " ".join(parts)


def log_turn(
    *,
    number: str,
    message: str,
    message_type: str,
    turn: Dict[str, Any],
    source: str,
    duration_ms: float,
) -> None:
    configure()
    logger.info(
        "[turno] %s %s | %s | %.0f ms | resposta: %s",
        source,
        mask_number(number),
        summarize(turn),
        duration_ms,
        _short(turn.get("reply_text")),
    )
    if logger.isEnabledFor(logging.DEBUG):
        for step in turn.get("trace") or []:
            logger.debug("    · %s: %s — %s", step["step"], step["result"], step["why"])

    path = os.getenv("TURN_LOG_PATH")
    if not path:
        return
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "source": source,
        "patient": mask_number(number),
        "message_type": message_type,
        "message": message if os.getenv("LOG_MESSAGE_TEXT") == "1" else None,
        "intent": turn.get("intent"),
        "confidence": turn.get("confidence"),
        "unit": (turn.get("unit_hypothesis") or {}).get("unit_id"),
        "escalation": turn.get("escalation"),
        "fallback": turn.get("fallback"),
        "handoff_mode": (turn.get("handoff") or {}).get("mode"),
        "tool_status": turn.get("tool_status"),
        "can_assert_facts": turn.get("can_assert_facts"),
        "reply_text": turn.get("reply_text"),
        "session": (turn.get("session") or {}).get("brief"),
        "trace": turn.get("trace"),
        "duration_ms": round(duration_ms, 1),
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with _write_lock, target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def timed(fn, *args, **kwargs):
    started = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, (time.perf_counter() - started) * 1000
