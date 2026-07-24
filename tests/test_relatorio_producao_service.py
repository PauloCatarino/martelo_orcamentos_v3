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


def test_dossier_obra_pdf_com_fases(tmp_path) -> None:
    from app.domain.assistente_obra import DossierObra

    dossier = DossierObra(
        codigo="26.1134_01_01_JF_VIVA",
        enc="1134",
        cliente="MÓVEIS J.F. VIVA",
        responsavel="Paulo",
        estado_local="Producao",
        data_inicio="25-06-2026",
        data_entrega="10-08-2026",
        descricao_producao="1 CLOSET 'U' COM TETOS SUTADOS",
        notas="INTERNO: falta validar preço",  # não deve ir para o PDF do cliente
        fases=(("Stock", 100.0, True), ("Corte", 0.0, False)),
        estado_global="🔄 28.6% (2/7)",
        encontrado_streamlit=True,
    )
    destino = tmp_path / "obra.pdf"

    caminho = svc.gerar_dossier_obra_pdf(dossier, caminho=destino, gerado_em="24-07-2026")

    assert caminho == destino
    assert destino.exists()
    assert destino.stat().st_size > 800


def test_dossier_obra_pdf_sem_streamlit(tmp_path) -> None:
    from app.domain.assistente_obra import DossierObra

    dossier = DossierObra(codigo="26.0800_01", cliente="X", encontrado_streamlit=False)
    destino = tmp_path / "obra2.pdf"

    svc.gerar_dossier_obra_pdf(dossier, caminho=destino)

    assert destino.exists()
