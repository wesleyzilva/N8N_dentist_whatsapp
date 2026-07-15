import json
import sys
from pathlib import Path


def validate_delivery(path: str | None = None) -> dict:
    base_path = Path(path) if path else Path(__file__).resolve().parent.parent / "delivery_checklist.json"
    with base_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    criteria = payload.get("acceptance_criteria", [])
    steps = payload.get("test_steps", [])
    return {
        "delivery_name": payload.get("delivery_name", "unnamed"),
        "criteria_count": len(criteria),
        "steps_count": len(steps),
        "status": "ready" if criteria and steps else "incomplete"
    }


if __name__ == "__main__":
    print(json.dumps(validate_delivery(), ensure_ascii=False))
