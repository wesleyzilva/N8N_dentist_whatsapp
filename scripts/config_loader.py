import json
from pathlib import Path
from typing import Any, Dict


def load_guardrails(path: str | None = None) -> Dict[str, Any]:
    base_path = Path(path) if path else Path(__file__).resolve().parent.parent / "config" / "guardrails.json"
    with base_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_guardrails(data: Dict[str, Any], path: str | None = None) -> None:
    base_path = Path(path) if path else Path(__file__).resolve().parent.parent / "config" / "guardrails.json"
    base_path.parent.mkdir(parents=True, exist_ok=True)
    with base_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
