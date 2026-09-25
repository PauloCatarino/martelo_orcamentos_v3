"""Orçamentos: o cliente tem de ter nome abreviado (Simplex).

Pedido do Paulo (25-09-2026): ao criar um orçamento novo ou ao trocar o
cliente, o nome abreviado tem de estar preenchido — é ele que dá o nome à
pasta ``{num}_{ABREVIADO}`` no servidor. Sem ele a pasta saía com o nome
completo do cliente. Vale para clientes do PHC e temporários.
"""

from __future__ import annotations

import os
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

import app.models  # noqa: F401  (registar os models)
from app.domain.clientes_simplex import erro_simplex_orcamento
from app.domain.orcamento_estados import ESTADO_INICIAL
from app.models import Cliente, Orcamento
from app.repositories.cliente_repository import ClienteListaResumo
from app.services.orcamento_service import (
    CriarOrcamentoSimplesData,
    EditarOrcamentoData,
    OrcamentoService,
)
from app.ui.dialogs import selecionar_cliente_dialog as seletor

_app = QApplication.instance() or QApplication([])


# -- regra ---------------------------------------------------------------


def test_cliente_phc_sem_abreviado_diz_para_corrigir_no_phc() -> None:
    erro = erro_simplex_orcamento(None, nome_cliente="A48 SISTEMAS", temporario=False)
    assert "«A48 SISTEMAS» não tem nome abreviado" in erro
    assert "NOME2" in erro and "Atualizar PHC" in erro
    assert "pasta do orçamento" in erro


def test_cliente_temporario_sem_abreviado_diz_para_corrigir_no_martelo() -> None:
    erro = erro_simplex_orcamento("  ", nome_cliente="Rui", temporario=True)
    assert "Clientes Temporários" in erro and "Atualizar PHC" not in erro


def test_abreviado_com_mais_de_19_caracteres_tambem_e_recusado() -> None:
    erro = erro_simplex_orcamento("X" * 20, nome_cliente="Rui")
    assert "20 caracteres" in erro and "máximo 19" in erro


def test_abreviado_bom_passa() -> None:
    assert erro_simplex_orcamento("JF_VIVA", nome_cliente="MÓVEIS J.F. VIVA") is None
    assert erro_simplex_orcamento("X" * 19) is None


# -- serviço (a rede de segurança por baixo da interface) -----------------


def _cliente(session, nome, simplex, *, temporario=False) -> Cliente:
    cliente = Cliente(nome=nome, nome_simplex=simplex, is_temporary=temporario)
    session.add(cliente)
    session.flush()
    return cliente


def _dados(cliente_id) -> CriarOrcamentoSimplesData:
    return CriarOrcamentoSimplesData(
        cliente_id=cliente_id, obra="Cozinha", descricao=None, localizacao=None,
        ref_cliente=None, ano=2026,
    )


def _editar(cliente_id) -> EditarOrcamentoData:
    return EditarOrcamentoData(
        obra="Cozinha", descricao=None, localizacao=None, ref_cliente=None,
        estado=ESTADO_INICIAL, cliente_id=cliente_id,
    )


def test_novo_orcamento_recusa_cliente_sem_abreviado(session) -> None:
    sem = _cliente(session, "A48 - SISTEMAS DE SEGURANÇA LDA", None)
    with pytest.raises(ValueError, match="não tem nome abreviado"):
        OrcamentoService(session).criar_orcamento_simples(_dados(sem.id))
    assert session.query(Orcamento).count() == 0


def test_novo_orcamento_com_abreviado_cria(session) -> None:
    com = _cliente(session, "MÓVEIS J.F. VIVA", "JF_VIVA")
    criado = OrcamentoService(session).criar_orcamento_simples(_dados(com.id))
    assert criado.orcamento_versao_id is not None


def test_trocar_para_cliente_sem_abreviado_e_recusado(session) -> None:
    service = OrcamentoService(session)
    com = _cliente(session, "MÓVEIS J.F. VIVA", "JF_VIVA")
    sem = _cliente(session, "Temporário sem nada", "", temporario=True)
    criado = service.criar_orcamento_simples(_dados(com.id))

    with pytest.raises(ValueError, match="Clientes Temporários"):
        service.editar_orcamento(
            criado.orcamento_id, _editar(sem.id),
            orcamento_versao_id=criado.orcamento_versao_id,
        )
    with pytest.raises(ValueError, match="não tem nome abreviado"):
        service.duplicar_versao_com_dados(criado.orcamento_versao_id, _editar(sem.id))
    session.rollback()
    assert session.get(Orcamento, criado.orcamento_id).cliente_id == com.id


def test_orcamento_antigo_que_ja_tinha_o_cliente_continua_a_editar_se(session) -> None:
    """Não trocar o cliente não esbarra na regra (orçamentos de antes dela)."""
    sem = _cliente(session, "Cliente antigo", None)
    orcamento = Orcamento(ano=2026, num_orcamento="260001", cliente_id=sem.id)
    session.add(orcamento)
    session.flush()
    service = OrcamentoService(session)
    service._exigir_simplex(sem.id, orcamento_id=orcamento.id)   # não levanta


# -- lista «Selecionar Cliente» -------------------------------------------


