"""Atalho de execução do serviço canônico (`POST /turn`).

Mantido na raiz porque README, Dockerfile e validate_local_flow.ps1 usam
`python intent_service.py`. A implementação vive em app/interfaces/http/.
O serviço antigo (agenda sintética, sem grounding) está em legacy/.
"""

from app.interfaces.http.intent_service import run_server

if __name__ == "__main__":
    run_server()
