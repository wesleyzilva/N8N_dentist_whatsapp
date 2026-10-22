import json
import os
import re
import unicodedata
import urllib.request
from typing import Dict

# Intents que a secretária sabe tratar. O que não cair aqui vira UNKNOWN e segue o
# fluxo de desculpa + (verificar com a dra. | deixar recado).
MAPPED_INTENTS = (
    "GREETING",
    "THANKS",
    "ACK",
    "BOT_IDENTITY",
    "CONFIRM",
    "RESCHEDULE",
    "CANCEL",
    "AVAILABILITY",
    "LOCATION",
    "QUESTION",
    "ESCALATE",
    "OPT_OUT",
)

_GEMINI_VALID = [
    "RESCHEDULE", "CANCEL", "CONFIRM", "AVAILABILITY", "QUESTION", "ESCALATE", "LOCATION", "OPT_OUT",
]


def fold(text: str) -> str:
    """Minúsculas, sem acento, sem letras repetidas em excesso ('oiii' -> 'oi')."""
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    plain = re.sub(r"(.)\1{2,}", r"\1", plain)
    return re.sub(r"\s+", " ", plain).strip()


_GREETING_PREFIX = re.compile(
    r"^(?:(?:oi+e?|ola+|opa|eae|e ai|hey|bom dia|boa tarde|boa noite|salve)\b[\s,!.:;-]*)+"
)
_GREETING_ONLY = re.compile(
    r"^(?:(?:oi+e?|ola+|opa|eae|e ai|hey|bom dia|boa tarde|boa noite|salve|tudo bem|td bem|tudo bom|como vai|tudo certo)\b[\s,!?.:;-]*)+$"
)
_THANKS = re.compile(r"^(?:muito |mto )?(?:obrigad[oa]s?|brigad[oa]|obg|valeu|vlw|agradec\w*)\b")
_EMOJI_THANKS = re.compile(r"^\W*(?:🙏|❤|😍|😊|😁|🥰)")
_PRAISE = re.compile(r"^(?:adorei|amei|gostei|excelente|maravilhos\w*|otimo|top|nota 10|(?:o )?atendimento (?:foi )?(?:otimo|excelente|perfeito))\b")
_ACK = re.compile(
    r"^(?:\W*(?:👍|👌|🆗)\W*|(?:ok)+|okay|certo|beleza|blz|combinado|entendi|entendido|tudo bem|ta bom|ta certo|show|perfeito|sim|isso|"
    r"isso mesmo|pode ser|uhum|aham|nao|negativo)[\s,!.]*$"
)

# Clínico: palavra inteira (evita 'adorei' casar com 'dor').
CLINICAL_RE = re.compile(
    r"\b(?:dor(?:es)?|doendo|(?:meu|minha|o|a)\s+\w+\s+doi|inchad\w*|inchac\w*|inflam\w*|piorand\w*|sangr\w*|febre|sintoma\w*|"
    r"vermelh\w*|roxo|hematoma|necrose|alergi\w*|coceira|infec\w*|pus|emergencia|urgente|urgencia|desmai\w*|"
    r"formigamento|dormente|assimetri\w*|caro[cç]o|endureci\w*)\b"
)
HUMAN_RE = re.compile(
    r"(?:humano|atendente|pessoa de verdade|falar com (?:uma |a |alguem|algu[eé]m|gente|a dra|a doutora|a dr)|"
    r"falar com (?:a )?(?:dra|doutora|daiana)|chama (?:a )?(?:dra|doutora|alguem)|quero (?:a )?(?:dra|doutora)\b|"
    r"passa (?:pra|para) (?:dra|doutora|alguem)|gerente|responsavel)"
)
COMPLAINT_RE = re.compile(
    r"(?:absurdo|pessim\w*|horrivel|inaceitavel|reembols\w*|dinheiro de volta|processo|procon|reclam\w*|"
    r"esperando h[aá]|ninguem me (?:atende|responde)|incompetente|descaso|vergonha|enganad\w*)"
)
BOT_RE = re.compile(
    r"(?:\brobo\w*|\bbot\b|\bia\b|inteligencia artificial|(?:voce|vc|tu|ce)\s*(?:e|eh)\s+(?:um |uma )?(?:humano|humana|pessoa|gente|real)|"
    r"(?:e|eh)\s+(?:um |uma )?(?:humano|humana|pessoa de verdade|gente de verdade)|com quem (?:eu )?(?:to|estou) falando|quem (?:e|eh) (?:voce|vc|tu|ce)|quem ta falando|maquina)"
)
_WANTS_PERSON = re.compile(r"(?:quero|preciso|gostaria|queria|passa|chama|falar com|me (?:passa|transfere))")
BARE_QUESTION_RE = re.compile(
    r"^(?:(?:eu )?(?:tenho|queria tirar|quero tirar|posso fazer|tenho so) (?:uma |umas )?(?:duvida|pergunta)s?|"
    r"posso (?:te )?perguntar(?: uma coisa)?|queria perguntar(?: uma coisa)?|uma duvida|uma pergunta|"
    r"preciso (?:de )?(?:uma )?(?:ajuda|informac\w+))[\s?!.,]*$"
)


