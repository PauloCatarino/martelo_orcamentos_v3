"""Tests for the trims (REMATES/GUARNICOES) seed script."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.medidas import validar_formula_dimensional
from app.domain.peca_funcao_types import FERRAGEM, REMATE
from app.domain.peca_natureza_types import (
    FERRAGEM as NATUREZA_FERRAGEM,
    HORIZONTAL,
    MATERIAL,
    NEUTRA,
    VERTICAL,
)
from app.domain.peca_types import SIMPLES
from app.models import DefOperacao, DefPeca, DefPecaOperacao, DefValuesetChave
from scripts.create_remates_guarnicoes import (
    CHAVES,
    CHAVE_GUARNICOES_COMPRA_L,
    CHAVE_REMATES_VERTICAIS,
    GRUPO_REMATES_GUARNICOES,
    PECAS,
    seed_remates_guarnicoes,
)


TOTAL_PECAS = 11
TOTAL_CHAVES = 6


def _criar_operacoes_base(session) -> None:
    """Create the cut/edging operations the seed attaches to each piece."""
    for codigo in ("CORTE_PAINEL", "ORLAGEM_PECA"):
        session.add(DefOperacao(codigo=codigo, nome=codigo.title(), ativo=True))
    session.flush()


def _get(pecas, codigo) -> DefPeca:
    return next(peca for peca in pecas if peca.codigo == codigo)


def test_seed_constants() -> None:
    codigos = [seed.codigo for seed in PECAS]
    chaves = [seed.codigo for seed in CHAVES]

    assert len(codigos) == TOTAL_PECAS
    assert len(codigos) == len(set(codigos))
    assert len(chaves) == TOTAL_CHAVES
    assert len(chaves) == len(set(chaves))
    # Todas as peças apontam para uma chave criada por este seed.
    assert {seed.chave_material for seed in PECAS} <= set(chaves)
    for seed in PECAS:
        assert len(seed.codigo_orlas) == 4


def test_formulas_das_tiras_sao_validas() -> None:
    for seed in PECAS:
        if seed.formula_comp is None:
            continue
        assert validar_formula_dimensional(seed.formula_comp, campo="Comp")
        assert validar_formula_dimensional(seed.formula_larg, campo="Larg")


def test_seed_cria_chaves_e_pecas(session) -> None:
    _criar_operacoes_base(session)

    result = seed_remates_guarnicoes(session)

    assert result.chaves_criadas == TOTAL_CHAVES
    assert result.chaves_renomeadas == 0
    assert result.pecas_criadas == TOTAL_PECAS
    assert result.pecas_reutilizadas == 0
    # Todas levam corte + orlagem menos a guarnicao comprada.
    assert result.operacoes_criadas == (TOTAL_PECAS - 1) * 2

    chave = session.execute(
        select(DefValuesetChave).where(
            DefValuesetChave.codigo == CHAVE_REMATES_VERTICAIS
        )
    ).scalar_one()
    assert chave.nome == "Material Remates Verticais"
    assert (chave.tipo, chave.grupo) == ("MATERIAL", "MATERIAIS")
    # Todas as chaves de placa deste grupo seguem o mesmo criterio de nome.
    assert all(
        seed.nome.startswith("Material ")
        for seed in CHAVES
        if seed.grupo == "MATERIAIS"
    )

    chave_compra = session.execute(
        select(DefValuesetChave).where(
            DefValuesetChave.codigo == CHAVE_GUARNICOES_COMPRA_L
        )
    ).scalar_one()
    assert (chave_compra.tipo, chave_compra.grupo) == ("FERRAGEM", "FERRAGENS")

    pecas = session.execute(
        select(DefPeca).where(DefPeca.grupo == GRUPO_REMATES_GUARNICOES)
    ).scalars().all()
    assert len(pecas) == TOTAL_PECAS
    for peca in pecas:
        assert peca.tipo_peca == SIMPLES
        assert peca.sem_material is False
        assert peca.ativo is True
        assert peca.permite_acabamento is True
        assert peca.chave_valueset_acabamento_sup is None
        assert peca.chave_valueset_acabamento_inf is None

    rodateto = _get(pecas, "RODATETO_2200")
    assert rodateto.natureza == MATERIAL
    assert rodateto.orientacao == HORIZONTAL
    assert rodateto.funcao == REMATE
    assert (rodateto.formula_comp, rodateto.formula_larg) == ("LM", "100")
    assert rodateto.chave_valueset_material == "MATERIAL_RODATETOS"
    assert (
        rodateto.orla_c1,
        rodateto.orla_c2,
        rodateto.orla_l1,
        rodateto.orla_l2,
    ) == (2, 2, 0, 0)

    rodape = _get(pecas, "RODAPE_2222")
    assert rodape.orientacao == HORIZONTAL
    assert (rodape.formula_comp, rodape.formula_larg) == ("LM", "75")
    assert rodape.chave_valueset_material == "MATERIAL_RODAPES"

    enchimento = _get(pecas, "ENCHIMENTO_GUARNICAO_2000")
    assert enchimento.orientacao == VERTICAL
    assert (enchimento.formula_comp, enchimento.formula_larg) == ("HM", "75")
    assert enchimento.chave_valueset_material == "MATERIAL_ENCHIMENTOS"
    assert (
        enchimento.orla_c1,
        enchimento.orla_c2,
        enchimento.orla_l1,
        enchimento.orla_l2,
    ) == (2, 0, 0, 0)

    guarnicao = _get(pecas, "GUARNICAO_PRODUZIDA_2222")
    assert guarnicao.orientacao == VERTICAL
    assert (guarnicao.formula_comp, guarnicao.formula_larg) == ("HM", "70")
    assert guarnicao.chave_valueset_material == "MATERIAL_GUARNICOES"


def test_guarnicao_de_compra_nao_leva_medidas_nem_operacoes(session) -> None:
    _criar_operacoes_base(session)

    seed_remates_guarnicoes(session)

    comprada = session.execute(
        select(DefPeca).where(DefPeca.codigo == "GUARNICAO_COMPRA_L")
    ).scalar_one()
    assert comprada.natureza == NATUREZA_FERRAGEM
    assert comprada.orientacao == NEUTRA
    assert comprada.funcao == FERRAGEM
    assert (comprada.formula_comp, comprada.formula_larg) == (None, None)
    assert comprada.chave_valueset_material == CHAVE_GUARNICOES_COMPRA_L
    assert comprada.permite_acabamento is True

    operacoes = session.execute(
        select(DefPecaOperacao).where(DefPecaOperacao.def_peca_id == comprada.id)
    ).scalars().all()
    assert operacoes == []


def test_tiras_levam_corte_e_orlagem(session) -> None:
    _criar_operacoes_base(session)

    seed_remates_guarnicoes(session)

    remate = session.execute(
        select(DefPeca).where(DefPeca.codigo == "REMATE_VERTICAL_2220")
    ).scalar_one()
    operacoes = session.execute(
        select(DefPecaOperacao).where(DefPecaOperacao.def_peca_id == remate.id)
    ).scalars().all()
    assert [operacao.ordem for operacao in operacoes] == [1, 2]
    assert all(operacao.ativo is True for operacao in operacoes)


def test_seed_corrige_o_nome_de_uma_chave_que_ja_existia(session) -> None:
    _criar_operacoes_base(session)
    session.add(
        DefValuesetChave(
            codigo="MATERIAL_ENCHIMENTOS",
            nome="Enchimentos",
            descricao=None,
            tipo="MATERIAL",
            grupo="MATERIAIS",
            sistema=True,
            ativo=True,
            ordem=1,
        )
    )
    session.flush()

    result = seed_remates_guarnicoes(session)

    assert result.chaves_renomeadas == 1
    assert result.chaves_criadas == TOTAL_CHAVES - 1

    chave = session.execute(
        select(DefValuesetChave).where(
            DefValuesetChave.codigo == "MATERIAL_ENCHIMENTOS"
        )
    ).scalar_one()
    assert chave.nome == "Material Enchimentos"


def test_seed_e_idempotente(session) -> None:
    _criar_operacoes_base(session)

    seed_remates_guarnicoes(session)
    result = seed_remates_guarnicoes(session)

    assert result.chaves_criadas == 0
    assert result.chaves_renomeadas == 0
    assert result.pecas_criadas == 0
    assert result.pecas_reutilizadas == TOTAL_PECAS
    assert result.operacoes_criadas == 0

    pecas = session.execute(
        select(DefPeca).where(DefPeca.grupo == GRUPO_REMATES_GUARNICOES)
    ).scalars().all()
    assert len(pecas) == TOTAL_PECAS
