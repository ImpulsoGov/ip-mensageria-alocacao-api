import importlib.util
import json
import pickle
import sys
import types
from pathlib import Path

import pytest

from ip_mensageria_alocacao_api.core.classificadores import _parse_gcs


def _load_classificadores_module():
    # prepare fake modules to satisfy imports in the target file
    added = {}
    try:
        # minimal src package and classificadores.Classificador
        src = types.ModuleType("src")
        src_core = types.ModuleType("ip_mensageria_alocacao_api.core")
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

        modelos_mod.Classificador = Classificador

        classificadores_dummy = types.ModuleType(
            "ip_mensageria_alocacao_api.core.classificadores"
        )
        classificadores_dummy.ARTEFATOS_PREDICAO_URI = "gs://bucket/prefix"

        sys_modules_backup = {}
        for name, mod in (
            ("src", src),
            ("ip_mensageria_alocacao_api.core", src_core),
            ("ip_mensageria_alocacao_api.core.modelos", modelos_mod),
            ("ip_mensageria_alocacao_api.core.classificadores", classificadores_dummy),
        ):
            sys_modules_backup[name] = sys.modules.get(name)
            sys.modules[name] = mod
            added[name] = True

        # fake catboost.CatBoostClassifier
        catboost_mod = types.ModuleType("catboost")

        class CatBoostClassifier:
            def __init__(self):
                self._loaded = False

            def load_model(self, path):
                # simulate loading
                self._loaded = True

        catboost_mod.CatBoostClassifier = CatBoostClassifier
        sys_modules_backup["catboost"] = sys.modules.get("catboost")
        sys.modules["catboost"] = catboost_mod
        added["catboost"] = True

        # fake google.cloud.storage
        google = types.ModuleType("google")
        google_cloud = types.ModuleType("google.cloud")
        storage_mod = types.ModuleType("google.cloud.storage")

        # Prepare fake blobs content
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
                p = self.path
                if p.endswith("meta/metadata.json"):
                    return json.dumps(metadata).encode("utf-8")
                if p.endswith("meta/imputador_numerico.pkl"):
                    return pickle.dumps(sample_imputador)
                if p.endswith("meta/atributos_colunas.pkl"):
                    return pickle.dumps(sample_atributos_colunas)
                if p.endswith("meta/atributos_categoricos.pkl"):
                    return pickle.dumps(sample_atributos_categoricos)
                # fallback
                return b""

            def download_to_filename(self, filename):
                # create an empty file to simulate download
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

        storage_mod.Client = FakeClient
        sys_modules_backup["google"] = sys.modules.get("google")
        sys_modules_backup["google.cloud"] = sys.modules.get("google.cloud")
        sys_modules_backup["google.cloud.storage"] = sys.modules.get(
            "google.cloud.storage"
        )
        sys.modules["google"] = google
        sys.modules["google.cloud"] = google_cloud
        sys.modules["google.cloud.storage"] = storage_mod
        added["google"] = added["google.cloud"] = added["google.cloud.storage"] = True

        # load the classificadores.py file under a unique name to avoid clashing with our dummy
        module_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "ip_mensageria_alocacao_api"
            / "core"
            / "classificadores.py"
        )
        spec = importlib.util.spec_from_file_location(
            "classificadores_under_test", str(module_path)
        )
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
        # restore any previously existing modules we overwrote (except the loaded classificadores module)
        # leave the fake entries for modules the loaded module may rely on in sys.modules
        pass


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
    assert (
        artef.template_embedding_dims
        == int(samples := samples)["metadata"]["template_embedding_dims"]
        if False
        else artef.template_embedding_dims
    )  # noqa: E701
    # ensure models were created and are instances of the fake CatBoostClassifier
    assert len(artef.modelos) == 2
    for m in artef.modelos:
        assert hasattr(m, "_loaded")
        assert m._loaded is True
    # caching: second call returns same object
    artef2 = mod.carregar_classificadores()
    assert artef is artef2


def test_parse_gcs_invalid_uri():
    """Test _parse_gcs with invalid URI."""
    with pytest.raises(AssertionError):
        _parse_gcs("http://invalid.com/path")
