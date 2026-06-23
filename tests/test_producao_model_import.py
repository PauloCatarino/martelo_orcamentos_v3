"""Import checks for the production model."""

from __future__ import annotations


def test_producao_model_has_key_columns() -> None:
    from app.models.producao import Producao

    columns = Producao.__table__.c

    for column_name in (
        "codigo_processo",
        "ano",
        "num_enc_phc",
        "versao_obra",
        "versao_plano",
        "estado",
        "cliente_id",
        "orcamento_id",
        "tipo_pasta",
    ):
        assert column_name in columns
