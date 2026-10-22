import json
import os
import re
import urllib.request
from typing import Dict


def _call_gemini(message: str, api_key: str) -> str:
    prompt = f"""Classifique a intenção desta mensagem de WhatsApp para um consultório médico/odontológico: "{message}".
Responda APENAS uma destas opções:
- RESCHEDULE (quer remarcar ou mudar dia/horário)
- CANCEL (quer cancelar ou não vai conseguir ir)
- CONFIRM (confirmar consulta, avisar atraso ou que chegou)
- AVAILABILITY (quer saber vagas, horários livres, se atende determinado dia/período)
- QUESTION (dúvidas sobre preços, procedimentos, se é robô)
- ESCALATE (reclamação grave, sintomas como dor/inchaço, pedir para falar com a Dra. ou pessoa humana)
- LOCATION (confirmando cidade como São Carlos ou Pato Branco)
- OPT_OUT (parar de receber mensagens ou sair)
- UNKNOWN (texto aleatório)
Resposta:"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 10}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=3) as response:
        data = json.loads(response.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
        for valid in ["RESCHEDULE", "CANCEL", "CONFIRM", "AVAILABILITY", "QUESTION", "ESCALATE", "LOCATION", "OPT_OUT"]:
            if valid in text:
                return valid
    return "UNKNOWN"


def classify_intent(message: str) -> Dict[str, str]:
    text = (message or "").strip().lower()
    if not text:
        return {"intent": "UNKNOWN", "confidence": "low"}

    # 1. Casos de Escalação Imediata (Dor, Reclamação, Falar com Humano/Dra)
    if re.search(r"(inchad|doend|dor|piorand|sangr|febre|sintoma|esperando h[aá]|absurdo|p[eé]ssim|dinheiro de volta|reembols|humano|atendente|falar com uma pessoa|falar com a dra)", text):
        return {"intent": "ESCALATE", "confidence": "high"}

    # 2. Opt Out
    if re.search(r"(sair|parar de receber|cancelar cadastro|opt-?out)", text):
        return {"intent": "OPT_OUT", "confidence": "high"}

    # 3. Reagendamento (sem \b no final para pegar 'reagendar', 'reagendamento', 'remarcar')
    if re.search(r"(reagend|remarc|mudar|trocar|adiar)", text):
        return {"intent": "RESCHEDULE", "confidence": "high"}

    # 4. Cancelamento
    if re.search(r"(cancel|desmarc|n[aã]o vou conseguir|n[aã]o posso ir)", text):
        return {"intent": "CANCEL", "confidence": "high"}

    # 5. Confirmação
    if re.search(r"(confirm|cheguei|estou a caminho|atrasad|vou chegar)", text):
        return {"intent": "CONFIRM", "confidence": "high"}

    # 6. Localização / Cidade
    if re.search(r"(s[aã]o carlos|pato branco)", text) and not re.search(r"(hor[aá]rio|vaga)", text):
        return {"intent": "LOCATION", "confidence": "high"}

    # 7. Disponibilidade de horários
    if re.search(r"(hor[aá]rio|vaga|dispon[ií]ve|quando tem|tem vaga|tem hor|quinta|sexta|semana que vem|manh[aã]|tarde|marca pra mim)", text):
        return {"intent": "AVAILABILITY", "confidence": "high"}

    # 8. Dúvidas
    if re.search(r"(quanto custa|valor|pre[cç]o|atende|funciona|domingo|rob[oô]|pessoa de verdade|telefone)", text):
        return {"intent": "QUESTION", "confidence": "high"}

    # 9. Fallback Inteligente no Gemini
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            gemini_intent = _call_gemini(message, api_key)
            if gemini_intent != "UNKNOWN":
                return {"intent": gemini_intent, "confidence": "high"}
        except Exception as e:
            print(f"[Gemini Classifier Warning]: {e}")

    return {"intent": "UNKNOWN", "confidence": "low"}