import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env da raiz do projeto
load_dotenv(Path(__file__).resolve().parent / ".env")

def get_integration_flags() -> dict:
    """
    Retorna o status binário (1 = Ativo, 0 = Inativo) das integrações da clínica.
    """
    # 1. WhatsApp: Verifica se há configuração da Evolution API ou Token no .env
    whatsapp_active = 1 if os.getenv("EVOLUTION_API_URL") and (os.getenv("EVOLUTION_API_KEY") or os.getenv("WHATSAPP_TOKEN")) else 0

    # 2. Gemini: Verifica se a chave GEMINI_API_KEY está presente e preenchida
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    gemini_active = 1 if gemini_key and not gemini_key.startswith("SUA_CHAVE") else 0

    # 3. Calendar: O ID oficial da agenda da Dra. Daiana está configurado
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "b7f9f29c5e491112263af69f24f06ab0f15be2e0bd240370f7f4efae99669cb4@group.calendar.google.com")
    calendar_active = 1 if calendar_id else 0

    return {
        "calendar": calendar_active,
        "gemini": gemini_active,
        "whatsapp": whatsapp_active
    }

if __name__ == "__main__":
    flags = get_integration_flags()
    print("=== Status das Integrações (Flags) ===")
    for service, status in flags.items():
        print(f"  - {service}: {status}")