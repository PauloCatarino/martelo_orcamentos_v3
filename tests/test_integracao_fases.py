"""Tests for the phase-7 integration report and assisted fixes."""

from __future__ import annotations

from decimal import Decimal

import pytest

from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import (
    Cliente,
    DefModulo,
    DefModuloCategoria,
    OrcamentoItem,
    OrcamentoVersao,
    OrcamentoVersaoEncomendaPhc,
)
from app.services.integracao_fases_service import (
    IntegracaoFasesService,
    formatar_relatorio,
)
from app.services.orcamento_service import (
    CriarOrcamentoSimplesData,
    OrcamentoService,
)


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _criar_versao(session, *, enc_phc: str | None = None) -> int:
    cliente = Cliente(nome="Cliente X", is_temporary=True)
    session.add(cliente)
    session.flush()
    service = OrcamentoService(session)
    service.criar_orcamento_simples(
        CriarOrcamentoSimplesData(
            cliente_id=cliente.id,
            obra="Obra",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            enc_phc=enc_phc,
            ano=2026,
        )
    )
    return service.list_orcamentos()[0].orcamento_versao_id


def _linha(relatorio, descricao_parcial: str):
    return next(
        (
            linha
            for linha in relatorio.linhas
            if descricao_parcial in linha.descricao
        ),
        None,
    )


def test_relatorio_sem_dados_nao_tem_ocorrencias_alem_da_revisao(session) -> None:
    # In-memory DB has no alembic_version table: that is the only warning.
    IntegracaoFasesService(session).aplicar_correcoes()

    relatorio = IntegracaoFasesService(session).gerar_relatorio()

    assert [linha.descricao for linha in relatorio.ocorrencias] == [
        "Revisão alembic"
    ]


def test_relatorio_conta_modalidades_e_perfis(session) -> None:
    versao_id = _criar_versao(session)
    session.add(
        OrcamentoItem(
            orcamento_versao_id=versao_id,
            ordem=1,
            item="Item A",
            quantidade=Decimal("1"),
            preco_unitario=Decimal("10"),
            preco_total=Decimal("10"),
            modalidade_custeio="SIMPLIFICADO",
        )
    )
    session.flush()

    relatorio = IntegracaoFasesService(session).gerar_relatorio()

    modalidades = _linha(relatorio, "modalidade de custeio")
    assert "Simplificado: 1" in modalidades.valor
    perfis = _linha(relatorio, "perfil de margens")
    assert "STANDARD: 1" in perfis.valor


def test_relatorio_detecta_versao_legada_so_com_enc_phc(session) -> None:
    versao_id = _criar_versao(session)
    versao = session.get(OrcamentoVersao, versao_id)
    versao.enc_phc = "475"  # legacy value without a child record
    session.flush()

    service = IntegracaoFasesService(session)
    relatorio = service.gerar_relatorio()
    assert _linha(relatorio, "sem registo filho") is not None

    resultado = service.aplicar_correcoes()
    assert resultado.encomendas_materializadas == 1

    registos = session.execute(
        select(OrcamentoVersaoEncomendaPhc).where(
            OrcamentoVersaoEncomendaPhc.orcamento_versao_id == versao_id
        )
    ).scalars().all()
    assert [(r.numero, r.is_principal) for r in registos] == [("475", True)]

    # Fixed and idempotent: no warning left, nothing new on a second run.
    assert _linha(service.gerar_relatorio(), "sem registo filho") is None
    assert service.aplicar_correcoes().encomendas_materializadas == 0


def test_relatorio_detecta_espelho_divergente(session) -> None:
    versao_id = _criar_versao(session, enc_phc="100")
    versao = session.get(OrcamentoVersao, versao_id)
    versao.enc_phc = "999"  # mirror manually broken
    session.flush()

    relatorio = IntegracaoFasesService(session).gerar_relatorio()

    assert _linha(relatorio, "difere da encomenda principal") is not None


def test_correcoes_importam_categorias_orfas(session) -> None:
    session.add(
        DefModulo(
            codigo="MOD_LEGADO",
            nome="Legado",
            ambito="GLOBAL",
            categoria="CATEGORIA_ANTIGA",
            ativo=True,
        )
    )
    session.flush()

    service = IntegracaoFasesService(session)
    relatorio = service.gerar_relatorio()
    assert _linha(relatorio, "sem registo") is not None

    resultado = service.aplicar_correcoes()
    # Seed (4) + the orphan legacy code.
    assert resultado.categorias_criadas == 5
    codigos = set(
        session.execute(select(DefModuloCategoria.codigo)).scalars()
    )
    assert "CATEGORIA_ANTIGA" in codigos

    assert _linha(service.gerar_relatorio(), "sem registo") is None


def test_formatar_relatorio_apresenta_ocorrencias(session) -> None:
    texto = formatar_relatorio(IntegracaoFasesService(session).gerar_relatorio())

    assert "Relatório de integração das fases" in texto
    assert "ocorrência" in texto or "Sem ocorrências" in texto
