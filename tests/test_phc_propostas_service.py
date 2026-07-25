"""Tests for reading PHC proposals (table BO, NDOS=3) — read-only.

Covers the query builders and the candidate-picking logic. The SQL execution
itself needs the real PHC server, so it is not exercised here.
"""

from __future__ import annotations

from app.services.phc_propostas_service import (
    NDOS_PROPOSTA,
    PropostaPhc,
    _linhas_para_propostas,
    build_query_max_obrano,
    build_query_propostas_do_ano,
    escolher_proposta_criada,
)


def _proposta(numero, *, ano=2026, num_cliente="35", ref="", data="25.07.2026"):
    return PropostaPhc(
        numero=numero,
        ano=ano,
        num_cliente=num_cliente,
        ref_cliente=ref or None,
        data=data,
    )


# -- Consultas -------------------------------------------------------------


def test_query_max_obrano_filtra_ano_e_tipo_proposta():
    query = build_query_max_obrano(2026)
    assert query.startswith("SELECT")
    assert f"BO.NDOS = {NDOS_PROPOSTA}" in query
    assert "YEAR(BO.DATAOBRA) = 2026" in query
    assert "MAX(BO.OBRANO)" in query


def test_query_propostas_filtra_sempre_por_ano():
    """O OBRANO repete-se entre anos — o filtro de ano nunca pode faltar."""
    query = build_query_propostas_do_ano(ano=2026)
    assert "YEAR(BO.DATAOBRA) = 2026" in query
    assert f"BO.NDOS = {NDOS_PROPOSTA}" in query


def test_query_propostas_com_obrano_minimo_e_cliente():
    query = build_query_propostas_do_ano(
        ano=2026, obrano_minimo=805, num_cliente="035"
    )
    assert "BO.OBRANO > 805" in query
    # O nº de cliente entra como inteiro (035 -> 35), como está no PHC.
    assert "BO.NO = 35" in query


def test_query_propostas_ignora_cliente_nao_numerico():
    query = build_query_propostas_do_ano(ano=2026, num_cliente="AB12")
    assert "BO.NO =" not in query


def test_query_propostas_ordena_por_numero_descendente():
    assert "ORDER BY BO.OBRANO DESC" in build_query_propostas_do_ano(ano=2026)


# -- Conversão das linhas ---------------------------------------------------


def test_linhas_para_propostas_converte_numeric_do_sqlserver():
    linhas = [
        {
            "Numero": 806.0,
            "Ano": 2026.0,
            "Num_Cliente": 35.0,
            "Ref_Cliente": "25100005",
            "Data": "25.07.2026",
        }
    ]
    propostas = _linhas_para_propostas(linhas)
    assert len(propostas) == 1
    assert propostas[0].numero == 806
    assert propostas[0].ano == 2026
    assert propostas[0].num_cliente == "35"
    assert propostas[0].ref_cliente == "25100005"


def test_linhas_para_propostas_ignora_linhas_sem_numero():
    assert _linhas_para_propostas([{"Numero": None, "Ano": 2026}]) == []
    assert _linhas_para_propostas([]) == []
    assert _linhas_para_propostas(None) == []


def test_linhas_para_propostas_normaliza_ref_vazia():
    linhas = [{"Numero": 806, "Ano": 2026, "Num_Cliente": 35, "Ref_Cliente": "   "}]
    assert _linhas_para_propostas(linhas)[0].ref_cliente is None


# -- Escolha da proposta criada --------------------------------------------


def test_escolher_sem_candidatas_devolve_none():
    assert escolher_proposta_criada([], num_cliente="35") is None


def test_escolher_prefere_a_ref_cliente_igual():
    candidatas = [
        _proposta(808, num_cliente="63"),
        _proposta(807, num_cliente="35", ref="25100005"),
        _proposta(806, num_cliente="35"),
    ]
    escolhida = escolher_proposta_criada(
        candidatas, num_cliente="35", ref_cliente="25100005"
    )
    assert escolhida.numero == 807


def test_escolher_usa_cliente_quando_nao_ha_ref():
    candidatas = [_proposta(807, num_cliente="63"), _proposta(808, num_cliente="35")]
    escolhida = escolher_proposta_criada(candidatas, num_cliente="35")
    assert escolhida.numero == 808


def test_escolher_nunca_devolve_proposta_de_outro_cliente():
    """Regressão: mapear o nº de uma proposta alheia seria um erro grave.

    Se outra pessoa criar uma proposta ao mesmo tempo, ela aparece como
    candidata — mas é de outro cliente e tem de ser descartada.
    """
    candidatas = [_proposta(801, num_cliente="5"), _proposta(802, num_cliente="63")]
    assert escolher_proposta_criada(candidatas, num_cliente="35") is None


def test_escolher_descarta_outros_clientes_e_fica_com_o_certo():
    candidatas = [
        _proposta(806, num_cliente="5"),
        _proposta(807, num_cliente="35"),
        _proposta(808, num_cliente="63"),
    ]
    escolhida = escolher_proposta_criada(candidatas, num_cliente="35")
    assert escolhida.numero == 807


def test_escolher_entre_empates_fica_com_o_numero_mais_baixo():
    candidatas = [_proposta(808), _proposta(806), _proposta(807)]
    escolhida = escolher_proposta_criada(candidatas, num_cliente="35")
    assert escolhida.numero == 806


def test_escolher_ignora_maiusculas_na_ref():
    candidatas = [_proposta(806, ref="obra-A"), _proposta(807)]
    escolhida = escolher_proposta_criada(
        candidatas, num_cliente="35", ref_cliente="OBRA-a"
    )
    assert escolhida.numero == 806


def test_escolher_aceita_cliente_com_zeros_a_esquerda():
    """O V3 formata 035; o PHC guarda 35 — têm de casar."""
    candidatas = [_proposta(807, num_cliente="63"), _proposta(806, num_cliente="35")]
    escolhida = escolher_proposta_criada(candidatas, num_cliente="035")
    assert escolhida.numero == 806
