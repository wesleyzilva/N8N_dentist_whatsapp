from typing import Any, Dict, Optional

from app.domains.appointments.intent_classifier import classify_intent
from app.domains.guardrails.grounding import allowed_claims
from app.domains.locations.resolver import resolve_unit
from app.domains.patients.session import city_for_unit, merge_session, session_brief
from app.domains.secretary.voice import render_reply
from app.infrastructure.config.config_loader import (
    load_guardrails,
    load_session,
    load_voice,
)
from app.infrastructure.mcp.calendar import CalendarGateway, MissingCalendarGateway
from app.infrastructure.memory.patient_cache import (
    InMemoryPatientCache,
    default_patient_cache,
)


def _is_clinical(message: str, keywords: list[str]) -> bool:
    text = (message or "").lower()
    urgent = [
        "inchad", "doend", "dor", "piorand", "sangr", "febre", "sintoma",
        "esperando", "ninguém me atende", "absurdo", "avaliação péssima",
        "dinheiro de volta", "falar com uma pessoa", "falar com a dra",
        "humano", "atendente", "reembolso", "incompetente"
    ]
    all_keywords = list(keywords) + urgent
    return any(k.lower() in text for k in all_keywords)


def _call_tool(call, *args) -> tuple[Any, str]:
    """Chama a ferramenta sem deixar uma falha virar resposta inventada."""
    try:
        result = call(*args)
    except Exception:
        return None, "error"
    if not result:
        return None, "empty"
    return result, "ok"


def _idle_tool_status(calendar: CalendarGateway) -> Dict[str, str]:
    return {
        "calendar_mode": getattr(calendar, "mode", "custom"),
        "freebusy": "not_queried",
        "presence": "not_queried",
    }


def _requested_claims(intent: str) -> list[str]:
    if intent == "AVAILABILITY":
        return ["availability_slots"]
    if intent == "LOCATION":
        return ["doctor_presence_city"]
    return []


def process_turn(
    message: str,
    whatsapp_number: str = "",
    calendar: Optional[CalendarGateway] = None,
    store: Optional[InMemoryPatientCache] = None,
) -> Dict[str, Any]:
    """Um turno WhatsApp: intent, unidade (hipótese), grounding, voz, sessão curta."""
    calendar = calendar or MissingCalendarGateway()
    cache = store if store is not None else default_patient_cache()
    previous = cache.get(whatsapp_number)

    classified = classify_intent(message)
    intent = classified["intent"]
    unit = resolve_unit(message, whatsapp_number)

    keywords = (
        load_guardrails()
        .get("guardrails", {})
        .get("clinical_escalate_keywords", [])
    )
    clinical = _is_clinical(message, keywords)

    merged = merge_session(
        message,
        unit,
        previous=previous,
        intent=intent,
        clinical=clinical,
    )
    session = merged["session"]
    if session.get("unit_id"):
        unit = dict(unit)
        unit["unit_id"] = session["unit_id"]
        unit["needs_confirmation"] = not session.get("unit_confirmed")

    if merged["opt_out"] or intent == "OPT_OUT":
        cache.put(whatsapp_number, session)
        brief = session_brief(session)
        return {
            "intent": "OPT_OUT",
            "confidence": "high",
            "unit_hypothesis": unit,
            "presence_evidence": "missing",
            "availability_evidence": "missing",
            "allowed_claims": allowed_claims([], {}),
            "escalation": {"needed": False, "reason": None},
            "reply_text": render_reply(
                "UNKNOWN",
                claims={"allowed": [], "blocked": [], "can_assert_facts": True},
                opt_out=True,
            ),
            "can_assert_facts": False,
            "tool_status": _idle_tool_status(calendar),
            "session": {
                "hit": previous is not None,
                "brief": brief,
                "unit_confirmed": False,
                "pending": None,
                "opt_out": True,
            },
        }

    # Escalação para casos clínicos, reclamações ou pedido de atendente humano
    if intent == "ESCALATE" or clinical:
        escalation = {"needed": True, "reason": "clinical"}
        reply_msg = load_voice().get("templates", {})["clinical_escalate"]
        cache.put(whatsapp_number, session)
        brief = session_brief(session)
        max_chars = int(load_session().get("llm_brief_max_chars", 160))
        return {
            "intent": intent,
            "confidence": "high",
            "unit_hypothesis": unit,
            "presence_evidence": "missing",
            "availability_evidence": "missing",
            "allowed_claims": allowed_claims([], {}),
            "escalation": escalation,
            "reply_text": reply_msg,
            "next": "handoff",
            "can_assert_facts": False,
            "tool_status": _idle_tool_status(calendar),
            "session": {
                "hit": previous is not None,
                "brief": brief,
                "unit_confirmed": bool(session.get("unit_confirmed")),
                "pending": session.get("pending"),
                "opt_out": False,
                "brief_chars": len(brief),
                "brief_max_chars": max_chars,
            },
        }

    evidence: Dict[str, Any] = {}
    tool_status = _idle_tool_status(calendar)

    if intent == "AVAILABILITY":
        slots, tool_status["freebusy"] = _call_tool(calendar.freebusy, "", "", "")
        if slots:
            evidence["availability_slots"] = slots
    if intent == "LOCATION":
        presence_raw, tool_status["presence"] = _call_tool(calendar.presence_blocks, "", "")
        city = presence_raw.get("city") if isinstance(presence_raw, dict) else None
        if city:
            evidence["doctor_presence_city"] = city
        elif tool_status["presence"] == "ok":
            tool_status["presence"] = "empty"

    claims = allowed_claims(_requested_claims(intent), evidence)
    city_label = city_for_unit(session.get("unit_id"))
    reply = render_reply(
        intent=intent,
        claims=claims,
        evidence=evidence,
        clinical=clinical,
        session=session,
        city=city_label,
        just_confirmed_unit=merged["just_confirmed_unit"],
    )

    cache.put(whatsapp_number, session)

    presence_evidence = (
        evidence.get("doctor_presence_city")
        if evidence.get("doctor_presence_city")
        else "missing"
    )
    availability_evidence = (
        evidence.get("availability_slots")
        if evidence.get("availability_slots")
        else "missing"
    )

    escalation = {
        "needed": clinical,
        "reason": "clinical" if clinical else None,
    }
    brief = session_brief(session)
    max_chars = int(load_session().get("llm_brief_max_chars", 160))

    return {
        "intent": session.get("last_intent") or intent,
        "confidence": classified.get("confidence", "medium"),
        "unit_hypothesis": unit,
        "presence_evidence": presence_evidence,
        "availability_evidence": availability_evidence,
        "allowed_claims": claims,
        "escalation": escalation,
        "reply_text": reply,
        "can_assert_facts": claims["can_assert_facts"] and not clinical,
        "tool_status": tool_status,
        "session": {
            "hit": previous is not None,
            "brief": brief,
            "unit_confirmed": bool(session.get("unit_confirmed")),
            "pending": session.get("pending"),
            "opt_out": False,
            "brief_chars": len(brief),
            "brief_max_chars": max_chars,
        },
    }