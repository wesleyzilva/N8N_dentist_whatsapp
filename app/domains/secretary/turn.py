from typing import Any, Dict, List, Optional

from app.domains.appointments.intent_classifier import (
    classify_intent,
    escalation_reason,
    is_clinical_text,
)
from app.domains.guardrails.grounding import allowed_claims
from app.domains.locations.resolver import resolve_unit
from app.domains.patients.session import city_for_unit, merge_session, session_brief
from app.domains.secretary import fallback
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

# Intents que a secretária responde sem precisar de fato externo.
_CONVERSATIONAL = {"GREETING", "THANKS", "ACK", "BOT_IDENTITY"}


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


def _requested_claims(intent: str) -> List[str]:
    if intent == "AVAILABILITY":
        return ["availability_slots"]
    if intent == "LOCATION":
        return ["doctor_presence_city"]
    return []


class _Turn:
    """Monta a resposta do turno e o rastro de decisões (para logs e para o Console)."""

    def __init__(self, calendar: CalendarGateway, previous: Optional[dict]):
        self.calendar = calendar
        self.previous = previous
        self.trace: List[Dict[str, str]] = []

    def note(self, step: str, result: Any, why: str) -> None:
        self.trace.append({"step": step, "result": str(result), "why": why})

    def build(
        self,
        *,
        intent: str,
        confidence: str,
        unit: Dict[str, Any],
        session: Dict[str, Any],
        reply: str,
        claims: Optional[Dict[str, Any]] = None,
        evidence: Optional[Dict[str, Any]] = None,
        tool_status: Optional[Dict[str, str]] = None,
        escalation: Optional[Dict[str, Any]] = None,
        fallback_info: Optional[Dict[str, Any]] = None,
        handoff: Optional[Dict[str, Any]] = None,
        can_assert: Optional[bool] = None,
    ) -> Dict[str, Any]:
        claims = claims or allowed_claims([], {})
        evidence = evidence or {}
        escalation = escalation or {"needed": False, "reason": None}
        if can_assert is None:
            can_assert = claims["can_assert_facts"] and not escalation["needed"]
        brief = session_brief(session)
        max_chars = int(load_session().get("llm_brief_max_chars", 160))
        out = {
            "intent": intent,
            "confidence": confidence,
            "unit_hypothesis": unit,
            "presence_evidence": evidence.get("doctor_presence_city") or "missing",
            "availability_evidence": evidence.get("availability_slots") or "missing",
            "allowed_claims": claims,
            "escalation": escalation,
            "reply_text": reply,
            "can_assert_facts": bool(can_assert),
            "tool_status": tool_status or _idle_tool_status(self.calendar),
            "session": {
                "hit": self.previous is not None,
                "brief": brief,
                "unit_confirmed": bool(session.get("unit_confirmed")),
                "pending": session.get("pending"),
                "opt_out": bool(session.get("opt_out")),
                "brief_chars": len(brief),
                "brief_max_chars": max_chars,
            },
            "fallback": fallback_info,
            "handoff": handoff,
            "trace": self.trace,
        }
        if escalation["needed"]:
            out["next"] = "handoff"
        return out


