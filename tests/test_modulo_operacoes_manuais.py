"""As operações afinadas à mão têm de viajar dentro do módulo.

O caso que motivou isto: uma linha de operação manual — um recorte 'L' de pilar
— com uma operação de CNC 5 eixos associada, com o setup e o tempo por peça
acertados para dar o preço pretendido. Guardar como módulo e voltar a importar
devolvia a peça ao catálogo e a afinação toda desaparecia, sem aviso.

Regra: **só** as linhas com operações editadas localmente é que ficam
congeladas no módulo. As outras continuam a resolver pelo catálogo da peça, e
por isso continuam a apanhar melhorias que se façam ao catálogo.
"""

from __future__ import annotations

import json
from decimal import Decimal

import app.models  # noqa: F401  (regista os modelos em Base.metadata)
from app.models import DefOperacao, DefPeca, OrcamentoItem
from app.repositories.orcamento_item_custeio_linha_operacao_repository import (
    OrcamentoItemCusteioLinhaOperacaoRepository,
)
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.services.def_modulo_service import DefModuloService
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)

ITEM_ORIGEM = 10


def _criar_item(session) -> int:
    item = OrcamentoItem(
        orcamento_versao_id=1,
        ordem=1,
        tipo_item="OUTRO",
        item="Item de teste",
        quantidade=Decimal("1"),
        altura=Decimal("2500"),
        largura=Decimal("1770"),
        profundidade=Decimal("630"),
    )
    session.add(item)
    session.flush()
    return item.id


def _criar_operacao_cnc(session) -> int:
    operacao = DefOperacao(
        codigo="CNC_5_EIXOS",
        nome="CNC 5 Eixos",
        tipo_operacao="CNC",
        ativo=True,
    )
    session.add(operacao)
    session.flush()
    return operacao.id


def _criar_peca(session) -> int:
    peca = DefPeca(codigo="OPERACAO_MANUAL", nome="Operação manual", ativo=True)
    session.add(peca)
    session.flush()
    return peca.id


def _inserir_custeio(session, **campos):
    base = dict(
        orcamento_item_id=ITEM_ORIGEM,
        tipo_linha="PECA",
        descricao="Linha",
        quantidade=Decimal("1"),
        nivel=0,
        ativo=True,
    )
    base.update(campos)
    return OrcamentoItemCusteioLinhaRepository(session).create_linha(**base)


def _operacao_local(session, linha_id: int, def_operacao_id: int) -> None:
    """O que fica na base quando alguém edita a operação só naquela linha."""
    OrcamentoItemCusteioLinhaOperacaoRepository(session).create(
        linha_id=linha_id,
        def_operacao_id=def_operacao_id,
        ordem=1,
        codigo="CNC_5_EIXOS",
        nome="CNC 5 Eixos",
        tipo_operacao="CNC",
        origem="LOCAL",
        metodo_calculo="TEMPO",
        quantidade_base=Decimal("1"),
        tempo_setup_minutos=Decimal("2"),
        tempo_por_unidade_minutos=Decimal("3"),
        unidade_tempo="PECA",
        obrigatorio=True,
        observacoes="Recorte 'L' do pilar",
        ativo=True,
    )


def _guardar_modulo(session, linhas, codigo="RECORTE_L"):
    return DefModuloService(session).guardar_de_linhas_custeio(
        orcamento_item_id=ITEM_ORIGEM,
        linha_ids=[linha.id for linha in linhas],
        codigo=codigo,
        nome="Recorte L do pilar",
        user_id=7,
    )


# ---------------------------------------------------------------- guardar --


def test_modulo_guarda_as_operacoes_editadas_a_mao(session) -> None:
    def_operacao_id = _criar_operacao_cnc(session)
    peca_id = _criar_peca(session)
    linha = _inserir_custeio(
        session,
        ordem=1,
        def_peca_id=peca_id,
        def_peca_codigo="OPERACAO_MANUAL",
        descricao="Recorte CNC 'L'",
        descricao_livre="RECORTE CNC 'L'",
    )
    _operacao_local(session, linha.id, def_operacao_id)
    session.commit()

    modulo = _guardar_modulo(session, [linha])

    guardada = modulo.linhas[0]
    assert guardada.operacoes_json, "a operação afinada não foi guardada no módulo"
    dados = json.loads(guardada.operacoes_json)
    assert len(dados) == 1
    assert dados[0]["def_operacao_id"] == def_operacao_id
    # Os tempos viajam como texto: em JSON um float perderia casas decimais.
    assert dados[0]["tempo_setup_minutos"] == "2.0000"
    assert dados[0]["tempo_por_unidade_minutos"] == "3.0000"
    assert dados[0]["observacoes"] == "Recorte 'L' do pilar"


