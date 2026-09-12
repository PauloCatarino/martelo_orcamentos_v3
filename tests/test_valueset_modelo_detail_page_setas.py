"""As setas da página do modelo movem mesmo as linhas que estão selecionadas."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _linha(id: int, chave: str, ordem: int):
    return SimpleNamespace(
        id=id,
        chave=chave,
        ordem=ordem,
        prioridade=1,
        nome_opcao=f"OPCAO {id}",
        codigo_opcao=f"OPCAO_{id}",
        ref_le=None,
        descricao_no_orcamento=None,
        unidade=None,
        preco_tabela=None,
        margem_percentagem=None,
        desconto_percentagem=None,
        preco_liquido=None,
        desperdicio_percentagem=None,
        tipo_materia_prima=None,
        familia_materia_prima=None,
        editado_localmente=False,
        ativo=True,
    )


@pytest.fixture()
def pagina(_app, monkeypatch):
    """The detail page over four lines, with the database faked out."""
    from app.ui.pages import def_valueset_modelo_detail_page as modulo

    linhas = [
        _linha(1, "MATERIAL_COSTAS", 1),
        _linha(2, "FERRAGEM_VARAO", 2),
        _linha(3, "FERRAGEM_VARAO", 3),
        _linha(4, "ACABAMENTO_FACE_SUP", 4),
    ]
    chamadas: list = []

    class _FakeSession:
        def __enter__(self):
            return None

        def __exit__(self, *_args):
            return False

    class _FakeLinhaService:
        def __init__(self, _session):
            pass

        def listar_linhas_do_modelo(self, _modelo_id):
            return linhas

        def mover_linhas(self, modelo_id, linha_ids, *, para_cima, ids_visiveis=None):
            chamadas.append(
                {
                    "modelo_id": modelo_id,
                    "ids": list(linha_ids),
                    "para_cima": para_cima,
                    "visiveis": list(ids_visiveis or []),
                }
            )
            return True

    class _FakeOperacaoLinhaService:
        def __init__(self, _session):
            pass

        def listar_operacoes_ativas_de_linhas(self, linha_ids):
            return {linha_id: [] for linha_id in linha_ids}

    class _FakeOperacaoService:
        def __init__(self, _session):
            pass

        def listar_operacoes(self):
            return []

    class _FakeChaveService:
        """O vocabulário das chaves, que dá o grupo e a ordem de cada uma."""

        def __init__(self, _session):
            pass

        def listar_chaves(self):
            return [
                SimpleNamespace(
                    codigo="MATERIAL_COSTAS", nome="Costas",
                    grupo="MATERIAIS", ordem=1,
                ),
                SimpleNamespace(
                    codigo="FERRAGEM_VARAO", nome="Varão",
                    grupo="FERRAGENS", ordem=1,
                ),
                SimpleNamespace(
                    codigo="ACABAMENTO_FACE_SUP", nome="Acabamento face superior",
                    grupo="ACABAMENTOS", ordem=1,
                ),
            ]

    monkeypatch.setattr(modulo, "SessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(modulo, "DefValuesetModeloLinhaService", _FakeLinhaService)
    monkeypatch.setattr(
        modulo, "DefValuesetModeloLinhaOperacaoService", _FakeOperacaoLinhaService
    )
    monkeypatch.setattr(modulo, "DefOperacaoService", _FakeOperacaoService)
    monkeypatch.setattr(modulo, "DefValuesetChaveService", _FakeChaveService)

    modelo = SimpleNamespace(
        id=10, codigo="ROUP_STD", nome="Roupeiro", tipo="ROUPEIRO",
        ambito="UTILIZADOR", ativo=True,
    )
    return modulo.DefValuesetModeloDetailPage(modelo), chamadas


def _row_da_linha(page, linha_id: int) -> int:
    """A linha da tabela onde está a linha do modelo com este id."""
    for row, linha in page._linhas_by_row.items():
        if linha.id == linha_id:
            return row
    raise AssertionError(f"linha {linha_id} nao esta' na tabela")


def test_a_tabela_segue_a_coluna_ordem(pagina) -> None:
    page, _chamadas = pagina

    # Ordem 1..4, e nao agrupada por chave (que poria ACABAMENTO em primeiro).
    assert page._ids_visiveis() == [1, 2, 3, 4]


def test_as_faixas_nao_reordenam_as_linhas(pagina) -> None:
    page, _chamadas = pagina

    # Com as faixas ligadas ha' mais linhas na tabela do que linhas do modelo,
    # mas as do modelo continuam pela ordem da coluna Ordem.
    assert page.table.rowCount() > len(page._linhas_by_row)
    assert page._cabecalhos_by_row  # ha' faixas de grupo/chave
    assert page._ids_visiveis() == [1, 2, 3, 4]


def test_faixa_fechada_esconde_as_linhas_da_chave(pagina) -> None:
    page, _chamadas = pagina
    row_faixa = next(
        row
        for row, dados in page._cabecalhos_by_row.items()
        if dados == ("chave", "FERRAGEM_VARAO")
    )

    page._alternar_cabecalho(row_faixa)

    # As duas linhas do varao saem da vista; as outras ficam.
    assert page._ids_visiveis() == [1, 4]


def _no_da_chave(page, codigo: str):
    """O no' do navegador desta chave (a arvore e' refeita a cada filtro)."""
    raiz = page.arvore_chaves.invisibleRootItem()
    for indice_grupo in range(raiz.childCount()):
        grupo = raiz.child(indice_grupo)
        for indice_chave in range(grupo.childCount()):
            no = grupo.child(indice_chave)
            if no.data(0, _papel()) == ("chave", codigo):
                return no
    raise AssertionError(f"chave {codigo} nao esta' no navegador")


def test_clicar_na_chave_do_navegador_filtra_a_tabela(pagina) -> None:
    page, _chamadas = pagina

    page._handle_clique_navegador(_no_da_chave(page, "FERRAGEM_VARAO"), 0)

    assert page._chave_selecionada == "FERRAGEM_VARAO"
    assert page._grupo_selecionado == "FERRAGENS"
    assert page._ids_visiveis() == [2, 3]

    # Clicar outra vez mostra tudo de novo.
    page._handle_clique_navegador(_no_da_chave(page, "FERRAGEM_VARAO"), 0)
    assert page._chave_selecionada is None
    assert page._ids_visiveis() == [1, 2, 3, 4]


def test_limpar_filtros_repoe_tudo(pagina) -> None:
    page, _chamadas = pagina
    page._chave_selecionada = "FERRAGEM_VARAO"
    page._grupo_selecionado = "FERRAGENS"
    page._chaves_fechadas.add("FERRAGEM_VARAO")

    page.limpar_filtros()

    assert page._chave_selecionada is None
    assert page._grupo_selecionado is None
    assert page._chaves_fechadas == set()
    assert page._ids_visiveis() == [1, 2, 3, 4]


def _papel():
    from PySide6.QtCore import Qt

    return Qt.ItemDataRole.UserRole


def test_seta_move_a_linha_selecionada(pagina) -> None:
    page, chamadas = pagina
    page.table.selectRow(_row_da_linha(page, 3))

    page.mover_linha(para_cima=True)

    assert chamadas[-1]["ids"] == [3]
    assert chamadas[-1]["para_cima"] is True
    # As linhas a` vista seguem para o servico, para nao trocar com escondidas.
    assert chamadas[-1]["visiveis"] == [1, 2, 3, 4]


def test_seta_move_varias_linhas_selecionadas(pagina) -> None:
    from PySide6.QtCore import QItemSelectionModel

    page, chamadas = pagina
    flags = (
        QItemSelectionModel.SelectionFlag.Select
        | QItemSelectionModel.SelectionFlag.Rows
    )
    modelo_selecao = page.table.selectionModel()
    modelo_selecao.clearSelection()
    for linha_id in (2, 3):
        modelo_selecao.select(
            page.table.model().index(_row_da_linha(page, linha_id), 0), flags
        )

    page.mover_linha(para_cima=False)

    assert chamadas[-1]["ids"] == [2, 3]
    assert chamadas[-1]["para_cima"] is False


def test_faixa_nao_entra_na_selecao_nem_nas_setas(pagina) -> None:
    page, chamadas = pagina
    row_faixa = next(iter(page._cabecalhos_by_row))

    page.table.clearSelection()
    page.table.setCurrentCell(row_faixa, 0)

    page.mover_linha(para_cima=True)

    assert chamadas == []
    assert "Selecione uma linha" in page.status_label.text()


def test_sem_selecao_avisa_e_nao_chama_o_servico(pagina) -> None:
    page, chamadas = pagina
    page.table.clearSelection()
    page.table.setCurrentCell(-1, -1)

    page.mover_linha(para_cima=True)

    assert chamadas == []
    assert "Selecione uma linha" in page.status_label.text()
