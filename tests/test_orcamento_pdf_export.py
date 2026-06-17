"""Teste do gerador do PDF do orçamento (fase 8W.4.1).

Só corre se o reportlab estiver instalado (``importorskip``). Confirma que o
ficheiro é gerado e tem conteúdo, com dados simples (sem DB).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.domain.relatorio_totais import calcular_totais_relatorio


def test_gerar_pdf_orcamento_cria_ficheiro(tmp_path) -> None:
    pytest.importorskip("reportlab")
    from app.services.orcamento_pdf_export import gerar_pdf_orcamento

    items = [
        SimpleNamespace(
            ordem=1,
            codigo="A1",
            descricao="Móvel de cozinha\ncom gavetas & puxadores <inox>",
            item="Móvel",
            altura=Decimal("720"),
            largura=Decimal("600"),
            profundidade=Decimal("560"),
            unidade="un",
            quantidade=Decimal("2"),
            preco_unitario=Decimal("100"),
            preco_total=Decimal("200"),
        ),
        SimpleNamespace(
            ordem=2,
            codigo=None,
            descricao=None,
            item="Prateleira",
            altura=None,
            largura=Decimal("800"),
            profundidade=None,
            unidade="un",
            quantidade=Decimal("1"),
            preco_unitario=Decimal("50"),
            preco_total=Decimal("50"),
        ),
    ]
    totais = calcular_totais_relatorio(items)
    cliente = SimpleNamespace(
        nome="JF & Filhos, Lda",
        nome_simplex="JF VIVA",
        morada="Rua A, 1",
        email="a@b.pt",
        telefone="912345678",
        num_cliente="C123",
    )
    orcamento = SimpleNamespace(
        num_orcamento="260655",
        numero_versao=1,
        ano=2026,
        obra="Cozinha",
        ref_cliente="REF-9",
        created_at=datetime(2026, 6, 17),
    )

    saida = tmp_path / "x.pdf"
    resultado = gerar_pdf_orcamento(
        saida, cliente=cliente, orcamento=orcamento, items=items, totais=totais
    )

    assert resultado == saida
    assert saida.exists()
    assert saida.stat().st_size > 0
