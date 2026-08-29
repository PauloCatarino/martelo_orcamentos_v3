"""A coluna "Def. Peça" tem de dizer que trabalho é a operação manual.

Numa operação manual o código é sempre o mesmo — OPERACAO_MANUAL — por isso
duas linhas com trabalhos completamente diferentes ficavam iguais na tabela.
Passa a ler-se "OPERACAO_MANUAL (CNC 5 Eixos)".
"""

from __future__ import annotations

from decimal import Decimal

import app.models  # noqa: F401  (regista os modelos em Base.metadata)
from app.models import DefOperacao, DefPeca, DefPecaOperacao
from app.repositories.orcamento_item_custeio_linha_operacao_repository import (
    OrcamentoItemCusteioLinhaOperacaoRepository,
)
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)

ITEM = 30


def _operacao(session, codigo: str, nome: str) -> int:
    operacao = DefOperacao(
        codigo=codigo, nome=nome, tipo_operacao="CNC", ativo=True
    )
    session.add(operacao)
    session.flush()
    return operacao.id


def _peca(session, codigo: str) -> int:
    peca = DefPeca(codigo=codigo, nome=codigo.title(), ativo=True)
    session.add(peca)
    session.flush()
    return peca.id


def _linha(session, **campos):
    base = dict(
        orcamento_item_id=ITEM,
        tipo_linha="PECA",
        descricao="Linha",
        quantidade=Decimal("1"),
        nivel=0,
        ativo=True,
    )
    base.update(campos)
    return OrcamentoItemCusteioLinhaRepository(session).create_linha(**base)


def _operacao_local(session, linha_id: int, def_operacao_id: int, nome: str) -> None:
    OrcamentoItemCusteioLinhaOperacaoRepository(session).create(
        linha_id=linha_id,
        def_operacao_id=def_operacao_id,
        ordem=1,
        codigo=nome.upper().replace(" ", "_"),
        nome=nome,
        tipo_operacao="CNC",
        origem="LOCAL",
        metodo_calculo="TEMPO",
        quantidade_base=Decimal("1"),
        obrigatorio=True,
        ativo=True,
    )


def test_linha_manual_devolve_o_nome_da_operacao(session) -> None:
    def_operacao_id = _operacao(session, "CNC_5_EIXOS", "CNC 5 Eixos")
    peca_id = _peca(session, "OPERACAO_MANUAL")
    linha = _linha(
        session,
        ordem=1,
        def_peca_id=peca_id,
        def_peca_codigo="OPERACAO_MANUAL",
        descricao="Recorte CNC 'L'",
    )
    _operacao_local(session, linha.id, def_operacao_id, "CNC 5 Eixos")
    session.commit()

    mapa = OrcamentoItemCusteioLinhaService(session).operacoes_das_linhas_manuais(ITEM)

    assert mapa == {linha.id: "CNC 5 Eixos"}


def test_varias_operacoes_aparecem_todas(session) -> None:
    cnc = _operacao(session, "CNC_5_EIXOS", "CNC 5 Eixos")
    lixar = _operacao(session, "LIXAR", "Lixar à mão")
    peca_id = _peca(session, "OPERACAO_MANUAL")
    linha = _linha(
        session, ordem=1, def_peca_id=peca_id, def_peca_codigo="OPERACAO_MANUAL"
    )
    _operacao_local(session, linha.id, cnc, "CNC 5 Eixos")
    repo = OrcamentoItemCusteioLinhaOperacaoRepository(session)
    repo.create(
        linha_id=linha.id,
        def_operacao_id=lixar,
        ordem=2,
        codigo="LIXAR",
        nome="Lixar à mão",
        tipo_operacao="MANUAL",
        origem="LOCAL",
        obrigatorio=True,
        ativo=True,
    )
    session.commit()

    mapa = OrcamentoItemCusteioLinhaService(session).operacoes_das_linhas_manuais(ITEM)

    assert mapa == {linha.id: "CNC 5 Eixos, Lixar à mão"}


def test_peca_normal_fica_de_fora(session) -> None:
    """Numa peça normal o código já diz o que é; repetir só tornava ilegível."""
    def_operacao_id = _operacao(session, "CORTE", "Corte")
    peca_id = _peca(session, "LATERAL_2000")
    session.add(
        DefPecaOperacao(
            def_peca_id=peca_id,
            def_operacao_id=def_operacao_id,
            ordem=1,
            obrigatorio=True,
            ativo=True,
        )
    )
    linha = _linha(
        session, ordem=1, def_peca_id=peca_id, def_peca_codigo="LATERAL_2000"
    )
    session.commit()

    mapa = OrcamentoItemCusteioLinhaService(session).operacoes_das_linhas_manuais(ITEM)

    assert linha.id not in mapa


def test_linha_manual_sem_operacoes_nao_entra(session) -> None:
    """Sem operações não há nada a acrescentar — a coluna fica como estava."""
    peca_id = _peca(session, "OPERACAO_MANUAL")
    linha = _linha(
        session, ordem=1, def_peca_id=peca_id, def_peca_codigo="OPERACAO_MANUAL"
    )
    session.commit()

    mapa = OrcamentoItemCusteioLinhaService(session).operacoes_das_linhas_manuais(ITEM)

    assert linha.id not in mapa
