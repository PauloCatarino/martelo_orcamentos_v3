"""'Cérebro' do assistente de resolução: diagnóstico das observações de produção."""

from __future__ import annotations

from app.services.custeio_auditoria_service import AVISO, CRITICO
from app.services.custeio_supervisor import (
    ORIGEM_OPERACOES,
    PAGINA_MAQUINAS_TARIFAS,
    PAGINA_MATERIAS_PRIMAS,
    chave_menu,
    diagnosticar_observacoes,
    pagina_de_chave,
    tem_erro_grave,
)


def test_observacao_critica_de_material_e_grave_com_sugestao_e_origem() -> None:
    diagnosticos = diagnosticar_observacoes(
        "Custo MP não calculado: área ou preço em falta."
    )
    assert len(diagnosticos) == 1
    d = diagnosticos[0]
    assert d.categoria == "Material"
    assert d.severidade == CRITICO
    assert d.grave is True
    assert d.porque  # explica o porquê
    assert d.sugestao  # sugere a correção
    assert d.origens  # tem pelo menos uma origem


def test_observacao_de_cnc_oferece_origem_operacoes() -> None:
    diagnosticos = diagnosticar_observacoes(
        "Custo CNC não calculado: falta tempo/máquina."
    )
    assert diagnosticos
    chaves = {origem.chave for d in diagnosticos for origem in d.origens}
    assert ORIGEM_OPERACOES in chaves


def test_observacao_neutra_nao_gera_diagnostico() -> None:
    # Texto sem marcadores críticos/aviso -> ignorado (apenas informativo).
    assert diagnosticar_observacoes("Peça standard, produção normal.") == []
    assert tem_erro_grave("Peça standard, produção normal.") is False


def test_snapshot_de_orla_e_aviso_nao_grave() -> None:
    texto = (
        "Compatibilidade: esta linha ainda não tinha snapshot local da orla em "
        "€/m²; foi usado temporariamente o preço atual do catálogo. Edite/guarde "
        "a linha para congelar o preço local."
    )
    diagnosticos = diagnosticar_observacoes(texto)
    # É informativo/aviso (contém "confirmar"? não; mas não tem marcador crítico).
    assert all(not d.grave for d in diagnosticos)
    assert tem_erro_grave(texto) is False


def test_tem_erro_grave_true_para_material_em_falta() -> None:
    assert tem_erro_grave("Custo MP não calculado: área ou preço em falta.") is True


def test_graves_aparecem_primeiro() -> None:
    texto = "Confirmar o desperdício.\nCusto MP não calculado: área ou preço em falta."
    diagnosticos = diagnosticar_observacoes(texto)
    assert diagnosticos[0].severidade == CRITICO
    assert any(d.severidade == AVISO for d in diagnosticos)


# ----- Fase 2: origens externas (menus) -----


def test_material_oferece_menu_materias_primas() -> None:
    diagnosticos = diagnosticar_observacoes(
        "Custo MP não calculado: área ou preço em falta."
    )
    chaves = [origem.chave for origem in diagnosticos[0].origens]
    assert chave_menu(PAGINA_MATERIAS_PRIMAS) in chaves


def test_cnc_oferece_menu_maquinas_tarifas() -> None:
    diagnosticos = diagnosticar_observacoes(
        "Custo CNC não calculado: falta tempo/máquina."
    )
    chaves = {origem.chave for d in diagnosticos for origem in d.origens}
    # Continua a oferecer as operações da linha E o menu externo de máquinas.
    assert ORIGEM_OPERACOES in chaves
    assert chave_menu(PAGINA_MAQUINAS_TARIFAS) in chaves


def test_pagina_de_chave_distingue_interna_de_externa() -> None:
    assert pagina_de_chave(chave_menu(PAGINA_MATERIAS_PRIMAS)) == PAGINA_MATERIAS_PRIMAS
    assert pagina_de_chave(ORIGEM_OPERACOES) is None
