"""Tests for the raw material dialog (V3-owned catalog)."""

from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.materia_prima_types import TIPO_PRECO_LIVRE
from app.repositories.def_materia_prima_repository import (
    DefMateriaPrimaResumo,
    PrecoHistoricoResumo,
)
from app.ui.dialogs.materia_prima_dialog import MateriaPrimaDialog

_app = QApplication.instance() or QApplication([])


def _materia(**overrides) -> DefMateriaPrimaResumo:
    base = {
        "id": 1,
        "ref_le": "PLC0052",
        "referencia_fornecedor": "413/BRILHO",
        "descricao": "AGL TERM BEGE ARDENNE 19MM",
        "tipo_original_excel": "AGLOMERADO",
        "familia_original_excel": "PLACAS",
        "tipo_martelo": None,
        "familia_martelo": None,
        "unidade": "M2",
        "preco_tabela": Decimal("31.20"),
        "desconto": Decimal("18"),
        "margem": None,
        "preco_liquido": Decimal("25.58"),
        "comprimento": Decimal("2800"),
        "largura": Decimal("2070"),
        "espessura": Decimal("19"),
        "fornecedor": "SONAE",
        "origem_dados": "EXCEL",
        "ativo": True,
        "observacoes": None,
        "created_at": datetime(2026, 6, 5),
        "updated_at": datetime(2026, 6, 9),
    }
    base.update(overrides)
    return DefMateriaPrimaResumo(**base)


def test_preco_liquido_e_calculado_e_nao_escrito() -> None:
    dialogo = MateriaPrimaDialog(_materia())

    assert "25,58" in dialogo.preco_liquido_label.text()

    dialogo.preco_tabela_input.setText("30")
    dialogo.desconto_input.setText("20")
    dialogo.margem_input.setText("")

    assert "24,00" in dialogo.preco_liquido_label.text()
    assert dialogo.get_data().preco_liquido == Decimal("24.00")


def test_material_de_preco_livre_nao_tem_campos_de_preco() -> None:
    dialogo = MateriaPrimaDialog(_materia())

    dialogo.tipo_preco_input.setCurrentIndex(
        dialogo.tipo_preco_input.findData(TIPO_PRECO_LIVRE)
    )

    assert dialogo.preco_tabela_input.isEnabled() is False
    assert "orçamento" in dialogo.preco_liquido_label.text()

    dados = dialogo.get_data()
    assert dados.preco_tabela is None
    assert dados.preco_liquido is None
    assert dados.tipo_preco == TIPO_PRECO_LIVRE


def test_auditoria_sem_autor_nao_diz_criado_por_ninguem() -> None:
    """Os materiais vindos do Excel não têm autor registado."""
    dialogo = MateriaPrimaDialog(_materia())

    texto = dialogo.auditoria_label.text()

    assert "Criado em 05-06-2026" in texto
    assert "por" not in texto.split("origem")[0]


def test_auditoria_com_autor_diz_quem_mexeu() -> None:
    dialogo = MateriaPrimaDialog(
        _materia(criado_por="paulo", alterado_por="admin", origem_dados="V3")
    )

    texto = dialogo.auditoria_label.text()

    assert "Criado por paulo em 05-06-2026" in texto
    assert "Última alteração por admin em 09-06-2026" in texto


def test_dialogo_novo_sugere_a_referencia_da_familia() -> None:
    dialogo = MateriaPrimaDialog(None, ref_le_sugerida=lambda familia: "PLC0121")

    dialogo.familia_input.setCurrentIndex(dialogo.familia_input.findData("PLACAS"))

    assert "PLC0121" in dialogo.ref_le_input.placeholderText()


def test_historico_mostra_a_variacao_face_ao_registo_anterior() -> None:
    historico = [
        PrecoHistoricoResumo(
            id=2, materia_prima_id=1, ref_le="PLC0052", preco_tabela=Decimal("31.20"),
            desconto=Decimal("18"), margem=None, preco_liquido=Decimal("25.58"),
            data_preco=date(2026, 8, 20), origem="FORNECEDOR", utilizador="paulo",
            observacoes=None,
        ),
        PrecoHistoricoResumo(
            id=1, materia_prima_id=1, ref_le="PLC0052", preco_tabela=Decimal("28.80"),
            desconto=Decimal("18"), margem=None, preco_liquido=Decimal("23.62"),
            data_preco=date(2025, 7, 23), origem="EXCEL", utilizador="paulo",
            observacoes=None,
        ),
    ]

    dialogo = MateriaPrimaDialog(_materia(), historico=historico, utilizacoes=7)

    assert dialogo.historico_table.rowCount() == 2
    assert dialogo.historico_table.item(0, 2).text() == "+8,3%"
    assert dialogo.historico_table.item(1, 2).text() == "—"
    assert "Usado em 7 linhas" in dialogo.utilizacoes_label.text()


def test_valida_a_familia_e_os_numeros() -> None:
    dialogo = MateriaPrimaDialog(None, ref_le_sugerida=lambda familia: "PLC0121")
    dialogo.descricao_input.setText("Material novo")

    dialogo._validar_e_aceitar()
    assert "família" in dialogo.error_label.text()

    dialogo.familia_input.setCurrentIndex(dialogo.familia_input.findData("PLACAS"))
    dialogo.preco_tabela_input.setText("trinta euros")
    dialogo._validar_e_aceitar()
    assert "não é um número" in dialogo.error_label.text()


def test_sem_ref_le_e_sem_fonte_de_sugestao_pede_a_referencia() -> None:
    """Só acontece fora da app: na página, a sugestão vem sempre do serviço."""
    dialogo = MateriaPrimaDialog(None)
    dialogo.descricao_input.setText("Material novo")
    dialogo.familia_input.setCurrentIndex(dialogo.familia_input.findData("PLACAS"))

    dialogo._validar_e_aceitar()

    assert "Ref LE" in dialogo.error_label.text()
