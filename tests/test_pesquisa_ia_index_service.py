"""O indexador da Pesquisa IA: a base primeiro, os ficheiros a seguir."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

from datetime import date
from decimal import Decimal

from openpyxl import Workbook

from app.services.catalogos.consulta import ArtigoConsulta
from app.services import pesquisa_ia_index_service as service_module


def _criar_excel(caminho: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Catalogo"
    ws.append(["Tabela de fornecedor"])
    ws.append(["Ref", "Descricao", "Preco", "Espessura"])
    ws.append(["ABC", "Dobradi\u00e7a", 12.5, "8 mm"])
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
        (
            "Ref: ABC | Descricao: Dobradi\u00e7a | Preco: 12.5 | Espessura: 8 mm",
            {"folha": "Catalogo", "linha": 3},
        ),
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
    # A base entra por aqui; este teste é sobre os ficheiros da pasta.
    monkeypatch.setattr(service_module, "listar_artigos", lambda _session: [])

    class _FakeVetores:
        def astype(self, _dtype: str):
            return self

    class _FakeModelo:
        def __init__(self, nome: str) -> None:
            self.nome = nome

        def encode(self, textos, **kwargs):  # noqa: ANN001
            assert textos == [
                "Ref: ABC | Descricao: Dobradi\u00e7a | Preco: 12.5 | Espessura: 8 mm"
            ]
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
    assert resultado.chunks == 1
    assert resultado.artigos == 0
    assert resultado.erros == 0
    assert resultado.pasta_indice == str(indice)
    assert (indice / service_module.EMBEDDINGS_FILENAME).read_bytes() == b"fake-npy"

    linhas_meta = [
        json.loads(linha)
        for linha in (indice / service_module.META_FILENAME).read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert linhas_meta[0]["ficheiro"] == "catalogo.xlsx"
    assert linhas_meta[0]["fornecedor"] == "FornecedorA"
    assert linhas_meta[0]["texto"] == (
        "Ref: ABC | Descricao: Dobradi\u00e7a | Preco: 12.5 | Espessura: 8 mm"
    )
    assert any("modelo-teste" in mensagem for mensagem in mensagens)


def test_o_ficheiro_que_virou_base_nao_e_indexado_outra_vez(
    tmp_path, monkeypatch
) -> None:
    """O Excel curado ja' entrou pela base — indexa-lo tambem seria duplicar."""
    catalogos = tmp_path / "catalogos"
    catalogos.mkdir()
    _criar_excel(catalogos / service_module.FICHEIRO_REFERENCIAS)
    _criar_excel(catalogos / "outro_fornecedor.xlsx")

    monkeypatch.setattr(
        service_module,
        "_config",
        lambda _session: (str(catalogos), str(tmp_path / "indice"), "modelo-teste"),
    )
    monkeypatch.setattr(service_module, "listar_artigos", lambda _session: [])

    class _FakeVetores:
        def astype(self, _dtype: str):
            return self

    class _FakeModelo:
        def __init__(self, nome: str) -> None:
            self.nome = nome

        def encode(self, textos, **kwargs):  # noqa: ANN001
            assert len(textos) == 1
            return _FakeVetores()

    monkeypatch.setitem(
        sys.modules,
        "numpy",
        SimpleNamespace(save=lambda caminho, _v: Path(caminho).write_bytes(b"x")),
    )
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=_FakeModelo),
    )

    resultado = service_module.indexar(object())

    assert resultado.ficheiros == 1
    assert resultado.chunks == 1


def test_as_copias_de_seguranca_ficam_de_fora(tmp_path, monkeypatch) -> None:
    """Cinco copias datadas do mesmo ficheiro sao cinco versoes do mesmo preco."""
    catalogos = tmp_path / "catalogos"
    backups = catalogos / "_backups"
    backups.mkdir(parents=True)
    _criar_excel(catalogos / "tabela_do_fornecedor.xlsx")
    _criar_excel(backups / "tabela_do_fornecedor_20260910.xlsx")

    monkeypatch.setattr(
        service_module,
        "_config",
        lambda _session: (str(catalogos), str(tmp_path / "indice"), "modelo-teste"),
    )
    monkeypatch.setattr(service_module, "listar_artigos", lambda _session: [])

    class _FakeVetores:
        def astype(self, _dtype: str):
            return self

    class _FakeModelo:
        def __init__(self, nome: str) -> None:
            self.nome = nome

        def encode(self, textos, **kwargs):  # noqa: ANN001
            assert len(textos) == 1
            return _FakeVetores()

    monkeypatch.setitem(
        sys.modules,
        "numpy",
        SimpleNamespace(save=lambda caminho, _v: Path(caminho).write_bytes(b"x")),
    )
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=_FakeModelo),
    )

    resultado = service_module.indexar(object())

    assert resultado.ficheiros == 1
    assert resultado.chunks == 1


def test_a_frase_de_um_artigo_diz_a_espessura_e_o_preco() -> None:
    """Era isto que faltava: no Excel a linha trazia dez precos e nenhum rotulo."""
    artigo = ArtigoConsulta(
        fornecedor="Balbino & Faustino",
        fabricante="EGGER",
        tabela="EGGER Balbino & Faustino",
        folha="Stock_B&F_Egger",
        data_tabela=date(2026, 4, 20),
        chave_natural="F037|ST76|PB STD|19mm",
        referencia="F037",
        descricao="EGGER F037 ST76 · Travertino Taormina · 19mm",
        nome_design="Travertino Taormina",
        acabamento="ST76",
        substrato="PB STD",
        substrato_origem="Eurodekor Aglomerado",
        espessura_mm=Decimal("19"),
        espessura="19mm",
        familia="Eurodekor",
        seccao="Eurodekor Aglomerado",
        grupo="Grupo 8",
        tipo="Eurodekor Aglomerado revestido",
        unidade="M2",
        preco=Decimal("21.02"),
        artigo_id=1,
        tabela_id=1,
    )

    frase = service_module._frase(artigo)

    assert "Referencia: F037" in frase
    assert "Espessura: 19mm" in frase
    assert "Preco: 21.02 EUR/M2" in frase
    assert "Substrato: PB STD" in frase
    assert "Tabela: EGGER Balbino & Faustino" in frase


def test_um_artigo_sem_preco_diz_sob_consulta() -> None:
    artigo = ArtigoConsulta(
        fornecedor="Somapil",
        fabricante="BLUM",
        tabela="BLUM · Somapil",
        folha="Somapil_BLUM",
        data_tabela=None,
        chave_natural="22.8000|Kit capas Cinza",
        referencia="22.8000",
        descricao="BLUM · Kit capas Cinza",
        nome_design=None,
        acabamento=None,
        substrato=None,
        substrato_origem=None,
        espessura_mm=None,
        espessura=None,
        familia=None,
        seccao=None,
        grupo=None,
        tipo="",
        unidade="UN",
        preco=None,
        artigo_id=2,
        tabela_id=2,
    )

    assert "Preco: sob consulta" in service_module._frase(artigo)
