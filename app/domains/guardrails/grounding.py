from typing import Any, Dict, Iterable, List, Optional


FORBIDDEN_WITHOUT_EVIDENCE = {
    "availability_slots",
    "doctor_presence_city",
    "address",
    "price",
    "procedure_details",
    "clinical_advice",
}


def allowed_claims(
    requested: Iterable[str],
    evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Só libera claim se houver evidência explícita da ferramenta/config."""
    evidence = evidence or {}
    allowed: List[str] = []
    blocked: List[str] = []

    for claim in requested:
        payload = evidence.get(claim)
        has_evidence = payload not in (None, "", [], {})
        if claim in FORBIDDEN_WITHOUT_EVIDENCE and not has_evidence:
            blocked.append(claim)
            continue
        if has_evidence or claim not in FORBIDDEN_WITHOUT_EVIDENCE:
            allowed.append(claim)

    missing = bool(blocked)
    return {
        "allowed": allowed,
        "blocked": blocked,
        "action_if_blocked": "ask_or_escalate" if missing else "respond",
        "can_assert_facts": not missing,
    }
