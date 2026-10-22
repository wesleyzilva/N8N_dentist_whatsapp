"""Fluxo de desculpa quando o pedido sai do que a secretária sabe tratar.

1. A secretária pede desculpa e oferece duas saídas (sem afirmar nada sobre a dra.):
   verificar se ela pode atender agora pelo WhatsApp, ou deixar um recado.
2. O paciente escolhe. Dúvida na escolha: se a mensagem for um pedido que sabemos tratar,
   segue o fluxo normal; senão, a própria mensagem vira o recado (sem laço de perguntas).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from app.domains.appointments.intent_classifier import fold
from app.infrastructure.config.config_loader import load_session

PENDING_CHOICE = "fallback_choice"
PENDING_MESSAGE = "leave_message"

CHECK_DRA = "check_dra"
LEAVE_MESSAGE = "leave_message"
DISMISS = "dismiss"


def _cfg() -> Dict[str, Any]:
    return load_session().get("fallback_choice", {})


def _contains(text: str, phrases: list[str]) -> bool:
    return any(fold(phrase) in text for phrase in phrases)


def _standalone(text: str, phrases: list[str]) -> bool:
    cleaned = re.sub(r"[^\w ]", "", text).strip()
    return cleaned in {fold(p) for p in phrases}


def classify_choice(message: str) -> Optional[str]:
    cfg = _cfg()
    text = fold(message)
    if not text:
        return None
    if "recado" in text:
        return LEAVE_MESSAGE
    if _contains(text, cfg.get("dismiss", [])):
        return DISMISS
    if _contains(text, cfg.get("check_dra", [])) or _standalone(text, cfg.get("affirmatives", [])):
        return CHECK_DRA
    if _contains(text, cfg.get("leave_message", [])):
        return LEAVE_MESSAGE
    return None
