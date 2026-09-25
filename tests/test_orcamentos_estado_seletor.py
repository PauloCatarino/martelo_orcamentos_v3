"""Seletor de Estado na lista de Orçamentos.

Mudar o estado obrigava a abrir o Editar Orçamento, mudar e gravar. Agora
muda-se na própria célula; Adjudicado continua a passar pelo editor, porque
precisa do nº da encomenda PHC.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

import app.models  # noqa: F401
from app.domain.orcamento_estados import ESTADO_ADJUDICADO
from app.models import Cliente, OrcamentoVersao, OrcamentoVersaoEvento
from app.services.orcamento_service import CriarOrcamentoSimplesData, OrcamentoService
from app.ui.dialogs.editar_orcamento_dialog import (
    EditarOrcamentoDialog,
    EditarOrcamentoDialogData,
)

_app = QApplication.instance() or QApplication([])


def _versao(session) -> int:
    cliente = Cliente(nome_simplex="ABREV", nome="Cliente X", is_temporary=False)
    session.add(cliente)
    session.flush()
    service = OrcamentoService(session)
    service.criar_orcamento_simples(
        CriarOrcamentoSimplesData(
            cliente_id=cliente.id, obra="Obra", descricao=None,
            localizacao=None, ref_cliente=None, created_by_id=None, ano=2026,
        )
    )
    return service.list_orcamentos()[0].orcamento_versao_id


def test_alterar_estado_grava_e_fica_no_historico(session) -> None:
    versao_id = _versao(session)
    service = OrcamentoService(session)

    assert service.alterar_estado(versao_id, "Enviado") is True
    assert session.get(OrcamentoVersao, versao_id).estado == "Enviado"
    eventos = session.query(OrcamentoVersaoEvento).filter_by(
        orcamento_versao_id=versao_id
    ).all()
    assert any("lista de or" in (e.descricao or "") for e in eventos)

    # O mesmo estado outra vez não faz nada.
    assert service.alterar_estado(versao_id, "Enviado") is False


def test_alterar_estado_recusa_adjudicado_e_estados_inventados(session) -> None:
    versao_id = _versao(session)
    service = OrcamentoService(session)
    with pytest.raises(ValueError, match="encomenda PHC"):
        service.alterar_estado(versao_id, ESTADO_ADJUDICADO)
    with pytest.raises(ValueError):
        service.alterar_estado(versao_id, "Qualquer coisa")


def _dialogo(**kw) -> EditarOrcamentoDialog:
    dados = EditarOrcamentoDialogData(
        obra="Obra", descricao=None, localizacao=None, ref_cliente=None,
        estado="Enviado",
    )
    return EditarOrcamentoDialog(None, dados, exigir_encomenda_se_adjudicado=True, **kw)


def test_adjudicar_pela_lista_exige_a_encomenda_phc() -> None:
    dialogo = _dialogo()
    dialogo.preparar_adjudicacao()
    assert dialogo.estado_combo.currentText() == ESTADO_ADJUDICADO

    dialogo._validate_and_accept()
    assert dialogo.result() == 0
    assert "encomenda PHC" in dialogo.error_label.text()


def test_numero_escrito_sem_adicionar_conta_ao_guardar() -> None:
    dialogo = _dialogo()
    dialogo.preparar_adjudicacao()
    dialogo.nova_encomenda_input.setText("1597")

    dialogo._validate_and_accept()

    assert dialogo.result() == 1
    dados = dialogo.get_data()
    assert dados.estado == ESTADO_ADJUDICADO
    assert dados.enc_phc == "1597"


def test_outro_estado_no_editor_nao_exige_encomenda() -> None:
    dialogo = _dialogo()
    dialogo.preparar_adjudicacao()
    dialogo.estado_combo.setCurrentText("Enviado")
    dialogo._validate_and_accept()
    assert dialogo.result() == 1


def _pagina(monkeypatch):
    from types import SimpleNamespace

    import app.ui.pages.orcamentos_page as modulo

    monkeypatch.setattr(modulo.OrcamentosPage, "carregar_orcamentos", lambda self: None)
    monkeypatch.setattr(modulo.OrcamentosPage, "_carregar_sinonimos", lambda self: None)
    pagina = modulo.OrcamentosPage()
    pagina._orcamentos_by_row = {
        0: SimpleNamespace(
            orcamento_versao_id=11, codigo_versao="260906_01", estado="Enviado"
        )
    }
    return modulo, pagina


def test_lista_estado_normal_grava_logo(monkeypatch) -> None:
    from contextlib import nullcontext

    modulo, pagina = _pagina(monkeypatch)
    chamadas: list = []
    monkeypatch.setattr(modulo, "SessionLocal", lambda: nullcontext(None))
    monkeypatch.setattr(
        modulo,
        "OrcamentoService",
        lambda _s: type("S", (), {"alterar_estado": lambda self, v, e: chamadas.append((v, e))})(),
    )

    pagina.mudar_estado(0, "Não Adjudicado")

    assert chamadas == [(11, "Não Adjudicado")]
    assert "Não Adjudicado" in pagina.status_label.text()


def test_lista_adjudicado_abre_o_editor(monkeypatch) -> None:
    modulo, pagina = _pagina(monkeypatch)
    abertos: list = []
    monkeypatch.setattr(modulo.QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(
        modulo.OrcamentosPage, "_editar_orcamento", lambda self, **kw: abertos.append(kw)
    )

    pagina.mudar_estado(0, ESTADO_ADJUDICADO)

    assert abertos == [{"adjudicar": True}]
