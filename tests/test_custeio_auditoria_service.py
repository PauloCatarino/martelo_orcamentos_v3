from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from app.domain.custeio_linha_types import OPERACAO_MANUAL, PECA, SEPARADOR
from app.services.custeio_auditoria_service import (
    LinhaAuditoriaDados,
    auditar_linhas,
    classificar_observacoes_producao,
    resumir_saude_versao,
)


def _linha(**kwargs):
    base = LinhaAuditoriaDados(
        linha_id=1, orcamento_versao_id=2, orcamento_item_id=3,
        codigo_orcamento="260001_01", cliente="Cliente", utilizador="paulo",
        item="Roupeiro",
        linha_codigo="LATERAL", tipo_linha=PECA, operacoes="",
        observacoes="", sem_material=True, preco_liquido=None, area_m2=None,
        tempo_corte=None, tempo_orlagem=None, tempo_cnc=None, tempo_manual=None,
        custo_corte=None, custo_orlagem=None, custo_cnc=None,
        custo_montagem_manual=None, custo_producao=None,
        comp_real=Decimal("1000"), larg_real=Decimal("500"), esp_real=Decimal("19"),
    )
    return replace(base, **kwargs)


def test_deteta_corte_orlagem_cnc_e_material_sem_valor() -> None:
    linha = _linha(
        operacoes="CORTE; ORLAGEM; CNC", observacoes="Custo CNC não calculado",
        sem_material=False, area_m2=Decimal("1.2"), preco_liquido=Decimal("0"),
        tempo_corte=Decimal("2"), tempo_orlagem=Decimal("3"), tempo_cnc=Decimal("4"),
        custo_corte=Decimal("0"), custo_orlagem=None, custo_cnc=Decimal("0"),
    )
    resultado = auditar_linhas([linha])
    assert {i.categoria for i in resultado.itens} == {"Corte", "Orlagem", "CNC", "Material"}
    assert all(i.impacto_eur is None for i in resultado.itens)
    assert all("€ por determinar" in i.impacto_texto for i in resultado.itens)


def test_deteta_operacao_manual_com_tempo_sem_custo() -> None:
    resultado = auditar_linhas([_linha(
        tipo_linha=OPERACAO_MANUAL, tempo_manual=Decimal("15"),
        custo_montagem_manual=Decimal("0"),
    )])
    assert resultado.total == 1
    assert resultado.itens[0].codigo_teste == "CUSTO_MANUAL_EM_FALTA"


def test_traduz_divergencia_producao_em_euros() -> None:
    resultado = auditar_linhas([_linha(
        custo_corte=Decimal("10"), custo_orlagem=Decimal("5"),
        custo_cnc=Decimal("2"), custo_producao=Decimal("20"),
    )])
    assert resultado.total == 1
    assert resultado.impacto_conhecido == Decimal("3")
    assert resultado.itens[0].impacto_eur == Decimal("3")


def test_linha_coerente_nao_cria_ocorrencia() -> None:
    resultado = auditar_linhas([_linha(
        custo_corte=Decimal("10"), custo_orlagem=Decimal("5"),
        custo_cnc=Decimal("2"), custo_producao=Decimal("17"),
    )])
    assert resultado.total == 0


def test_valida_quantidade_dimensoes_desperdicio_e_tempo() -> None:
    resultado = auditar_linhas([_linha(
        quantidade=Decimal("0"), comp_real=None,
        desperdicio_percentagem=Decimal("150"), tempo_setup=Decimal("-1"),
    )])
    testes = {item.codigo_teste for item in resultado.itens}
    assert {"QUANTIDADE_INVALIDA", "DIMENSOES_PECA_EM_FALTA", "DESPERDICIO_ELEVADO", "TEMPO_NEGATIVO"} <= testes


def test_exclusao_manual_mostra_impacto_exato_e_saude() -> None:
    resultado = auditar_linhas([_linha(
        custo_mp=Decimal("35"), excluir_mp=True,
    )])
    assert resultado.impacto_conhecido == Decimal("35")
    assert resultado.resumos[0].saude_pct == 90
    assert resultado.resumos[0].avisos == 1


def test_separador_com_quantidade_zero_nao_e_erro() -> None:
    resultado = auditar_linhas([_linha(tipo_linha=SEPARADOR, quantidade=Decimal("0"))])
    assert resultado.total == 0


def test_observacao_producao_incompleta_penaliza_saude() -> None:
    resultado = auditar_linhas([_linha(
        sem_material=True,
        observacoes="Material ValueSet em falta; preço incompleto.",
    )])
    assert resultado.total == 1
    assert resultado.itens[0].categoria == "Material"
    assert resultado.itens[0].codigo_teste.startswith("OBS_PRODUCAO_MATERIAL")
    assert resultado.resumos[0].saude_pct == 75


def test_observacao_de_confirmacao_e_aviso_e_texto_neutro_e_ignorado() -> None:
    classificadas = classificar_observacoes_producao(
        "Confirmar tempo manual com a produção.\nNota estética sem impacto financeiro."
    )
    assert classificadas == [
        ("Operação manual", "AVISO", "Confirmar tempo manual com a produção.")
    ]


def test_observacao_nao_duplica_cnc_estruturado() -> None:
    resultado = auditar_linhas([_linha(
        operacoes="CNC", tempo_cnc=Decimal("5"), custo_cnc=Decimal("0"),
        observacoes="Custo CNC não calculado: tarifa em falta.",
    )])
    assert [item.categoria for item in resultado.itens].count("CNC") == 1


def test_saude_versao_usa_item_menos_saudavel() -> None:
    resultado = auditar_linhas(
        [
            _linha(linha_id=1, orcamento_item_id=10, custo_mp=Decimal("5"), excluir_mp=True),
            _linha(
                linha_id=2,
                orcamento_item_id=20,
                quantidade=Decimal("0"),
                comp_real=None,
            ),
        ]
    )

    saude = resumir_saude_versao(resultado)

    assert saude.saude_pct == 50
    assert saude.criticos == 2
    assert saude.avisos == 1
    assert saude.ocorrencias == 3


def test_saude_versao_sem_ocorrencias_e_cem_porcento() -> None:
    saude = resumir_saude_versao(auditar_linhas([_linha()]))
    assert saude.saude_pct == 100
    assert saude.ocorrencias == 0
