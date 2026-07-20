"""Pré-carregamento do "Estado de Produção" no arranque (em segundo plano).

Confirma que ``iniciar_carregamento_estado_fundo`` consulta numa thread, desenha
os resultados na thread da UI, chama ``quando_terminar`` exatamente uma vez e,
em erro, abre na mesma (sem pop-up).
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from app.ui.pages.ponto_situacao_page import PontoSituacaoPage

_app = QApplication.instance() or QApplication([])


def _page_sem_bd(monkeypatch):
    monkeypatch.setattr(PontoSituacaoPage, "_carregar", lambda self, *a: None)
    monkeypatch.setattr(PontoSituacaoPage, "_carregar_estado", lambda self, *a: None)
    return PontoSituacaoPage()


def _esperar(condicao, ms: int = 3000) -> bool:
    """Roda o event loop até ``condicao`` ou até esgotar o tempo."""
    for _ in range(ms // 10):
        if condicao():
            return True
        _app.processEvents()
        QThread.msleep(10)
    return condicao()


def test_preload_desenha_resultados_e_chama_callback(monkeypatch) -> None:
    page = _page_sem_bd(monkeypatch)

    sentinela = ["obra-a", "obra-b"]
    desenhados: list = []
    monkeypatch.setattr(
        PontoSituacaoPage, "_consultar_estado",
        lambda texto, estado, cliente, responsavel: sentinela,
    )
    monkeypatch.setattr(
        PontoSituacaoPage, "_preencher_estado",
        lambda self, resultados: desenhados.append(resultados),
    )
    monkeypatch.setattr(PontoSituacaoPage, "_texto_estado", lambda self, r: "ok")

    terminou: list[bool] = []
    page.iniciar_carregamento_estado_fundo(quando_terminar=lambda: terminou.append(True))

    assert _esperar(lambda: terminou == [True]), "callback nao foi chamado"
    assert desenhados == [sentinela]
    assert page._estado_carregado is True


def test_preload_em_erro_abre_na_mesma_sem_popup(monkeypatch) -> None:
    page = _page_sem_bd(monkeypatch)

    def _rebenta(texto, estado, cliente, responsavel):
        raise RuntimeError("Streamlit offline")

    monkeypatch.setattr(PontoSituacaoPage, "_consultar_estado", _rebenta)

    terminou: list[bool] = []
    page.iniciar_carregamento_estado_fundo(quando_terminar=lambda: terminou.append(True))

    assert _esperar(lambda: terminou == [True]), "callback nao foi chamado em erro"
    # Em erro o estado NAO fica marcado como carregado (permite tentar de novo).
    assert page._estado_carregado is False


def test_finalizar_preload_e_idempotente(monkeypatch) -> None:
    page = _page_sem_bd(monkeypatch)

    contador: list[bool] = []
    page._preload_terminar = lambda: contador.append(True)
    page._preload_terminado = False

    page._finalizar_preload()
    page._finalizar_preload()

    assert contador == [True]
