import json
import urllib.request

URL_N8N = "http://localhost:5678/webhook/intent-webhook"

# 3 Mensagens simulando um paciente real agendando para o filho
CENARIOS_TESTE = [
    "Olá! Gostaria de agendar uma consulta para o meu filho Arthur nesta quinta-feira à tarde. Meu nome é Wesley.",
    "Prefiro o horário das 14h30! Pode marcar para nós?",
    "Vocês atendem pelo plano Bradesco ou emitem nota para reembolso?"
]

print("\n🚀 INICIANDO TESTE DA SECRETARIA INTELIGENTE VIA CÓDIGO...\n" + "="*60)

for i, mensagem in enumerate(CENARIOS_TESTE, 1):
    print(f"\n💬 [Turno {i}] Paciente enviando: '{mensagem}'")
    
    payload = json.dumps({
        "message": mensagem,
        "from": "5516997214286",
        "name": "Wesley Gomes da Silva"
    }).encode("utf-8")
    
    req = urllib.request.Request(
        URL_N8N,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            resultado = json.loads(response.read().decode("utf-8"))
            print(f"🤖 [Resposta da SecretarIA]:\n{resultado.get('reply_text', resultado)}")
    except Exception as e:
        print(f"❌ Erro ao chamar n8n: {e}")

print("\n" + "="*60 + "\n✅ Teste finalizado!")