"""Espelho do nó n8n Grounded Reply. Sem horário no canvas — só reply_text."""


def map_turn_to_webhook_response(payload: dict) -> dict:
    can_assert = payload.get("can_assert_facts") is True
    reply = payload.get("reply_text") or ""
    escalation = payload.get("escalation") or {}
    if can_assert:
        nxt = "respond"
    elif escalation.get("needed"):
        nxt = "handoff"
    else:
        nxt = "ask"
    return {
        "intent": payload.get("intent") or "UNKNOWN",
        "confidence": payload.get("confidence") or "medium",
        "unit_hypothesis": payload.get("unit_hypothesis"),
        "presence_evidence": payload.get("presence_evidence") or "missing",
        "availability_evidence": payload.get("availability_evidence") or "missing",
        "allowed_claims": payload.get("allowed_claims") or {},
        "escalation": escalation,
        "can_assert_facts": can_assert,
        "reply_text": reply,
        "next": nxt,
    }
