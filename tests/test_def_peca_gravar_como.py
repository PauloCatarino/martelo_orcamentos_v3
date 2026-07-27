"""Checks for "Gravar como…" on the piece definition page (copy/paste of a piece)."""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.repositories.def_peca_repository import DefPecaResumo
from app.services.def_peca_service import CriarDefPecaData, DefPecaService

_app = QApplication.instance() or QApplication([])


def _peca_resumo() -> DefPecaResumo:
    return DefPecaResumo(
        id=1,
        codigo="TETO_2000",
        nome="Teto[2000]",
        descricao=None,
        grupo="TETOS",
        tipo_peca="SIMPLES",
        ativo=True,
        revisao_numero=1,
    )


def test_form_embutido_mostra_gravar_como_quando_ha_callback() -> None:
    from app.ui.dialogs.editar_def_peca_dialog import EditarDefPecaDialog

    com_callback = EditarDefPecaDialog(
        _peca_resumo(), on_save_as=lambda _data: True, embedded=True
    )
    sem_callback = EditarDefPecaDialog(_peca_resumo(), embedded=True)

    assert com_callback.save_as_button.isVisible() is False  # ainda não foi mostrado
    assert com_callback.save_as_button.isVisibleTo(com_callback) is True
    assert sem_callback.save_as_button.isVisibleTo(sem_callback) is False


def test_pagina_da_peca_liga_o_gravar_como() -> None:
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    tab_source = inspect.getsource(DefPecaDetailPage._create_dados_gerais_tab)
    assert "on_save_as=self._gravar_dados_gerais_como" in tab_source

    gravar_como = inspect.getsource(DefPecaDetailPage._gravar_dados_gerais_como)
    assert "gravar_peca_como" in gravar_como
    assert "CriarDefPecaData" in gravar_como
    # Um código igual ao original daria erro de duplicado: avisa antes de gravar.
    assert "Mude o código antes de gravar como nova peça." in gravar_como

    assert "on_peca_duplicada" in inspect.signature(DefPecaDetailPage).parameters


def test_lista_de_pecas_abre_a_peca_criada() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    source = inspect.getsource(DefPecasPage._show_detail_page)
    assert "on_peca_duplicada=self.abrir_peca_por_id" in source


def test_gravar_peca_como_copia_associados_e_operacoes(session) -> None:
    from app.models import DefOperacao

    service = DefPecaService(session)
    original = service.criar_peca(
        CriarDefPecaData(
            codigo="TETO_2000",
            nome="Teto[2000]",
            grupo="TETOS",
            orla_c1=2,
            orla_c2=0,
            orla_l1=0,
            orla_l2=0,
            chave_valueset_material="MATERIAL_TETOS",
        )
    )
    uniao = service.criar_peca(
        CriarDefPecaData(codigo="SISTEMAS_UNIAO", nome="Sistemas Uniao", grupo="FERRAGENS")
    )
    operacao = DefOperacao(codigo="CORTE_PAINEL", nome="Corte de painel", ativo=True)
    session.add(operacao)
    session.flush()

    from app.services.def_peca_componente_service import (
        CriarDefPecaComponenteData,
        DefPecaComponenteService,
    )
    from app.services.def_peca_operacao_service import (
        CriarDefPecaOperacaoData,
        DefPecaOperacaoService,
    )

    DefPecaOperacaoService(session).adicionar_operacao_a_peca(
        CriarDefPecaOperacaoData(
            def_peca_id=original.id,
            def_operacao_id=operacao.id,
            ordem=1,
            regra_calculo="POR_PECA",
            metodo_calculo="ESCALAO_AREA",
        )
    )
    for prioridade in (1, 2):
        DefPecaComponenteService(session).criar_componente(
            CriarDefPecaComponenteData(
                def_peca_pai_id=original.id,
                tipo_componente="PECA",
                def_peca_componente_id=uniao.id,
                zona_aplicacao="DOIS_TOPOS",
                numero_topos=2,
                prioridade_valueset=prioridade,
            )
        )

    nova = service.gravar_peca_como(
        original.id,
        CriarDefPecaData(
            codigo="TETO_2222",
            nome="Teto[2222]",
            grupo="TETOS",
            orla_c1=2,
            orla_c2=2,
            orla_l1=2,
            orla_l2=2,
            chave_valueset_material="MATERIAL_TETOS",
        ),
    )

    assert nova.id != original.id
    assert nova.codigo == "TETO_2222"

    operacoes_novas = DefPecaOperacaoService(session).listar_operacoes_da_peca(nova.id)
    componentes_novos = DefPecaComponenteService(session).listar_componentes(nova.id)
    assert [item.def_operacao_id for item in operacoes_novas] == [operacao.id]
    assert operacoes_novas[0].metodo_calculo == "ESCALAO_AREA"
    assert [item.def_peca_componente_id for item in componentes_novos] == [
        uniao.id,
        uniao.id,
    ]
    assert componentes_novos[0].numero_topos == 2
    # As uniões distinguem-se pela prioridade (cavilha 1, parafuso 2): copiar
    # sem ela transformava as duas variantes na mesma.
    assert sorted(item.prioridade_valueset for item in componentes_novos) == [1, 2]

    # A original fica intacta.
    assert len(DefPecaComponenteService(session).listar_componentes(original.id)) == 2
