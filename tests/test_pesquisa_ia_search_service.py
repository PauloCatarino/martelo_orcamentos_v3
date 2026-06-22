"""Tests for the Pesquisa IA catalog retrieval service."""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import numpy as np

from app.services import pesquisa_ia_search_service as service_module


def test_pesquisa_catalogos_disponivel_e_retrieval_hibrido(
    tmp_path, monkeypatch
) -> None:
    indice = tmp_path / "indice"
    indice.mkdir()
    np.save(
        indice / service_module.EMBEDDINGS_FILENAME,
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype="float32"),
    )
    metas = [
        {
            "fornecedor": "Fornecedor A",
            "ficheiro": "catalogo.xlsx",
            "caminho": "C:/catalogo.xlsx",
            "folha": "Orlas",
            "linha": 7,
            "texto": "Orla PVC branco mate",
        },
        {
            "fornecedor": "Fornecedor B",
            "ficheiro": "dobradicas.pdf",
            "caminho": "C:/dobradicas.pdf",
            "pagina": 3,
            "texto": "Dobradi\u00e7a Blum",
        },
    ]
    with open(indice / service_module.META_FILENAME, "w", encoding="utf-8") as meta:
        for linha in metas:
            meta.write(json.dumps(linha) + "\n")

    class _FakeSystemSettingService:
        def __init__(self, session) -> None:
            self.session = session

        def obter_valor(self, chave: str, default: str | None = None) -> str | None:
            valores = {
                "pasta_embeddings_ia": str(indice),
                "modelo_embeddings_ia": "modelo-teste",
            }
            return valores.get(chave, default)

    class _FakeModelo:
        def __init__(self, nome: str) -> None:
            assert nome == "modelo-teste"

        def encode(self, textos, **kwargs):  # noqa: ANN001
            assert textos == ["orla pvc"]
            assert kwargs["normalize_embeddings"] is True
            return np.array([[1.0, 0.0]], dtype="float32")

    monkeypatch.setattr(
        service_module, "SystemSettingService", _FakeSystemSettingService
    )
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=_FakeModelo),
    )

    servico = service_module.PesquisaCatalogosService(object())

    assert servico.disponivel() is True
    resultados = servico.pesquisar("orla pvc", top_n=2)

    assert resultados[0].fornecedor == "Fornecedor A"
    assert resultados[0].ficheiro == "catalogo.xlsx"
    assert resultados[0].local == "Folha Orlas / linha 7"
    assert resultados[0].score == 1.3
    assert resultados[1].local == "P\u00e1gina 3"


def test_pesquisa_catalogos_sem_indice_devolve_vazio(tmp_path, monkeypatch) -> None:
    class _FakeSystemSettingService:
        def __init__(self, session) -> None:
            self.session = session

        def obter_valor(self, chave: str, default: str | None = None) -> str | None:
            if chave == "pasta_embeddings_ia":
                return str(tmp_path / "sem_indice")
            return default

    monkeypatch.setattr(
        service_module, "SystemSettingService", _FakeSystemSettingService
    )

    servico = service_module.PesquisaCatalogosService(object())

    assert servico.disponivel() is False
    assert servico.pesquisar("orla") == []


def test_normalizar_remove_acentos_para_keywords() -> None:
    assert service_module._normalizar("Dobradi\u00e7a Blum") == "dobradica blum"
