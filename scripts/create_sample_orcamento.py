"""Create a sample budget for validating the Orcamentos page."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import Cliente, Orcamento, OrcamentoItem, OrcamentoVersao  # noqa: E402


CLIENTE_NOME = "Cliente Teste V3"
CLIENTE_EMAIL = "cliente.teste@martelo.local"
CLIENTE_SOURCE_SYSTEM = "manual"
CLIENTE_IS_TEMPORARY = True

ORCAMENTO_ANO = 2026
ORCAMENTO_NUMERO = "260001"
ORCAMENTO_DESCRICAO = "Or\u00e7amento de teste criado por script"
ORCAMENTO_OBRA = "Obra Teste Martelo V3"
ORCAMENTO_LOCALIZACAO = "Local Teste"
ORCAMENTO_REF_CLIENTE = "REF-TESTE"

VERSAO_NUMERO = 1
VERSAO_ESTADO = "rascunho"
VERSAO_PRECO_TOTAL = Decimal("0")

ITEM_ORDEM = 1
ITEM_CODIGO = "ITEM-TESTE-001"
ITEM_NOME = "Roupeiro Teste"
ITEM_DESCRICAO = "Item de teste para validar listagem"
ITEM_ALTURA = Decimal("2400")
ITEM_LARGURA = Decimal("1800")
ITEM_PROFUNDIDADE = Decimal("600")
ITEM_QUANTIDADE = Decimal("1")
ITEM_UNIDADE = "un"
ITEM_PRECO_UNITARIO = Decimal("0")
ITEM_PRECO_TOTAL = Decimal("0")


@dataclass(frozen=True)
class EntityResult:
    """Result for one sample entity."""

    status: str
    entity: object


@dataclass(frozen=True)
class SampleOrcamentoResult:
    """Result of the sample budget seed."""

    cliente_status: str
    orcamento_status: str
    versao_status: str
    item_status: str


def format_codigo_versao(num_orcamento: str, numero_versao: int) -> str:
    """Format the commercial version code."""
    return f"{num_orcamento}_{numero_versao:02d}"


def get_or_create_cliente(session: Session) -> EntityResult:
    """Create or reuse the sample customer."""
    cliente = session.execute(
        select(Cliente).where(Cliente.email == CLIENTE_EMAIL)
    ).scalar_one_or_none()

    if cliente is not None:
        return EntityResult(status="reutilizado", entity=cliente)

    cliente = Cliente(
        nome=CLIENTE_NOME,
        email=CLIENTE_EMAIL,
        source_system=CLIENTE_SOURCE_SYSTEM,
        is_temporary=CLIENTE_IS_TEMPORARY,
    )
    session.add(cliente)
    session.flush()

    return EntityResult(status="criado", entity=cliente)


def get_or_create_orcamento(session: Session, cliente: Cliente) -> EntityResult:
    """Create or reuse the sample budget."""
    orcamento = session.execute(
        select(Orcamento).where(
            Orcamento.ano == ORCAMENTO_ANO,
            Orcamento.num_orcamento == ORCAMENTO_NUMERO,
        )
    ).scalar_one_or_none()

    if orcamento is not None:
        return EntityResult(status="reutilizado", entity=orcamento)

    orcamento = Orcamento(
        ano=ORCAMENTO_ANO,
        num_orcamento=ORCAMENTO_NUMERO,
        cliente_id=cliente.id,
        descricao=ORCAMENTO_DESCRICAO,
        obra=ORCAMENTO_OBRA,
        localizacao=ORCAMENTO_LOCALIZACAO,
        ref_cliente=ORCAMENTO_REF_CLIENTE,
    )
    session.add(orcamento)
    session.flush()

    return EntityResult(status="criado", entity=orcamento)


def get_or_create_versao(session: Session, orcamento: Orcamento) -> EntityResult:
    """Create or reuse version 01 of the sample budget."""
    versao = session.execute(
        select(OrcamentoVersao).where(
            OrcamentoVersao.orcamento_id == orcamento.id,
            OrcamentoVersao.numero_versao == VERSAO_NUMERO,
        )
    ).scalar_one_or_none()

    if versao is not None:
        return EntityResult(status="reutilizado", entity=versao)

    versao = OrcamentoVersao(
        orcamento_id=orcamento.id,
        numero_versao=VERSAO_NUMERO,
        codigo_versao=format_codigo_versao(ORCAMENTO_NUMERO, VERSAO_NUMERO),
        estado=VERSAO_ESTADO,
        preco_total=VERSAO_PRECO_TOTAL,
        preco_origem=VERSAO_PRECO_TOTAL,
        is_locked=False,
    )
    session.add(versao)
    session.flush()

    return EntityResult(status="criado", entity=versao)


def get_or_create_item(session: Session, versao: OrcamentoVersao) -> EntityResult:
    """Create or reuse the sample line item."""
    item = session.execute(
        select(OrcamentoItem).where(
            OrcamentoItem.orcamento_versao_id == versao.id,
            OrcamentoItem.ordem == ITEM_ORDEM,
        )
    ).scalar_one_or_none()

    if item is not None:
        return EntityResult(status="reutilizado", entity=item)

    item = OrcamentoItem(
        orcamento_versao_id=versao.id,
        ordem=ITEM_ORDEM,
        codigo=ITEM_CODIGO,
        item=ITEM_NOME,
        descricao=ITEM_DESCRICAO,
        altura=ITEM_ALTURA,
        largura=ITEM_LARGURA,
        profundidade=ITEM_PROFUNDIDADE,
        quantidade=ITEM_QUANTIDADE,
        unidade=ITEM_UNIDADE,
        preco_unitario=ITEM_PRECO_UNITARIO,
        preco_total=ITEM_PRECO_TOTAL,
    )
    session.add(item)
    session.flush()

    return EntityResult(status="criado", entity=item)


def ensure_sample_orcamento(session: Session) -> SampleOrcamentoResult:
    """Create or reuse all entities for the sample budget."""
    cliente_result = get_or_create_cliente(session)
    orcamento_result = get_or_create_orcamento(session, cliente_result.entity)
    versao_result = get_or_create_versao(session, orcamento_result.entity)
    item_result = get_or_create_item(session, versao_result.entity)

    session.commit()

    return SampleOrcamentoResult(
        cliente_status=cliente_result.status,
        orcamento_status=orcamento_result.status,
        versao_status=versao_result.status,
        item_status=item_result.status,
    )


def print_result(result: SampleOrcamentoResult) -> None:
    """Print user-facing seed result messages."""
    print(f"Cliente {result.cliente_status}")
    print(f"Or\u00e7amento {result.orcamento_status}")
    print(f"Vers\u00e3o {result.versao_status}")
    print(f"Item {result.item_status}")


def main() -> int:
    """Create or reuse the sample budget in the configured database."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = ensure_sample_orcamento(session)

    print_result(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
