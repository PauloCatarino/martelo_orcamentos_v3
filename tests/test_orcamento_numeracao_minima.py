"""O piso da numeracao dos orcamentos.

Sem isto, o Martelo V3 -- que arranca com a tabela de orcamentos vazia --
comecava no 260001, um numero que em 2026 pertence a um orcamento real do
Martelo V2 cuja pasta esta' no servidor com trabalho de um cliente la' dentro.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.domain.orcamento_numeracao import (
    chave_numero_minimo,
    primeiro_numero_do_ano,
)
from app.models import Cliente, Orcamento, SystemSetting
from app.repositories.orcamento_repository import OrcamentoRepository


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine, future=True)
    with fabrica() as sessao:
        yield sessao


def _definir_piso(sessao: Session, ano: int, valor: str, *, ativo: bool = True) -> None:
    sessao.add(
        SystemSetting(
            chave=chave_numero_minimo(ano),
            valor=valor,
            tipo="numero",
            grupo="Orcamentos",
            ativo=ativo,
        )
    )
    sessao.commit()


def _criar_orcamento(sessao: Session, ano: int, numero: str) -> None:
    cliente = sessao.query(Cliente).first()
    if cliente is None:
        cliente = Cliente(nome="Cliente")
        sessao.add(cliente)
        sessao.flush()
    sessao.add(Orcamento(ano=ano, num_orcamento=numero, cliente_id=cliente.id))
    sessao.commit()


# ---------------------------------------------------------------------------
# O caso que motivou tudo
# ---------------------------------------------------------------------------

def test_sem_piso_o_ano_comeca_no_primeiro_numero(session: Session) -> None:
    """O comportamento de sempre, para um ano que o V3 comeca do zero."""
    assert OrcamentoRepository(session).get_next_num_orcamento(2027) == "270001"


def test_com_piso_o_primeiro_orcamento_do_v3_nao_pisa_os_do_v2(session: Session) -> None:
    _definir_piso(session, 2026, "260868")

    assert OrcamentoRepository(session).get_next_num_orcamento(2026) == "260868"


def test_o_piso_vale_apenas_para_o_ano_dele(session: Session) -> None:
    _definir_piso(session, 2026, "260868")

    assert OrcamentoRepository(session).get_next_num_orcamento(2027) == "270001"


# ---------------------------------------------------------------------------
# O piso e' um piso, nao uma resposta fixa
# ---------------------------------------------------------------------------

def test_depois_de_haver_orcamentos_a_numeracao_segue_normalmente(session: Session) -> None:
    _definir_piso(session, 2026, "260868")
    _criar_orcamento(session, 2026, "260868")
    _criar_orcamento(session, 2026, "260869")

    assert OrcamentoRepository(session).get_next_num_orcamento(2026) == "260870"


def test_um_piso_ja_ultrapassado_nao_faz_a_numeracao_recuar(session: Session) -> None:
    _definir_piso(session, 2026, "260868")
    _criar_orcamento(session, 2026, "260900")

    assert OrcamentoRepository(session).get_next_num_orcamento(2026) == "260901"


# ---------------------------------------------------------------------------
# Um piso estragado nao pode partir a criacao de orcamentos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("valor", ["", "   ", "abc", "260 868", "260868,5", "-5"])
def test_piso_com_lixo_e_ignorado_em_vez_de_rebentar(session: Session, valor: str) -> None:
    _definir_piso(session, 2026, valor)

    assert OrcamentoRepository(session).get_next_num_orcamento(2026) == "260001"


def test_piso_desativado_nao_conta(session: Session) -> None:
    _definir_piso(session, 2026, "260868", ativo=False)

    assert OrcamentoRepository(session).get_next_num_orcamento(2026) == "260001"


# ---------------------------------------------------------------------------
# As chaves
# ---------------------------------------------------------------------------

def test_a_chave_leva_o_ano_no_fim() -> None:
    assert chave_numero_minimo(2026) == "orcamento_numero_minimo_2026"
    assert chave_numero_minimo(2027) == "orcamento_numero_minimo_2027"


def test_primeiro_numero_do_ano() -> None:
    assert primeiro_numero_do_ano(2026) == 260001
    assert primeiro_numero_do_ano(2030) == 300001
