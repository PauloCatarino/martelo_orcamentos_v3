"""As operações inativas de uma linha ValueSet ficam escondidas por defeito."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _ligacao(id: int, *, ativo: bool, ordem: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        def_operacao_id=id,
        ordem=ordem,
        acao="ADICIONAR",
        regra_calculo="POR_PECA",
        metodo_calculo=None,
        quantidade_base=None,
        rasgo_qt_comp=0,
        rasgo_qt_larg=0,
        tempo_setup_minutos=None,
        tempo_por_unidade_minutos=None,
        unidade_tempo=None,
        obrigatorio=True,
        ativo=ativo,
        observacoes=None,
    )


def _abrir_dialogo(monkeypatch, ligacoes):
    """Open the dialog with fake data (no database behind it)."""
    from app.ui.dialogs import valueset_linha_operacoes_dialog as modulo

    class _FakeService:
        def __init__(self, _session):
            pass

        def listar_operacoes(self):
            return []

        def listar_maquinas(self):
            return []

    class _FakeSession:
        def __enter__(self):
            return None

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(modulo, "SessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(modulo, "DefOperacaoService", _FakeService)
    monkeypatch.setattr(modulo, "DefMaquinaService", _FakeService)

    return modulo.ValuesetLinhaOperacoesDialog(
        titulo="Operações da linha ValueSet",
        listar_operacoes=lambda: ligacoes,
        criar_operacao=lambda _dados: None,
        editar_operacao=lambda _id, _dados: None,
        alternar_operacao=lambda _ligacao: None,
    )


def test_por_defeito_so_mostra_as_ativas(_app, monkeypatch) -> None:
    dialog = _abrir_dialogo(
        monkeypatch,
        [_ligacao(1, ativo=True, ordem=1), _ligacao(2, ativo=False, ordem=2)],
    )

    assert dialog.mostrar_inativas_check.isChecked() is False
    assert dialog.operacoes_table.rowCount() == 1
    # A linha visível é a ativa, e é ela que a seleção devolve.
    assert dialog._operacoes_by_row[0].id == 1


def test_com_o_visto_mostra_todas(_app, monkeypatch) -> None:
    dialog = _abrir_dialogo(
        monkeypatch,
        [_ligacao(1, ativo=True, ordem=1), _ligacao(2, ativo=False, ordem=2)],
    )

    dialog.mostrar_inativas_check.setChecked(True)

    assert dialog.operacoes_table.rowCount() == 2
    assert dialog._operacoes_by_row[1].id == 2


def test_so_com_inativas_explica_como_as_ver(_app, monkeypatch) -> None:
    dialog = _abrir_dialogo(monkeypatch, [_ligacao(1, ativo=False, ordem=1)])

    assert dialog.operacoes_table.rowCount() == 0
    assert "Mostrar inativas" in dialog.status_label.text()
