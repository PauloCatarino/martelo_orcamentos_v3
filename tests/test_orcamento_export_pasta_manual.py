"""Tests for folder resolution of legacy budgets with a manual folder."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.domain.orcamento_estados import ESTADO_INICIAL
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import Cliente, Orcamento, OrcamentoVersao, SystemSetting
from app.services.orcamento_export_service import OrcamentoExportService


def _criar_orcamento(
    session: Session,
    *,
    pasta_manual: str | None = None,
    ano: int = 2025,
    num_orcamento: str = "1049",
) -> OrcamentoVersao:
    cliente = Cliente(nome="Costa", nome_simplex="COSTA", is_temporary=True)
    session.add(cliente)
    session.flush()

    orcamento = Orcamento(
        ano=ano,
        num_orcamento=num_orcamento,
        cliente_id=cliente.id,
        obra="Obra X",
        pasta_manual=pasta_manual,
    )
    session.add(orcamento)
    session.flush()

    versao = OrcamentoVersao(
        orcamento_id=orcamento.id,
        numero_versao=1,
        codigo_versao=f"{num_orcamento}_01",
        estado=ESTADO_INICIAL,
        preco_total=Decimal("100"),
        preco_origem=Decimal("0"),
    )
    session.add(versao)
    session.flush()

    return versao


def _definir_pasta_base(session: Session, base: Path) -> None:
    session.add(
        SystemSetting(chave="pasta_base_orcamentos", valor=str(base))
    )
    session.flush()


def test_resolver_pasta_versao_usa_pasta_manual(session, tmp_path) -> None:
    pasta = tmp_path / "2025" / "1049_COSTA & ZEFERINO"
    pasta.mkdir(parents=True)
    versao = _criar_orcamento(session, pasta_manual=str(pasta))
    _definir_pasta_base(session, tmp_path)

    resultado = OrcamentoExportService(session).resolver_pasta_versao(versao.id)

    # Grava diretamente na pasta escolhida, sem subpasta de versão.
    assert resultado == pasta


def test_resolver_pasta_versao_manual_cria_pasta_em_falta(session, tmp_path) -> None:
    pasta = tmp_path / "2025" / "1049_COSTA"
    versao = _criar_orcamento(session, pasta_manual=str(pasta))

    resultado = OrcamentoExportService(session).resolver_pasta_versao(
        versao.id, criar=True
    )

    assert resultado == pasta
    assert pasta.exists()


def test_resolver_pasta_versao_manual_dispensa_pasta_base(session, tmp_path) -> None:
    pasta = tmp_path / "1049_COSTA"
    pasta.mkdir()
    versao = _criar_orcamento(session, pasta_manual=str(pasta))

    resultado = OrcamentoExportService(session).resolver_pasta_versao(
        versao.id, criar=False
    )

    assert resultado == pasta


def test_resolver_pasta_versao_sem_manual_mantem_convencao(session, tmp_path) -> None:
    versao = _criar_orcamento(session, ano=2026, num_orcamento="260001")
    _definir_pasta_base(session, tmp_path)

    resultado = OrcamentoExportService(session).resolver_pasta_versao(versao.id)

    assert resultado == tmp_path / "2026" / "260001_COSTA" / "01"


def test_pasta_orcamento_atual_devolve_pasta_manual(session, tmp_path) -> None:
    pasta = tmp_path / "1049_COSTA"
    pasta.mkdir()
    versao = _criar_orcamento(session, pasta_manual=str(pasta))

    assert OrcamentoExportService(session).pasta_orcamento_atual(versao.id) == pasta


def test_pasta_orcamento_atual_manual_inexistente_devolve_none(
    session, tmp_path
) -> None:
    versao = _criar_orcamento(
        session, pasta_manual=str(tmp_path / "nao_existe")
    )

    assert OrcamentoExportService(session).pasta_orcamento_atual(versao.id) is None


def test_nome_pretendido_e_renomear_ignoram_pasta_manual(session, tmp_path) -> None:
    pasta = tmp_path / "1049_COSTA"
    pasta.mkdir()
    versao = _criar_orcamento(session, pasta_manual=str(pasta))
    _definir_pasta_base(session, tmp_path)

    servico = OrcamentoExportService(session)

    assert servico.nome_pasta_orcamento_pretendido(versao.id) is None
    assert servico.renomear_pasta_para_cliente(versao.id) is None
