import pathlib

from starlette.config import Config

config = Config(pathlib.Path.cwd() / ".env")

# Configuracoes de autenticacao.
API_CHAVE = config("API_CHAVE", str)
JWT_ALGORITMO = config("JWT_ALGORITMO", str)
TOKEN_VALIDADE_MINUTOS = config(
    "TOKEN_VALIDADE_MINUTOS", int
)  # infinito

BQ_PROJETO = config("BQ_PROJETO", str)
GOOGLE_ARQUIVO_CREDENCIAIS = config(
    "GOOGLE_ARQUIVO_CREDENCIAIS", str
)
ARTEFATOS_PREDICAO_URI = config("ARTEFATOS_PREDICAO_URI", str)  # gs://bucket/