def _resumo(id, nome, simplex, *, temporario=False) -> ClienteListaResumo:
    return ClienteListaResumo(
        id=id, nome=nome, nome_simplex=simplex, morada=None, email=None,
        email_orcamentos=None, email_projeto_producao=None, pagina_web=None,
        telefone=None, telemovel=None, num_cliente_phc=None, info_1=None,
        info_2=None, is_temporary=temporario, created_at=datetime(2026, 9, 25),
    )


CLIENTES = [
    _resumo(1, "MÓVEIS J.F. VIVA", "JF_VIVA"),
    _resumo(2, "A48 - SISTEMAS DE SEGURANÇA LDA", None),
    _resumo(3, "Rui Temporário", "", temporario=True),
    _resumo(4, "Nome abreviado grande", "ABREVIADO_GRANDE_DEMAIS"),
]


@pytest.fixture
def lista(monkeypatch):
    monkeypatch.setattr(seletor.ClienteRepository, "list_todos", lambda _self: CLIENTES)
    avisos = []
    monkeypatch.setattr(
        seletor.QMessageBox, "warning", lambda _p, titulo, texto: avisos.append(texto)
    )
    return avisos


def _escolher(dialog, linha) -> None:
    dialog.table.selectRow(linha)
    dialog.table.setCurrentCell(linha, 0)
    dialog._selecionar()


def test_lista_marca_quem_nao_tem_abreviado(lista) -> None:
    dialog = seletor.SelecionarClienteDialog(None, exigir_simplex=True)
    try:
        assert dialog.table.item(0, 2).text() == "JF_VIVA"
        assert dialog.table.item(1, 2).text() == "(vazio no PHC)"
        assert dialog.table.item(2, 2).text() == "(vazio)"
        assert "Atualizar PHC" in dialog.table.item(1, 2).toolTip()
        assert "máximo 19" in dialog.table.item(3, 2).toolTip()
        assert "nome abreviado" in dialog.status_label.text()
    finally:
        dialog.close()


def test_escolher_cliente_sem_abreviado_para_orcamento_e_recusado(lista) -> None:
    dialog = seletor.SelecionarClienteDialog(None, exigir_simplex=True)
    try:
        for linha in (1, 2, 3):
            _escolher(dialog, linha)
            assert dialog.selected_cliente is None
        assert len(lista) == 3 and "Clientes Temporários" in lista[1]
        _escolher(dialog, 0)
        assert dialog.selected_cliente.id == 1
    finally:
        dialog.close()


def test_sem_exigir_a_lista_continua_a_deixar_escolher(lista) -> None:
    dialog = seletor.SelecionarClienteDialog(None)
    try:
        _escolher(dialog, 1)
        assert dialog.selected_cliente.id == 2 and not lista
    finally:
        dialog.close()


# -- Novo Orçamento e Editar Orçamento pedem a lista com a regra ----------


class _SeletorFalso:
    pedidos: list[dict] = []
    cliente: ClienteListaResumo | None = None

    def __init__(self, parent=None, **kwargs):
        _SeletorFalso.pedidos.append(kwargs)
        self.selected_cliente = _SeletorFalso.cliente

    def exec(self):
        return 1


def test_novo_e_editar_orcamento_exigem_o_abreviado(monkeypatch) -> None:
    from app.ui.dialogs.editar_orcamento_dialog import (
        EditarOrcamentoContexto,
        EditarOrcamentoDialog,
    )
    from app.ui.dialogs.novo_orcamento_dialog import NovoOrcamentoDialog

    monkeypatch.setattr(seletor, "SelecionarClienteDialog", _SeletorFalso)
    monkeypatch.setattr(EditarOrcamentoDialog, "_carregar_utilizadores", lambda _s: None)
    _SeletorFalso.pedidos = []
    _SeletorFalso.cliente = CLIENTES[0]

    novo = NovoOrcamentoDialog()
    editar = EditarOrcamentoDialog(
        None,
        contexto=EditarOrcamentoContexto(
            num_orcamento="260900", numero_versao=1, codigo_versao="26090001",
            cliente=CLIENTES[1],
        ),
    )
    try:
        # O cliente atual sem abreviado vê-se no painel, a ocre.
        assert "por corrigir" in editar.cliente_simplex_label.text()
        assert "Atualizar PHC" in editar.cliente_simplex_label.toolTip()

        novo._escolher_cliente()
        editar._trocar_cliente()
        assert _SeletorFalso.pedidos == [{"exigir_simplex": True}] * 2
        assert "abreviado: JF_VIVA" in novo.cliente_label.text()
        assert editar.cliente_simplex_label.text() == "JF_VIVA"
        assert editar.cliente_simplex_label.styleSheet() == ""

        # Rede de segurança no «Guardar» do Novo Orçamento.
        novo._erro_simplex = erro_simplex_orcamento(None, nome_cliente="X")
        avisos = []
        monkeypatch.setattr(
            "app.ui.dialogs.novo_orcamento_dialog.QMessageBox.warning",
            lambda _p, _t, texto: avisos.append(texto),
        )
        novo._validate_and_accept()
        assert avisos and novo.result() != 1
        assert "nome abreviado" in novo.error_label.text()
    finally:
        novo.close()
        editar.close()
