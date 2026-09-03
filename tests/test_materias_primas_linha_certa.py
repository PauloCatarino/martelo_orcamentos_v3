"""A ficha que abre tem de ser a da linha escolhida, mesmo com a tabela ordenada.

A tabela das Matérias-Primas é ordenável: clicar num cabeçalho troca as linhas
de sítio. O mapa linha→material era guardado pelo NÚMERO DA LINHA, que é
exatamente o que a ordenação muda — bastava reordenar para o botão "Editar"
abrir a ficha de outro material. E como o "Guardar" da ficha grava no material
que ela abriu, a alteração ia parar ao material errado.

Apanhado pelo Paulo a 31-08-2026: linha do PLC0051 escolhida, ficha do PLC0055
aberta.
"""

from __future__ import annotations

import os
from decimal import Decimal
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidget

from app.ui.pages.materias_primas_page import MateriasPrimasPage

_app = QApplication.instance() or QApplication([])


def _materia(id_: int, ref_le: str, descricao: str, preco: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=id_,
        ref_le=ref_le,
        descricao=descricao,
        tipo_original_excel="AGLOMERADO",
        familia_original_excel="PLACAS",
        unidade="M2",
        tipo_preco="TABELA",
        preco_tabela=Decimal(preco),
        preco_liquido=Decimal(preco),
        desconto=None,
        margem=Decimal("10"),
        desperdicio_percentagem=Decimal("20"),
        fornecedor="J.P.LEITÃO",
        referencia_fornecedor=None,
        nome_fabricante="ABET LAMINATI",
        cor="BRANCO",
        ref_phc=None,
        link=None,
        imagem_ficheiro=None,
        coresp_orla_0_4="ORL0004",
        coresp_orla_1_0="ORL0005",
        comprimento=Decimal("3050"),
        largura=Decimal("1300"),
        espessura=Decimal("19"),
        observacoes=None,
        criado_por="Paulo",
        alterado_por="Paulo",
        ativo=True,
        data_ultimo_preco=None,
        stock=False,
    )


def _pagina_falsa() -> SimpleNamespace:
    """O mínimo da página para correr o preenchimento da tabela a sério."""
    return SimpleNamespace(
        table=QTableWidget(0, len(MateriasPrimasPage.TABLE_HEADERS)),
        _materias_por_id={},
        _larguras_restauradas=True,
        _larguras_seed_feito=True,
        _pintar_avisos=lambda _row, _materia: None,
        _texto_preco=lambda materia: str(materia.preco_liquido),
        _texto_data_preco=lambda _materia: "",
        _texto_stock=lambda _materia: "Não",
    )


#: Os dois materiais do print do Paulo, na ordem em que a base os devolve.
PLC0051 = _materia(91, "PLC0051", "AGL TERM BRANCO GHIACCIO 410/BRILHO  19MM", "22.40")
PLC0055 = _materia(92, "PLC0055", "AGL TERM BRANCO GHIACCIO 410/MATE  19MM", "25.81")


def test_encher_a_tabela_ja_reordena_as_linhas() -> None:
    """Porque é que isto rebentava mesmo sem ninguém clicar em cabeçalho nenhum.

    O ``setSortingEnabled(True)`` no fim do preenchimento faz a tabela ordenar
    ali mesmo. A ordem em que os materiais entram NÃO é a ordem em que ficam à
    vista — e era essa ordem de entrada que o mapa antigo usava como chave.
    """
    pagina = _pagina_falsa()
    MateriasPrimasPage._preencher_tabela(pagina, [PLC0051, PLC0055])

    refs_a_vista = [
        pagina.table.item(row, 0).text() for row in range(pagina.table.rowCount())
    ]
    assert refs_a_vista != [PLC0051.ref_le, PLC0055.ref_le]


def test_cada_linha_devolve_o_material_que_mostra() -> None:
    pagina = _pagina_falsa()
    MateriasPrimasPage._preencher_tabela(pagina, [PLC0051, PLC0055])

    for row in range(pagina.table.rowCount()):
        materia = MateriasPrimasPage._materia_da_linha(pagina, row)
        assert materia is not None
        assert materia.ref_le == pagina.table.item(row, 0).text()


def test_linha_certa_depois_de_ordenar_ao_contrario() -> None:
    """O bug: com a tabela ordenada ao contrário, a linha 0 é o outro material."""
    pagina = _pagina_falsa()
    MateriasPrimasPage._preencher_tabela(pagina, [PLC0051, PLC0055])

    pagina.table.sortItems(0, Qt.SortOrder.DescendingOrder)  # Ref LE, Z→A

    assert pagina.table.item(0, 0).text() == "PLC0055"
    assert MateriasPrimasPage._materia_da_linha(pagina, 0) is PLC0055
    assert MateriasPrimasPage._materia_da_linha(pagina, 1) is PLC0051


def test_linha_certa_depois_de_ordenar_por_outra_coluna() -> None:
    pagina = _pagina_falsa()
    MateriasPrimasPage._preencher_tabela(pagina, [PLC0051, PLC0055])

    coluna_descricao = MateriasPrimasPage.TABLE_HEADERS.index("Descrição")
    pagina.table.sortItems(coluna_descricao, Qt.SortOrder.DescendingOrder)

    primeira = MateriasPrimasPage._materia_da_linha(pagina, 0)
    assert primeira is not None
    assert primeira.descricao == pagina.table.item(0, coluna_descricao).text()


def test_linha_sem_material_devolve_nada() -> None:
    pagina = _pagina_falsa()
    MateriasPrimasPage._preencher_tabela(pagina, [])

    assert MateriasPrimasPage._materia_da_linha(pagina, 0) is None


def test_o_id_viaja_em_todas_as_celulas_da_linha() -> None:
    """Assim a linha continua identificável mesmo com colunas escondidas."""
    pagina = _pagina_falsa()
    MateriasPrimasPage._preencher_tabela(pagina, [PLC0051])

    ids = {
        pagina.table.item(0, coluna).data(Qt.ItemDataRole.UserRole)
        for coluna in range(pagina.table.columnCount())
    }
    assert ids == {PLC0051.id}
