import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

from app.domains.appointments.intent_classifier import classify_intent
from app.domains.secretary.turn import process_turn
from app.infrastructure.mcp.calendar import CALENDAR_MODES, build_calendar_gateway
from app.infrastructure.memory.patient_cache import (
    default_patient_cache,
    reset_default_patient_cache,
)
from app.infrastructure.observability.turn_log import configure as configure_logging
from app.infrastructure.observability.turn_log import log_turn, logger, timed
from app.interfaces.meta import whatsapp_cloud

_TURN_PATHS = {"/turn", "/turn/"}
_CLASSIFY_PATHS = {"/classify", "/classify/"}
_HEALTH_PATHS = {"/healthz", "/"}
_SIMULATE_TURN = "/simulate/turn"
_SIMULATE_RESET = "/simulate/reset"
_META_WEBHOOK = "/meta/webhook"


def simulation_enabled() -> bool:
    return os.getenv("SIMULATION_ENABLED", "").lower() in {"1", "true", "yes"}


def run_turn(source: str, message: str, number: str, message_type: str = "text", calendar=None) -> dict:
    """Executa o turno e registra o rastro (terminal e TURN_LOG_PATH)."""
    kwargs = {"message_type": message_type}
    if calendar is not None:
        kwargs["calendar"] = calendar
    turn, elapsed = timed(process_turn, message, number, **kwargs)
    log_turn(number=number, message=message, message_type=message_type, turn=turn, source=source, duration_ms=elapsed)
    return turn


class IntentRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        split = urlsplit(self.path)
        if split.path == _META_WEBHOOK:
            status, body = whatsapp_cloud.verify_subscription(
                dict(parse_qsl(split.query)), os.getenv("META_VERIFY_TOKEN", "")
            )
            self._send_text(status, body)
            return

        if self.path in _HEALTH_PATHS:
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "secretaria-turn",
                    "simulation_enabled": simulation_enabled(),
                    "calendar_modes": list(CALENDAR_MODES),
                    "meta_webhook": {
                        "verify_token_configured": bool(os.getenv("META_VERIFY_TOKEN")),
                        "signature_required": bool(os.getenv("META_APP_SECRET")),
                    },
                },
            )
            return

        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        payload, error = self._read_json()
        if self.path.split("?")[0] == _META_WEBHOOK:
            self._handle_meta(payload, error)
            return
        if error:
            self._send_json(400, {"error": error})
            return

        message = str(payload.get("message") or payload.get("text") or "")
        whatsapp_number = str(
            payload.get("whatsapp_number") or payload.get("from") or ""
        )
        message_type = str(payload.get("message_type") or "text")

        if self.path in _CLASSIFY_PATHS:
            self._send_json(200, classify_intent(message))
            return

        if self.path in _TURN_PATHS:
            self._send_json(200, run_turn("turn", message, whatsapp_number, message_type))
            return

        if self.path in {_SIMULATE_TURN, _SIMULATE_RESET}:
            if not simulation_enabled():
                self._send_json(403, {"error": "simulation disabled (SIMULATION_ENABLED=1)"})
                return
            self._handle_simulation(payload, message, whatsapp_number, message_type)
            return

        self._send_json(404, {"error": "not found"})

    def _handle_simulation(self, payload: dict, message: str, whatsapp_number: str, message_type: str = "text") -> None:
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
            run_turn("simulate", message, whatsapp_number, message_type, calendar=gateway),
        )

    def _handle_meta(self, payload: dict, error: str | None) -> None:
        secret = os.getenv("META_APP_SECRET", "")
        if secret:
            if not whatsapp_cloud.verify_signature(self._raw_body, self.headers.get("X-Hub-Signature-256"), secret):
                logger.warning("[meta] assinatura inválida: webhook rejeitado")
                self._send_json(403, {"error": "assinatura inválida"})
                return
        elif not (simulation_enabled() or os.getenv("META_ALLOW_UNSIGNED") == "1"):
            self._send_json(503, {"error": "META_APP_SECRET não configurado"})
            return
        if error:
            self._send_json(400, {"error": error})
            return
        result = whatsapp_cloud.handle_webhook(
            payload,
            lambda text, number, message_type="text": run_turn("meta", text, number, message_type),
        )
        self._send_json(200, result)

    def _read_json(self) -> tuple[dict, str | None]:
        length = int(self.headers.get("Content-Length", "0"))
        self._raw_body = self.rfile.read(length) if length else b""
        body = self._raw_body.decode("utf-8") if self._raw_body else "{}"
        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            return {}, "invalid json"
        if not isinstance(payload, dict):
            return {}, "invalid json"
        return payload, None

    def _send_text(self, status_code: int, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        logger.debug("http %s", format % args)


def run_server(host: str | None = None, port: int | None = None) -> None:
    host = host or os.getenv("HOST", "0.0.0.0")
    port = port or int(os.getenv("PORT", "8001"))
    configure_logging()
    server = ThreadingHTTPServer((host, port), IntentRequestHandler)
    logger.info("serviço no ar em http://%s:%s (simulação=%s, log de turnos=%s)", host, port, simulation_enabled(), os.getenv("TURN_LOG_PATH") or "desligado")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
