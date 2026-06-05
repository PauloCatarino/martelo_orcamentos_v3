"""Import checks for the OrcamentoItemModulo model."""

from __future__ import annotations


def test_orcamento_item_modulo_model_imports() -> None:
    from app.models import OrcamentoItemModulo

    assert OrcamentoItemModulo.__tablename__ == "orcamento_item_modulos"
