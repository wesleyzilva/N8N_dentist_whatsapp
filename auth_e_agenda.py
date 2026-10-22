import os
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv(Path(__file__).resolve().parent / ".env")

# Escopo de leitura da agenda
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def autenticar_e_testar():
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "b7f9f29c5e491112263af69f24f06ab0f15be2e0bd240370f7f4efae99669cb4@group.calendar.google.com")
    print(f"🔗 Conectando ao Google Calendar ID: {calendar_id}\n")

    creds = None
    token_path = Path(__file__).resolve().parent / "token.json"
    credentials_path = Path(__file__).resolve().parent / "credentials.json"

    # Se já existe um token salvo, carrega
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    
    # Se não há credenciais válidas, faz o fluxo de login via navegador
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif credentials_path.exists():
            print("🌐 Abrindo o navegador para você autorizar o acesso à sua Google Agenda...")
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            print("✅ Token salvo com sucesso em token.json!")
        else:
            print("❌ ATENÇÃO: O arquivo 'credentials.json' (chaves da API do Google Cloud) não foi encontrado na raiz do projeto.")
            print("   Baixe as credenciais OAuth do Google Cloud Console e coloque como 'credentials.json' na raiz.")
            return

    # Constrói o serviço e busca os eventos de hoje
    service = build('calendar', 'v3', credentials=creds)
    
    hoje = datetime.now(timezone.utc)
    inicio = hoje.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    fim = hoje.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

    print(f"📅 Buscando eventos na agenda para hoje...")
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=inicio,
        timeMax=fim,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])

    if not events:
        print("⚠️ Nenhum evento encontrado na agenda para hoje. (Verifique se a agenda certa está selecionada no .env)")
    else:
        print(f"✅ Encontrados {len(events)} evento(s) hoje:")
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date', ''))
            summary = event.get('summary', 'Sem Título')
            print(f"   • Horário: {start} -> Evento: {summary}")

if __name__ == '__main__':
    autenticar_e_testar()