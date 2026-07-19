"""Tests for the 'Configurar como…' configuration recipes (phase G3)."""

from __future__ import annotations

from app.domain.metodo_calculo_types import METODO_CALCULO_LABELS
from app.domain.operacao_receitas import (
    CAMPO_DEF_REGRA_QUANTIDADE,
    CAMPO_DIMENSAO_REFERENCIA,
    CAMPO_METODO_CALCULO,
    CAMPO_MODO_QUANTIDADE,
    CAMPO_NUMERO_TOPOS,
    CAMPO_QUANTIDADE,
    CAMPO_QUANTIDADE_BASE,
    CAMPO_RASGO_QT_COMP,
    CAMPO_RASGO_QT_LARG,
    CAMPO_REGRA_CALCULO,
    CAMPO_REGRA_QUANTIDADE,
    CAMPO_TEMPO_POR_UNIDADE,
    CAMPO_TEMPO_SETUP,
    CAMPO_UNIDADE_TEMPO,
    CAMPO_ZONA_APLICACAO,
    get_receitas_associado,
    get_receitas_operacao,
)
from app.domain.regra_operacao_types import REGRA_OPERACAO_LABELS
from app.ui.dialogs.def_peca_operacao_dialog import UNIDADE_TEMPO_OPCOES

_CAMPOS_OPERACAO = {
    CAMPO_METODO_CALCULO,
    CAMPO_REGRA_CALCULO,
    CAMPO_QUANTIDADE_BASE,
    CAMPO_TEMPO_SETUP,
    CAMPO_TEMPO_POR_UNIDADE,
    CAMPO_UNIDADE_TEMPO,
    CAMPO_RASGO_QT_COMP,
    CAMPO_RASGO_QT_LARG,
}

_CAMPOS_ASSOCIADO = {
    CAMPO_QUANTIDADE,
    CAMPO_REGRA_QUANTIDADE,
    CAMPO_DEF_REGRA_QUANTIDADE,
    CAMPO_ZONA_APLICACAO,
    CAMPO_DIMENSAO_REFERENCIA,
    CAMPO_NUMERO_TOPOS,
    CAMPO_MODO_QUANTIDADE,
}


def test_receitas_operacao_bem_formadas() -> None:
    receitas = get_receitas_operacao()
    assert len(receitas) >= 5
    assert len({r.key for r in receitas}) == len(receitas)

    for receita in receitas:
        assert receita.label and receita.descricao
        assert set(receita.valores) <= _CAMPOS_OPERACAO
        regra = receita.valores.get(CAMPO_REGRA_CALCULO)
        if regra is not None:
            assert regra in REGRA_OPERACAO_LABELS
        metodo = receita.valores.get(CAMPO_METODO_CALCULO)
        if metodo is not None:
            assert metodo in METODO_CALCULO_LABELS
        unidade = receita.valores.get(CAMPO_UNIDADE_TEMPO)
        if unidade is not None:
            assert unidade in UNIDADE_TEMPO_OPCOES


def test_receita_rasgo_usa_metodo_rasgo() -> None:
    # New model: the groove is a METHOD of the machine's operation, not a
    # dedicated catalog operation (CNC_RASGO was removed).
    receita = next(
        r for r in get_receitas_operacao() if r.key == "RASGO_POR_COMPRIMENTO"
    )

    assert receita.operacao_codigo is None
    assert receita.valores[CAMPO_METODO_CALCULO] == "RASGO"
    assert receita.valores[CAMPO_RASGO_QT_COMP] == 1
    assert receita.valores[CAMPO_REGRA_CALCULO] == "RASGO_CNC"


def test_receitas_associado_bem_formadas() -> None:
    receitas = get_receitas_associado()
    assert len(receitas) >= 4
    assert len({r.key for r in receitas}) == len(receitas)

    for receita in receitas:
        assert receita.label and receita.descricao
        assert set(receita.valores) <= _CAMPOS_ASSOCIADO


def test_receita_uniao_dois_topos_espelha_o_custeio() -> None:
    receita = next(
        r for r in get_receitas_associado() if r.key == "UNIAO_DOIS_TOPOS"
    )

    assert receita.valores[CAMPO_ZONA_APLICACAO] == "DOIS_TOPOS"
    assert receita.valores[CAMPO_MODO_QUANTIDADE] == "POR_TOPO"
    assert receita.valores[CAMPO_NUMERO_TOPOS] == 2
    assert receita.valores[CAMPO_DIMENSAO_REFERENCIA] == "MEDIDA_TOPO"
