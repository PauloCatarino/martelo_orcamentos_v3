"""O separador Associados esconde os inativos, como os outros menus."""

from __future__ import annotations

from decimal import Decimal
import sys

import pytest

from app.domain.componente_types import PECA
from app.repositories.def_peca_componente_repository import DefPecaComponenteResumo
from app.repositories.def_peca_repository import DefPecaResumo


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _componente(id: int, ordem: int, descricao: str, *, ativo: bool):
    return DefPecaComponenteResumo(
        id=id,
        def_peca_pai_id=1,
        tipo_componente=PECA,
        def_peca_componente_id=99,
        referencia_componente=None,
        descricao=descricao,
        ordem=ordem,
        quantidade=Decimal("1.000"),
        regra_quantidade="FIXA",
        obrigatorio=True,
        ativo=ativo,
        observacoes=None,
    )


@pytest.fixture()
def page(_app):
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    peca = DefPecaResumo(
        id=1,
        codigo="FUNDO_2222+PES",
        nome="FUNDO[2222]+PES",
        descricao=None,
        grupo="FUNDOS",
        tipo_peca="COMPOSTA",
        ativo=True,
    )
    componentes = [
        _componente(1, 1, "Fundo com Orla 2222", ativo=True),
        _componente(2, 2, "Pes com Regra aplicada Fundo", ativo=True),
        _componente(3, 3, "Unioes para Modulos Cavilha", ativo=False),
        _componente(4, 4, "Unioes para Modulos Parafusos", ativo=False),
    ]
    return DefPecaDetailPage(peca, componentes=componentes)


def _descricoes(page) -> list[str]:
    return [
        page.componentes_table.item(row, 3).text()
        for row in range(page.componentes_table.rowCount())
    ]


def test_por_defeito_so_mostra_os_ativos(page) -> None:
    assert page.mostrar_componentes_inativos_check.isChecked() is False
    assert _descricoes(page) == [
        "Fundo com Orla 2222",
        "Pes com Regra aplicada Fundo",
    ]


def test_com_o_visto_mostra_tudo(page) -> None:
    page.mostrar_componentes_inativos_check.setChecked(True)

    assert len(_descricoes(page)) == 4
    assert "Unioes para Modulos Cavilha" in _descricoes(page)


def test_a_linha_selecionada_e_a_certa_com_o_filtro_ligado(page) -> None:
    # A tabela mostra 2 linhas; a segunda tem de dar o associado 2, nao o 3.
    page.componentes_table.selectRow(1)

    selecionado = page._get_selected_componente()
    assert selecionado is not None
    assert selecionado.id == 2


def test_regras_seguem_a_mesma_lista(page) -> None:
    # As duas tabelas andam a par: e por indice que o duplo clique nas Regras
    # encontra o associado a editar.
    assert page.regras_componentes_table.rowCount() == 2

    page.mostrar_componentes_inativos_check.setChecked(True)
    assert page.regras_componentes_table.rowCount() == 4


def test_avisa_quando_estao_todos_inativos(_app) -> None:
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    peca = DefPecaResumo(
        id=2,
        codigo="X",
        nome="X",
        descricao=None,
        grupo="FUNDOS",
        tipo_peca="COMPOSTA",
        ativo=True,
    )
    pagina = DefPecaDetailPage(
        peca, componentes=[_componente(1, 1, "Uniao", ativo=False)]
    )

    assert "Mostrar inativos" in pagina.componentes_status_label.text()
