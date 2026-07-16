import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.domains.appointments.intent_classifier import classify_intent


class IntentRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in {"/healthz", "/"}:
            self._send_json(200, {"status": "ok"})
            return

        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path not in {"/classify", "/classify/"}:
            self._send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"

        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid json"})
            return

        message = payload.get("message", "")
        result = classify_intent(message)
        self._send_json(200, result)

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def run_server(host: str = "0.0.0.0", port: int | None = None) -> None:
    port = port or int(os.getenv("PORT", "8001"))
    server = ThreadingHTTPServer((host, port), IntentRequestHandler)
    print(f"Intent service running on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
