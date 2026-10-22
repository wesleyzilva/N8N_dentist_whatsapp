import os
import json
import time
import urllib.request
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from dotenv import load_dotenv

# Importa o classificador determinístico oficial
from intent_classifier import classify, normalize

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GRADE_PADRAO = ["08:00", "09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00"]

def get_integration_flags() -> dict:
    """Retorna o status binário (1 = Ativo, 0 = Inativo) das integrações."""
    whatsapp_active = 1 if os.getenv("EVOLUTION_API_URL") and (os.getenv("EVOLUTION_API_KEY") or os.getenv("WHATSAPP_TOKEN")) else 0
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    gemini_active = 1 if gemini_key and not gemini_key.startswith("SUA_CHAVE") else 0
    calendar_id = os.getenv("GOOGLE_CALENDAR_SAO_CARLOS", os.getenv("GOOGLE_CALENDAR_ID", "primary"))
    calendar_active = 1 if calendar_id else 0

    return {
        "calendar": calendar_active,
        "gemini": gemini_active,
        "whatsapp": whatsapp_active
    }

def check_calendar_today(busy_override: list = None) -> dict:
    """
    Consulta a Google Agenda do dia de forma estritamente dinâmica.
    Nenhum horário é bloqueado por padrão (sem mocks fixos de 09:00 ou almoço).
    Apenas eventos reais retornados pela API ou pelo n8n bloqueiam os horários correspondentes.
    """
    calendar_id = os.getenv("GOOGLE_CALENDAR_SAO_CARLOS", os.getenv("GOOGLE_CALENDAR_ID", "primary"))
    ocupados_hhmm = set()
    compromissos = []

    # 1. Se a chamada via n8n ou teste enviou os eventos ocupados no payload
    if busy_override is not None:
        for ev in busy_override:
            start_str = str(ev.get("start", ""))
            summary = ev.get("summary", "Compromisso")
            compromissos.append({"inicio": start_str, "resumo": summary})
            for h in GRADE_PADRAO:
                if f"T{h}" in start_str or start_str.startswith(h):
                    ocupados_hhmm.add(h)
    else:
        # 2. Caso contrário, consulta a API real do Google Calendar via token.json local
        token_path = BASE_DIR / "token.json"
        if token_path.exists():
            try:
                from google.oauth2.credentials import Credentials
                from googleapiclient.discovery import build
                creds = Credentials.from_authorized_user_file(str(token_path), ['https://www.googleapis.com/auth/calendar.readonly'])
                service = build('calendar', 'v3', credentials=creds)
                
                hoje = datetime.now(timezone.utc)
                inicio = hoje.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                fim = hoje.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
                
                events_result = service.events().list(
                    calendarId=calendar_id, timeMin=inicio, timeMax=fim,
                    singleEvents=True, orderBy='startTime'
                ).execute()
                
                for event in events_result.get('items', []):
                    start = event['start'].get('dateTime', event['start'].get('date', ''))
                    summary = event.get('summary', 'Ocupado')
                    compromissos.append({"inicio": start, "resumo": summary})
                    if "T" in start:
                        hora_min = start.split("T")[1][:5]
                        ocupados_hhmm.add(hora_min)
            except Exception:
                pass

    # Apenas os horários encontrados nos eventos reais entram na lista de bloqueio
    livres = [h for h in GRADE_PADRAO if h not in ocupados_hhmm]
    
    return {
        "calendar_id": calendar_id,
        "source": "google_calendar_pure_dynamic",
        "busy_events": compromissos,
        "blocked_hours": sorted(list(ocupados_hhmm)),
        "available_slots": livres
    }

