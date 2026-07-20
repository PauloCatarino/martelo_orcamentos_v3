"""UI do assistente de resolução: botão dinâmico "Resolver" + navegação do diálogo."""

from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.services.custeio_supervisor import (
    ORIGEM_LINHA,
    ORIGEM_OPERACOES,
    ORIGEM_RESOLVER_MATERIAL,
    PAGINA_MATERIAS_PRIMAS,
    chave_menu,
    diagnosticar_observacoes,
)
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


def test_botao_nao_fica_fantasma_ao_reutilizar_linha() -> None:
    """Recarregar a mesma linha (índice) sem erro grave remove o botão anterior."""
    coluna = OrcamentoItemCusteioPage.TABLE_HEADERS.index("Resolver")
    fake = _fake_page()

    grave = SimpleNamespace(
        id=1, observacoes="Custo MP não calculado: área ou preço em falta."
    )
    OrcamentoItemCusteioPage._realcar_supervisor(fake, 0, grave)
    assert fake.table.cellWidget(0, coluna) is not None

    # A mesma posição passa a ter uma linha só com aviso informativo (orla):
    informativa = SimpleNamespace(
        id=1,
        observacoes=(
            "Compatibilidade: esta linha ainda não tinha snapshot local da orla "
            "em €/m²; foi usado temporariamente o preço atual do catálogo."
        ),
    )
    OrcamentoItemCusteioPage._realcar_supervisor(fake, 0, informativa)
    assert fake.table.cellWidget(0, coluna) is None  # botão fantasma removido


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


def test_navegar_supervisor_origem_externa_abre_menu() -> None:
    """Origem 'menu:materias_primas': navega com a Ref LE (alvo) e ativa o modo
    resolução (ao_escolher) quando a linha aceita material (3B)."""
    chamadas: list[tuple] = []
    selecionadas: list[int] = []
    operacoes: list[bool] = []
    fake = SimpleNamespace(
        _on_navegar_menu=lambda pagina, alvo=None, ao_escolher=None: chamadas.append(
            (pagina, alvo, ao_escolher is not None)
        ),
        _linha_por_id=lambda lid: SimpleNamespace(ref_le="PLC0033", mat_default=None),
        _linha_aceita_material=lambda linha: True,
        selecionar_linha_por_id=lambda lid: selecionadas.append(lid),
        abrir_operacoes_da_linha=lambda: operacoes.append(True),
    )

    OrcamentoItemCusteioPage._navegar_supervisor(
        fake, 7, chave_menu(PAGINA_MATERIAS_PRIMAS)
    )
    assert chamadas == [(PAGINA_MATERIAS_PRIMAS, "PLC0033", True)]
    # Origem externa não seleciona/abre a linha (vai para outro menu).
    assert selecionadas == [] and operacoes == []


def test_navegar_supervisor_origens_internas() -> None:
    """Operações abre as operações da linha; 'linha' apenas foca a linha."""
    selecionadas: list[int] = []
    operacoes: list[bool] = []
    fake = SimpleNamespace(
        _on_navegar_menu=lambda _p: None,
        selecionar_linha_por_id=lambda lid: selecionadas.append(lid),
        abrir_operacoes_da_linha=lambda: operacoes.append(True),
    )

    OrcamentoItemCusteioPage._navegar_supervisor(fake, 3, ORIGEM_OPERACOES)
    assert selecionadas == [3] and operacoes == [True]

    OrcamentoItemCusteioPage._navegar_supervisor(fake, 5, ORIGEM_LINHA)
    assert selecionadas == [3, 5] and operacoes == [True]


def test_navegar_supervisor_resolver_material_inline() -> None:
    """A chave de resolução inline chama resolver_material_linha (sem sair)."""
    resolvidas: list[int] = []
    selecionadas: list[int] = []
    fake = SimpleNamespace(
        _on_navegar_menu=lambda _p: None,
        selecionar_linha_por_id=lambda lid: selecionadas.append(lid),
        abrir_operacoes_da_linha=lambda: None,
        resolver_material_linha=lambda lid: resolvidas.append(lid),
    )

    OrcamentoItemCusteioPage._navegar_supervisor(fake, 9, ORIGEM_RESOLVER_MATERIAL)

    assert resolvidas == [9]
    # Resolução inline não navega/foca a linha por outro caminho.
    assert selecionadas == []
