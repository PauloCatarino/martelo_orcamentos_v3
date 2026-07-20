"""Fase 3C: as resoluções pelo assistente ficam no histórico da versão."""

from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages import orcamento_item_custeio_page as mod

_app = QApplication.instance() or QApplication([])


def test_registar_resolucao_regista_evento_e_commita(monkeypatch) -> None:
    registados: list[tuple] = []

    class _FakeHistorico:
        def __init__(self, _session) -> None:
            pass

        def registar(self, versao_id, tipo, descricao) -> None:
            registados.append((versao_id, tipo, descricao))

    monkeypatch.setattr(mod, "OrcamentoHistoricoService", _FakeHistorico)
    commits: list[bool] = []
    session = SimpleNamespace(commit=lambda: commits.append(True))
    fake = SimpleNamespace(orcamento_versao_id=7)

    mod.OrcamentoItemCusteioPage._registar_resolucao(fake, session, "Resolvido X")

    assert registados == [(7, "RESOLUÇÃO", "Resolvido X")]
    assert commits == [True]


def test_registar_resolucao_sem_versao_nao_faz_nada(monkeypatch) -> None:
    chamou: list = []
    monkeypatch.setattr(
        mod,
        "OrcamentoHistoricoService",
        lambda _s: chamou.append(True),
    )
    session = SimpleNamespace(commit=lambda: chamou.append("commit"))
    fake = SimpleNamespace(orcamento_versao_id=None)

    mod.OrcamentoItemCusteioPage._registar_resolucao(fake, session, "x")

    assert chamou == []  # não regista nem faz commit sem versão