def process_turn(
    message: str,
    whatsapp_number: str = "",
    calendar: Optional[CalendarGateway] = None,
    store: Optional[InMemoryPatientCache] = None,
    message_type: str = "text",
) -> Dict[str, Any]:
    """Um turno WhatsApp: intent, unidade (hipótese), grounding, voz, sessão curta e fallback."""
    calendar = calendar or MissingCalendarGateway()
    cache = store if store is not None else default_patient_cache()
    previous = cache.get(whatsapp_number)
    turn = _Turn(calendar, previous)
    templates = load_voice().get("templates", {})
    is_media = message_type != "text"

    classified = classify_intent(message) if not is_media else {"intent": "UNKNOWN", "confidence": "low"}
    intent = classified["intent"]
    turn.note(
        "classificar",
        intent,
        f"mensagem de mídia ({message_type}); não leio áudio/imagem" if is_media else f"regras de texto → {intent} ({classified['confidence']})",
    )
    unit = resolve_unit(message if not is_media else "", whatsapp_number)

    keywords = load_guardrails().get("guardrails", {}).get("clinical_escalate_keywords", [])
    clinical = (not is_media) and is_clinical_text(message, keywords)
    if clinical:
        turn.note("risco clínico", "sim", "palavra de sintoma na mensagem; vai para a equipe, sem orientação")

    pending_prev = (previous or {}).get("pending")
    merged = merge_session(message if not is_media else "", unit, previous=previous, intent=intent, clinical=clinical)
    session = merged["session"]
    if session.get("unit_id"):
        unit = dict(unit)
        unit["unit_id"] = session["unit_id"]
        unit["needs_confirmation"] = not session.get("unit_confirmed")
    turn.note(
        "unidade",
        unit.get("unit_id") or "desconhecida",
        "hipótese pelo DDD/texto; não diz onde a dra. está" if unit.get("unit_id") else "sem pista de cidade: vou perguntar quando for preciso",
    )

    if merged["opt_out"] or intent == "OPT_OUT":
        cache.put(whatsapp_number, session)
        turn.note("opt-out", "sim", "paciente pediu para parar; sessão limpa e sem novas mensagens")
        return turn.build(
            intent="OPT_OUT",
            confidence="high",
            unit=unit,
            session={**session, "opt_out": True},
            reply=render_reply("UNKNOWN", claims={"allowed": [], "blocked": [], "can_assert_facts": True}, opt_out=True),
            can_assert=False,
        )

    if intent == "ESCALATE" or clinical:
        reason = escalation_reason(message) if intent == "ESCALATE" or clinical else "clinical"
        template = {"clinical": "clinical_escalate", "human_requested": "human_requested", "complaint": "complaint"}[reason]
        session["pending"] = None
        cache.put(whatsapp_number, session)
        turn.note("escalar", reason, "pedido clínico, reclamação ou de atendimento humano: a equipe assume")
        return turn.build(
            intent="ESCALATE" if not clinical else intent,
            confidence="high",
            unit=unit,
            session=session,
            reply=templates[template],
            escalation={"needed": True, "reason": reason},
            handoff={"mode": "escalate", "reason": reason, "message": message if not is_media else None},
        )

    # Paciente respondendo à oferta de desculpa (verificar com a dra. | deixar recado).
    if pending_prev == fallback.PENDING_MESSAGE:
        session["pending"] = None
        cache.put(whatsapp_number, session)
        turn.note("recado", "recebido", "o texto (ou mídia) vai para a equipe; não fica guardado na sessão")
        return turn.build(
            intent="LEAVE_MESSAGE",
            confidence="high",
            unit=unit,
            session=session,
            reply=templates["fallback_message_saved"],
            escalation={"needed": True, "reason": "message_left"},
            fallback_info={"state": "message_saved"},
            handoff={
                "mode": "leave_message",
                "reason": "message_left",
                "message": message if not is_media else None,
                "media_type": message_type if is_media else None,
            },
        )

    if pending_prev == fallback.PENDING_CHOICE:
        choice = fallback.classify_choice(message) if not is_media else None
        turn.note("escolha", choice or "indefinida", "resposta à oferta: verificar com a dra. ou deixar recado")
        if choice == fallback.CHECK_DRA:
            session["pending"] = None
            cache.put(whatsapp_number, session)
            return turn.build(
                intent="CHECK_DRA",
                confidence="high",
                unit=unit,
                session=session,
                reply=templates["fallback_check_dra"],
                escalation={"needed": True, "reason": "doctor_check"},
                fallback_info={"state": "check_dra"},
                handoff={"mode": "check_dra", "reason": "doctor_check", "message": None},
            )
        if choice == fallback.LEAVE_MESSAGE:
            session["pending"] = fallback.PENDING_MESSAGE
            cache.put(whatsapp_number, session)
            return turn.build(
                intent="LEAVE_MESSAGE",
                confidence="high",
                unit=unit,
                session=session,
                reply=templates["fallback_ask_message"],
                fallback_info={"state": "awaiting_message"},
            )
        if choice == fallback.DISMISS:
            session["pending"] = None
            cache.put(whatsapp_number, session)
            return turn.build(
                intent="DISMISS",
                confidence="high",
                unit=unit,
                session=session,
                reply=templates["fallback_dismiss"],
                fallback_info={"state": "dismissed"},
            )
        if intent not in {"UNKNOWN", "QUESTION", "ACK", "THANKS"} and not is_media:
            turn.note("escolha", "ignorada", "mensagem é um pedido que sei tratar; segue o fluxo normal")
        else:
            session["pending"] = None
            cache.put(whatsapp_number, session)
            turn.note("recado", "implícito", "não ficou claro, então tratei a mensagem como recado para não repetir perguntas")
            return turn.build(
                intent="LEAVE_MESSAGE",
                confidence="medium",
                unit=unit,
                session=session,
                reply=templates["fallback_message_saved"],
                escalation={"needed": True, "reason": "message_left"},
                fallback_info={"state": "message_saved"},
                handoff={
                    "mode": "leave_message",
                    "reason": "message_left",
                    "message": message if not is_media else None,
                    "media_type": message_type if is_media else None,
                },
            )

    # Fora do que sei tratar: desculpa + oferta (sem afirmar nada sobre a dra.).
    open_question = intent == "QUESTION" and not _is_bare_question(message)
    if is_media or intent == "UNKNOWN" or open_question:
        reason = "media" if is_media else ("no_evidence" if open_question else "unmapped")
        session["pending"] = fallback.PENDING_CHOICE
        cache.put(whatsapp_number, session)
        turn.note(
            "fora do mapa",
            reason,
            "não tenho fonte segura para responder (preço, endereço, procedimento ou assunto novo): peço desculpa e ofereço verificar com a dra. ou recado",
        )
        return turn.build(
            intent=intent,
            confidence=classified.get("confidence", "low"),
            unit=unit,
            session=session,
            reply=templates["fallback_media" if is_media else "fallback_offer"],
            fallback_info={"state": "offer", "reason": reason},
            handoff={"mode": "offer", "reason": reason, "message": message if not is_media else None, "media_type": message_type if is_media else None},
            can_assert=False,
        )

    evidence: Dict[str, Any] = {}
    tool_status = _idle_tool_status(calendar)

    if intent == "AVAILABILITY":
        slots, tool_status["freebusy"] = _call_tool(calendar.freebusy, "", "", "")
        if slots:
            evidence["availability_slots"] = slots
        turn.note("agenda", tool_status["freebusy"], "consultei o calendário; sem resultado não cito horário")
    if intent == "LOCATION":
        presence_raw, tool_status["presence"] = _call_tool(calendar.presence_blocks, "", "")
        city = presence_raw.get("city") if isinstance(presence_raw, dict) else None
        if city:
            evidence["doctor_presence_city"] = city
        elif tool_status["presence"] == "ok":
            tool_status["presence"] = "empty"
        turn.note("presença", tool_status["presence"], "cidade da dra. só vem do calendário")

    claims = allowed_claims(_requested_claims(intent), evidence)
    turn.note(
        "grounding",
        "liberado" if claims["can_assert_facts"] else "bloqueado",
        f"claims liberadas={claims['allowed']} bloqueadas={claims['blocked']}",
    )
    city_label = city_for_unit(session.get("unit_id"))
    if pending_prev == "ask_unit" and not session.get("unit_id") and not merged["just_confirmed_unit"] and intent in {"ACK", "UNKNOWN"}:
        reply = templates["ask_unit"]
    else:
        reply = render_reply(
            intent=intent,
            claims=claims,
            evidence=evidence,
            clinical=False,
            session=session,
            city=city_label,
            just_confirmed_unit=merged["just_confirmed_unit"],
        )
    if intent in _CONVERSATIONAL:
        session["pending"] = session.get("pending") if pending_prev == "ask_unit" and not session.get("unit_confirmed") else None
    cache.put(whatsapp_number, session)
    turn.note("voz", "template", "texto montado só com as claims liberadas")

    return turn.build(
        intent=session.get("last_intent") or intent,
        confidence=classified.get("confidence", "medium"),
        unit=unit,
        session=session,
        reply=reply,
        claims=claims,
        evidence=evidence,
        tool_status=tool_status,
    )


def _is_bare_question(message: str) -> bool:
    from app.domains.appointments.intent_classifier import BARE_QUESTION_RE, fold

    return bool(BARE_QUESTION_RE.match(fold(message)))
