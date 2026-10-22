import hashlib
import hmac
import json
import sys
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.domains.secretary.turn import process_turn
from app.infrastructure.memory.patient_cache import InMemoryPatientCache
from app.interfaces.http.intent_service import IntentRequestHandler
from app.interfaces.meta import whatsapp_cloud as meta


def webhook(messages=None, statuses=None):
    value = {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": "554600000000", "phone_number_id": "PNID123"},
        "contacts": [{"profile": {"name": "Ana"}, "wa_id": "5546999887766"}],
    }
    if messages is not None:
        value["messages"] = messages
    if statuses is not None:
        value["statuses"] = statuses
    return {"object": "whatsapp_business_account", "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": value}]}]}


def text_message(body, message_id="wamid.A1"):
    return {"from": "5546999887766", "id": message_id, "timestamp": "1760000000", "type": "text", "text": {"body": body}}


def handle(payload, store=None, seen=None):
    store = store or InMemoryPatientCache()
    return meta.handle_webhook(
        payload,
        lambda text, number, message_type="text": process_turn(text, number, store=store, message_type=message_type),
        seen=seen or meta.SeenMessages(),
    )


def test_verify_subscription():
    ok = meta.verify_subscription({"hub.mode": "subscribe", "hub.verify_token": "segredo", "hub.challenge": "1158201444"}, "segredo")
    assert ok == (200, "1158201444")
    assert meta.verify_subscription({"hub.mode": "subscribe", "hub.verify_token": "errado", "hub.challenge": "x"}, "segredo")[0] == 403
    assert meta.verify_subscription({}, "")[0] == 503


def test_signature():
    body = b'{"a":1}'
    good = "sha256=" + hmac.new(b"app-secret", body, hashlib.sha256).hexdigest()
    assert meta.verify_signature(body, good, "app-secret")
    assert not meta.verify_signature(body, good, "outro")
    assert not meta.verify_signature(body, None, "app-secret")
    assert not meta.verify_signature(body, good, "")


def test_text_message_gets_reply_payload_for_graph_api():
    result = handle(webhook([text_message("Oi, tudo bem?")]))
    reply = result["replies"][0]
    assert reply["to"] == "5546999887766"
    assert reply["intent"] == "GREETING"
    payload = reply["send_payload"]
    assert payload["messaging_product"] == "whatsapp"
    assert payload["to"] == "5546999887766"
    assert payload["type"] == "text"
    assert payload["context"] == {"message_id": "wamid.A1"}
    assert payload["text"]["body"] == reply["turn"]["reply_text"]


def test_status_updates_and_reactions_do_not_trigger_replies():
    statuses = [{"id": "wamid.X", "status": "delivered", "recipient_id": "5546999887766"}]
    assert handle(webhook(statuses=statuses))["replies"] == []
    reaction = {"from": "5546999887766", "id": "wamid.R", "type": "reaction", "reaction": {"emoji": "👍", "message_id": "wamid.A1"}}
    result = handle(webhook([reaction]))
    assert result["replies"] == []
    assert result["ignored"]["silent"] == 1


def test_duplicate_delivery_is_answered_once():
    seen = meta.SeenMessages()
    payload = webhook([text_message("oi", "wamid.DUP")])
    assert len(handle(payload, seen=seen)["replies"]) == 1
    second = handle(payload, seen=seen)
    assert second["replies"] == []
    assert second["duplicates"] == ["wamid.DUP"]


def test_audio_triggers_apology_and_offer_not_a_guess():
    audio = {"from": "5546999887766", "id": "wamid.AUD", "type": "audio", "audio": {"id": "MEDIA1", "mime_type": "audio/ogg"}}
    reply = handle(webhook([audio]))["replies"][0]
    assert reply["turn"]["fallback"]["state"] == "offer"
    assert "Desculpa" in reply["send_payload"]["text"]["body"]
    assert reply["handoff"]["media_type"] == "audio"


def test_interactive_button_reply_is_read_as_text():
    message = {
        "from": "5546999887766", "id": "wamid.BTN", "type": "interactive",
        "interactive": {"type": "button_reply", "button_reply": {"id": "b1", "title": "Quero remarcar"}},
    }
    reply = handle(webhook([message]))["replies"][0]
    assert reply["intent"] == "RESCHEDULE"


def test_fallback_conversation_through_meta_payloads_keeps_state():
    store = InMemoryPatientCache()
    first = handle(webhook([text_message("quanto custa o botox?", "wamid.1")]), store=store)["replies"][0]
    assert first["turn"]["fallback"]["state"] == "offer"
    second = handle(webhook([text_message("pode verificar", "wamid.2")]), store=store)["replies"][0]
    assert second["handoff"]["mode"] == "check_dra"
    assert second["escalation"]["reason"] == "doctor_check"


def _serve():
    server = ThreadingHTTPServer(("127.0.0.1", 0), IntentRequestHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _request(server, method, path, body=None, headers=None):
    host, port = server.server_address
    conn = HTTPConnection(host, port, timeout=5)
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    data = response.read().decode("utf-8")
    conn.close()
    return response.status, data


def test_http_webhook_verification(monkeypatch):
    monkeypatch.setenv("META_VERIFY_TOKEN", "segredo")
    server = _serve()
    try:
        assert _request(server, "GET", "/meta/webhook?hub.mode=subscribe&hub.verify_token=segredo&hub.challenge=42") == (200, "42")
        assert _request(server, "GET", "/meta/webhook?hub.mode=subscribe&hub.verify_token=x&hub.challenge=42")[0] == 403
    finally:
        server.shutdown()


def test_http_webhook_requires_signature_when_secret_is_set(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", "app-secret")
    monkeypatch.delenv("SIMULATION_ENABLED", raising=False)
    body = json.dumps(webhook([text_message("oi", "wamid.SIG")])).encode("utf-8")
    server = _serve()
    try:
        assert _request(server, "POST", "/meta/webhook", body, {"Content-Type": "application/json"})[0] == 403
        signature = "sha256=" + hmac.new(b"app-secret", body, hashlib.sha256).hexdigest()
        status, data = _request(server, "POST", "/meta/webhook", body, {"Content-Type": "application/json", "X-Hub-Signature-256": signature})
        assert status == 200
        assert json.loads(data)["replies"][0]["intent"] == "GREETING"
    finally:
        server.shutdown()
        meta.default_seen().clear()


def test_http_webhook_refuses_unsigned_when_no_secret_and_not_simulating(monkeypatch):
    monkeypatch.delenv("META_APP_SECRET", raising=False)
    monkeypatch.delenv("SIMULATION_ENABLED", raising=False)
    monkeypatch.delenv("META_ALLOW_UNSIGNED", raising=False)
    server = _serve()
    try:
        status, _ = _request(server, "POST", "/meta/webhook", b"{}", {"Content-Type": "application/json"})
        assert status == 503
    finally:
        server.shutdown()
