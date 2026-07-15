import sys
from app.domains.appointments.intent_classifier import classify_intent


if __name__ == "__main__":
    import json

    if len(sys.argv) < 2:
        print(json.dumps({"error": "missing message"}, ensure_ascii=False))
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    print(json.dumps(classify_intent(message), ensure_ascii=False))
