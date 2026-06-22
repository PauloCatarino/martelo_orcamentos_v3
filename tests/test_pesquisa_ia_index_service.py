"""Tests for the Pesquisa IA local catalog indexer."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

from openpyxl import Workbook

from app.services import pesquisa_ia_index_service as service_module


def _criar_excel(caminho: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Catalogo"
    ws.append(["Ref", "Descricao", "Preco"])
    ws.append(["ABC", "Dobradi\u00e7a", 12.5])
    wb.save(caminho)


def test_config_usa_settings_e_fallback_do_modelo(monkeypatch) -> None:
    valores = {
        "pasta_pesquisa_profunda_ia": "C:/catalogos",
        "pasta_embeddings_ia": "C:/indice",
        "modelo_embeddings_ia": "",
    }

    class _FakeSystemSettingService:
        def __init__(self, session) -> None:
            self.session = session

        def obter_valor(self, chave: str, default: str | None = None) -> str | None:
            return valores.get(chave, default)

    monkeypatch.setattr(
        service_module, "SystemSettingService", _FakeSystemSettingService
    )

    assert service_module._config(object()) == (
        "C:/catalogos",
        "C:/indice",
        service_module.MODELO_EMBEDDINGS_DEFAULT,
    )


def test_chunks_excel_linha_por_linha(tmp_path) -> None:
    caminho = tmp_path / "catalogo.xlsx"
    _criar_excel(caminho)

    chunks = list(service_module._chunks_excel(caminho))

    assert chunks == [
        ("Ref | Descricao | Preco", {"folha": "Catalogo", "linha": 1}),
        ("ABC | Dobradi\u00e7a | 12.5", {"folha": "Catalogo", "linha": 2}),
    ]


def test_indexar_grava_embeddings_e_meta_sem_deps_pesadas(tmp_path, monkeypatch) -> None:
    catalogos = tmp_path / "catalogos"
    fornecedor = catalogos / "FornecedorA"
    fornecedor.mkdir(parents=True)
    _criar_excel(fornecedor / "catalogo.xlsx")
    indice = tmp_path / "indice"

    monkeypatch.setattr(
        service_module,
        "_config",
        lambda _session: (str(catalogos), str(indice), "modelo-teste"),
    )

    class _FakeVetores:
        def astype(self, _dtype: str):
            return self

    class _FakeModelo:
        def __init__(self, nome: str) -> None:
            self.nome = nome

        def encode(self, textos, **kwargs):  # noqa: ANN001
            assert textos == ["Ref | Descricao | Preco", "ABC | Dobradi\u00e7a | 12.5"]
            assert kwargs["normalize_embeddings"] is True
            return _FakeVetores()

    fake_numpy = SimpleNamespace(
        save=lambda caminho, _vetores: Path(caminho).write_bytes(b"fake-npy")
    )
    fake_sentence_transformers = SimpleNamespace(SentenceTransformer=_FakeModelo)
    monkeypatch.setitem(sys.modules, "numpy", fake_numpy)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_sentence_transformers)

    mensagens: list[str] = []
    resultado = service_module.indexar(object(), progresso=mensagens.append)

    assert resultado.ficheiros == 1
    assert resultado.chunks == 2
    assert resultado.erros == 0
    assert resultado.pasta_indice == str(indice)
    assert (indice / service_module.EMBEDDINGS_FILENAME).read_bytes() == b"fake-npy"

    linhas_meta = [
        json.loads(linha)
        for linha in (indice / service_module.META_FILENAME).read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert linhas_meta[1]["ficheiro"] == "catalogo.xlsx"
    assert linhas_meta[1]["fornecedor"] == "FornecedorA"
    assert linhas_meta[1]["texto"] == "ABC | Dobradi\u00e7a | 12.5"
    assert any("modelo-teste" in mensagem for mensagem in mensagens)