def test_linha_sem_edicao_local_nao_congela_operacoes(session) -> None:
    """Sem edição local a linha continua a resolver pelo catálogo da peça.

    É o que faz um módulo antigo continuar a apanhar melhorias do catálogo.
    """
    peca_id = _criar_peca(session)
    linha = _inserir_custeio(
        session, ordem=1, def_peca_id=peca_id, def_peca_codigo="OPERACAO_MANUAL"
    )
    session.commit()

    modulo = _guardar_modulo(session, [linha], codigo="SEM_EDICAO")

    assert modulo.linhas[0].operacoes_json is None


# --------------------------------------------------------------- importar --


def test_importar_modulo_repoe_as_operacoes_com_os_tempos(session) -> None:
    def_operacao_id = _criar_operacao_cnc(session)
    peca_id = _criar_peca(session)
    linha = _inserir_custeio(
        session,
        ordem=1,
        def_peca_id=peca_id,
        def_peca_codigo="OPERACAO_MANUAL",
        descricao="Recorte CNC 'L'",
    )
    _operacao_local(session, linha.id, def_operacao_id)
    session.commit()
    modulo = _guardar_modulo(session, [linha])

    destino_id = _criar_item(session)
    session.commit()

    resultado = OrcamentoItemCusteioLinhaService(session).inserir_modulo_no_item(
        destino_id, modulo.modulo.id
    )
    assert resultado.criadas == 1

    novas = OrcamentoItemCusteioLinhaRepository(session).list_active_by_orcamento_item(
        destino_id
    )
    assert len(novas) == 1
    operacoes = OrcamentoItemCusteioLinhaOperacaoRepository(session).list_active(
        novas[0].id
    )
    assert len(operacoes) == 1, "a operação guardada não voltou na importação"
    assert operacoes[0].def_operacao_id == def_operacao_id
    assert operacoes[0].tempo_setup_minutos == Decimal("2")
    assert operacoes[0].tempo_por_unidade_minutos == Decimal("3")
    assert operacoes[0].observacoes == "Recorte 'L' do pilar"


def test_importar_avisa_quando_a_operacao_saiu_do_catalogo(session) -> None:
    """Se a operação foi eliminada entretanto, importa-se o resto e avisa-se."""
    def_operacao_id = _criar_operacao_cnc(session)
    peca_id = _criar_peca(session)
    linha = _inserir_custeio(
        session, ordem=1, def_peca_id=peca_id, def_peca_codigo="OPERACAO_MANUAL"
    )
    _operacao_local(session, linha.id, def_operacao_id)
    session.commit()
    modulo = _guardar_modulo(session, [linha])

    # A operação desaparece do catálogo depois de o módulo estar guardado.
    session.delete(session.get(DefOperacao, def_operacao_id))
    session.commit()

    destino_id = _criar_item(session)
    session.commit()
    resultado = OrcamentoItemCusteioLinhaService(session).inserir_modulo_no_item(
        destino_id, modulo.modulo.id
    )

    assert resultado.criadas == 1, "a importação não pode ser abortada por isto"
    assert any("já não existe no catálogo" in aviso for aviso in resultado.avisos)


def test_importar_modulo_sem_operacoes_guardadas_nao_cria_edicao_local(
    session,
) -> None:
    peca_id = _criar_peca(session)
    linha = _inserir_custeio(
        session, ordem=1, def_peca_id=peca_id, def_peca_codigo="OPERACAO_MANUAL"
    )
    session.commit()
    modulo = _guardar_modulo(session, [linha], codigo="SEM_OPS")

    destino_id = _criar_item(session)
    session.commit()
    OrcamentoItemCusteioLinhaService(session).inserir_modulo_no_item(
        destino_id, modulo.modulo.id
    )

    novas = OrcamentoItemCusteioLinhaRepository(session).list_active_by_orcamento_item(
        destino_id
    )
    assert not OrcamentoItemCusteioLinhaOperacaoRepository(session).has_any(
        novas[0].id
    )
