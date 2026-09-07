"""O preço de tabela escrito em parcelas: «0,25 + 0,15».

Pedido pelo Paulo a 07-09-2026, depois do suporte TRIS: uma ferragem é muitas
vezes um conjunto de artigos com preços diferentes, e só o total ficava
guardado. Daí a uns meses ninguém se lembrava de onde vinha.

**O total continua a ser quem manda nas contas.** As parcelas são memória.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.services.def_materia_prima_service import (
    CriarDefMateriaPrimaData,
    DefMateriaPrimaService,
    EditarDefMateriaPrimaData,
)
from app.ui.dialogs.materia_prima_dialog import MateriaPrimaDialog

_app = QApplication.instance() or QApplication([])


# --- o ecrã -----------------------------------------------------------------


def test_o_campo_aceita_uma_soma_e_devolve_o_total() -> None:
    dialogo = MateriaPrimaDialog()
    dialogo.descricao_input.setText("SUPORTE PRATELEIRA TRIS COM PERNO")

    dialogo.preco_tabela_input.setText("0,25+0,15")

    dados = dialogo.get_data()
    assert dados.preco_tabela == Decimal("0.40")
    assert dados.preco_tabela_parcelas == "0,25+0,15"
    dialogo.deleteLater()


def test_um_preco_simples_nao_guarda_parcelas_nenhumas() -> None:
    # Guardar «0,25» duas vezes nao serve de nada.
    dialogo = MateriaPrimaDialog()
    dialogo.descricao_input.setText("QUALQUER COISA")

    dialogo.preco_tabela_input.setText("0,25")

    dados = dialogo.get_data()
    assert dados.preco_tabela == Decimal("0.25")
    assert dados.preco_tabela_parcelas is None
    dialogo.deleteLater()


def test_a_soma_aparece_ao_lado_do_campo() -> None:
    dialogo = MateriaPrimaDialog()

    dialogo.preco_tabela_input.setText("0,25 + 0,15")

    assert "0,40" in dialogo.preco_tabela_soma_label.text()
    dialogo.deleteLater()


def test_num_preco_simples_a_etiqueta_fica_vazia() -> None:
    dialogo = MateriaPrimaDialog()

    dialogo.preco_tabela_input.setText("0,25")

    assert dialogo.preco_tabela_soma_label.text() == ""
    dialogo.deleteLater()


def test_o_preco_liquido_usa_o_total_da_soma() -> None:
    dialogo = MateriaPrimaDialog()
    dialogo.preco_tabela_input.setText("0,25+0,15")

    dialogo.desconto_input.setText("50")

    # 0,40 com 50% de desconto = 0,20.
    assert dialogo.get_data().preco_liquido == Decimal("0.20")
    assert "0,20" in dialogo.preco_liquido_label.text()
    dialogo.deleteLater()


def test_uma_soma_a_meio_de_escrever_nao_deixa_gravar() -> None:
    gravou: list = []
    dialogo = MateriaPrimaDialog(
        on_save=lambda dados: gravou.append(dados) or True,
        ref_le_sugerida=lambda familia: "FER0999",
    )
    dialogo.descricao_input.setText("QUALQUER COISA")
    dialogo.familia_input.setCurrentText("FERRAGENS")
    dialogo.preco_tabela_input.setText("0,25+")

    dialogo._validar_e_aceitar()

    assert gravou == []
    assert "soma de parcelas" in dialogo.error_label.text()
    dialogo.deleteLater()


# --- a base -----------------------------------------------------------------


@pytest.fixture()
def catalogo(session) -> DefMateriaPrimaService:
    return DefMateriaPrimaService(session)


def test_as_parcelas_ficam_gravadas_e_voltam(catalogo) -> None:
    criada = catalogo.criar_materia_prima(
        CriarDefMateriaPrimaData(
            descricao="SUPORTE PRATELEIRA TRIS COM PERNO",
            familia_original_excel="FERRAGENS",
            unidade="UND",
            preco_tabela=Decimal("0.40"),
            preco_tabela_parcelas="0,25+0,15",
        )
    )

    lida = catalogo.obter_por_ref_le(criada.ref_le)
    assert lida.preco_tabela == Decimal("0.4000")
    assert lida.preco_tabela_parcelas == "0,25+0,15"


def test_a_ficha_reabre_com_as_parcelas_e_nao_com_o_total(catalogo) -> None:
    criada = catalogo.criar_materia_prima(
        CriarDefMateriaPrimaData(
            descricao="SUPORTE TRIS",
            familia_original_excel="FERRAGENS",
            unidade="UND",
            preco_tabela=Decimal("0.40"),
            preco_tabela_parcelas="0,25+0,15",
        )
    )

    dialogo = MateriaPrimaDialog(criada)

    assert dialogo.preco_tabela_input.text() == "0,25+0,15"
    assert "0,40" in dialogo.preco_tabela_soma_label.text()
    dialogo.deleteLater()


def test_passar_a_preco_simples_esquece_as_parcelas(catalogo) -> None:
    criada = catalogo.criar_materia_prima(
        CriarDefMateriaPrimaData(
            descricao="SUPORTE TRIS",
            familia_original_excel="FERRAGENS",
            unidade="UND",
            preco_tabela=Decimal("0.40"),
            preco_tabela_parcelas="0,25+0,15",
        )
    )

    catalogo.editar_materia_prima(
        criada.id,
        EditarDefMateriaPrimaData(
            descricao=criada.descricao,
            ref_le=criada.ref_le,
            familia_original_excel="FERRAGENS",
            unidade="UND",
            preco_tabela=Decimal("0.50"),
        ),
    )

    lida = catalogo.obter_por_ref_le(criada.ref_le)
    assert lida.preco_tabela == Decimal("0.5000")
    # A soma antiga nao pode ficar a mentir sobre o preco novo.
    assert lida.preco_tabela_parcelas is None


def test_o_historico_de_precos_continua_a_guardar_o_total(catalogo) -> None:
    criada = catalogo.criar_materia_prima(
        CriarDefMateriaPrimaData(
            descricao="SUPORTE TRIS",
            familia_original_excel="FERRAGENS",
            unidade="UND",
            preco_tabela=Decimal("0.40"),
            preco_tabela_parcelas="0,25+0,15",
        )
    )

    historico = catalogo.historico_precos(criada.id)

    assert historico
    assert historico[0].preco_tabela == Decimal("0.4000")


def test_a_migracao_das_parcelas_chama_os_grants() -> None:
    from pathlib import Path

    migracao = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260907_110_preco_tabela_em_parcelas.py"
    )
    fonte = migracao.read_text(encoding="utf-8")

    assert "CALL martelo_aplicar_grants()" in fonte
    assert 'down_revision: str | Sequence[str] | None = "20260906_109"' in fonte
