from __future__ import annotations

import re
from typing import Any, Dict, Optional

from app.infrastructure.config.config_loader import load_clinic, load_session

_WS = re.compile(r"\s+")


def empty_session() -> Dict[str, Any]:
    return {
        "unit_id": None,
        "unit_confirmed": False,
        "last_intent": None,
        "pending": None,
        "opt_out": False,
    }


def city_for_unit(unit_id: Optional[str]) -> Optional[str]:
    if not unit_id:
        return None
    for unit in load_clinic().get("units", []):
        if unit.get("id") == unit_id:
            return unit.get("city")
    return None


def _normalize(text: str) -> str:
    return _WS.sub(" ", (text or "").strip().lower())


_PUNCT = re.compile(r"[^\wáéíóúãõâêôç ]", re.I)


def _matches_any(text: str, phrases: list[str]) -> bool:
    if not text:
        return False
    return any(phrase.lower() in text for phrase in phrases)


def _standalone(text: str, phrases: list[str]) -> bool:
    cleaned = _PUNCT.sub("", text).strip().lower()
    cleaned = _WS.sub(" ", cleaned)
    return cleaned in {phrase.lower() for phrase in phrases}


def session_brief(session: Dict[str, Any], max_chars: int | None = None) -> str:
    """Texto mínimo para um LLM futuro. Não inclui mensagem, slot nem presença."""
    cfg = load_session()
    limit = max_chars or int(cfg.get("llm_brief_max_chars", 160))
    unit = session.get("unit_id") or "-"
    flag = "ok" if session.get("unit_confirmed") else "ask"
    pending = session.get("pending") or "-"
    intent = session.get("last_intent") or "-"
    opt = "out" if session.get("opt_out") else "in"
    brief = f"u={unit}:{flag} p={pending} i={intent} o={opt}"
    return brief[:limit]


def merge_session(
    message: str,
    unit: Dict[str, Any],
    previous: Optional[Dict[str, Any]] = None,
    intent: str = "UNKNOWN",
    clinical: bool = False,
) -> Dict[str, Any]:
    """Atualiza slots. Nunca copia horário ou cidade da dra."""
    cfg = load_session()
    text = _normalize(message)
    prev = previous or empty_session()
    if prev.get("opt_out"):
        prev = empty_session()

    opt_phrases = cfg.get("opt_out", [])
    short_opt = [p for p in opt_phrases if " " not in p]
    long_opt = [p for p in opt_phrases if " " in p]
    if _standalone(text, short_opt) or _matches_any(text, long_opt):
        merged = empty_session()
        merged["opt_out"] = True
        merged["last_intent"] = "OPT_OUT"
        return {"session": merged, "just_confirmed_unit": False, "opt_out": True}

    unit_id = unit.get("unit_id") or prev.get("unit_id")
    confirmed = bool(prev.get("unit_confirmed"))
    just_confirmed = False
    pending_prev = prev.get("pending")

    source = unit.get("source")
    if source == "message_text":
        unit_id = unit.get("unit_id")
        confirmed = True
    elif source == "message_overrides_ddd":
        unit_id = unit.get("unit_id")
        confirmed = False
    elif source == "ddd_hypothesis" and not confirmed:
        unit_id = unit.get("unit_id")
        confirmed = False
    elif confirmed and prev.get("unit_id"):
        unit_id = prev.get("unit_id")

    if pending_prev == "ask_unit" and unit_id and _standalone(text, cfg.get("affirmatives", [])):
        confirmed = True
        just_confirmed = True

    if pending_prev == "ask_unit" and _standalone(text, cfg.get("negatives", [])):
        confirmed = False
        unit_id = None
        just_confirmed = False

    pending = None
    if clinical:
        pending = None
    elif not confirmed:
        pending = "ask_unit"
    elif intent == "AVAILABILITY":
        pending = "ask_availability"
    elif intent == "LOCATION":
        pending = "ask_presence"

    session = {
        "unit_id": unit_id,
        "unit_confirmed": confirmed,
        "last_intent": "UNIT_CONFIRM" if just_confirmed else intent,
        "pending": pending,
        "opt_out": False,
    }
    return {
        "session": session,
        "just_confirmed_unit": just_confirmed,
        "opt_out": False,
    }
