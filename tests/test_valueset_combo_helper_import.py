"""Import checks for the ValueSet combo helper."""

from __future__ import annotations

import inspect


def test_helper_imports() -> None:
    from app.ui.helpers.valueset_combo_helper import (
        carregar_chaves_valueset_combo,
        obter_valor_chave_combo,
    )

    assert carregar_chaves_valueset_combo is not None
    assert obter_valor_chave_combo is not None


def test_carregar_signature() -> None:
    from app.ui.helpers.valueset_combo_helper import carregar_chaves_valueset_combo

    params = inspect.signature(carregar_chaves_valueset_combo).parameters

    assert "combo" in params
    assert "tipo" in params
    assert "valor_atual" in params


def test_helper_uses_service_with_domain_fallback() -> None:
    from app.ui.helpers import valueset_combo_helper as helper

    source = inspect.getsource(helper)

    assert "DefValuesetChaveService" in source
    assert "get_valueset_key_options" in source
    assert "Sem chave" in source
    assert "nao configurada" in source


def test_obter_valor_returns_current_data() -> None:
    from app.ui.helpers.valueset_combo_helper import obter_valor_chave_combo

    source = inspect.getsource(obter_valor_chave_combo)

    assert "currentData" in source


def test_natureza_peca_da_chave_espelha_regra_do_custeio() -> None:
    """G1: hardware-like keys give the FERRAGEM context to the operation guide."""
    from app.ui.helpers.valueset_combo_helper import natureza_peca_da_chave

    source = inspect.getsource(natureza_peca_da_chave)

    # DB-configured type first, prefix fallback after (same families as costing).
    assert "obter_por_codigo" in source
    assert "TIPOS_FERRAGEM" in source

    # Pure paths (no DB configured key): prefix fallback and empty key.
    assert natureza_peca_da_chave(None) is None
    assert natureza_peca_da_chave("  ") is None
