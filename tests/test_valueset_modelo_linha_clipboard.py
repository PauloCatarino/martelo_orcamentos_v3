"""Clipboard de conteúdo entre linhas existentes de chaves ValueSet diferentes."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.models import (
    DefMaquina,
    DefOperacao,
    DefValuesetModelo,
    DefValuesetModeloLinha,
    DefValuesetModeloLinhaOperacao,
)
from app.services.def_valueset_modelo_linha_operacao_service import (
    DefValuesetModeloLinhaOperacaoService,
)
from app.services.def_valueset_modelo_linha_service import (
    DefValuesetModeloLinhaService,
)


def _montar(session):
    modelo = DefValuesetModelo(codigo="MATERIAIS", nome="Materiais", ativo=True)
    session.add(modelo)
    session.flush()
    portas = DefValuesetModeloLinha(
        def_valueset_modelo_id=modelo.id,
        chave="MATERIAL_PORTAS",
        codigo_opcao="PORTA_A",
        nome_opcao="Portas",
        prioridade=1,
        ordem=2,
        ref_materia_prima="PLAC-CARV",
        descricao_materia_prima="Placa Carvalho",
        ref_le="LE-CARV",
        descricao_no_orcamento="Carvalho",
        preco_tabela=Decimal("80"),
        margem_percentagem=Decimal("10"),
        desconto_percentagem=Decimal("5"),
        preco_liquido=Decimal("83.6"),
        unidade="M2",
        desperdicio_percentagem=Decimal("12"),
        comp_mp=Decimal("2800"),
        larg_mp=Decimal("2070"),
        esp_mp=Decimal("19"),
        ativo=True,
    )
    remates = DefValuesetModeloLinha(
        def_valueset_modelo_id=modelo.id,
        chave="MATERIAL_REMATES",
        codigo_opcao="REMATE_A",
        nome_opcao="Remates",
        prioridade=7,
        ordem=9,
        ref_materia_prima="ANTIGA",
        ref_le="LE-ANTIGA",
        ativo=False,
        observacoes="Identidade do remate",
    )
    session.add_all([portas, remates])
    maquina = DefMaquina(codigo="CNC_CLIP", nome="CNC Clipboard")
    session.add(maquina)
    session.flush()
    nova = DefOperacao(codigo="CNC_PORTA", nome="CNC Porta", maquina_id=maquina.id)
    antiga = DefOperacao(codigo="CNC_REMATE", nome="CNC Remate", maquina_id=maquina.id)
    session.add_all([nova, antiga])
    session.flush()
    origem_op = DefValuesetModeloLinhaOperacao(
        def_valueset_modelo_linha_id=portas.id,
        def_operacao_id=nova.id,
        ordem=1,
        metodo_calculo="TEMPO",
        tempo_por_unidade_minutos=Decimal("3.5"),
        ativo=True,
    )
    destino_op = DefValuesetModeloLinhaOperacao(
        def_valueset_modelo_linha_id=remates.id,
        def_operacao_id=antiga.id,
        ordem=1,
        metodo_calculo="TEMPO",
        tempo_por_unidade_minutos=Decimal("9"),
        ativo=True,
    )
    session.add_all([origem_op, destino_op])
    session.commit()
    return portas, remates, origem_op, destino_op


def _operacoes(session, linha_id: int):
    return list(
        session.execute(
            select(DefValuesetModeloLinhaOperacao).where(
                DefValuesetModeloLinhaOperacao.def_valueset_modelo_linha_id
                == linha_id
            )
        ).scalars()
    )


def test_cola_material_portas_em_remates_sem_trocar_identidade(session) -> None:
    portas, remates, origem_op, destino_op = _montar(session)
    linha_service = DefValuesetModeloLinhaService(session)
    operacao_service = DefValuesetModeloLinhaOperacaoService(session)
    snapshot = linha_service.copiar_snapshot_linha(portas.id)
    operacoes = operacao_service.listar_operacoes_da_linha(portas.id)

    linha_service.aplicar_snapshot_linha(remates.id, snapshot, commit=False)
    operacao_service.substituir_operacoes_de(operacoes, remates.id, commit=False)
    session.commit()
    session.expire_all()

    destino = session.get(DefValuesetModeloLinha, remates.id)
    assert destino.def_valueset_modelo_id == remates.def_valueset_modelo_id
    assert destino.chave == "MATERIAL_REMATES"
    assert destino.codigo_opcao == "REMATE_A"
    assert destino.nome_opcao == "Remates"
    assert destino.prioridade == portas.prioridade
    assert destino.ordem == 9
    assert destino.ativo is False
    assert destino.observacoes == "Identidade do remate"
    assert destino.ref_materia_prima == "PLAC-CARV"
    assert destino.ref_le == "LE-CARV"
    assert destino.preco_liquido == Decimal("83.6000")
    assert destino.comp_mp == Decimal("2800.0000")
    assert destino.origem_dados == "EDITADO_LOCALMENTE"
    assert destino.editado_localmente is True

    [operacao_destino] = _operacoes(session, remates.id)
    assert operacao_destino.id == destino_op.id
    assert operacao_destino.id != origem_op.id
    assert operacao_destino.def_operacao_id == origem_op.def_operacao_id
    assert operacao_destino.tempo_por_unidade_minutos == Decimal("3.5000")


def test_rollback_reverte_dados_e_operacoes_da_colagem(session) -> None:
    portas, remates, _origem_op, destino_op = _montar(session)
    linha_service = DefValuesetModeloLinhaService(session)
    operacao_service = DefValuesetModeloLinhaOperacaoService(session)
    snapshot = linha_service.copiar_snapshot_linha(portas.id)
    operacoes = operacao_service.listar_operacoes_da_linha(portas.id)

    linha_service.aplicar_snapshot_linha(remates.id, snapshot, commit=False)
    operacao_service.substituir_operacoes_de(operacoes, remates.id, commit=False)
    session.rollback()
    session.expire_all()

    destino = session.get(DefValuesetModeloLinha, remates.id)
    assert destino.ref_materia_prima == "ANTIGA"
    assert destino.prioridade == 7
    assert destino.ref_le == "LE-ANTIGA"
    assert destino.editado_localmente is False
    [operacao_destino] = _operacoes(session, remates.id)
    assert operacao_destino.id == destino_op.id
    assert operacao_destino.def_operacao_id == destino_op.def_operacao_id
    assert operacao_destino.tempo_por_unidade_minutos == Decimal("9.0000")
