"""Gateways de calendário (P4/P5).

Regra de ouro: sem resultado de ferramenta, a secretária não afirma horário nem
cidade da dra. O gateway padrão (`MissingCalendarGateway`) devolve vazio.
`FixtureCalendarGateway` e `ErrorCalendarGateway` existem só para simulação/QA.
O cliente real do Google Calendar (Fase 3) ainda não existe.
"""

from typing import Any, Dict, List, Optional, Protocol

MODE_MISSING = "missing"
MODE_ERROR = "error"
MODE_FIXTURE = "fixture"
CALENDAR_MODES = (MODE_MISSING, MODE_ERROR, MODE_FIXTURE)


class CalendarGateway(Protocol):
    mode: str

    def freebusy(self, calendar_id: str, time_min: str, time_max: str) -> List[Dict[str, Any]]:
        ...

    def presence_blocks(self, calendar_id: str, at_iso: str) -> Dict[str, Any]:
        ...


class MissingCalendarGateway:
    """Calendário não configurado: nunca devolve horário nem presença."""

    mode = MODE_MISSING

    def freebusy(self, calendar_id: str = "", time_min: str = "", time_max: str = "") -> List[Dict[str, Any]]:
        return []

    def presence_blocks(self, calendar_id: str = "", at_iso: str = "") -> Dict[str, Any]:
        return {}


class ErrorCalendarGateway:
    """Simula ferramenta fora do ar (timeout, OAuth expirado)."""

    mode = MODE_ERROR

    def freebusy(self, calendar_id: str = "", time_min: str = "", time_max: str = "") -> List[Dict[str, Any]]:
        raise RuntimeError("calendar unavailable (simulated)")

    def presence_blocks(self, calendar_id: str = "", at_iso: str = "") -> Dict[str, Any]:
        raise RuntimeError("calendar unavailable (simulated)")


class FixtureCalendarGateway:
    """Resultado fixo e rotulado de teste. Nunca usar como padrão de produção."""

    mode = MODE_FIXTURE

    def __init__(self, city: Optional[str] = "São Carlos"):
        self.city = city

    def freebusy(self, calendar_id: str = "", time_min: str = "", time_max: str = "") -> List[Dict[str, Any]]:
        return [
            {"start": "quinta-feira às 09:00", "end": "quinta-feira às 10:00", "fixture": True},
            {"start": "quinta-feira às 14:30", "end": "quinta-feira às 15:30", "fixture": True},
        ]

    def presence_blocks(self, calendar_id: str = "", at_iso: str = "") -> Dict[str, Any]:
        if not self.city:
            return {}
        return {"city": self.city, "evidence": "fixture"}


def build_calendar_gateway(mode: str = MODE_MISSING, fixture_city: Optional[str] = "São Carlos") -> CalendarGateway:
    if mode == MODE_ERROR:
        return ErrorCalendarGateway()
    if mode == MODE_FIXTURE:
        return FixtureCalendarGateway(city=fixture_city or None)
    return MissingCalendarGateway()
