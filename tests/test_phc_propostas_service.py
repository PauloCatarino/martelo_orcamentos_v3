"""Tests for reading PHC proposals (table BO, NDOS=3) — read-only.

Covers the query builders and the candidate-picking logic. The SQL execution
itself needs the real PHC server, so it is not exercised here.
"""

from __future__ import annotations

import pytest

from app.services.phc_propostas_service import (
    NDOS_PROPOSTA,
    PropostaPhc,
    _linhas_para_propostas,
    build_query_dossiers_do_dia,
    build_query_linhas_proposta,
    build_query_max_obrano,
    build_query_propostas_do_ano,
    detetar_tipo_errado,
    escolher_proposta_criada,
    verificar_proposta_gravada,
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
        ano=2026, obrano_minimo=805, num_cliente="0035"
    )
    assert "BO.OBRANO > 805" in query
    # O nº de cliente entra como inteiro (0035 -> 35), como está no PHC.
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
    """O V3 formata 0035; o PHC guarda 35 — têm de casar."""
    candidatas = [_proposta(807, num_cliente="63"), _proposta(806, num_cliente="35")]
    escolhida = escolher_proposta_criada(candidatas, num_cliente="0035")
    assert escolhida.numero == 806


# -- Verificação do que ficou gravado (rede de segurança) -------------------


def test_query_linhas_proposta_filtra_numero_e_ano():
    query = build_query_linhas_proposta(ano=2026, numero=806)
    assert query.startswith("SELECT")
    assert "BO.OBRANO = 806" in query
    assert "YEAR(BO.DATAOBRA) = 2026" in query
    assert f"BO.NDOS = {NDOS_PROPOSTA}" in query


def test_verificar_sem_avisos_quando_tudo_conforme():
    proposta = _proposta(806, ref="25100010")
    avisos = verificar_proposta_gravada(
        proposta,
        ["Obra: 25100010"],
        ref_cliente="25100010",
        designacao="Obra: 25100010",
    )
    assert avisos == []


def test_verificar_avisa_quando_a_ref_ficou_noutro_campo():
    """Se os TABs caírem no campo errado, a ref fica vazia no PHC."""
    proposta = _proposta(806, ref="")
    avisos = verificar_proposta_gravada(
        proposta,
        ["Obra: 25100010"],
        ref_cliente="25100010",
        designacao="Obra: 25100010",
    )
    assert len(avisos) == 1
    assert "Ref. Cliente" in avisos[0]


def test_verificar_avisa_quando_a_designacao_nao_existe():
    proposta = _proposta(806, ref="25100010")
    avisos = verificar_proposta_gravada(
        proposta, [], ref_cliente="25100010", designacao="Obra: 25100010"
    )
    assert len(avisos) == 1
    assert "nenhuma linha" in avisos[0]


def test_verificar_avisa_quando_a_designacao_ficou_diferente():
    proposta = _proposta(806, ref="25100010")
    avisos = verificar_proposta_gravada(
        proposta,
        ["outra coisa qualquer"],
        ref_cliente="25100010",
        designacao="Obra: 25100010",
    )
    assert len(avisos) == 1
    assert "designação" in avisos[0]


def test_verificar_acumula_varios_avisos():
    proposta = _proposta(806, ref="errada")
    avisos = verificar_proposta_gravada(
        proposta, [], ref_cliente="25100010", designacao="Obra: 25100010"
    )
    assert len(avisos) == 2


def test_verificar_ignora_maiusculas_e_espacos():
    proposta = _proposta(806, ref=" 25100010 ")
    avisos = verificar_proposta_gravada(
        proposta,
        ["  obra: 25100010  "],
        ref_cliente="25100010",
        designacao="Obra: 25100010",
    )
    assert avisos == []


def test_verificar_sem_ref_esperada_nao_avisa_da_ref():
    proposta = _proposta(806, ref="")
    avisos = verificar_proposta_gravada(
        proposta, ["Obra:"], ref_cliente=None, designacao="Obra:"
    )
    assert avisos == []


# -- Deteção de documento com o tipo errado --------------------------------


def test_query_dossiers_do_dia_filtra_por_data_nao_por_numero():
    """As séries de OBRANO são por tipo — comparar números entre tipos erra."""
    query = build_query_dossiers_do_dia(data_iso="20260725")
    assert "BO.DATAOBRA >= '20260725'" in query
    assert "BO.OBRANO >" not in query
    # Sem filtro de NDOS: queremos ver dossiers de QUALQUER tipo.
    assert "BO.NDOS =" not in query


def test_query_dossiers_do_dia_recusa_data_invalida():
    with pytest.raises(ValueError):
        build_query_dossiers_do_dia(data_iso="2026")


def _linha(numero, ndos, tipo, num_cliente="35", ref=""):
    return {
        "Numero": numero,
        "Ndos": ndos,
        "Tipo": tipo,
        "Num_Cliente": num_cliente,
        "Ref_Cliente": ref,
    }


def test_detetar_tipo_errado_encontra_encomenda_do_mesmo_cliente():
    linhas = [_linha(1330, 1, "Encomenda de Cliente", num_cliente="35")]
    achado = detetar_tipo_errado(linhas, num_cliente="0035")
    assert achado == "Encomenda de Cliente nº 1330"


def test_detetar_tipo_errado_ignora_propostas():
    """Uma proposta não é um erro — é o que se queria criar."""
    linhas = [_linha(806, NDOS_PROPOSTA, "Proposta", num_cliente="35")]
    assert detetar_tipo_errado(linhas, num_cliente="35") is None


def test_detetar_tipo_errado_ignora_documentos_de_outros_clientes():
    """Não acusar documentos que outra pessoa criou legitimamente."""
    linhas = [_linha(1330, 1, "Encomenda de Cliente", num_cliente="99")]
    assert detetar_tipo_errado(linhas, num_cliente="35") is None


def test_detetar_tipo_errado_usa_a_ref_quando_o_cliente_difere():
    linhas = [_linha(1330, 1, "Encomenda de Cliente", num_cliente="99", ref="R1")]
    achado = detetar_tipo_errado(linhas, num_cliente="35", ref_cliente="R1")
    assert achado == "Encomenda de Cliente nº 1330"


def test_detetar_tipo_errado_sem_linhas():
    assert detetar_tipo_errado([], num_cliente="35") is None
    assert detetar_tipo_errado(None, num_cliente="35") is None