def is_clinical_text(message: str, extra_keywords: list[str] | None = None) -> bool:
    text = fold(message)
    if CLINICAL_RE.search(text):
        return True
    for keyword in extra_keywords or []:
        key = fold(keyword)
        if key and re.search(rf"\b{re.escape(key)}\w*", text) and key not in {"dor"}:
            return True
    return False


def escalation_reason(message: str) -> str:
    """clinical | human_requested | complaint (clínico tem prioridade; depois reclamação)."""
    text = fold(message)
    if CLINICAL_RE.search(text):
        return "clinical"
    if COMPLAINT_RE.search(text):
        return "complaint"
    if HUMAN_RE.search(text):
        return "human_requested"
    return "clinical"


def _call_gemini(message: str, api_key: str) -> str:
    prompt = f"""Classifique a intenção desta mensagem de WhatsApp de um consultório de harmonização orofacial: "{message}".
Responda APENAS uma destas opções:
- RESCHEDULE (quer remarcar ou mudar dia/horário)
- CANCEL (quer cancelar ou não vai conseguir ir)
- CONFIRM (confirmar consulta, avisar atraso ou que chegou)
- AVAILABILITY (quer saber vagas, horários livres, se atende determinado dia/período)
- QUESTION (dúvidas sobre preços, procedimentos)
- ESCALATE (reclamação grave, sintomas como dor/inchaço, pedir para falar com a Dra. ou pessoa humana)
- LOCATION (confirmando cidade como São Carlos ou Pato Branco)
- OPT_OUT (parar de receber mensagens ou sair)
- UNKNOWN (texto aleatório)
Resposta:"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 10},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=3) as response:
        data = json.loads(response.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
        for valid in _GEMINI_VALID:
            if valid in text:
                return valid
    return "UNKNOWN"


_RULES = [
    ("OPT_OUT", r"(?:\bsair\b|(?:parar|pare|para) de (?:me )?(?:receber|enviar|mandar)|nao quero (?:mais )?receber|cancelar cadastro|"
                r"descadastr\w*|opt-?out|\bstop\b|me tire|me tira da lista|nao me (?:mande|envie|chame))"),
    ("RESCHEDULE", r"(?:reagend\w*|remarc\w*|mudar (?:o |a |de )?(?:dia|horario|data|consulta|atendimento)|"
                   r"trocar (?:o |a |de )?(?:dia|horario|data)|adiar|antecipar|passar (?:pra|para) (?:outro|outra)|outro (?:dia|horario))"),
    ("CANCEL", r"(?:cancel\w*|desmarc\w*|nao vou (?:conseguir|poder|comparecer|ir)|nao (?:consigo|posso) (?:ir|comparecer|vir)|"
               r"nao vou mais|vou (?:ter que )?faltar|nao vai dar|desisti|desistir)"),
    ("CONFIRM", r"(?:confirm\w*|cheguei|estou a caminho|to a caminho|vou chegar|atrasad\w*|chegando|vou me atrasar|estarei presente|"
                r"estarei ai|to indo)"),
]
# Dados da consulta que o paciente já tem: sem sistema de agendamento ligado, não há fonte para responder.
_OWN_APPOINTMENT = re.compile(
    r"(?:(?:minha|meu) (?:consulta|horario|atendimento|avaliacao|agendamento).{0,25}(?:que dia|que horas|qual|quando|onde)|"
    r"(?:qual|que) (?:o |a )?(?:horario|dia|hora).{0,20}(?:minha|meu)|esqueci (?:o |a )?(?:horario|dia|hora|consulta)|"
    r"(?:nao )?(?:recebi|chegou).{0,15}lembrete)"
)
_ASKS_SLOT = re.compile(r"(?:tem|ha|existe|sobrou|abriu)\s+(?:algum |um )?(?:horario|vaga|encaixe)|horario livre|vaga livre")
_LOCATION = re.compile(
    r"(?:sao carlos|pato branco|(?:onde|em que cidade|qual cidade).{0,25}(?:dra|doutora|esta|atende|atendendo))"
)
_AVAIL_BLOCK = re.compile(r"(?:horario|vaga|disponib\w*|agenda)")
_AVAIL = re.compile(
    r"(?:horario|vaga|disponib\w*|quando tem|\bhj\b|tem agenda|agenda (?:da|de|da dra)|encaixe|marcar|agendar|agendamento|"
    r"avaliacao|primeira consulta|"
    r"segunda|terca|quarta|quinta|sexta|sabado|domingo|amanha|hoje|semana que vem|proxima semana|essa semana|"
    r"manha|tarde|noite|marca pra mim|dia \d{1,2}|atende (?:hoje|amanha|sabado|domingo|segunda|terca|quarta|quinta|sexta))"
)
_QUESTION = re.compile(
    r"(?:\bdoi\b|quanto (?:custa|e|fica|sai)|valor|preco|orcamento|parcel\w*|cartao|pix|desconto|promocao|convenio|plano de saude|"
    r"atende|funciona|telefone|endereco|onde fica|localizacao|como chego|estacionamento|"
    r"duvida|pergunta|fazem|faz |harmoniza\w*|orofacial|botox|toxina|preench\w*|bioestimul\w*|fios?\b|labio|"
    r"bigode|olheira|papada|rinomodel\w*|skinbooster|acido hialuronico|procedimento|tratamento|resultado|duracao|dura quanto|"
    r"quanto tempo|anestesia|primeira vez|como (?:e|funciona)|quem (?:e|sao)|doutora|dra\b|especialidade|"
    r"cirurgia|laser|peeling|limpeza de pele|dentist\w*|ortodont\w*|clareamento)"
)


def classify_intent(message: str) -> Dict[str, str]:
    text = fold(message)
    if not text:
        return {"intent": "UNKNOWN", "confidence": "low"}

    if BOT_RE.search(text) and not _WANTS_PERSON.search(text):
        return {"intent": "BOT_IDENTITY", "confidence": "high"}

    if CLINICAL_RE.search(text) or COMPLAINT_RE.search(text) or HUMAN_RE.search(text):
        return {"intent": "ESCALATE", "confidence": "high"}

    if _GREETING_ONLY.match(text):
        return {"intent": "GREETING", "confidence": "high"}

    core = _GREETING_PREFIX.sub("", text).strip() or text
    if _EMOJI_THANKS.match(core) or _PRAISE.match(core):
        return {"intent": "THANKS", "confidence": "high"}
    thanks = _THANKS.match(core)
    if thanks:
        rest = core[thanks.end():].strip(" ,.!?;:-")
        if not re.sub(r"[\W_]+", "", rest) or re.match(r"^(?:pela|pelo|por)\b", rest):
            return {"intent": "THANKS", "confidence": "high"}
        core = rest

    if _ACK.match(core):
        return {"intent": "ACK", "confidence": "high"}

    if _OWN_APPOINTMENT.search(core):
        return {"intent": "QUESTION", "confidence": "high"}

    if _ASKS_SLOT.search(core):
        return {"intent": "AVAILABILITY", "confidence": "high"}

    for intent, pattern in _RULES:
        if re.search(pattern, core):
            return {"intent": intent, "confidence": "high"}

    if _LOCATION.search(core) and not _AVAIL_BLOCK.search(core):
        return {"intent": "LOCATION", "confidence": "high"}

    if BARE_QUESTION_RE.match(core):
        return {"intent": "QUESTION", "confidence": "high"}

    if _AVAIL.search(core) and not _is_price_or_topic(core):
        return {"intent": "AVAILABILITY", "confidence": "high"}

    if _QUESTION.search(core):
        return {"intent": "QUESTION", "confidence": "high"}

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            gemini_intent = _call_gemini(message, api_key)
            if gemini_intent != "UNKNOWN":
                return {"intent": gemini_intent, "confidence": "medium"}
        except Exception as exc:
            print(f"[Gemini Classifier Warning]: {exc}")

    return {"intent": "UNKNOWN", "confidence": "low"}


_PRICE_OR_TOPIC = re.compile(
    r"(?:quanto|valor|preco|orcamento|parcel\w*|cartao|pix|desconto|convenio|botox|toxina|preench\w*|bioestimul\w*|labio|"
    r"procedimento|tratamento|resultado|duracao|anestesia|endereco|telefone|onde fica)"
)


def _is_price_or_topic(core: str) -> bool:
    """Pergunta sobre preço/procedimento que também cita dia ou 'consulta' não é pedido de agenda."""
    return bool(_PRICE_OR_TOPIC.search(core))
