from google.cloud import bigquery
from google.oauth2 import service_account

from ip_mensageria_alocacao_api.core.configs import (
    BQ_PROJETO,
    GOOGLE_ARQUIVO_CREDENCIAIS,
)

credentials = service_account.Credentials.from_service_account_file(
    GOOGLE_ARQUIVO_CREDENCIAIS,
)

bq_client = bigquery.Client(
    project=BQ_PROJETO,
    credentials=credentials,
)
