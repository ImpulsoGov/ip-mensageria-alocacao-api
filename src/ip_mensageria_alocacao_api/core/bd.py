from pathlib import Path

from google.cloud import bigquery
from google.oauth2 import service_account

from ip_mensageria_alocacao_api.core.configs import (
    BQ_PROJETO,
    GOOGLE_ARQUIVO_CREDENCIAIS,
)

_bq_client = None


def make_bq_client() -> bigquery.Client:
    global _bq_client

    if _bq_client is not None:
        return _bq_client

    # Em dev/local, pode haver um arquivo de service account montado no container.
    if GOOGLE_ARQUIVO_CREDENCIAIS and Path(GOOGLE_ARQUIVO_CREDENCIAIS).exists():
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_ARQUIVO_CREDENCIAIS,
        )
        _bq_client = bigquery.Client(project=BQ_PROJETO, credentials=credentials)

    # No Cloud Run, use Application Default Credentials (Workload Identity).
    else:
        _bq_client = bigquery.Client(project=BQ_PROJETO)

    return _bq_client
