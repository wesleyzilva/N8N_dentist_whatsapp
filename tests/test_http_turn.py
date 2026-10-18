import json
import sys
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.interfaces.http.intent_service import IntentRequestHandler


def _serve():
    server = ThreadingHTTPServer(("127.0.0.1", 0), IntentRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _post(server, path: str, payload: dict) -> dict:
    host, port = server.server_address
    conn = HTTPConnection(host, port, timeout=5)
    body = json.dumps(payload).encode("utf-8")
    conn.request("POST", path, body=body, headers={"Content-Type": "application/json"})
    response = conn.getresponse()
    data = json.loads(response.read().decode("utf-8"))
    conn.close()
    return {"status": response.status, "body": data}


def test_classify_still_works():
    server = _serve()
    try:
        result = _post(server, "/classify", {"message": "Quero cancelar"})
        assert result["status"] == 200
        assert result["body"]["intent"] == "CANCEL"
    finally:
        server.shutdown()


def test_turn_round_trip_question():
    server = _serve()
    try:
        result = _post(
            server,
            "/turn",
            {"message": "Tenho uma dúvida", "whatsapp_number": "554611112222"},
        )
        assert result["status"] == 200
        body = result["body"]
        assert body["intent"] == "QUESTION"
        assert body["reply_text"]
        assert "intent" in body
        assert body["presence_evidence"] == "missing"
    finally:
        server.shutdown()


def test_turn_does_not_invent_horario():
    server = _serve()
    try:
        result = _post(
            server,
            "/turn",
            {"message": "Quero ver disponibilidade", "from": "5516988887777"},
        )
        assert result["status"] == 200
        body = result["body"]
        assert body["intent"] == "AVAILABILITY"
        assert body["can_assert_facts"] is False
        assert "14h" not in body["reply_text"]
        assert "09:00" not in body["reply_text"]
    finally:
        server.shutdown()
