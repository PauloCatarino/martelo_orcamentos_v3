"""'Cérebro' do assistente de resolução: diagnóstico das observações de produção."""

from __future__ import annotations

from app.services.custeio_auditoria_service import AVISO, CRITICO
from app.services.custeio_supervisor import (
    ORIGEM_OPERACOES,
    ORIGEM_RESOLVER_MATERIAL,
    PAGINA_MAQUINAS_TARIFAS,
    PAGINA_MATERIAS_PRIMAS,
    alvo_de_chave,
    chave_menu,
    diagnostico_de_ocorrencia,
    diagnostico_de_operacao,
    diagnosticar_observacoes,
    origem_resolver_material,
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


def test_orla_do_catalogo_e_informativo_mas_sem_preco_e_grave() -> None:
    from app.services.orcamento_item_custeio_linha_service import (
        AVISO_PRECO_ORLA_CATALOGO,
        AVISO_PRECO_ORLA_EM_FALTA,
    )

    # Catálogo usado (há preço) -> só informativo, sem botão Resolver.
    assert tem_erro_grave(AVISO_PRECO_ORLA_CATALOGO) is False
    # Preço em falta (não calcula) -> grave, com botão Resolver.
    assert tem_erro_grave(AVISO_PRECO_ORLA_EM_FALTA) is True


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


def test_material_em_falta_e_grave_e_classifica_como_material() -> None:
    from app.domain.custos import AVISO_MATERIA_PRIMA_EM_FALTA

    diagnosticos = diagnosticar_observacoes(AVISO_MATERIA_PRIMA_EM_FALTA)
    assert len(diagnosticos) == 1
    assert diagnosticos[0].categoria == "Material"
    assert diagnosticos[0].grave is True
    chaves = {origem.chave for origem in diagnosticos[0].origens}
    assert chave_menu(PAGINA_MATERIAS_PRIMAS) in chaves


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
    # Continua a oferecer as operações da linha E o menu externo de máquinas
    # (a chave carrega o alvo "CNC", por isso comparo pela página).
    assert ORIGEM_OPERACOES in chaves
    assert PAGINA_MAQUINAS_TARIFAS in {pagina_de_chave(c) for c in chaves}


def test_pagina_de_chave_distingue_interna_de_externa() -> None:
    assert pagina_de_chave(chave_menu(PAGINA_MATERIAS_PRIMAS)) == PAGINA_MATERIAS_PRIMAS
    assert pagina_de_chave(ORIGEM_OPERACOES) is None


def test_chave_menu_com_alvo_para_destacar() -> None:
    chave = chave_menu(PAGINA_MAQUINAS_TARIFAS, "CNC")
    assert pagina_de_chave(chave) == PAGINA_MAQUINAS_TARIFAS  # página sem o alvo
    assert alvo_de_chave(chave) == "CNC"
    assert alvo_de_chave(chave_menu(PAGINA_MAQUINAS_TARIFAS)) is None


def test_maquinas_origem_leva_categoria_como_alvo() -> None:
    # CNC/Corte/Orlagem -> a origem Máquinas destaca a máquina certa; Tempos não.
    for categoria, esperado in [("CNC", "CNC"), ("Corte", "CORTE"), ("Orlagem", "ORLAGEM")]:
        d = diagnostico_de_ocorrencia(categoria, CRITICO, f"{categoria} sem custo.", None)
        maq = next(o for o in d.origens if o.titulo == "Máquinas e Tarifas")
        assert alvo_de_chave(maq.chave) == esperado
    d_tempos = diagnostico_de_ocorrencia("Tempos", CRITICO, "Sem tempos.", None)
    maq_tempos = next(o for o in d_tempos.origens if o.titulo == "Máquinas e Tarifas")
    assert alvo_de_chave(maq_tempos.chave) is None


# ----- Fase 2C: diagnóstico a partir de uma ocorrência da auditoria -----


def test_diagnostico_de_ocorrencia_usa_problema_e_acao() -> None:
    d = diagnostico_de_ocorrencia(
        "CNC", CRITICO, "CNC previsto mas sem custo.", "Validar máquina e tarifa CNC."
    )
    assert d.mensagem == "CNC previsto mas sem custo."
    assert d.sugestao == "Validar máquina e tarifa CNC."
    assert d.grave is True
    chaves = {origem.chave for origem in d.origens}
    assert ORIGEM_OPERACOES in chaves
    assert PAGINA_MAQUINAS_TARIFAS in {pagina_de_chave(c) for c in chaves}


def test_diagnostico_de_ocorrencia_sem_acao_usa_sugestao_generica() -> None:
    d = diagnostico_de_ocorrencia("Dimensões", CRITICO, "Sem medidas reais.", None)
    assert d.sugestao  # cai numa sugestão (genérica) em vez de vazio


def test_orlagem_grave_aponta_a_materias_primas() -> None:
    # O preço da orla vive no material/Matérias-Primas: a origem tem de lá apontar.
    d = diagnostico_de_ocorrencia(
        "Orlagem", CRITICO, "Custo de orla não calculado: preço da orla em falta.", None
    )
    chaves = {origem.chave for origem in d.origens}
    assert chave_menu(PAGINA_MATERIAS_PRIMAS) in chaves


# ----- Fase 2B: diagnóstico a partir do audit de operações -----


def test_diagnostico_de_operacao_verificar_e_grave() -> None:
    d = diagnostico_de_operacao("VERIFICAR", "Existem operações mas custo a zero.")
    assert d.severidade == CRITICO
    assert d.grave is True
    chaves = {origem.chave for origem in d.origens}
    assert ORIGEM_OPERACOES in chaves
    assert chave_menu(PAGINA_MAQUINAS_TARIFAS) in chaves


def test_diagnostico_de_operacao_atencao_e_aviso() -> None:
    d = diagnostico_de_operacao("ATENÇÃO", "Ferragem sem operações.")
    assert d.grave is False  # pode ser intencional (ferragem comprada)


# ----- Fase 3A: resolver + recalcular sem sair -----


def test_origem_resolver_material_tem_chave_propria() -> None:
    origem = origem_resolver_material()
    assert origem.chave == ORIGEM_RESOLVER_MATERIAL
    assert origem.titulo  # "Resolver aqui"
    assert pagina_de_chave(origem.chave) is None  # não é um salto de menu
