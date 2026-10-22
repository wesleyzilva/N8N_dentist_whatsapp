"""Adaptador da WhatsApp Cloud API (Meta).

Só traduz formatos: payload do webhook -> mensagens do paciente; resposta da secretária ->
corpo do POST /{phone_number_id}/messages. Nenhuma regra de unidade, agenda ou tom mora aqui.
O envio de fato (HTTP para o Graph API com o token) fica no n8n.

Referências do formato: webhook `entry[].changes[].value.messages[]` e `statuses[]`;
verificação por GET com `hub.mode`, `hub.verify_token` e `hub.challenge`;
assinatura no cabeçalho `X-Hub-Signature-256` (HMAC SHA-256 do corpo com o App Secret).
"""

from __future__ import annotations

import hashlib
import hmac
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

TEXT_TYPES = {"text"}
INTERACTIVE_KEYS = ("button_reply", "list_reply")
# Eventos que não pedem resposta da secretária.
SILENT_TYPES = {"reaction", "system", "ephemeral", "request_welcome"}


def verify_subscription(query: Dict[str, str], verify_token: str) -> Tuple[int, str]:
    """GET de verificação do webhook: devolve o `hub.challenge` se o token confere."""
    if not verify_token:
        return 503, "META_VERIFY_TOKEN não configurado"
    if query.get("hub.mode") == "subscribe" and hmac.compare_digest(query.get("hub.verify_token", ""), verify_token):
        return 200, query.get("hub.challenge", "")
    return 403, "token de verificação inválido"


def verify_signature(raw_body: bytes, header: Optional[str], app_secret: str) -> bool:
    if not app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.split("=", 1)[1])


def _text_of(message: Dict[str, Any]) -> Optional[str]:
    kind = message.get("type")
    if kind in TEXT_TYPES:
        return (message.get("text") or {}).get("body")
    if kind == "interactive":
        interactive = message.get("interactive") or {}
        for key in INTERACTIVE_KEYS:
            if key in interactive:
                return interactive[key].get("title")
    if kind == "button":
        return (message.get("button") or {}).get("text")
    return None


def parse_inbound(payload: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Extrai mensagens do paciente. Atualizações de status e reações são separadas."""
    messages: List[Dict[str, Any]] = []
    statuses: List[Dict[str, Any]] = []
    silent: List[Dict[str, Any]] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            if change.get("field") not in (None, "messages"):
                continue
            value = change.get("value") or {}
            phone_number_id = (value.get("metadata") or {}).get("phone_number_id")
            names = {c.get("wa_id"): (c.get("profile") or {}).get("name") for c in value.get("contacts") or []}
            statuses.extend(value.get("statuses") or [])
            for message in value.get("messages") or []:
                kind = message.get("type") or "unsupported"
                item = {
                    "message_id": message.get("id"),
                    "from": message.get("from"),
                    "name": names.get(message.get("from")),
                    "timestamp": message.get("timestamp"),
                    "phone_number_id": phone_number_id,
                    "type": kind,
                    "text": _text_of(message),
                }
                (silent if kind in SILENT_TYPES else messages).append(item)
    return {"messages": messages, "statuses": statuses, "silent": silent}


def build_text_message(to: str, body: str, reply_to: Optional[str] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    if reply_to:
        payload["context"] = {"message_id": reply_to}
    return payload


class SeenMessages:
    """A Meta reenvia o webhook se não receber 200 a tempo. Evita responder duas vezes.

    Em memória por enquanto; no passo E4 vira a tabela processed_messages do Postgres.
    """

    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 10000):
        self.ttl = ttl_seconds
        self.max = max_entries
        self._lock = threading.Lock()
        self._data: Dict[str, float] = {}

    def first_time(self, message_id: Optional[str]) -> bool:
        if not message_id:
            return True
        now = time.time()
        with self._lock:
            for key in [k for k, ts in self._data.items() if now - ts > self.ttl]:
                del self._data[key]
            if message_id in self._data:
                return False
            if len(self._data) >= self.max:
                self._data.pop(next(iter(self._data)))
            self._data[message_id] = now
            return True

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


_default_seen = SeenMessages()


def default_seen() -> SeenMessages:
    return _default_seen


TurnFn = Callable[..., Dict[str, Any]]


def handle_webhook(
    payload: Dict[str, Any],
    process_turn: TurnFn,
    seen: Optional[SeenMessages] = None,
) -> Dict[str, Any]:
    """Processa um webhook da Meta e devolve o que o n8n precisa enviar."""
    seen = seen or _default_seen
    parsed = parse_inbound(payload)
    replies: List[Dict[str, Any]] = []
    duplicates: List[str] = []
    for message in parsed["messages"]:
        if not message["from"]:
            continue
        if not seen.first_time(message["message_id"]):
            duplicates.append(message["message_id"])
            continue
        is_text = message["type"] in TEXT_TYPES or message["text"] is not None
        turn = process_turn(
            message["text"] or "",
            message["from"],
            message_type="text" if is_text else message["type"],
        )
        reply_text = turn.get("reply_text") or ""
        replies.append(
            {
                "to": message["from"],
                "in_reply_to": message["message_id"],
                "patient_name": message["name"],
                "phone_number_id": message["phone_number_id"],
                "send_payload": build_text_message(message["from"], reply_text, reply_to=message["message_id"]) if reply_text else None,
                "handoff": turn.get("handoff"),
                "escalation": turn.get("escalation"),
                "intent": turn.get("intent"),
                "turn": turn,
            }
        )
    return {
        "replies": replies,
        "duplicates": duplicates,
        "ignored": {"statuses": len(parsed["statuses"]), "silent": len(parsed["silent"])},
    }
