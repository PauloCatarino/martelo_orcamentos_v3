"""O separador Componentes da ficha da matéria-prima.

É o ecrã onde o mapa entre as ferragens do iMos e os conjuntos do Martelo é
construído à mão — cerca de vinte conjuntos, uma vez só.
"""

from __future__ import annotations

import os
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.materia_prima_types import PAPEL_PRINCIPAL, PAPEL_SECUNDARIO
from app.repositories.def_materia_prima_componente_repository import ComponenteResumo
from app.ui.dialogs.materia_prima_dialog import MateriaPrimaDialog

_app = QApplication.instance() or QApplication([])


def _componente(
    id_: int,
    papel: str,
    descricao: str,
    nome_imos: str,
    ref_phc: str = "",
    ref_fornecedor: str = "",
    quantidade: str = "1",
) -> ComponenteResumo:
    return ComponenteResumo(
        id=id_,
        materia_prima_id=1,
        papel=papel,
        descricao=descricao,
        quantidade=Decimal(quantidade),
        nome_imos=nome_imos,
        ref_phc=ref_phc or None,
        ref_fornecedor=ref_fornecedor or None,
        ref_fornecedor_norm=None,
        componente_materia_prima_id=None,
        preco_liquido=None,
        ordem=id_,
        ativo=True,
    )


COPO = _componente(
    1,
    PAPEL_PRINCIPAL,
    "Dobradiça de copo recta BLUMOTION",
    "BL_DOB_RETA_75B1550_pontear",
    "FF00060",
    "75B1550    BLUM",
)
CALCO = _componente(
    2,
    PAPEL_SECUNDARIO,
    "Calço Euro H0",
    "BL_CALCO_H0_174H7100E",
    "FF00003",
    "174H7100E    BLUM",
)


def test_a_ficha_tem_o_separador_componentes() -> None:
    dialogo = MateriaPrimaDialog()

    titulos = [dialogo.abas.tabText(i) for i in range(dialogo.abas.count())]

    assert titulos == ["Dados", "Componentes", "Histórico de preços"]
    dialogo.deleteLater()


def test_os_componentes_que_ja_existem_aparecem_na_tabela() -> None:
    dialogo = MateriaPrimaDialog(componentes=[COPO, CALCO])

    assert dialogo.componentes_table.rowCount() == 2
    lidos = dialogo.componentes()
    assert [c.papel for c in lidos] == [PAPEL_PRINCIPAL, PAPEL_SECUNDARIO]
    assert [c.nome_imos for c in lidos] == [
        "BL_DOB_RETA_75B1550_pontear",
        "BL_CALCO_H0_174H7100E",
    ]
    assert [c.ref_phc for c in lidos] == ["FF00060", "FF00003"]
    # A referência do fornecedor viaja como veio; é o serviço que a limpa.
    assert lidos[0].ref_fornecedor == "75B1550    BLUM"
    dialogo.deleteLater()


def test_uma_ficha_sem_componentes_abre_vazia_e_explica() -> None:
    dialogo = MateriaPrimaDialog()

    assert dialogo.componentes_table.rowCount() == 0
    assert dialogo.componentes() == []
    assert "Sem componentes" in dialogo.componentes_status.text()
    dialogo.deleteLater()


def test_acrescentar_uma_linha_nasce_secundaria_com_quantidade_um() -> None:
    # Só quem manda na contagem é que se declara principal, de propósito.
    dialogo = MateriaPrimaDialog()

    dialogo._acrescentar_componente()

    linha = dialogo.componentes()[0]
    assert linha.papel == PAPEL_SECUNDARIO
    assert linha.quantidade == Decimal("1")
    dialogo.deleteLater()


def test_a_ordem_segue_a_da_tabela() -> None:
    dialogo = MateriaPrimaDialog(componentes=[COPO, CALCO])

    assert [c.ordem for c in dialogo.componentes()] == [1, 2]
    dialogo.deleteLater()


def test_eliminar_a_linha_escolhida() -> None:
    dialogo = MateriaPrimaDialog(componentes=[COPO, CALCO])
    dialogo.componentes_table.selectRow(0)

    dialogo._remover_componente()

    lidos = dialogo.componentes()
    assert len(lidos) == 1
    assert lidos[0].nome_imos == "BL_CALCO_H0_174H7100E"
    dialogo.deleteLater()


def test_eliminar_sem_escolher_linha_avisa_em_vez_de_apagar() -> None:
    dialogo = MateriaPrimaDialog(componentes=[COPO])
    dialogo.componentes_table.clearSelection()
    dialogo.componentes_table.setCurrentCell(-1, -1)

    dialogo._remover_componente()

    assert dialogo.componentes_table.rowCount() == 1
    assert "Escolha primeiro" in dialogo.componentes_status.text()
    dialogo.deleteLater()


def test_a_linha_de_apoio_conta_os_principais() -> None:
    dialogo = MateriaPrimaDialog(componentes=[COPO, CALCO])

    texto = dialogo.componentes_status.text()

    assert "2 componentes" in texto
    assert "1 principal" in texto
    dialogo.deleteLater()


def test_sem_principal_nenhum_a_ficha_avisa() -> None:
    # Um conjunto sem principal nunca é contado numa obra — isso tem de se ver.
    dialogo = MateriaPrimaDialog(componentes=[CALCO])

    assert "nunca vai ser contado" in dialogo.componentes_status.text()
    dialogo.deleteLater()


def test_quantidade_escrita_a_mao_e_lida_como_numero() -> None:
    dialogo = MateriaPrimaDialog(componentes=[CALCO])
    dialogo.componentes_table.item(0, 2).setText("2,5")

    assert dialogo.componentes()[0].quantidade == Decimal("2.5")
    dialogo.deleteLater()


def test_quantidade_em_branco_conta_como_uma() -> None:
    dialogo = MateriaPrimaDialog(componentes=[CALCO])
    dialogo.componentes_table.item(0, 2).setText("")

    assert dialogo.componentes()[0].quantidade == Decimal("1")
    dialogo.deleteLater()


def test_celulas_vazias_viajam_como_none() -> None:
    dialogo = MateriaPrimaDialog()
    dialogo._acrescentar_componente()
    dialogo.componentes_table.item(0, 3).setText("SO_O_NOME_IMOS")

    linha = dialogo.componentes()[0]
    assert linha.nome_imos == "SO_O_NOME_IMOS"
    assert linha.ref_phc is None
    assert linha.ref_fornecedor is None
    assert linha.descricao is None
    dialogo.deleteLater()
