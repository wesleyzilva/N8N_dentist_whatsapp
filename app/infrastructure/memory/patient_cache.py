from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

from app.infrastructure.config.config_loader import load_session


def normalize_patient_key(whatsapp_number: str) -> str:
    return "".join(ch for ch in (whatsapp_number or "") if ch.isdigit())


class InMemoryPatientCache:
    """Cache TTL de slots curtos. Não guarda texto da conversa nem agenda."""

    def __init__(self, ttl_seconds: int = 86400, max_entries: int = 5000):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._data: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def from_config(cls) -> "InMemoryPatientCache":
        cfg = load_session()
        return cls(
            ttl_seconds=int(cfg.get("ttl_seconds", 86400)),
            max_entries=int(cfg.get("max_entries", 5000)),
        )

    def get(self, whatsapp_number: str) -> Optional[Dict[str, Any]]:
        key = normalize_patient_key(whatsapp_number)
        if not key:
            return None
        now = time.time()
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                return None
            if now - entry["updated_at"] > self.ttl_seconds:
                del self._data[key]
                return None
            return dict(entry["payload"])

    def put(self, whatsapp_number: str, payload: Dict[str, Any]) -> None:
        key = normalize_patient_key(whatsapp_number)
        if not key:
            return
        with self._lock:
            self._evict_locked()
            self._data[key] = {
                "updated_at": time.time(),
                "payload": dict(payload),
            }

    def delete(self, whatsapp_number: str) -> None:
        key = normalize_patient_key(whatsapp_number)
        if not key:
            return
        with self._lock:
            self._data.pop(key, None)

    def _evict_locked(self) -> None:
        now = time.time()
        expired = [
            key
            for key, entry in self._data.items()
            if now - entry["updated_at"] > self.ttl_seconds
        ]
        for key in expired:
            del self._data[key]
        if len(self._data) < self.max_entries:
            return
        oldest = sorted(self._data.items(), key=lambda item: item[1]["updated_at"])
        overflow = len(self._data) - self.max_entries + 1
        for key, _ in oldest[:overflow]:
            del self._data[key]


_DEFAULT: Optional[InMemoryPatientCache] = None
_DEFAULT_LOCK = threading.Lock()


def default_patient_cache() -> InMemoryPatientCache:
    global _DEFAULT
    with _DEFAULT_LOCK:
        if _DEFAULT is None:
            _DEFAULT = InMemoryPatientCache.from_config()
        return _DEFAULT


def reset_default_patient_cache() -> None:
    global _DEFAULT
    with _DEFAULT_LOCK:
        _DEFAULT = InMemoryPatientCache.from_config()
