from __future__ import annotations

import json
import logging
import pickle
import tempfile
from pathlib import Path
from typing import Optional

from catboost import CatBoostClassifier
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import storage
from google.cloud.storage.bucket import Bucket

from ip_mensageria_alocacao_api.core import configs
from ip_mensageria_alocacao_api.core.modelos import Classificador

_ARTEFATOS: Optional[Classificador] = None

logger = logging.getLogger(__name__)


def _classificador_offline() -> Classificador:
    return Classificador(
        modelos=[],
        atributos_colunas=[],
        atributos_categoricos=[],
        imputador_numerico=None,
        template_embedding_dims=0,
        midia_embedding_dims=0,
    )


def _make_storage_client() -> storage.Client:
    # Em dev/local, se houver JSON montado, o próprio google lib pega via
    # GOOGLE_APPLICATION_CREDENTIALS (ou você pode manter sua envvar e exportar).
    # Em Cloud Run, ADC/Workload Identity funciona automaticamente sem chave JSON.
    try:
        if (
            configs.GOOGLE_ARQUIVO_CREDENCIAIS
            and Path(configs.GOOGLE_ARQUIVO_CREDENCIAIS).exists()
        ):
            return storage.Client.from_service_account_json(
                configs.GOOGLE_ARQUIVO_CREDENCIAIS
            )
        return storage.Client()
    except DefaultCredentialsError as exc:
        raise RuntimeError(
            "Não foi possível autenticar com as credenciais do Google Cloud"
        ) from exc


def _parse_gcs(uri: str) -> tuple[str, str]:
    assert uri.startswith("gs://")
    bucket, *path = uri[5:].split("/", 1)
    return bucket, (path[0] if path else "")


def _baixar_blob_como_bytes(bucket: Bucket, path: str) -> bytes:
    blob = bucket.blob(path)
    return blob.download_as_bytes()


def carregar_classificadores() -> Classificador:
    global _ARTEFATOS
    if configs.CARREGAR_CLASSIFICADORES_OFFLINE:
        logger.warning("Modo offline ativado: retornando classificador vazio")
        return _classificador_offline()

    if _ARTEFATOS is not None:
        return _ARTEFATOS

    artefatos_predicao_uri = configs.ARTEFATOS_PREDICAO_URI
    if not artefatos_predicao_uri or not artefatos_predicao_uri.startswith("gs://"):
        raise RuntimeError(
            "Defina a envvar ARTEFATOS_PREDICAO_URI (gs://bucket/prefix)"
        )

    storage_client = _make_storage_client()
    bucket_name, prefix = _parse_gcs(artefatos_predicao_uri)
    bucket = storage_client.bucket(bucket_name)

    meta = json.loads(
        _baixar_blob_como_bytes(bucket, f"{prefix}/meta/metadata.json").decode("utf-8"),
    )
    num_modelos = int(meta["num_modelos"])
    template_embedding_dims = int(meta["template_embedding_dims"])
    midia_embedding_dims = int(meta["midia_embedding_dims"])

    # pickles
    imputador_numerico = pickle.loads(
        _baixar_blob_como_bytes(
            bucket,
            f"{prefix}/meta/imputador_numerico.pkl",
        )
    )
    atributos_colunas = pickle.loads(
        _baixar_blob_como_bytes(
            bucket,
            f"{prefix}/meta/atributos_colunas.pkl",
        )
    )
    atributos_categoricos = pickle.loads(
        _baixar_blob_como_bytes(
            bucket,
            f"{prefix}/meta/atributos_categoricos.pkl",
        )
    )

    # modelos
    modelos: list[CatBoostClassifier] = []
    for i in range(num_modelos):
        path = f"{prefix}/modelos/modelo_{i:03d}.cbm"
        m = CatBoostClassifier()

        # Para Cloud Run ser "stateless", usamos NamedTemporaryFile.
        with tempfile.NamedTemporaryFile(suffix=".cbm") as tmp:
            blob = bucket.blob(path)
            blob.download_to_filename(tmp.name)
            m.load_model(tmp.name)
        modelos.append(m)

    _ARTEFATOS = Classificador(
        modelos=modelos,
        atributos_colunas=atributos_colunas,
        atributos_categoricos=atributos_categoricos,
        imputador_numerico=imputador_numerico,
        template_embedding_dims=template_embedding_dims,
        midia_embedding_dims=midia_embedding_dims,
    )
    return _ARTEFATOS
