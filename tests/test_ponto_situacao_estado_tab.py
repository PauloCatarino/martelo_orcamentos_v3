"""Smoke da página Ponto Situação: separador "Estado de Produção" (PD3).

Instancia a página offscreen, sem tocar na BD/rede (o dashboard e a consulta de
estado são neutralizados), e confirma a estrutura de 2 separadores + lazy load.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.ponto_situacao_page import PontoSituacaoPage

_app = QApplication.instance() or QApplication([])


def _page_sem_bd(monkeypatch):
    """Constrói a página com o dashboard e o estado neutralizados (sem BD/rede)."""
    monkeypatch.setattr(PontoSituacaoPage, "_carregar", lambda self, *a: None)
    chamadas: list[bool] = []
    monkeypatch.setattr(
        PontoSituacaoPage,
        "_carregar_estado",
        lambda self, *a: chamadas.append(True),
    )
    return PontoSituacaoPage(), chamadas


def test_pagina_tem_dois_separadores_e_estado_lazy(monkeypatch) -> None:
    page, chamadas = _page_sem_bd(monkeypatch)

    assert page.tabs.count() == 2
    assert page.tabs.tabText(0) == "Resumo"
    assert "Estado de Produ" in page.tabs.tabText(1)

    # Lazy: ao construir, o estado ainda não foi consultado no Streamlit.
    assert chamadas == []
    assert page._estado_carregado is False
    assert page.estado_table.rowCount() == 0
    # 9 colunas de identificação (Processo/Cliente/Enc PHC/Enc Streamlit/Ref
    # Cliente/Responsável/Estado/Preço/% Global) + 8 setores.
    assert page.estado_table.columnCount() == 17


def test_abrir_separador_estado_dispara_carregamento_uma_vez(monkeypatch) -> None:
    page, chamadas = _page_sem_bd(monkeypatch)

    # Abrir o separador "Estado de Produção" dispara o lazy load.
    page.tabs.setCurrentIndex(1)

    assert chamadas == [True]
