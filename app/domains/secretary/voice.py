from typing import Any, Dict, Optional

from app.infrastructure.config.config_loader import load_voice


def _format_slots(slots: Any) -> str:
    if not slots:
        return ""
    parts = []
    for slot in slots:
        if isinstance(slot, str):
            parts.append(slot)
            continue
        start = slot.get("start") or slot.get("when") or ""
        if start:
            parts.append(str(start))
    return ", ".join(parts)


def render_reply(
    intent: str,
    claims: Dict[str, Any],
    evidence: Optional[Dict[str, Any]] = None,
    templates: Optional[Dict[str, str]] = None,
    clinical: bool = False,
    session: Optional[Dict[str, Any]] = None,
    city: Optional[str] = None,
    just_confirmed_unit: bool = False,
    opt_out: bool = False,
) -> str:
    """Redige só com claims liberadas. Sem evidência, pergunta — não inventa fato."""
    templates = templates or load_voice().get("templates", {})
    evidence = evidence or {}
    session = session or {}
    allowed = set(claims.get("allowed") or [])
    blocked = set(claims.get("blocked") or [])

    if opt_out:
        return templates["opt_out"]

    if clinical:
        return templates["clinical_escalate"]

    if just_confirmed_unit and city:
        return templates["unit_confirmed"].format(city=city)

    if "availability_slots" in blocked or (
        intent == "AVAILABILITY" and "availability_slots" not in allowed
    ):
        return templates["ask_availability"]

    if "availability_slots" in allowed:
        slots = _format_slots(evidence.get("availability_slots"))
        if slots:
            return templates["tenho_horarios"].format(slots=slots)
        return templates["ask_availability"]

    if "doctor_presence_city" in blocked or (
        intent == "LOCATION" and "doctor_presence_city" not in allowed
    ):
        return templates["ask_presence"]

    if "doctor_presence_city" in allowed:
        city_presence = evidence.get("doctor_presence_city")
        if city_presence:
            return templates["presence_known"].format(city=city_presence)
        return templates["ask_presence"]

    text = templates.get(intent) or templates["UNKNOWN"]
    if (
        not session.get("unit_confirmed")
        and intent not in {"UNKNOWN", "AVAILABILITY", "LOCATION"}
    ):
        if city:
            text = f"{text} {templates['ask_unit_hypothesis'].format(city=city)}"
        else:
            text = f"{text} {templates['ask_unit']}"
    return text
