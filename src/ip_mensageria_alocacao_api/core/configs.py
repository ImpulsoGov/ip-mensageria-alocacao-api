import os
import pathlib

from starlette.config import Config

# Em dev/local, pode existir um arquivo .env. Em Cloud Run, normalmente não existe.
# Se não houver .env, usamos apenas variáveis de ambiente do sistema operacional.
_env_path = pathlib.Path.cwd() / ".env"
config = Config(_env_path if _env_path.exists() else None, environ=os.environ)

# Configuracoes de autenticacao.
API_CHAVE = config("API_CHAVE", cast=str)
JWT_ALGORITMO = config("JWT_ALGORITMO", cast=str)
TOKEN_VALIDADE_MINUTOS = config("TOKEN_VALIDADE_MINUTOS", cast=int)  # infinito

BQ_PROJETO = config("BQ_PROJETO", cast=str)
# Opcional: em Cloud Run, prefira ADC/Workload Identity e não use arquivo JSON.
GOOGLE_ARQUIVO_CREDENCIAIS = config(
    "GOOGLE_ARQUIVO_CREDENCIAIS", cast=str, default=None
)
ARTEFATOS_PREDICAO_URI = config("ARTEFATOS_PREDICAO_URI", cast=str)  # gs://bucket/
