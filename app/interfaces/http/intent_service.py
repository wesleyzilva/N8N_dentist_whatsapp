import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.domains.appointments.intent_classifier import classify_intent
from app.domains.secretary.turn import process_turn
from app.infrastructure.mcp.calendar import CALENDAR_MODES, build_calendar_gateway
from app.infrastructure.memory.patient_cache import (
    default_patient_cache,
    reset_default_patient_cache,
)

_TURN_PATHS = {"/turn", "/turn/"}
_CLASSIFY_PATHS = {"/classify", "/classify/"}
_HEALTH_PATHS = {"/healthz", "/"}
_SIMULATE_TURN = "/simulate/turn"
_SIMULATE_RESET = "/simulate/reset"


def simulation_enabled() -> bool:
    return os.getenv("SIMULATION_ENABLED", "").lower() in {"1", "true", "yes"}


class IntentRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in _HEALTH_PATHS:
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "secretaria-turn",
                    "simulation_enabled": simulation_enabled(),
                    "calendar_modes": list(CALENDAR_MODES),
                },
            )
            return

        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        payload, error = self._read_json()
        if error:
            self._send_json(400, {"error": error})
            return

        message = str(payload.get("message") or payload.get("text") or "")
        whatsapp_number = str(
            payload.get("whatsapp_number") or payload.get("from") or ""
        )

        if self.path in _CLASSIFY_PATHS:
            self._send_json(200, classify_intent(message))
            return

        if self.path in _TURN_PATHS:
            self._send_json(200, process_turn(message, whatsapp_number))
            return

        if self.path in {_SIMULATE_TURN, _SIMULATE_RESET}:
            if not simulation_enabled():
                self._send_json(403, {"error": "simulation disabled (SIMULATION_ENABLED=1)"})
                return
            self._handle_simulation(payload, message, whatsapp_number)
            return

        self._send_json(404, {"error": "not found"})

    def _handle_simulation(self, payload: dict, message: str, whatsapp_number: str) -> None:
        if self.path == _SIMULATE_RESET:
            if whatsapp_number:
                default_patient_cache().delete(whatsapp_number)
            else:
                reset_default_patient_cache()
            self._send_json(200, {"status": "reset"})
            return

        mode = str(payload.get("calendar_mode") or "missing")
        if mode not in CALENDAR_MODES:
            self._send_json(400, {"error": f"calendar_mode must be one of {list(CALENDAR_MODES)}"})
            return
        gateway = build_calendar_gateway(mode, payload.get("fixture_city") or None)
        self._send_json(
            200,
            process_turn(message, whatsapp_number, calendar=gateway),
        )

    def _read_json(self) -> tuple[dict, str | None]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            return {}, "invalid json"
        if not isinstance(payload, dict):
            return {}, "invalid json"
        return payload, None

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def run_server(host: str | None = None, port: int | None = None) -> None:
    host = host or os.getenv("HOST", "0.0.0.0")
    port = port or int(os.getenv("PORT", "8001"))
    server = ThreadingHTTPServer((host, port), IntentRequestHandler)
    print(f"Intent service running on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
