from app.domain.peca_funcao_types import (
    DIVISORIA,
    FUNDO,
    LATERAL,
    TETO,
    get_peca_funcao_options,
    normalize_peca_funcao,
)


def test_origens_estruturais_incluem_familias_base() -> None:
    codigos = {codigo for codigo, _label in get_peca_funcao_options()}
    assert {TETO, FUNDO, LATERAL, DIVISORIA} <= codigos


def test_origem_personalizada_continua_permitida_e_normalizada() -> None:
    assert normalize_peca_funcao("  tampo de secretária  ") == "TAMPO DE SECRETÁRIA"
    assert normalize_peca_funcao("  ") is None
