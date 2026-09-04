"""Importar um módulo tem de repor os associados das peças SIMPLES.

O módulo guarda a árvore toda — uma peça simples com as uniões dos topos por
baixo fica lá com os filhos e tudo. Mas o importador só sabia descer os filhos
de uma peça COMPOSTA: os de uma peça simples eram descartados sem uma palavra,
e o mesmo módulo voltava mais barato do que tinha saído.

Medido a 2026-09-04 num teste de 5 peças: −1,13 €. O Paulo apanhou ~−4 € num
módulo de lavandaria.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import (
    Cliente,
    DefModulo,
    DefModuloLinha,
    DefPeca,
    Orcamento,
    OrcamentoItem,
    OrcamentoItemCusteioLinha,
    OrcamentoVersao,
)
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)


@pytest.fixture()
def item(session: Session) -> OrcamentoItem:
    cliente = Cliente(nome="Cliente Modulos", is_temporary=True)
    session.add(cliente)
    session.flush()
    orcamento = Orcamento(ano=2026, num_orcamento="260881", cliente_id=cliente.id)
    session.add(orcamento)
    session.flush()
    versao = OrcamentoVersao(
        orcamento_id=orcamento.id,
        numero_versao=1,
        codigo_versao="260881_01",
        estado="Falta Orçamentar",
    )
    session.add(versao)
    session.flush()
    item = OrcamentoItem(
        orcamento_versao_id=versao.id,
        ordem=1,
        codigo="LAVANDARIA",
        tipo_item="OUTRO",
        item="LAVANDARIA",
        quantidade=Decimal("1"),
        unidade="un",
    )
    session.add(item)
    session.flush()
    return item


@pytest.fixture()
def modulo_com_associado(session: Session) -> DefModulo:
    """Um módulo com um teto (peça simples) e as uniões por baixo dele."""
    teto = DefPeca(codigo="TETO_2000", nome="Teto[2000]", ativo=True)
    uniao = DefPeca(codigo="SISTEMAS_UNIAO", nome="Sistemas Uniao", ativo=True)
    session.add_all([teto, uniao])
    session.flush()

    modulo = DefModulo(codigo="MOD_TETO", nome="Módulo teto", ativo=True)
    session.add(modulo)
    session.flush()
    session.add_all(
        [
            DefModuloLinha(
                def_modulo_id=modulo.id,
                ordem=1,
                tipo_linha="PECA",
                def_peca_id=teto.id,
                def_peca_codigo="TETO_2000",
                descricao="Teto[2000]",
                qt_mod="1",
                qt_und="1",
                nivel=0,
                ativo=True,
            ),
            DefModuloLinha(
                def_modulo_id=modulo.id,
                ordem=2,
                tipo_linha="FERRAGEM",
                def_peca_id=uniao.id,
                def_peca_codigo="SISTEMAS_UNIAO",
                descricao="Sistemas Uniao",
                qt_mod="1",
                qt_und="10",
                linha_pai_ordem=1,
                nivel=1,
                ativo=True,
            ),
        ]
    )
    session.flush()
    return modulo


def _linhas(session, item) -> list[OrcamentoItemCusteioLinha]:
    return list(
        session.execute(
            select(OrcamentoItemCusteioLinha).where(
                OrcamentoItemCusteioLinha.orcamento_item_id == item.id
            )
        ).scalars()
    )


def test_os_associados_de_uma_peca_simples_voltam_do_modulo(
    session: Session, item: OrcamentoItem, modulo_com_associado: DefModulo
) -> None:
    resultado = OrcamentoItemCusteioLinhaService(session).inserir_modulo_no_item(
        item.id, modulo_com_associado.id
    )
    session.flush()

    linhas = _linhas(session, item)
    assert len(linhas) == 2

    por_codigo = {linha.def_peca_codigo: linha for linha in linhas}
    teto = por_codigo["TETO_2000"]
    uniao = por_codigo["SISTEMAS_UNIAO"]

    assert teto.linha_pai_id is None
    assert uniao.linha_pai_id == teto.id
    assert uniao.nivel == 1
    assert uniao.qt_und == Decimal("10")
    # O associado conta como componente no resumo da importação.
    assert resultado.componentes == 1


def test_o_modulo_sem_filhos_continua_a_importar_so_a_peca(
    session: Session, item: OrcamentoItem
) -> None:
    peca = DefPeca(codigo="RODAPE_2200", nome="Rodapé[2200]", ativo=True)
    session.add(peca)
    session.flush()
    modulo = DefModulo(codigo="MOD_RODAPE", nome="Módulo rodapé", ativo=True)
    session.add(modulo)
    session.flush()
    session.add(
        DefModuloLinha(
            def_modulo_id=modulo.id,
            ordem=1,
            tipo_linha="PECA",
            def_peca_id=peca.id,
            def_peca_codigo="RODAPE_2200",
            descricao="Rodapé[2200]",
            qt_mod="1",
            qt_und="1",
            nivel=0,
            ativo=True,
        )
    )
    session.flush()

    OrcamentoItemCusteioLinhaService(session).inserir_modulo_no_item(
        item.id, modulo.id
    )
    session.flush()

    linhas = _linhas(session, item)
    assert len(linhas) == 1
    assert linhas[0].def_peca_codigo == "RODAPE_2200"
