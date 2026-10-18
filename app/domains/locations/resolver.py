from __future__ import annotations

import re
from typing import Any, Dict, Optional

from app.infrastructure.config.config_loader import load_clinic

_DDD_IN_TEXT = re.compile(r"\b(?:ddd\s*)?(\d{2})\b")
_BR_MSISDN = re.compile(r"^(?:\+?55)?(\d{2})\d{8,9}$")


def _normalize(text: str) -> str:
    return (
        (text or "")
        .lower()
        .replace("á", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )


def resolve_unit(
    message: str = "",
    whatsapp_number: str = "",
    clinic: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Hipótese de unidade do paciente. Nunca afirma presença da dra."""
    clinic = clinic or load_clinic()
    units = clinic.get("units", [])
    text = _normalize(message)
    digits = re.sub(r"\D", "", whatsapp_number or "")

    from_text = None
    for unit in units:
        aliases = [_normalize(alias) for alias in unit.get("aliases", [])]
        aliases.append(_normalize(unit.get("city", "")))
        if any(alias and alias in text for alias in aliases):
            from_text = unit
            break

    ddd_from_number = None
    match_msisdn = _BR_MSISDN.match(digits)
    if match_msisdn:
        ddd_from_number = match_msisdn.group(1)

    ddd_from_text = None
    for ddd in _DDD_IN_TEXT.findall(text):
        if any(unit.get("ddd") == ddd for unit in units):
            ddd_from_text = ddd
            break

    from_ddd = None
    chosen_ddd = ddd_from_text or ddd_from_number
    if chosen_ddd:
        from_ddd = next((unit for unit in units if unit.get("ddd") == chosen_ddd), None)

    if from_text and from_ddd and from_text["id"] != from_ddd["id"]:
        return {
            "unit_id": from_text["id"],
            "source": "message_overrides_ddd",
            "confidence": "medium",
            "conflict": True,
            "patient_ddd": chosen_ddd,
            "is_presence": False,
            "needs_confirmation": True,
        }

    if from_text:
        return {
            "unit_id": from_text["id"],
            "source": "message_text",
            "confidence": "high",
            "conflict": False,
            "patient_ddd": chosen_ddd,
            "is_presence": False,
            "needs_confirmation": False,
        }

    if from_ddd:
        return {
            "unit_id": from_ddd["id"],
            "source": "ddd_hypothesis",
            "confidence": "medium",
            "conflict": False,
            "patient_ddd": chosen_ddd,
            "is_presence": False,
            "needs_confirmation": True,
        }

    return {
        "unit_id": None,
        "source": "unknown",
        "confidence": "low",
        "conflict": False,
        "patient_ddd": chosen_ddd,
        "is_presence": False,
        "needs_confirmation": True,
    }
