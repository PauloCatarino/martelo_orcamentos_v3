"""Gravar como… leva as operações da linha de onde foi copiada."""

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


def _montar(session) -> tuple[int, int]:
    """Two lines of one model; the first one carries two operations."""
    modelo = DefValuesetModelo(codigo="ROUP_STD", nome="Roupeiro", ativo=True)
    session.add(modelo)
    session.flush()

    origem = DefValuesetModeloLinha(
        def_valueset_modelo_id=modelo.id,
        chave="FERRAGEM_VARAO",
        codigo_opcao="VARAO_STD",
        ordem=1,
        ativo=True,
    )
    destino = DefValuesetModeloLinha(
        def_valueset_modelo_id=modelo.id,
        chave="FERRAGEM_VARAO",
        codigo_opcao="VARAO_SILK",
        ordem=2,
        ativo=True,
    )
    session.add_all([origem, destino])

    maquina = DefMaquina(codigo="CNC", nome="CNC")
    session.add(maquina)
    session.flush()
    operacoes = [
        DefOperacao(codigo="OPERACAO_MANUAL", nome="Manual", maquina_id=maquina.id),
        DefOperacao(codigo="EMBALAMENTO", nome="Embalamento", maquina_id=maquina.id),
    ]
    session.add_all(operacoes)
    session.flush()

    session.add_all(
        [
            DefValuesetModeloLinhaOperacao(
                def_valueset_modelo_linha_id=origem.id,
                def_operacao_id=operacoes[0].id,
                ordem=1,
                acao="ADICIONAR",
                regra_calculo="POR_PECA",
                quantidade_base=Decimal("3.0000"),
                tempo_setup_minutos=Decimal("0.0100"),
                tempo_por_unidade_minutos=Decimal("0.0100"),
                unidade_tempo="PECA",
                obrigatorio=True,
                ativo=True,
                observacoes="Aplicar perfil",
            ),
            DefValuesetModeloLinhaOperacao(
                def_valueset_modelo_linha_id=origem.id,
                def_operacao_id=operacoes[1].id,
                ordem=2,
                acao="DESATIVAR",
                regra_calculo="FIXA",
                obrigatorio=True,
                ativo=False,
            ),
        ]
    )
    session.flush()

    return origem.id, destino.id


def _ligacoes(session, linha_id: int) -> list[DefValuesetModeloLinhaOperacao]:
    return list(
        session.execute(
            select(DefValuesetModeloLinhaOperacao)
            .where(
                DefValuesetModeloLinhaOperacao.def_valueset_modelo_linha_id == linha_id
            )
            .order_by(DefValuesetModeloLinhaOperacao.ordem)
        ).scalars()
    )


def test_copia_todas_as_operacoes(session) -> None:
    origem_id, destino_id = _montar(session)

    copiadas = DefValuesetModeloLinhaOperacaoService(
        session
    ).copiar_operacoes_entre_linhas(origem_id, destino_id)

    assert copiadas == 2
    manual, embalamento = _ligacoes(session, destino_id)

    assert manual.ordem == 1
    assert manual.acao == "ADICIONAR"
    assert manual.regra_calculo == "POR_PECA"
    assert manual.quantidade_base == Decimal("3.0000")
    assert manual.tempo_setup_minutos == Decimal("0.0100")
    assert manual.unidade_tempo == "PECA"
    assert manual.observacoes == "Aplicar perfil"

    # As desativadas vão como estão: a variante nova fica igual à original.
    assert embalamento.acao == "DESATIVAR"
    assert embalamento.ativo is False


def test_a_linha_original_fica_intacta(session) -> None:
    origem_id, destino_id = _montar(session)

    DefValuesetModeloLinhaOperacaoService(session).copiar_operacoes_entre_linhas(
        origem_id, destino_id
    )

    assert len(_ligacoes(session, origem_id)) == 2


def test_linha_sem_operacoes_nao_copia_nada(session) -> None:
    origem_id, destino_id = _montar(session)

    copiadas = DefValuesetModeloLinhaOperacaoService(
        session
    ).copiar_operacoes_entre_linhas(destino_id, origem_id)

    assert copiadas == 0
    assert len(_ligacoes(session, origem_id)) == 2


def test_substituir_reutiliza_ligacoes_e_e_idempotente(session) -> None:
    origem_id, destino_id = _montar(session)
    service = DefValuesetModeloLinhaOperacaoService(session)
    origem = service.listar_operacoes_da_linha(origem_id)

    assert service.substituir_operacoes_de(origem, destino_id) == 2
    ids_primeira = [ligacao.id for ligacao in _ligacoes(session, destino_id)]

    assert service.substituir_operacoes_de(origem, destino_id) == 2
    destino = _ligacoes(session, destino_id)
    assert [ligacao.id for ligacao in destino] == ids_primeira
    assert len(destino) == 2
    assert destino[0].def_operacao_id == origem[0].def_operacao_id
    assert destino[0].metodo_calculo == origem[0].metodo_calculo
    assert destino[1].ativo is False


def test_substituir_desativa_operacoes_excedentes_sem_apagar(session) -> None:
    origem_id, destino_id = _montar(session)
    service = DefValuesetModeloLinhaOperacaoService(session)
    origem = service.listar_operacoes_da_linha(origem_id)
    service.substituir_operacoes_de(origem, destino_id)

    service.substituir_operacoes_de(origem[:1], destino_id)

    destino = _ligacoes(session, destino_id)
    assert len(destino) == 2
    assert destino[0].ativo is True
    assert destino[1].ativo is False
