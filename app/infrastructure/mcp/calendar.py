"""Contrato do MCP google-calendar. Implementação real entra na Fase 3."""

from typing import Any, Dict, List, Protocol


class CalendarGateway(Protocol):
    def freebusy(self, calendar_id: str, time_min: str, time_max: str) -> List[Dict[str, Any]]:
        ...

    def presence_blocks(self, calendar_id: str, at_iso: str) -> Dict[str, Any]:
        ...


class MissingCalendarGateway:
    """Falha fechada: sem cliente, não há slots."""

    def freebusy(self, calendar_id: str, time_min: str, time_max: str) -> List[Dict[str, Any]]:
        return []

    def presence_blocks(self, calendar_id: str, at_iso: str) -> Dict[str, Any]:
        return {"city": None, "evidence": None, "status": "unavailable"}
