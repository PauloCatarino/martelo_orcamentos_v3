from __future__ import annotations

from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from app.ui import tema
from app.ui.widgets.estilo_tabela_orcamentos import (
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
