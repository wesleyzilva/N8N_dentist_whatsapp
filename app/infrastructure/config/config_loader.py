import json
from pathlib import Path
from typing import Any, Dict


def _config_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "config"


def load_json(relative_name: str, path: str | None = None) -> Dict[str, Any]:
    base_path = Path(path) if path else _config_dir() / relative_name
    with base_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_guardrails(path: str | None = None) -> Dict[str, Any]:
    return load_json("guardrails.json", path)


def load_clinic(path: str | None = None) -> Dict[str, Any]:
    return load_json("clinic.json", path)


def load_voice(path: str | None = None) -> Dict[str, Any]:
    return load_json("voice.json", path)


def load_session(path: str | None = None) -> Dict[str, Any]:
    return load_json("session.json", path)


def save_guardrails(data: Dict[str, Any], path: str | None = None) -> None:
    base_path = Path(path) if path else _config_dir() / "guardrails.json"
    base_path.parent.mkdir(parents=True, exist_ok=True)
    with base_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
