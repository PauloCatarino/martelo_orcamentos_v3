from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from app.ui import tema
from app.ui.widgets.estilo_tabela_orcamentos import (
    FUNDO_LINHA_ROLE,
    FundoLinhaDelegate,
    aplicar_estilo_linha_orcamento,
    configurar_tabela_orcamentos,
    grupos_versoes,
)


def test_estilo_comum_configura_e_realca_linha() -> None:
    app = QApplication.instance() or QApplication([])
    tabela = QTableWidget(1, 3)
    for coluna, texto in enumerate(("260001_01", "Adjudicado", "100,00 €")):
        tabela.setItem(0, coluna, QTableWidgetItem(texto))

    configurar_tabela_orcamentos(tabela, compacta=True)
    aplicar_estilo_linha_orcamento(
        tabela, 0, coluna_codigo=0, coluna_estado=1,
        estado="Adjudicado", coluna_total=2, preco_manual=True,
    )

    assert tabela.showGrid() is False
    assert tabela.verticalHeader().defaultSectionSize() == 25
    assert tabela.item(0, 0).font().bold()
    assert tabela.item(0, 1).font().bold()
    assert tabela.item(0, 2).font().bold()
    assert "preço manual" in tabela.item(0, 2).toolTip().casefold()
    tabela.deleteLater()
    app.processEvents()


def test_grupos_versoes_ignora_orcamentos_com_uma_so_versao() -> None:
    assert grupos_versoes([10, 20, 30]) == {}


def test_grupos_versoes_numera_grupos_pela_ordem_da_lista() -> None:
    # 40 aparece 3x e 60 2x; 50 tem uma só versão e fica de fora.
    assert grupos_versoes([40, 40, 40, 50, 60, 60]) == {40: 0, 60: 1}


def test_cor_grupo_versoes_alterna_e_difere_da_zebra() -> None:
    cores_zebra = {tema.cor_zebra(0), tema.cor_zebra(1)}
    assert tema.cor_grupo_versoes(0) != tema.cor_grupo_versoes(1)
    assert not cores_zebra & {tema.cor_grupo_versoes(0), tema.cor_grupo_versoes(1)}


def test_configurar_instala_delegate_de_fundo() -> None:
    app = QApplication.instance() or QApplication([])
    tabela = QTableWidget(1, 1)
    configurar_tabela_orcamentos(tabela)
    assert isinstance(tabela.itemDelegate(), FundoLinhaDelegate)
    tabela.deleteLater()
    app.processEvents()


def test_delegate_pinta_fundo_da_linha_apesar_do_stylesheet() -> None:
    # Guards the regression: the ``::item`` stylesheet rule makes Qt ignore
    # setBackground, so the highlight must come from the delegate + role.
    app = QApplication.instance() or QApplication([])
    tabela = QTableWidget(2, 1)
    realce = tema.cor_grupo_versoes(0)
    com_realce = QTableWidgetItem("A")
    com_realce.setData(FUNDO_LINHA_ROLE, QColor(realce))
    tabela.setItem(0, 0, com_realce)
    tabela.setItem(1, 0, QTableWidgetItem("B"))
    configurar_tabela_orcamentos(tabela)
    tabela.resize(200, 80)
    tabela.show()
    app.processEvents()

    imagem = tabela.grab().toImage()
    cabecalho = tabela.horizontalHeader().height()
    y_realce = cabecalho + tabela.rowViewportPosition(0) + tabela.rowHeight(0) // 2
    y_normal = cabecalho + tabela.rowViewportPosition(1) + tabela.rowHeight(1) // 2
    cor_realce = imagem.pixelColor(20, y_realce)
    cor_normal = imagem.pixelColor(20, y_normal)

    assert cor_realce.name() == QColor(realce).name()
    assert cor_normal.name() != QColor(realce).name()
    tabela.deleteLater()
    app.processEvents()
