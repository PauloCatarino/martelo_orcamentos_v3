"""Fase 3B: destacar a matéria-prima exata (por Ref LE) na página Matérias-Primas."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from app.ui.pages.materias_primas_page import MateriasPrimasPage

_app = QApplication.instance() or QApplication([])


def _tabela_com_refs(refs: list[str]) -> QTableWidget:
    table = QTableWidget(len(refs), 1)
    for row, ref in enumerate(refs):
        table.setItem(row, 0, QTableWidgetItem(ref))
    return table


def test_focar_materia_prima_seleciona_a_linha_certa() -> None:
    table = _tabela_com_refs(["PLC0001", "PLC0033", "PLC0099"])
    piscadas: list[int] = []
    fake = SimpleNamespace(
        campo_pesquisa=SimpleNamespace(definir_texto=lambda _t: None),
        table=table,
        _piscar_linha=lambda row: piscadas.append(row),
    )

    MateriasPrimasPage.focar_materia_prima(fake, "plc0033")  # case-insensitive

    assert table.currentRow() == 1
    assert piscadas == [1]


def test_duplo_clique_em_modo_resolucao_aplica_materia() -> None:
    aplicadas: list = []
    materia = SimpleNamespace(id=5, ref_le="PLC0033")
    fake = SimpleNamespace(
        _materia_da_linha=lambda _row: materia,
        _resolucao_callback=aplicadas.append,
        sair_modo_resolucao=lambda: None,
    )

    MateriasPrimasPage._on_duplo_clique(fake, 0, 0)

    assert aplicadas == [materia]


def test_duplo_clique_fora_de_modo_resolucao_abre_a_ficha() -> None:
    """Fora do modo resolução, o duplo-clique passou a abrir a ficha para editar."""
    abertas: list = []
    materia = SimpleNamespace(id=5)
    fake = SimpleNamespace(
        _materia_da_linha=lambda _row: materia,
        _resolucao_callback=None,  # não está em modo resolução
        sair_modo_resolucao=lambda: None,
        _abrir_dialogo=abertas.append,
    )

    MateriasPrimasPage._on_duplo_clique(fake, 0, 0)

    assert abertas == [materia]


def test_duplo_clique_em_linha_sem_materia_nao_faz_nada() -> None:
    fake = SimpleNamespace(
        _materia_da_linha=lambda _row: None,
        _resolucao_callback=None,
        sair_modo_resolucao=lambda: None,
        _abrir_dialogo=lambda _materia: pytest.fail("não devia abrir nada"),
    )

    MateriasPrimasPage._on_duplo_clique(fake, 0, 0)


def test_focar_materia_prima_ignora_ref_vazia() -> None:
    table = _tabela_com_refs(["PLC0001"])
    chamou_pesquisa: list[str] = []
    fake = SimpleNamespace(
        campo_pesquisa=SimpleNamespace(definir_texto=chamou_pesquisa.append),
        table=table,
        _piscar_linha=lambda row: None,
    )

    MateriasPrimasPage.focar_materia_prima(fake, None)

    assert chamou_pesquisa == []  # nem sequer filtra


def test_mostrar_onde_ficou_realca_sem_filtrar_a_lista() -> None:
    """Depois de gravar interessa ver a vizinhança, não isolar a linha."""
    table = _tabela_com_refs(["PLC0001", "PLC0002", "PLC0003"])
    pesquisas: list[str] = []
    piscadas: list[int] = []
    fake = SimpleNamespace(
        table=table,
        campo_pesquisa=SimpleNamespace(definir_texto=pesquisas.append),
        _piscar_linha=piscadas.append,
    )

    MateriasPrimasPage.mostrar_onde_ficou(fake, "plc0002")

    assert piscadas == [1]
    assert pesquisas == []  # a pesquisa não é tocada
    assert table.currentRow() == 1


def test_mostrar_onde_ficou_ignora_ref_vazia() -> None:
    table = _tabela_com_refs(["PLC0001"])
    fake = SimpleNamespace(
        table=table,
        _piscar_linha=lambda _row: pytest.fail("não devia piscar nada"),
    )

    MateriasPrimasPage.mostrar_onde_ficou(fake, None)
