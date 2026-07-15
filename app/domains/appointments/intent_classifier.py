import json
import sys
from typing import Dict

from app.infrastructure.config.config_loader import load_guardrails


def classify_intent(message: str) -> Dict[str, str]:
    text = (message or "").strip().lower()
    config = load_guardrails()
    default_intent = config.get("default_intent", "UNKNOWN")

    if not text:
        return {"intent": default_intent, "confidence": "low"}

    intents = config.get("intent_examples", {})
    for intent, examples in intents.items():
        normalized_examples = [example.lower() for example in examples]
        if any(example in text for example in normalized_examples):
            return {"intent": intent, "confidence": "high"}

    if any(word in text for word in ["ajuda", "duvida", "pergunta", "como", "qual", "onde"]):
        return {"intent": "QUESTION", "confidence": "medium"}

    return {"intent": default_intent, "confidence": "medium"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "missing message"}, ensure_ascii=False))
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    print(json.dumps(classify_intent(message), ensure_ascii=False))
