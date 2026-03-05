import importlib.util
import json
import pickle
import sys
import types
from pathlib import Path

import pytest

from ip_mensageria_alocacao_api.core import classificadores as core_classificadores


def _load_classificadores_module(artefatos_predicao_uri: str = "gs://bucket/prefix"):
    configs_mod = types.ModuleType("ip_mensageria_alocacao_api.core.configs")
    setattr(configs_mod, "ARTEFATOS_PREDICAO_URI", artefatos_predicao_uri)
    setattr(configs_mod, "GOOGLE_ARQUIVO_CREDENCIAIS", None)
    setattr(configs_mod, "CARREGAR_CLASSIFICADORES_OFFLINE", False)

    src = types.ModuleType("src")
    src_core = types.ModuleType("ip_mensageria_alocacao_api.core")
    setattr(src_core, "configs", configs_mod)

    modelos_mod = types.ModuleType("ip_mensageria_alocacao_api.core.modelos")

    class Classificador:
        def __init__(
            self,
            modelos,
            atributos_colunas,
            atributos_categoricos,
            imputador_numerico,
            template_embedding_dims,
            midia_embedding_dims,
        ):
            self.modelos = modelos
            self.atributos_colunas = atributos_colunas
            self.atributos_categoricos = atributos_categoricos
            self.imputador_numerico = imputador_numerico
            self.template_embedding_dims = template_embedding_dims
            self.midia_embedding_dims = midia_embedding_dims

    setattr(modelos_mod, "Classificador", Classificador)

    fake_catboost = types.ModuleType("catboost")

    class CatBoostClassifier:
        def __init__(self):
            self._loaded = False

        def load_model(self, path):
            self._loaded = True

    setattr(fake_catboost, "CatBoostClassifier", CatBoostClassifier)

    metadata = {
        "num_modelos": 2,
        "template_embedding_dims": 16,
        "midia_embedding_dims": 8,
    }
    sample_imputador = {"imputer": "ok"}
    sample_atributos_colunas = ["a", "b", "c"]
    sample_atributos_categoricos = ["x", "y"]

    class FakeBlob:
        def __init__(self, path):
            self.path = path

        def download_as_bytes(self):
            if self.path.endswith("meta/metadata.json"):
                return json.dumps(metadata).encode("utf-8")
            if self.path.endswith("meta/imputador_numerico.pkl"):
                return pickle.dumps(sample_imputador)
            if self.path.endswith("meta/atributos_colunas.pkl"):
                return pickle.dumps(sample_atributos_colunas)
            if self.path.endswith("meta/atributos_categoricos.pkl"):
                return pickle.dumps(sample_atributos_categoricos)
            return b""

        def download_to_filename(self, filename):
            Path(filename).write_bytes(b"")

    class FakeBucket:
        def __init__(self, name):
            self.name = name

        def blob(self, path):
            return FakeBlob(path)

    class FakeClient:
        def __init__(self, credentials=None):
            pass

        def bucket(self, name):
            return FakeBucket(name)

        @staticmethod
        def from_service_account_json(filename):
            return FakeClient()

    google = types.ModuleType("google")
    google_cloud = types.ModuleType("google.cloud")
    storage_mod = types.ModuleType("google.cloud.storage")
    setattr(storage_mod, "Client", FakeClient)

    sys_modules_backup = {}

    for name, mod in (
        ("src", src),
        ("ip_mensageria_alocacao_api.core", src_core),
        ("ip_mensageria_alocacao_api.core.configs", configs_mod),
        ("ip_mensageria_alocacao_api.core.modelos", modelos_mod),
        ("catboost", fake_catboost),
        ("google", google),
        ("google.cloud", google_cloud),
        ("google.cloud.storage", storage_mod),
    ):
        sys_modules_backup[name] = sys.modules.get(name)
        sys.modules[name] = mod

    module_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ip_mensageria_alocacao_api"
        / "core"
        / "classificadores.py"
    )
    try:
        spec = importlib.util.spec_from_file_location(
            "classificadores_under_test", str(module_path)
        )
        assert spec is not None
        assert spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        sys.modules["classificadores_under_test"] = mod
        spec.loader.exec_module(mod)
        return mod, {
            "metadata": metadata,
            "imputador": sample_imputador,
            "atributos_colunas": sample_atributos_colunas,
            "atributos_categoricos": sample_atributos_categoricos,
        }
    finally:
        for name, original in sys_modules_backup.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
        sys.modules.pop("classificadores_under_test", None)


def test_parse_gcs_variants():
    mod, _ = _load_classificadores_module()
    assert mod._parse_gcs("gs://bucket/prefix/path") == ("bucket", "prefix/path")
    assert mod._parse_gcs("gs://bucket") == ("bucket", "")


def test_carregar_classificadores_and_caching():
    mod, samples = _load_classificadores_module()
    artef = mod.carregar_classificadores()
    assert artef.atributos_colunas == samples["atributos_colunas"]
    assert artef.atributos_categoricos == samples["atributos_categoricos"]
    assert artef.imputador_numerico == samples["imputador"]
    assert len(artef.modelos) == 2
    assert artef.modelos[0]._loaded is True
    artef2 = mod.carregar_classificadores()
    assert artef is artef2


def test_parse_gcs_invalid_uri():
    with pytest.raises(AssertionError):
        _load_classificadores_module()[0]._parse_gcs("http://invalid.com/path")


def test_carregar_classificadores_offline_mode(monkeypatch):
    monkeypatch.setattr(
        core_classificadores.configs,
        "CARREGAR_CLASSIFICADORES_OFFLINE",
        True,
        raising=False,
    )
    core_classificadores._ARTEFATOS = None  # type: ignore[attr-defined]
    classificador = core_classificadores.carregar_classificadores()
    assert classificador.modelos == []
    assert classificador.template_embedding_dims == 0
    assert classificador.midia_embedding_dims == 0
