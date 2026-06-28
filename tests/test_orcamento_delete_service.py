"""Tests for deleting budget versions and their children."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domain.orcamento_estados import ESTADO_INICIAL
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import (
    Cliente,
    Orcamento,
    OrcamentoItem,
    OrcamentoItemCusteioLinha,
    OrcamentoItemModulo,
    OrcamentoItemValuesetLinha,
    OrcamentoItemVariavel,
    OrcamentoValuesetLinha,
    OrcamentoVersao,
    OrcamentoVersaoEvento,
    OrcamentoVersaoPlacaNaoStock,
    Producao,
    SystemSetting,
)
from app.services.orcamento_delete_service import (
    PRODUCAO_LIGADA_MSG,
    _remover_pasta_orcamento_segura,
    eliminar_versao_completo,
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


def test_eliminar_versao_nao_ultima_remove_filhos_e_preserva_orcamento(session) -> None:
    orcamento, versao_1, versao_2 = _criar_orcamento_com_duas_versoes(session)
    versao_2_item_vsl = session.scalar(
        select(OrcamentoItemValuesetLinha)
        .join(OrcamentoItem, OrcamentoItem.id == OrcamentoItemValuesetLinha.orcamento_item_id)
        .where(OrcamentoItem.orcamento_versao_id == versao_2.id)
    )
    assert versao_2_item_vsl.origem_orcamento_versao_id == versao_1.id

    eliminar_versao_completo(
        session,
        orcamento_versao_id=versao_1.id,
        apagar_registo=True,
        apagar_pasta=False,
    )

    assert session.get(Orcamento, orcamento.id) is not None
    assert session.get(OrcamentoVersao, versao_1.id) is None
    assert session.get(OrcamentoVersao, versao_2.id) is not None
    assert _count_by_versao(session, OrcamentoItem, versao_1.id) == 0
    assert _count_by_versao(session, OrcamentoValuesetLinha, versao_1.id) == 0
    assert _count_by_versao(session, OrcamentoVersaoPlacaNaoStock, versao_1.id) == 0
    assert _count_by_versao(session, OrcamentoVersaoEvento, versao_1.id) == 0
    assert _count_children_for_versao(session, versao_1.id) == 0

    sobrevivente_item_vsl = session.get(OrcamentoItemValuesetLinha, versao_2_item_vsl.id)
    assert sobrevivente_item_vsl is not None
    assert sobrevivente_item_vsl.origem_orcamento_versao_id is None
    assert sobrevivente_item_vsl.origem_orcamento_valueset_linha_id is None


def test_eliminar_ultima_versao_remove_orcamento(session) -> None:
    orcamento, versao_1, versao_2 = _criar_orcamento_com_duas_versoes(session)
    orcamento_id = orcamento.id
    versao_1_id = versao_1.id
    versao_2_id = versao_2.id
    eliminar_versao_completo(
        session,
        orcamento_versao_id=versao_1_id,
        apagar_registo=True,
        apagar_pasta=False,
    )

    eliminar_versao_completo(
        session,
        orcamento_versao_id=versao_2_id,
        apagar_registo=True,
        apagar_pasta=False,
    )

    assert session.get(Orcamento, orcamento_id) is None
    assert session.get(OrcamentoVersao, versao_2_id) is None
    assert _count_by_versao(session, OrcamentoItem, versao_2_id) == 0
    assert _count_children_for_versao(session, versao_2_id) == 0


def test_eliminar_ultima_versao_bloqueia_quando_tem_producao_ligada(session) -> None:
    orcamento, versao = _criar_orcamento_com_uma_versao(session)
    producao = Producao(
        codigo_processo="26.0001_01_01",
        ano="2026",
        num_enc_phc="0001",
        versao_obra="01",
        versao_plano="01",
        orcamento_id=orcamento.id,
    )
    session.add(producao)
    session.flush()

    with pytest.raises(ValueError, match=PRODUCAO_LIGADA_MSG):
        eliminar_versao_completo(
            session,
            orcamento_versao_id=versao.id,
            apagar_registo=True,
            apagar_pasta=False,
        )

    assert session.get(Orcamento, orcamento.id) is not None
    assert session.get(OrcamentoVersao, versao.id) is not None
    assert session.get(Producao, producao.id).orcamento_id == orcamento.id


def test_remover_pasta_orcamento_segura_valida_base_e_nome(session, tmp_path) -> None:
    base = tmp_path / "orcamentos"
    pasta_correta = base / "2026" / "260001_CLIENTE" / "01"
    pasta_correta.mkdir(parents=True)
    (pasta_correta / "ficheiro.txt").write_text("x", encoding="utf-8")
    fora_base = tmp_path / "fora" / "01"
    fora_base.mkdir(parents=True)
    session.add(
        SystemSetting(
            chave="pasta_base_orcamentos",
            valor=str(base),
            tipo="pasta",
            grupo="caminhos",
        )
    )
    session.flush()

    with pytest.raises(ValueError, match="fora da pasta base"):
        _remover_pasta_orcamento_segura(
            session,
            fora_base,
            nome_esperado=fora_base.name,
        )
    with pytest.raises(ValueError, match="Nome da pasta"):
        _remover_pasta_orcamento_segura(
            session,
            pasta_correta,
            nome_esperado="nome-errado",
        )

    _remover_pasta_orcamento_segura(
        session,
        pasta_correta,
        nome_esperado=pasta_correta.name,
    )

    assert not pasta_correta.exists()
    assert base.exists()


def _criar_orcamento_com_uma_versao(session: Session) -> tuple[Orcamento, OrcamentoVersao]:
    orcamento, versao_1, _versao_2 = _criar_orcamento_com_duas_versoes(
        session,
        criar_segunda=False,
    )
    return orcamento, versao_1


def _criar_orcamento_com_duas_versoes(
    session: Session,
    *,
    criar_segunda: bool = True,
) -> tuple[Orcamento, OrcamentoVersao, OrcamentoVersao | None]:
    cliente = Cliente(nome="Cliente X", is_temporary=True)
    session.add(cliente)
    session.flush()

    orcamento = Orcamento(
        ano=2026,
        num_orcamento="260001",
        cliente_id=cliente.id,
        obra="Obra X",
    )
    session.add(orcamento)
    session.flush()

    versao_1 = _criar_versao_com_filhos(session, orcamento.id, 1)
    versao_2 = None
    if criar_segunda:
        origem_vsl = session.scalar(
            select(OrcamentoValuesetLinha).where(
                OrcamentoValuesetLinha.orcamento_versao_id == versao_1.id
            )
        )
        versao_2 = _criar_versao_com_filhos(
            session,
            orcamento.id,
            2,
            origem_vsl_id=origem_vsl.id,
            origem_versao_id=versao_1.id,
        )

    return orcamento, versao_1, versao_2


def _criar_versao_com_filhos(
    session: Session,
    orcamento_id: int,
    numero_versao: int,
    *,
    origem_vsl_id: int | None = None,
    origem_versao_id: int | None = None,
) -> OrcamentoVersao:
    versao = OrcamentoVersao(
        orcamento_id=orcamento_id,
        numero_versao=numero_versao,
        codigo_versao=f"260001_{numero_versao:02d}",
        estado=ESTADO_INICIAL,
        preco_total=Decimal("100"),
        preco_origem=Decimal("0"),
    )
    session.add(versao)
    session.flush()

    vsl = OrcamentoValuesetLinha(
        orcamento_versao_id=versao.id,
        chave="MATERIAL",
        codigo_opcao=f"MDF-{numero_versao}",
        nome_opcao="MDF",
        padrao=True,
        ordem=1,
        ativo=True,
    )
    session.add(vsl)
    session.flush()

    session.add(
        OrcamentoVersaoPlacaNaoStock(
            orcamento_versao_id=versao.id,
            ref_le=f"REF-{numero_versao}",
            descricao="MDF",
            esp=Decimal("19"),
        )
    )
    session.add(
        OrcamentoVersaoEvento(
            orcamento_versao_id=versao.id,
            tipo="teste",
            descricao="Evento teste",
        )
    )

    item = OrcamentoItem(
        orcamento_versao_id=versao.id,
        ordem=1,
        tipo_item="OUTRO",
        item=f"Item {numero_versao}",
        quantidade=Decimal("1"),
        preco_total=Decimal("100"),
    )
    session.add(item)
    session.flush()

    session.add(
        OrcamentoItemVariavel(
            item_id=item.id,
            nome="L",
            valor=Decimal("800"),
            unidade="mm",
            ordem=1,
        )
    )
    modulo = OrcamentoItemModulo(
        orcamento_item_id=item.id,
        ordem=1,
        nome="Modulo",
        quantidade=Decimal("1"),
    )
    session.add(modulo)
    session.flush()

    session.add(
        OrcamentoItemValuesetLinha(
            orcamento_item_id=item.id,
            chave="MATERIAL",
            codigo_opcao=f"MDF-{numero_versao}",
            nome_opcao="MDF",
            padrao=True,
            ordem=1,
            origem_orcamento_valueset_linha_id=origem_vsl_id or vsl.id,
            origem_orcamento_versao_id=origem_versao_id or versao.id,
            herdado_do_orcamento=True,
            ativo=True,
        )
    )

    pai = OrcamentoItemCusteioLinha(
        orcamento_item_id=item.id,
        orcamento_item_modulo_id=modulo.id,
        tipo_linha="PECA_COMPOSTA",
        descricao="Pai",
        quantidade=Decimal("1"),
        nivel=0,
        ordem=1,
        ativo=True,
    )
    session.add(pai)
    session.flush()
    session.add(
        OrcamentoItemCusteioLinha(
            orcamento_item_id=item.id,
            linha_pai_id=pai.id,
            tipo_linha="PECA",
            descricao="Filho",
            quantidade=Decimal("1"),
            nivel=1,
            ordem=2,
            ativo=True,
        )
    )
    session.flush()

    return versao


def _count_by_versao(session: Session, model, versao_id: int) -> int:
    return len(
        list(
            session.scalars(
                select(model).where(model.orcamento_versao_id == versao_id)
            )
        )
    )


def _count_children_for_versao(session: Session, versao_id: int) -> int:
    item_ids = list(
        session.scalars(
            select(OrcamentoItem.id).where(OrcamentoItem.orcamento_versao_id == versao_id)
        )
    )
    if not item_ids:
        return 0

    return (
        len(
            list(
                session.scalars(
                    select(OrcamentoItemCusteioLinha).where(
                        OrcamentoItemCusteioLinha.orcamento_item_id.in_(item_ids)
                    )
                )
            )
        )
        + len(
            list(
                session.scalars(
                    select(OrcamentoItemValuesetLinha).where(
                        OrcamentoItemValuesetLinha.orcamento_item_id.in_(item_ids)
                    )
                )
            )
        )
        + len(
            list(
                session.scalars(
                    select(OrcamentoItemVariavel).where(
                        OrcamentoItemVariavel.item_id.in_(item_ids)
                    )
                )
            )
        )
        + len(
            list(
                session.scalars(
                    select(OrcamentoItemModulo).where(
                        OrcamentoItemModulo.orcamento_item_id.in_(item_ids)
                    )
                )
            )
        )
    )
