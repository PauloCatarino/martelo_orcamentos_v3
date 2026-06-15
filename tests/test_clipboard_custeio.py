"""Tests for copy/cut/paste of cost lines (phase 8V.5)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import OrcamentoItem, OrcamentoItemValuesetLinha
from app.repositories.def_peca_componente_repository import DefPecaComponenteRepository
from app.repositories.def_peca_repository import DefPecaRepository
from app.repositories.def_regra_quantidade_repository import (
    DefRegraQuantidadeRepository,
)
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
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


def _criar_item(
    session, *, altura="2000", largura="1000", profundidade="500", ordem=1
) -> int:
    item = OrcamentoItem(
        orcamento_versao_id=1, ordem=ordem, tipo_item="OUTRO", item="Item",
        quantidade=Decimal("1"), altura=Decimal(altura),
        largura=Decimal(largura), profundidade=Decimal(profundidade),
    )
    session.add(item)
    session.flush()
    return item.id


def _criar_linha(session, item_id, **fields):
    base = dict(
        orcamento_item_id=item_id, tipo_linha="PECA", descricao="Linha",
        quantidade=Decimal("1"), nivel=0, ativo=True,
    )
    base.update(fields)
    linha = OrcamentoItemCusteioLinhaRepository(session).create_linha(**base)
    session.commit()
    return linha


def _valueset(session, item_id, chave):
    session.add(OrcamentoItemValuesetLinha(
        orcamento_item_id=item_id, chave=chave, padrao=True, ordem=1,
        preco_liquido=Decimal("5.79"), unidade="m2",
        desperdicio_percentagem=Decimal("5"),
    ))
    session.flush()


def _linhas(session, item_id):
    return OrcamentoItemCusteioLinhaRepository(session).list_active_by_orcamento_item(
        item_id
    )


def test_copiar_peca_simples_e_colar_abaixo_duplica(session) -> None:
    item_id = _criar_item(session)
    _valueset(session, item_id, "MATERIAL_LATERAIS")
    a = _criar_linha(session, item_id, descricao="A", comp="H", larg="P",
                     chave_valueset="MATERIAL_LATERAIS", qt_und=Decimal("2"))
    b = _criar_linha(session, item_id, descricao="B")
    service = OrcamentoItemCusteioLinhaService(session)

    clip = service.construir_clipboard(item_id, [a.id], "COPIAR")
    resultado = service.colar_clipboard(item_id, clip, a.id)

    assert resultado.inseridas == 1
    assert resultado.cortadas == 0
    descricoes = [l.descricao for l in _linhas(session, item_id)]
    # The copy lands right below A: A, A(copy), B.
    assert descricoes == ["A", "A", "B"]

    # Pipeline re-evaluates the copy against the destination variables/ValueSet.
    service.recalcular_medidas_do_item(item_id)
    service.recalcular_custo_materia_prima_do_item(item_id)
    copia = _linhas(session, item_id)[1]
    assert copia.comp_real == Decimal("2000.000")  # H
    assert copia.larg_real == Decimal("500.000")   # P
    assert copia.custo_mp is not None and copia.custo_mp > 0


def _composta_com_regra(session):
    """def_pecas: GAVETA (composta) with FUNDO + PES (rule), in an item."""
    peca_repo = DefPecaRepository(session)
    comp_repo = DefPecaComponenteRepository(session)
    regra_repo = DefRegraQuantidadeRepository(session)
    fundo = peca_repo.create_def_peca(
        codigo="FUNDO", nome="Fundo", descricao=None, grupo=None,
        tipo_peca="SIMPLES", chave_valueset_material="MATERIAL_FUNDOS",
    )
    pes = peca_repo.create_def_peca(
        codigo="PES", nome="Pé", descricao=None, grupo=None,
        tipo_peca="SIMPLES", chave_valueset_material=None,
    )
    gaveta = peca_repo.create_def_peca(
        codigo="GAVETA", nome="Gaveta", descricao=None, grupo=None,
        tipo_peca="COMPOSTA",
    )
    regra = regra_repo.create_regra(
        codigo="PES_NIV", nome="Pés", expressao="CEIL(COMP / 500)",
    )
    comp_pes = comp_repo.create_componente(
        def_peca_pai_id=gaveta.id, tipo_componente="FERRAGEM",
        def_peca_componente_id=pes.id, referencia_componente="PES",
        descricao="Pé", ordem=2, quantidade=Decimal("1"),
        regra_quantidade="FIXA", obrigatorio=True, ativo=True, observacoes=None,
        def_regra_quantidade_id=regra.id,
    )
    return fundo.id, pes.id, gaveta.id, comp_pes.id


def _bloco_composta(session, item_id, fundo_id, pes_id, gaveta_id, comp_pes_id):
    """A composite block in the item: header + FUNDO child + PES child."""
    header = _criar_linha(
        session, item_id, tipo_linha="PECA_COMPOSTA", def_peca_id=gaveta_id,
        def_peca_codigo="GAVETA", descricao="Gaveta",
    )
    fundo = _criar_linha(
        session, item_id, tipo_linha="PECA", def_peca_id=fundo_id,
        def_peca_codigo="FUNDO", descricao="Fundo", nivel=1,
        linha_pai_id=header.id, comp="L", larg="P",
        chave_valueset="MATERIAL_FUNDOS",
    )
    pes = _criar_linha(
        session, item_id, tipo_linha="FERRAGEM", def_peca_id=pes_id,
        def_peca_codigo="PES", descricao="Pé", nivel=1,
        linha_pai_id=header.id, origem_id=comp_pes_id, qt_und=Decimal("1"),
    )
    return header, fundo, pes


def test_copiar_composta_pelo_filho_cola_bloco_completo(session) -> None:
    item_id = _criar_item(session)
    _valueset(session, item_id, "MATERIAL_FUNDOS")
    fundo_id, pes_id, gaveta_id, comp_pes_id = _composta_com_regra(session)
    header, fundo, pes = _bloco_composta(
        session, item_id, fundo_id, pes_id, gaveta_id, comp_pes_id
    )
    tail = _criar_linha(session, item_id, descricao="Z")
    service = OrcamentoItemCusteioLinhaService(session)

    # Select only a CHILD -> the whole block is copied.
    clip = service.construir_clipboard(item_id, [fundo.id], "COPIAR")
    assert [s.fields["tipo_linha"] for s in clip.linhas] == [
        "PECA_COMPOSTA", "PECA", "FERRAGEM"
    ]

    service.colar_clipboard(item_id, clip, header.id)

    linhas = _linhas(session, item_id)
    tipos = [l.tipo_linha for l in linhas]
    # The pasted block goes AFTER the whole original composite (not in the middle).
    assert tipos == [
        "PECA_COMPOSTA", "PECA", "FERRAGEM",   # original block
        "PECA_COMPOSTA", "PECA", "FERRAGEM",   # pasted block
        "PECA",                                # Z
    ]
    # The pasted children hang from the pasted header (structure preserved).
    novo_header = linhas[3]
    assert linhas[4].linha_pai_id == novo_header.id
    assert linhas[5].linha_pai_id == novo_header.id

    # The quantity rule applies on the pasted PES (origem_id preserved).
    service.recalcular_medidas_do_item(item_id)
    service.aplicar_regras_quantidade_do_item(item_id)
    novo_pes = linhas[5]
    novo_pes = OrcamentoItemCusteioLinhaRepository(session).get_by_id(novo_pes.id)
    assert novo_pes.qt_und == Decimal("2")  # CEIL(1000/500)


def test_colar_nao_parte_composta_de_destino(session) -> None:
    item_id = _criar_item(session)
    fundo_id, pes_id, gaveta_id, comp_pes_id = _composta_com_regra(session)
    header, fundo, pes = _bloco_composta(
        session, item_id, fundo_id, pes_id, gaveta_id, comp_pes_id
    )
    simples = _criar_linha(session, item_id, descricao="Simples")
    service = OrcamentoItemCusteioLinhaService(session)

    clip = service.construir_clipboard(item_id, [simples.id], "COPIAR")
    # Paste targeting the composite HEADER -> must go after the whole block.
    service.colar_clipboard(item_id, clip, header.id)

    descricoes = [l.descricao for l in _linhas(session, item_id)]
    assert descricoes == ["Gaveta", "Fundo", "Pé", "Simples", "Simples"]


def test_cortar_move_linha_origem_eliminada_apos_colar(session) -> None:
    item_id = _criar_item(session)
    a = _criar_linha(session, item_id, descricao="A")
    b = _criar_linha(session, item_id, descricao="B")
    service = OrcamentoItemCusteioLinhaService(session)

    clip = service.construir_clipboard(item_id, [a.id], "CORTAR")
    resultado = service.colar_clipboard(item_id, clip, b.id)

    assert resultado.cortadas == 1
    descricoes = [l.descricao for l in _linhas(session, item_id)]
    # A moved to below B (original A removed): B, A.
    assert descricoes == ["B", "A"]


def test_colar_entre_items_recalcula_no_destino(session) -> None:
    origem_id = _criar_item(session, altura="3000", largura="1000", profundidade="600")
    destino_id = _criar_item(
        session, altura="2000", largura="800", profundidade="500", ordem=2
    )
    _valueset(session, destino_id, "MATERIAL_LATERAIS")
    peca = _criar_linha(session, origem_id, descricao="Lateral", comp="H", larg="P",
                        chave_valueset="MATERIAL_LATERAIS", qt_und=Decimal("1"))
    alvo = _criar_linha(session, destino_id, descricao="Base")
    service = OrcamentoItemCusteioLinhaService(session)

    clip = service.construir_clipboard(origem_id, [peca.id], "COPIAR")
    service.colar_clipboard(destino_id, clip, alvo.id)

    service.recalcular_medidas_do_item(destino_id)
    copia = _linhas(session, destino_id)[1]
    # Re-evaluated against the DESTINATION variables (H=2000, P=500), not 3000/600.
    assert copia.comp_real == Decimal("2000.000")
    assert copia.larg_real == Decimal("500.000")


def test_construir_clipboard_sem_selecao_erro(session) -> None:
    item_id = _criar_item(session)
    service = OrcamentoItemCusteioLinhaService(session)
    with pytest.raises(ValueError):
        service.construir_clipboard(item_id, [], "COPIAR")