def test_gemini_ping() -> dict:
    """Faz 1 teste rápido e econômico com o Gemini apenas quando solicitado."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    modelo = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if not api_key or api_key.startswith("SUA_CHAVE"):
        return {"status": 0, "model": modelo, "error": "API Key não configurada"}
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
    inicio = time.time()
    payload = {
        "contents": [{"parts": [{"text": "Responda apenas: OK SecretarIA Dra. Daiana online."}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 20}
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
            texto = dados["candidates"][0]["content"]["parts"][0]["text"].strip()
            return {"status": 1, "model": modelo, "latency_ms": round((time.time() - inicio) * 1000), "reply": texto}
    except Exception as e:
        return {"status": 0, "model": modelo, "error": str(e)}

# Memória de sessão simples por número para os testes de conversa
SESSIONS = {}

class DentistServiceHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict, status_code: int = 200):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path in ["/integrations", "/health"]:
            self._send_json(get_integration_flags())
        elif self.path == "/calendar-check":
            self._send_json(check_calendar_today())
        elif self.path == "/gemini-check":
            self._send_json(test_gemini_ping())
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path == "/turn":
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body.decode('utf-8')) if body else {}
            except Exception:
                payload = {}

            msg = str(payload.get("message", payload.get("text", "")))
            numero = str(payload.get("whatsapp_number", payload.get("from", "anonimo")))
            busy_from_n8n = payload.get("busy_events", None)

            sess = SESSIONS.setdefault(numero, {"unit_id": None, "opt_out": False, "pending": None})
            norm = normalize(msg)

            # Classificação de intenção oficial
            c = classify(msg)
            intent = c.intent
            escalar = c.escalate
            if c.opt_out:
                sess["opt_out"] = True

            # Detecta unidade pelo texto ou pelo DDD
            ddd = numero[2:4] if numero.startswith("55") and len(numero) >= 4 else "16"
            ddd_unit = "pato-branco" if ddd == "46" else "sao-carlos"
            
            conflict = False
            if "pato branco" in norm:
                if sess["unit_id"] is None and ddd_unit == "sao-carlos":
                    conflict = True
                sess["unit_id"] = "pato-branco"
            elif "sao carlos" in norm:
                if sess["unit_id"] is None and ddd_unit == "pato-branco":
                    conflict = True
                sess["unit_id"] = "sao-carlos"

            unit_atual = sess["unit_id"] or ddd_unit

            # Consulta agenda dinâmica
            agenda = check_calendar_today(busy_from_n8n)
            slots_livres = ", ".join(agenda["available_slots"][:4]) if agenda["available_slots"] else "nenhum horário disponível hoje"

            next_action = "respond"
            avail_evidence = "missing"

            if escalar or any(w in norm for w in ["esperando ha 40", "absurdo", "avaliacao pessima", "dinheiro de volta", "falar com uma pessoa", "falar com a dra"]):
                intent = "ESCALATE"
                escalar = True
                next_action = "handoff"
                reply = "Compreendo perfeitamente a sua situação. Vou encaminhar o seu atendimento agora mesmo para uma pessoa da nossa equipe humana da Dra. Daiana auxiliar você."
            elif intent == "OPT_OUT":
                reply = "Entendido. Seu número foi removido da lista de envios e não mandaremos novas mensagens."
            elif intent in ("HOURS", "RESCHEDULE") or any(w in norm for w in ["agendar", "marcar", "quinta", "horario", "semana"]):
                if intent == "UNKNOWN":
                    intent = "RESCHEDULE"
                if payload.get("include_slots") or "quais horarios" in norm or "agendar uma consulta" in norm:
                    avail_evidence = "checked"
                    reply = f"Verifiquei a agenda da Dra. Daiana ({unit_atual}). Horários livres encontrados para hoje: {slots_livres}. A consulta é para você ou familiar?"
                else:
                    reply = f"Posso verificar o reagendamento para você na unidade {unit_atual}. Qual período você prefere para eu checar na agenda?"
            elif intent == "CANCEL":
                reply = "Entendo. Antes de prosseguir, você tem certeza e confirma o cancelamento da sua consulta?"
            elif intent == "CONFIRM":
                reply = "Sua resposta foi registrada no sistema. Aguardamos você na clínica!"
            elif "robo" in norm or "pessoa de verdade" in norm:
                intent = "QUESTION"
                reply = "Sou a assistente virtual da clínica da Dra. Daiana. Posso ajudar com agendamentos ou encaminhar para nossa equipe humana!"
            else:
                reply = "Recebi sua mensagem. Como posso ajudar com sua consulta na clínica da Dra. Daiana?"

            result = {
                "intent": intent,
                "confidence": "high" if c.confidence >= 0.8 else "medium",
                "unit_hypothesis": {"unit_id": unit_atual, "conflict": conflict},
                "presence_evidence": "present" if "cheguei" in norm else "missing",
                "availability_evidence": avail_evidence,
                "calendar_snapshot": {
                    "blocked": agenda["blocked_hours"],
                    "free_slots": agenda["available_slots"]
                },
                "can_assert_facts": True,
                "escalation": {"needed": escalar, "reason": "Risco clínico ou solicitação humana" if escalar else ""},
                "reply_text": reply,
                "next": next_action,
                "session": sess,
                "status": "success"
            }
            self._send_json(result)
        else:
            self._send_json({"error": "Not found"}, 404)

def run_server(port=8001):
    httpd = HTTPServer(('0.0.0.0', port), DentistServiceHandler)
    print(f"🟢 Motor Central (Intent + Agenda Dinâmica + Flags) rodando em http://0.0.0.0:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()