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
    nome_jogo_imos: str = "",
) -> ComponenteResumo:
    return ComponenteResumo(
        id=id_,
        materia_prima_id=1,
        papel=papel,
        descricao=descricao,
        quantidade=Decimal(quantidade),
        nome_jogo_imos=nome_jogo_imos or None,
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
    nome_jogo_imos="Dob_Recta_BL_75B1550_H0",
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
    dialogo.componentes_table.item(0, 3).setText("2,5")

    assert dialogo.componentes()[0].quantidade == Decimal("2.5")
    dialogo.deleteLater()


def test_quantidade_em_branco_conta_como_uma() -> None:
    dialogo = MateriaPrimaDialog(componentes=[CALCO])
    dialogo.componentes_table.item(0, 3).setText("")

    assert dialogo.componentes()[0].quantidade == Decimal("1")
    dialogo.deleteLater()


def test_celulas_vazias_viajam_como_none() -> None:
    dialogo = MateriaPrimaDialog()
    dialogo._acrescentar_componente()
    dialogo.componentes_table.item(0, 4).setText("SO_O_NOME_IMOS")

    linha = dialogo.componentes()[0]
    assert linha.nome_imos == "SO_O_NOME_IMOS"
    assert linha.ref_phc is None
    assert linha.ref_fornecedor is None
    assert linha.descricao is None
    dialogo.deleteLater()


# --- O campo Nome iMos (materiais simples, 1 para 1) -------------------------


def test_a_ficha_tem_o_campo_nome_imos() -> None:
    # Faltava, e sem ele o «Guardar» de QUALQUER matéria-prima rebentava:
    # a página pedia dados.nome_imos a uma dataclass que não o tinha.
    dialogo = MateriaPrimaDialog()
    dialogo.descricao_input.setText("AGL MLM LINHO CANCUN 19MM")
    dialogo.nome_imos_input.setText("  AGL_MLM_LINHO_CANCUN_19MM  ")

    assert dialogo.get_data().nome_imos == "AGL_MLM_LINHO_CANCUN_19MM"
    dialogo.deleteLater()


def test_sem_nome_imos_escrito_fica_none() -> None:
    dialogo = MateriaPrimaDialog()
    dialogo.descricao_input.setText("QUALQUER COISA")

    assert dialogo.get_data().nome_imos is None
    dialogo.deleteLater()


# --- A ficha tem de caber ----------------------------------------------------


def test_a_ficha_e_larga_para_as_colunas_dos_componentes_caberem() -> None:
    dialogo = MateriaPrimaDialog()

    largura_das_colunas = sum(MateriaPrimaDialog.COMPONENTES_LARGURAS.values())

    assert dialogo.minimumWidth() >= largura_das_colunas
    dialogo.deleteLater()


# --- "Gravar como..." avisa antes de deixar os componentes para trás --------


def test_gravar_como_sem_componentes_nao_pergunta_nada() -> None:
    dialogo = MateriaPrimaDialog()

    assert dialogo._componentes_ficam_para_tras() is True
    dialogo.deleteLater()


def test_gravar_como_com_componentes_pergunta_e_diz_quantos(monkeypatch) -> None:
    from PySide6.QtWidgets import QMessageBox

    from app.ui.dialogs import materia_prima_dialog as modulo

    perguntas: list[str] = []

    def _fingir(parent, titulo, texto, botoes, defeito):
        perguntas.append(texto)
        return QMessageBox.StandardButton.Cancel

    monkeypatch.setattr(modulo.QMessageBox, "question", staticmethod(_fingir))
    dialogo = MateriaPrimaDialog(componentes=[COPO, CALCO])

    assert dialogo._componentes_ficam_para_tras() is False
    assert len(perguntas) == 1
    assert "2 componentes" in perguntas[0]
    assert "SEM eles" in perguntas[0]
    dialogo.deleteLater()


def test_gravar_como_avisa_no_tooltip_do_botao() -> None:
    dialogo = MateriaPrimaDialog(componentes=[COPO])

    assert "componentes" in dialogo.save_as_button.toolTip().lower()
    dialogo.deleteLater()


# --- De onde vem cada coluna (o Paulo perguntou, e enganou-se numa) ---------


def test_cada_coluna_dos_componentes_diz_de_onde_vem() -> None:
    dialogo = MateriaPrimaDialog()

    for indice, cabecalho in enumerate(MateriaPrimaDialog.COMPONENTES_HEADERS):
        titulo = dialogo.componentes_table.horizontalHeaderItem(indice)
        assert titulo is not None
        assert titulo.toolTip() == MateriaPrimaDialog.COMPONENTES_DICAS[cabecalho]
        assert titulo.toolTip().strip()
    dialogo.deleteLater()


def test_a_dica_do_nome_imos_diz_que_e_o_nome_da_uniao() -> None:
    # Foi ele que reparou: o nome da uniao nunca muda, os parametros la'
    # dentro mudam.
    dica = MateriaPrimaDialog.COMPONENTES_DICAS["Nome União (iMos)"]

    assert "união" in dica.lower()
    assert "nunca muda" in dica.lower()


def test_a_dica_da_ref_fornecedor_diz_a_origem_e_que_pode_faltar() -> None:
    # Sondagem ao PHC a 03-09-2026: dos 2336 artigos FF, ZERO tinham o
    # `forref` preenchido. A referencia do fornecedor so' pode vir do iMos.
    dica = MateriaPrimaDialog.COMPONENTES_DICAS["Ref Fornecedor"]

    assert "PHC" in dica
    assert "iMos" in dica
    assert "vazia" in dica
    # E nao e' o numero do catalogo que vem dentro da descricao Hafele.
    assert "637.76.352" in dica


def test_a_dica_da_descricao_diz_que_e_so_para_ler() -> None:
    dica = MateriaPrimaDialog.COMPONENTES_DICAS["Descrição"]

    assert "PHC" in dica
    assert "não liga nada" in dica


def test_as_celulas_tambem_levam_a_dica_da_coluna() -> None:
    # O tooltip da tabela nao chega a's celulas, e e' com o cursor em cima da
    # celula que a duvida aparece.
    dialogo = MateriaPrimaDialog(componentes=[COPO])

    for coluna in range(1, len(MateriaPrimaDialog.COMPONENTES_HEADERS)):
        celula = dialogo.componentes_table.item(0, coluna)
        cabecalho = MateriaPrimaDialog.COMPONENTES_HEADERS[coluna]
        assert celula.toolTip() == MateriaPrimaDialog.COMPONENTES_DICAS[cabecalho]
    dialogo.deleteLater()


def test_a_dica_do_papel_esta_na_lista_de_escolha() -> None:
    dialogo = MateriaPrimaDialog(componentes=[COPO])

    escolha = dialogo.componentes_table.cellWidget(0, 0)

    assert escolha.toolTip() == MateriaPrimaDialog.COMPONENTES_DICAS["Papel"]
    dialogo.deleteLater()


# --- O «Nome iMos» dos Dados num conjunto conta a mesma linha duas vezes ----


def test_conjunto_com_nome_imos_nos_dados_e_avisado() -> None:
    dialogo = MateriaPrimaDialog(componentes=[COPO, CALCO])

    dialogo.nome_imos_input.setText("PE_AXILO_H72_92_63776352")

    assert "contada duas vezes" in dialogo.componentes_status.text()
    dialogo.deleteLater()


def test_limpar_o_nome_imos_dos_dados_tira_o_aviso() -> None:
    dialogo = MateriaPrimaDialog(componentes=[COPO, CALCO])
    dialogo.nome_imos_input.setText("PE_AXILO_H72_92_63776352")

    dialogo.nome_imos_input.setText("")

    assert "contada duas vezes" not in dialogo.componentes_status.text()
    assert "2 componentes" in dialogo.componentes_status.text()
    dialogo.deleteLater()


def test_material_simples_com_nome_imos_nao_leva_aviso_nenhum() -> None:
    # Sem componentes, o campo dos Dados e' exactamente onde ele deve estar.
    dialogo = MateriaPrimaDialog()

    dialogo.nome_imos_input.setText("AGL_MLM_LINHO_CANCUN_19MM")

    assert "contada duas vezes" not in dialogo.componentes_status.text()
    dialogo.deleteLater()


def test_a_dica_do_campo_dos_dados_manda_deixar_vazio_num_conjunto() -> None:
    dialogo = MateriaPrimaDialog()

    dica = dialogo.nome_imos_input.toolTip()

    assert "CONJUNTO" in dica
    assert "vazio" in dica
    dialogo.deleteLater()


# --- O Jogo de Unioes: a 4.a chave, e a melhor -----------------------------


def test_a_tabela_tem_a_coluna_do_jogo_de_unioes() -> None:
    # Descoberto na base do iMos a 06-09-2026: a IDBPURCH tem
    # CONNECTORSETNAME, que agrupa a dobradica + calco + batente + parafusos
    # exactamente como o Martelo os orca numa linha so'.
    assert MateriaPrimaDialog.COMPONENTES_HEADERS == [
        "Papel",
        "Jogo de Uniões (iMos)",
        "Descrição",
        "Qt/conj.",
        "Nome União (iMos)",
        "Ref PHC",
        "Ref Fornecedor",
    ]


def test_a_dica_do_jogo_explica_onde_ele_esta_no_imos() -> None:
    dica = MateriaPrimaDialog.COMPONENTES_DICAS["Jogo de Uniões (iMos)"]

    assert "Jogos de uniões" in dica
    assert "conjunto inteiro" in dica
    # A regra que o servico faz cumprir tem de estar escrita no ecra.
    assert "um jogo só pode pertencer a uma" in dica


def test_o_jogo_e_lido_e_devolvido_pela_tabela() -> None:
    dialogo = MateriaPrimaDialog(componentes=[COPO])

    assert dialogo.componentes_table.item(0, 1).text() == "Dob_Recta_BL_75B1550_H0"
    assert dialogo.componentes()[0].nome_jogo_imos == "Dob_Recta_BL_75B1550_H0"
    dialogo.deleteLater()


def test_uma_linha_so_com_o_jogo_ja_e_valida() -> None:
    # Mapear pelo jogo dispensa preencher o componente: a linha do iMos traz
    # o jogo, e e' isso que identifica o conjunto.
    dialogo = MateriaPrimaDialog()
    dialogo._acrescentar_componente()
    dialogo.componentes_table.item(0, 1).setText("Pe_Axilo_H72_92_4pontear")

    linha = dialogo.componentes()[0]

    assert linha.nome_jogo_imos == "Pe_Axilo_H72_92_4pontear"
    assert linha.nome_imos is None
    assert linha.ref_phc is None
    dialogo.deleteLater()


def test_a_celula_do_jogo_leva_a_dica_da_coluna() -> None:
    dialogo = MateriaPrimaDialog(componentes=[COPO])

    celula = dialogo.componentes_table.item(0, 1)

    assert celula.toolTip() == MateriaPrimaDialog.COMPONENTES_DICAS[
        "Jogo de Uniões (iMos)"
    ]
    dialogo.deleteLater()


def test_o_texto_de_apoio_manda_comecar_pelo_jogo() -> None:
    # Enquanto o ecra so' falava em componentes, o caminho curto ficava
    # escondido e ele preenchia as quatro colunas uma a uma.
    dialogo = MateriaPrimaDialog()
    aba = dialogo.abas.widget(1)

    textos = [
        w.text()
        for w in aba.findChildren(type(dialogo.componentes_status))
        if w.text()
    ]
    apoio = "\n".join(textos)

    assert "CAMINHO CURTO" in apoio
    assert "uma linha só com ele chega" in apoio
    # Um jogo do iMos traz os parafusos de fixacao la' dentro.
    assert "parafusos de fixação" in apoio
    dialogo.deleteLater()
