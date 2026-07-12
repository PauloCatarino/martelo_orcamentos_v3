"""Behavior tests for the G4 deterministic copy suggestions."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.domain.configuracao_sugestoes import (
    CAMPO_FORMULA_COMP,
    ORIGEM_MODELO_LINHA,
    ORIGEM_PECA,
    ConfigAssociadoExistente,
    ConfigOperacaoExistente,
    construir_sugestoes_associado,
    construir_sugestoes_operacao,
)
from app.domain.operacao_receitas import (
    CAMPO_DEF_REGRA_QUANTIDADE,
    CAMPO_NUMERO_TOPOS,
    CAMPO_QUANTIDADE_BASE,
    CAMPO_TEMPO_POR_UNIDADE,
    CAMPO_UNIDADE_TEMPO,
)


def _config_operacao(
    origem_id: int,
    label: str,
    *,
    def_operacao_id: int = 10,
    quantidade: str | None = "4",
    tempo_unidade: str | None = "0.04",
    setup: str | None = "0.5",
    unidade: str | None = "FURO",
    rasgo_comp: int = 0,
    rasgo_larg: int = 0,
    atualizado: datetime | None = None,
) -> ConfigOperacaoExistente:
    return ConfigOperacaoExistente(
        origem_tipo=ORIGEM_PECA,
        origem_id=origem_id,
        origem_label=label,
        def_operacao_id=def_operacao_id,
        regra_calculo="POR_FURACAO",
        quantidade_base=Decimal(quantidade) if quantidade else None,
        rasgo_qt_comp=rasgo_comp,
        rasgo_qt_larg=rasgo_larg,
        tempo_setup_minutos=Decimal(setup) if setup else None,
        tempo_por_unidade_minutos=Decimal(tempo_unidade) if tempo_unidade else None,
        unidade_tempo=unidade,
        atualizado_em=atualizado,
    )


def test_agrupa_configuracoes_identicas_numa_so_sugestao() -> None:
    configs = [
        _config_operacao(1, "Peça DOBRADICA_35"),
        _config_operacao(2, "Peça DOBRADICA_INOX"),
        _config_operacao(3, "Peça PUXADOR", quantidade="2"),
    ]

    sugestoes = construir_sugestoes_operacao(configs, 10)

    assert len(sugestoes) == 2
    # The configuration used twice ranks first and lists both origins.
    assert sugestoes[0].ocorrencias == 2
    assert "DOBRADICA_35" in sugestoes[0].detalhe
    assert "DOBRADICA_INOX" in sugestoes[0].detalhe
    assert sugestoes[1].ocorrencias == 1


def test_so_considera_a_operacao_selecionada() -> None:
    configs = [
        _config_operacao(1, "Peça A", def_operacao_id=10),
        _config_operacao(2, "Peça B", def_operacao_id=99),
    ]

    sugestoes = construir_sugestoes_operacao(configs, 10)

    assert len(sugestoes) == 1
    assert "Peça A" in sugestoes[0].label
    assert construir_sugestoes_operacao(configs, None) == []


def test_ignora_configuracoes_sem_nada_para_copiar() -> None:
    vazia = _config_operacao(
        1, "Peça CORTE", quantidade=None, tempo_unidade=None, setup=None, unidade=None
    )

    assert construir_sugestoes_operacao([vazia], 10) == []


def test_valores_da_sugestao_preenchem_o_formulario() -> None:
    sugestoes = construir_sugestoes_operacao([_config_operacao(1, "Peça X")], 10)

    valores = sugestoes[0].valores
    assert valores[CAMPO_QUANTIDADE_BASE] == "4"
    assert valores[CAMPO_TEMPO_POR_UNIDADE] == "0.04"
    assert valores[CAMPO_UNIDADE_TEMPO] == "FURO"
    assert "4 furo(s) × 0,04 min" in sugestoes[0].label
    assert "setup 0,5 min" in sugestoes[0].label


def test_resumo_de_rasgo_mostra_a_construcao() -> None:
    config = _config_operacao(
        1,
        "Peça COSTA+RASGO",
        quantidade=None,
        tempo_unidade=None,
        setup=None,
        unidade=None,
        rasgo_comp=2,
        rasgo_larg=1,
    )

    sugestoes = construir_sugestoes_operacao([config], 10)

    assert "rasgo 2 × COMP + 1 × LARG" in sugestoes[0].label


def test_ordena_por_ocorrencias_e_data_mais_recente() -> None:
    antiga = _config_operacao(
        1, "Peça ANTIGA", quantidade="2", atualizado=datetime(2026, 1, 1)
    )
    recente = _config_operacao(
        2, "Peça RECENTE", quantidade="3", atualizado=datetime(2026, 7, 1)
    )

    sugestoes = construir_sugestoes_operacao([antiga, recente], 10)

    assert "RECENTE" in sugestoes[0].label
    assert "ANTIGA" in sugestoes[1].label


def test_limita_o_numero_de_sugestoes() -> None:
    configs = [
        _config_operacao(i, f"Peça {i}", quantidade=str(i)) for i in range(1, 9)
    ]

    assert len(construir_sugestoes_operacao(configs, 10)) == 5


def _config_associado(
    origem_id: int,
    label: str,
    *,
    def_peca_componente_id: int | None = 7,
    referencia: str | None = None,
    quantidade: str = "1",
    regra_id: int | None = 3,
    regra_codigo: str | None = "CAV300",
    modo: str = "POR_TOPO",
    topos: int = 2,
    formula_comp: str | None = None,
) -> ConfigAssociadoExistente:
    return ConfigAssociadoExistente(
        origem_id=origem_id,
        def_peca_pai_id=origem_id,
        origem_label=label,
        tipo_componente="PECA" if def_peca_componente_id else "FERRAGEM",
        def_peca_componente_id=def_peca_componente_id,
        referencia_componente=referencia,
        quantidade=Decimal(quantidade),
        def_regra_quantidade_id=regra_id,
        def_regra_quantidade_codigo=regra_codigo,
        zona_aplicacao="DOIS_TOPOS",
        dimensao_referencia="MEDIDA_TOPO",
        numero_topos=topos,
        modo_quantidade=modo,
        formula_comp=formula_comp,
    )


def test_associado_sugere_pela_mesma_peca_componente() -> None:
    configs = [
        _config_associado(1, "Peça PRATELEIRA"),
        _config_associado(2, "Peça LATERAL"),
        _config_associado(3, "Peça OUTRA", def_peca_componente_id=99),
    ]

    sugestoes = construir_sugestoes_associado(configs, def_peca_componente_id=7)

    assert len(sugestoes) == 1
    assert sugestoes[0].ocorrencias == 2
    assert "regra CAV300" in sugestoes[0].label
    assert "por topo × 2" in sugestoes[0].label
    valores = sugestoes[0].valores
    assert valores[CAMPO_DEF_REGRA_QUANTIDADE] == 3
    assert valores[CAMPO_NUMERO_TOPOS] == 2
    assert valores[CAMPO_FORMULA_COMP] == ""


def test_associado_sugere_pela_referencia_sem_peca() -> None:
    configs = [
        _config_associado(
            1, "Peça A", def_peca_componente_id=None, referencia="CAVILHA_8"
        ),
        _config_associado(
            2, "Peça B", def_peca_componente_id=None, referencia="outra_ref"
        ),
    ]

    sugestoes = construir_sugestoes_associado(
        configs, referencia_componente="  cavilha_8 "
    )

    assert len(sugestoes) == 1
    assert "Peça A" in sugestoes[0].label


def test_associado_sem_selecao_nao_sugere() -> None:
    configs = [_config_associado(1, "Peça A")]

    assert construir_sugestoes_associado(configs) == []
    assert construir_sugestoes_associado(configs, referencia_componente="  ") == []
