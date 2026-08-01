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

        def listar_operacoes_ativas_da_linha(self, _linha_id):
            return []

    class _FakeOperacaoService:
        def __init__(self, _session):
            pass

        def listar_operacoes(self):
            return []

    monkeypatch.setattr(modulo, "SessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(modulo, "DefValuesetModeloLinhaService", _FakeLinhaService)
    monkeypatch.setattr(
        modulo, "DefValuesetModeloLinhaOperacaoService", _FakeOperacaoLinhaService
    )
    monkeypatch.setattr(modulo, "DefOperacaoService", _FakeOperacaoService)

    modelo = SimpleNamespace(
        id=10, codigo="ROUP_STD", nome="Roupeiro", tipo="ROUPEIRO",
        ambito="UTILIZADOR", ativo=True,
    )
    return modulo.DefValuesetModeloDetailPage(modelo), chamadas


def test_a_tabela_segue_a_coluna_ordem(pagina) -> None:
    page, _chamadas = pagina

    # Ordem 1..4, e não agrupada por chave (que poria ACABAMENTO em primeiro).
    assert [page._linhas_by_row[row].id for row in range(4)] == [1, 2, 3, 4]


def test_seta_move_a_linha_selecionada(pagina) -> None:
    page, chamadas = pagina
    page.table.selectRow(2)

    page.mover_linha(para_cima=True)

    assert chamadas[-1]["ids"] == [3]
    assert chamadas[-1]["para_cima"] is True
    # As linhas à vista seguem para o serviço, para não trocar com escondidas.
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
    for row in (1, 2):
        modelo_selecao.select(page.table.model().index(row, 0), flags)

    page.mover_linha(para_cima=False)

    assert chamadas[-1]["ids"] == [2, 3]
    assert chamadas[-1]["para_cima"] is False


def test_sem_selecao_avisa_e_nao_chama_o_servico(pagina) -> None:
    page, chamadas = pagina
    page.table.clearSelection()
    page.table.setCurrentCell(-1, -1)

    page.mover_linha(para_cima=True)

    assert chamadas == []
    assert "Selecione uma linha" in page.status_label.text()
