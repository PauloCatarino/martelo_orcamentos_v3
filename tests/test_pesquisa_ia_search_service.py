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


# ---------------------------------------------------------------------------
# Quando a pesquisa por IA nao esta' disponivel
# ---------------------------------------------------------------------------
#
# O executavel que vai para os PCs nao leva a biblioteca de IA (sao centenas de
# MB para uma so' funcionalidade). Mas o INDICE vive numa pasta do servidor, e
# por isso existe em todos os PCs. Antes olhava-se so' para o indice: a app
# dizia "disponivel", ia buscar o modelo e estoirava com "No module named
# 'sentence_transformers'" -- uma frase que nao ajuda ninguem no escritorio.

def _servico_com_indice(tmp_path):
    """Um servico apontado a um indice que existe mesmo."""
    indice = tmp_path / "indice"
    indice.mkdir()
    np.save(indice / service_module.EMBEDDINGS_FILENAME, np.array([[1.0, 0.0]], dtype="float32"))
    (indice / service_module.META_FILENAME).write_text(
        json.dumps({"texto": "Orla PVC branco"}) + "\n", encoding="utf-8"
    )

    servico = service_module.PesquisaCatalogosService.__new__(
        service_module.PesquisaCatalogosService
    )
    servico._pasta = str(indice)
    servico._modelo_nome = "modelo-qualquer"
    servico._meta = None
    servico._matriz = None
    servico._modelo = None
    return servico


def _sem_biblioteca_de_ia(monkeypatch):
    """Finge o executavel que vai para os PCs: sem sentence-transformers."""
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    real = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def _importar(nome, *args, **kwargs):
        if nome.split(".")[0] == "sentence_transformers":
            raise ImportError("No module named 'sentence_transformers'")
        return real(nome, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _importar)


def test_sem_a_biblioteca_de_ia_nao_se_diz_que_esta_disponivel(tmp_path, monkeypatch) -> None:
    """O indice existe (esta' no servidor), mas a biblioteca nao."""
    servico = _servico_com_indice(tmp_path)
    _sem_biblioteca_de_ia(monkeypatch)

    assert servico.disponivel() is False


def test_sem_a_biblioteca_a_pesquisa_devolve_vazio_em_vez_de_rebentar(
    tmp_path, monkeypatch
) -> None:
    servico = _servico_com_indice(tmp_path)
    _sem_biblioteca_de_ia(monkeypatch)

    assert servico.pesquisar("porta de correr") == []


def test_o_motivo_e_escrito_para_quem_o_le(tmp_path, monkeypatch) -> None:
    """Nada de nomes de modulos nem comandos: quem le' trabalha no escritorio."""
    servico = _servico_com_indice(tmp_path)
    _sem_biblioteca_de_ia(monkeypatch)

    motivo = servico.motivo_indisponivel()

    assert motivo is not None
    assert "pesquisa por IA" in motivo
    for jargao in ("sentence_transformers", "python -m", "pip install", "ImportError"):
        assert jargao not in motivo


def test_sem_indice_o_motivo_diz_qual_a_pasta(tmp_path) -> None:
    servico = service_module.PesquisaCatalogosService.__new__(
        service_module.PesquisaCatalogosService
    )
    servico._pasta = str(tmp_path / "nao_existe")
    servico._modelo_nome = "x"
    servico._meta = None
    servico._matriz = None
    servico._modelo = None

    motivo = servico.motivo_indisponivel()

    assert motivo is not None
    assert "nao_existe" in motivo


def test_sem_pasta_configurada_o_motivo_manda_as_configuracoes(tmp_path) -> None:
    servico = service_module.PesquisaCatalogosService.__new__(
        service_module.PesquisaCatalogosService
    )
    servico._pasta = ""
    servico._modelo_nome = "x"
    servico._meta = None
    servico._matriz = None
    servico._modelo = None

    motivo = servico.motivo_indisponivel()

    assert motivo is not None
    assert "Configuracoes" in motivo
