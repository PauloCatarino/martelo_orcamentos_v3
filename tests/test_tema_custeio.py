"""Tests for the costing-table theme/styling helpers (phase 8V.4)."""

from __future__ import annotations

from app.domain.custeio_linha_types import (
    DIVISAO_INDEPENDENTE,
    FERRAGEM,
    PECA,
    PECA_COMPOSTA,
    SEPARADOR,
)
from app.ui import tema
from app.ui.tema import cor_zebra, estilo_linha_custeio


def test_palette_constants() -> None:
    # The Lança Encanto palette is exposed as reusable hex constants.
    assert tema.CASTANHO_ESCURO == "#5A3E2B"
    assert tema.CASTANHO_MEDIO == "#8B6F4E"
    assert tema.BEGE_AREIA == "#EFE7DA"
    assert tema.BEGE_CLARO == "#F7F2EA"
    assert tema.CINZA_CASTANHO == "#D9CFC2"
    assert tema.TEXTO_NORMAL == "#2E2A26"


def test_estilo_divisao_independente() -> None:
    estilo = estilo_linha_custeio(DIVISAO_INDEPENDENTE)
    assert estilo.fundo == tema.DIVISAO_FUNDO == "#8B6F4E"
    assert estilo.texto == "#FFFFFF"
    assert estilo.negrito is True
    assert estilo.maiusculas is True
    assert estilo.italico is False


def test_estilo_peca_composta() -> None:
    estilo = estilo_linha_custeio(PECA_COMPOSTA)
    assert estilo.texto == tema.CASTANHO_ESCURO
    assert estilo.negrito is True
    assert estilo.realce_estrutural is True
    # No full-row background: the beige highlight is column-scoped.
    assert estilo.fundo is None


def test_estilo_filho_de_composta() -> None:
    # A composite child (linha_pai set) -> italic, medium brown, zebra background.
    estilo = estilo_linha_custeio(FERRAGEM, eh_filho=True)
    assert estilo.italico is True
    assert estilo.texto == tema.CASTANHO_MEDIO
    assert estilo.negrito is False
    assert estilo.fundo is None


def test_estilo_separador() -> None:
    estilo = estilo_linha_custeio(SEPARADOR)
    assert estilo.fundo == tema.CINZA_CASTANHO == "#D9CFC2"
    assert estilo.negrito is False
    assert estilo.maiusculas is False


def test_estilo_linha_normal() -> None:
    estilo = estilo_linha_custeio(PECA)
    assert estilo.texto == tema.TEXTO_NORMAL
    assert estilo.fundo is None
    assert estilo.negrito is False
    assert estilo.italico is False
    assert estilo.realce_estrutural is False


def test_cor_zebra_alterna() -> None:
    assert cor_zebra(0) == tema.ZEBRA_BASE == "#FFFFFF"
    assert cor_zebra(1) == tema.ZEBRA_ALT == "#F7F2EA"
    assert cor_zebra(2) == tema.ZEBRA_BASE


def test_colunas_realce_composta() -> None:
    # The beige highlight covers the structural columns only.
    for header in ("Tipo linha", "Código", "Descrição", "QT mod", "QT und"):
        assert header in tema.COLUNAS_REALCE_COMPOSTA
    for header in ("Custo total", "Preço total", "Mat. default", "Módulo"):
        assert header not in tema.COLUNAS_REALCE_COMPOSTA
