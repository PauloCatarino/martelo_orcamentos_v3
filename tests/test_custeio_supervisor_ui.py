"""UI do assistente de resolução: botão dinâmico "Resolver" + navegação do diálogo."""

from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.services.custeio_supervisor import ORIGEM_OPERACOES, diagnosticar_observacoes
from app.ui.dialogs.custeio_supervisor_dialog import CusteioSupervisorDialog
from app.ui.pages.orcamento_item_custeio_page import (
    CusteioLinhasTable,
    OrcamentoItemCusteioPage,
)

_app = QApplication.instance() or QApplication([])


def _fake_page():
    """`self` mínimo para exercitar _realcar_supervisor sem construir a página toda."""
    table = CusteioLinhasTable(1, len(OrcamentoItemCusteioPage.TABLE_HEADERS))
    return SimpleNamespace(
        table=table,
        TABLE_HEADERS=OrcamentoItemCusteioPage.TABLE_HEADERS,
        _abrir_supervisor=lambda _lid: None,
    )


def test_coluna_resolver_existe() -> None:
    assert "Resolver" in OrcamentoItemCusteioPage.TABLE_HEADERS


def test_botao_aparece_so_em_linha_grave() -> None:
    coluna = OrcamentoItemCusteioPage.TABLE_HEADERS.index("Resolver")

    grave = SimpleNamespace(
        id=1, observacoes="Custo MP não calculado: área ou preço em falta."
    )
    fake = _fake_page()
    OrcamentoItemCusteioPage._realcar_supervisor(fake, 0, grave)
    assert fake.table.cellWidget(0, coluna) is not None

    limpa = SimpleNamespace(id=2, observacoes="Peça standard.")
    fake2 = _fake_page()
    OrcamentoItemCusteioPage._realcar_supervisor(fake2, 0, limpa)
    assert fake2.table.cellWidget(0, coluna) is None


def test_dialogo_navega_para_origem_e_fecha() -> None:
    diagnosticos = diagnosticar_observacoes(
        "Custo CNC não calculado: falta tempo/máquina."
    )
    navegados: list[str] = []
    dialog = CusteioSupervisorDialog(
        "PORTA_SIMPLES",
        diagnosticos,
        navegar=navegados.append,
    )

    dialog._ir(ORIGEM_OPERACOES)

    assert navegados == [ORIGEM_OPERACOES]
    # _ir chama accept() antes de navegar -> diálogo já não está a correr.
    assert dialog.result() == CusteioSupervisorDialog.DialogCode.Accepted
