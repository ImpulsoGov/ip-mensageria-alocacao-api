from pathlib import Path

from google.cloud import bigquery
from google.oauth2 import service_account

from ip_mensageria_alocacao_api.core.configs import (
    BQ_PROJETO,
    GOOGLE_ARQUIVO_CREDENCIAIS,
)


def make_bq_client() -> bigquery.Client:
    # Em dev/local, pode haver um arquivo de service account montado no container.
    if GOOGLE_ARQUIVO_CREDENCIAIS and Path(GOOGLE_ARQUIVO_CREDENCIAIS).exists():
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_ARQUIVO_CREDENCIAIS,
        )
        return bigquery.Client(project=BQ_PROJETO, credentials=credentials)

    # No Cloud Run, use Application Default Credentials (Workload Identity).
    return bigquery.Client(project=BQ_PROJETO)


bq_client = make_bq_client()
