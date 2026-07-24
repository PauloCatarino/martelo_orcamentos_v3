"""Testes do relatório PDF das obras (ação do IA Martelo)."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services import relatorio_producao_service as svc

pytestmark = pytest.mark.skipif(
    not svc.REPORTLAB_DISPONIVEL, reason="reportlab não instalado"
)


def _obra(**kw) -> SimpleNamespace:
    base = {
        "codigo_processo": "26.0346_01_01_JF_VIVA",
        "nome_cliente": "MÓVEIS J.F. VIVA",
        "estado": "Producao",
        "responsavel": "Paulo",
        "data_inicio": "25-02-2026",
        "data_entrega": "23-03-2026",
        "qt_artigos": 7,
        "preco_total": Decimal("10900"),
        "descricao_producao": "1 CONSOLA 2 GAVETAS · 1 ROUPEIRO 4 PORTAS",
    }
    base.update(kw)
    return SimpleNamespace(**base)


def test_gera_pdf_nao_vazio(tmp_path) -> None:
    destino = tmp_path / "relatorio.pdf"

    caminho = svc.gerar_relatorio_obras_pdf(
        [_obra(), _obra(codigo_processo="26.0380_01", preco_total=None, data_inicio=None)],
        titulo="Relatório de obras",
        subtitulo="Pergunta: «obras do Paulo» · 2 obras",
        caminho=destino,
    )

    assert caminho == destino
    assert destino.exists()
    assert destino.stat().st_size > 500  # tem mesmo conteúdo


def test_lista_vazia_ainda_gera_pdf(tmp_path) -> None:
    destino = tmp_path / "vazio.pdf"

    svc.gerar_relatorio_obras_pdf(
        [], titulo="Relatório", subtitulo="0 obras", caminho=destino
    )

    assert destino.exists()
    assert destino.stat().st_size > 200
