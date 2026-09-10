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


#: O trecho que o `_chunks_pdf` de mentira devolve por cada PDF.
TRECHO = "Ref: ABC | Descricao: Dobradica | Preco: 12.5"


def _criar_pdf(caminho: Path) -> None:
    """Um PDF de mentira: quem o le' e' um duplo, so' o nome conta."""
    caminho.write_bytes(b"%PDF-1.4 fake")


def _fingir(monkeypatch, catalogos: Path, indice: Path, esperado: int | None = None):
    """Poe de pe' tudo o que o indexador precisa e nao deve ser testado aqui."""
    monkeypatch.setattr(
        service_module,
        "_config",
        lambda _session: (str(catalogos), str(indice), "modelo-teste"),
    )
    # A base tem os seus proprios testes; estes sao sobre a pasta.
    monkeypatch.setattr(service_module, "listar_artigos", lambda _session: [])
    monkeypatch.setattr(
        service_module, "_chunks_pdf", lambda caminho: iter([(TRECHO, {"pagina": 1})])
    )

    class _FakeVetores:
        def astype(self, _dtype: str):
            return self

    class _FakeModelo:
        def __init__(self, nome: str) -> None:
            self.nome = nome

        def encode(self, textos, **kwargs):  # noqa: ANN001
            if esperado is not None:
                assert textos == [TRECHO] * esperado
            assert kwargs["normalize_embeddings"] is True
            return _FakeVetores()

    monkeypatch.setitem(
        sys.modules,
        "numpy",
        SimpleNamespace(
            save=lambda caminho, _v: Path(caminho).write_bytes(b"fake-npy")
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=_FakeModelo),
    )


def test_indexar_grava_embeddings_e_meta_sem_deps_pesadas(tmp_path, monkeypatch) -> None:
    catalogos = tmp_path / "catalogos"
    fornecedor = catalogos / "FornecedorA"
    fornecedor.mkdir(parents=True)
    _criar_pdf(fornecedor / "catalogo.pdf")
    indice = tmp_path / "indice"
    _fingir(monkeypatch, catalogos, indice, esperado=1)

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
        for linha in (indice / service_module.META_FILENAME)
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert linhas_meta[0]["ficheiro"] == "catalogo.pdf"
    assert linhas_meta[0]["fornecedor"] == "FornecedorA"
    assert linhas_meta[0]["texto"] == TRECHO
    assert any("modelo-teste" in mensagem for mensagem in mensagens)


def test_o_ficheiro_que_virou_base_nao_e_indexado_outra_vez(
    tmp_path, monkeypatch
) -> None:
    """O Excel curado ja' entrou pela base — indexa-lo tambem seria duplicar."""
    catalogos = tmp_path / "catalogos"
    catalogos.mkdir()
    _criar_excel(catalogos / service_module.FICHEIRO_REFERENCIAS)
    _criar_pdf(catalogos / "catalogo_de_fornecedor.pdf")
    _fingir(monkeypatch, catalogos, tmp_path / "indice", esperado=1)

    resultado = service_module.indexar(object())

    assert resultado.ficheiros == 1
    assert resultado.chunks == 1
    assert ("12_Placas_Referencias_COMPLETO.xlsx", "ja' entrou pela base") in [
        (nome, razao) for nome, razao in resultado.ignorados
    ]


def test_um_excel_sem_adaptador_fica_de_fora_mas_e_nomeado(
    tmp_path, monkeypatch
) -> None:
    """Uma folha de precos em bruto enchia o indice sem o melhorar.

    Uma tabela de ferragens de 2021 fazia sozinha 10 032 dos 49 330 trechos.
    Fica de fora — mas **dita em voz alta**: um ficheiro que desaparece do
    indice sem ninguem dizer nada e' a falha que este projeto passa a vida a
    evitar.
    """
    catalogos = tmp_path / "catalogos"
    catalogos.mkdir()
    _criar_excel(catalogos / "Tabela_de_ferragens_2021.xlsx")
    _criar_pdf(catalogos / "catalogo.pdf")
    _fingir(monkeypatch, catalogos, tmp_path / "indice", esperado=1)

    resultado = service_module.indexar(object())

    assert resultado.ficheiros == 1
    nomes = {nome: razao for nome, razao in resultado.ignorados}
    assert "Tabela_de_ferragens_2021.xlsx" in nomes
    assert "sem adaptador" in nomes["Tabela_de_ferragens_2021.xlsx"]


def test_as_copias_de_seguranca_ficam_de_fora(tmp_path, monkeypatch) -> None:
    """Cinco copias datadas do mesmo ficheiro sao cinco versoes do mesmo preco."""
    catalogos = tmp_path / "catalogos"
    backups = catalogos / "_backups"
    backups.mkdir(parents=True)
    _criar_pdf(catalogos / "tabela_do_fornecedor.pdf")
    _criar_pdf(backups / "tabela_do_fornecedor_20260910.pdf")
    _fingir(monkeypatch, catalogos, tmp_path / "indice", esperado=1)

    resultado = service_module.indexar(object())

    assert resultado.ficheiros == 1
    assert resultado.chunks == 1
    # Uma copia de seguranca nao e' um ficheiro «ignorado» a assinalar: e' uma
    # pasta inteira que nao conta, e enche-la de avisos so' dava ruido.
    assert resultado.ignorados == ()


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
