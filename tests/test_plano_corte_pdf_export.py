"""Teste do gerador do PDF do plano de corte (C3.3)."""

from __future__ import annotations

import pytest

from app.domain.plano_corte_dados import GrupoCorte
from app.domain.plano_corte import PecaCorte
from app.services.plano_corte_pdf_export import (
    REPORTLAB_DISPONIVEL,
    gerar_pdf_plano_corte,
)


def _grupos() -> list[GrupoCorte]:
    return [
        # Grupo com peças que cabem (gera 1 página de placa) + 1 que não cabe
        # (gera a página de "não alocadas").
        GrupoCorte(
            ref="MDF 19",
            esp=19.0,
            placa_comp=2750.0,
            placa_larg=1830.0,
            pecas=[
                PecaCorte(1, "LATERAL", 600.0, 400.0),
                PecaCorte(2, "COSTA", 700.0, 500.0),
                PecaCorte(3, "PRATELEIRA", 800.0, 300.0),
                PecaCorte(4, "GIGANTE", 5000.0, 4000.0),
            ],
            placas_orcamento=2,
        ),
        GrupoCorte(
            ref="MDF 8",
            esp=8.0,
            placa_comp=2750.0,
            placa_larg=1830.0,
            pecas=[PecaCorte(5, "FUNDO", 900.0, 450.0)],
            placas_orcamento=1,
        ),
    ]


@pytest.mark.skipif(not REPORTLAB_DISPONIVEL, reason="reportlab não instalado")
def test_gerar_pdf_plano_corte_cria_ficheiro(tmp_path) -> None:
    output = tmp_path / "plano_corte.pdf"

    resultado = gerar_pdf_plano_corte(
        output, grupos=_grupos(), num_versao="260001_01"
    )

    assert resultado == output
    assert output.exists()
    assert output.stat().st_size > 0


@pytest.mark.skipif(not REPORTLAB_DISPONIVEL, reason="reportlab não instalado")
def test_gerar_pdf_plano_corte_sem_grupos_nao_rebenta(tmp_path) -> None:
    output = tmp_path / "plano_corte_vazio.pdf"

    gerar_pdf_plano_corte(output, grupos=[], num_versao="260001_01")

    assert output.exists()
    assert output.stat().st_size > 0
