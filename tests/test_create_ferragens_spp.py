"""Tests for the SPP profiles (ML hardware) seed script."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.domain.peca_natureza_types import CONJUNTO, FERRAGEM, MATERIAL, NEUTRA
from app.domain.peca_subgrupo_types import GRUPO_FERRAGENS, SUBGRUPOS_FERRAGENS
from app.domain.peca_types import COMPOSTA, SIMPLES
from app.domain.regras_quantidade_expr import avaliar_regra_quantidade
from app.models import DefPeca, DefPecaComponente, DefRegraQuantidade, DefValuesetChave
from scripts.create_ferragens_spp import (
    CHAVES,
    CONJUNTOS,
    PECAS,
    REGRAS,
    seed_ferragens_spp,
)


def _peca(session, codigo: str) -> DefPeca:
    return session.execute(
        select(DefPeca).where(DefPeca.codigo == codigo)
    ).scalar_one()


def _componentes(session, codigo: str) -> list[DefPecaComponente]:
    pai = _peca(session, codigo)
    return list(
        session.execute(
            select(DefPecaComponente)
            .where(DefPecaComponente.def_peca_pai_id == pai.id)
            .order_by(DefPecaComponente.ordem)
        ).scalars()
    )


def test_seed_constants() -> None:
    codigos = [seed.codigo for seed in PECAS] + [seed.codigo for seed in CONJUNTOS]

    assert len(codigos) == len(set(codigos))
    assert {seed.chave for seed in PECAS} == {seed.codigo for seed in CHAVES}
    # Cada sub-familia usada tem de ser uma das conhecidas.
    usadas = {seed.subfamilia for seed in PECAS} | {
        seed.subfamilia for seed in CONJUNTOS
    }
    assert usadas <= set(SUBGRUPOS_FERRAGENS)


def test_regras_calculam_o_que_esta_escrito() -> None:
    por_codigo = {seed.codigo: seed.expressao for seed in REGRAS}

    # 2 terminais por perfil, seja qual for o comprimento.
    assert avaliar_regra_quantidade(
        por_codigo["TERMINAIS_PERFIL_LL"], {"COMP": Decimal("3000")}
    ) == (2, None)

    # 2 grampas por cada 650 mm (ou fração).
    grampas = por_codigo["GRAMPAS_RODAPE_650"]
    assert avaliar_regra_quantidade(grampas, {"COMP": Decimal("650")}) == (2, None)
    assert avaliar_regra_quantidade(grampas, {"COMP": Decimal("651")}) == (4, None)
    assert avaliar_regra_quantidade(grampas, {"COMP": Decimal("1300")}) == (4, None)
    assert avaliar_regra_quantidade(grampas, {"COMP": Decimal("2000")}) == (8, None)

    # Os esquadros do puxador de gola seguem a mesma conta.
    esquadros = por_codigo["ESQUADROS_PUX_GOLA_650"]
    assert avaliar_regra_quantidade(esquadros, {"COMP": Decimal("1300")}) == (4, None)


def test_seed_cria_chaves_regras_e_ferragens(session) -> None:
    result = seed_ferragens_spp(session)

    assert result.chaves_criadas == len(CHAVES)
    assert result.regras_criadas == len(REGRAS)
    assert result.pecas_criadas == len(PECAS)
    assert result.conjuntos_criados == len(CONJUNTOS)
    assert result.componentes_criados == 2 * len(CONJUNTOS)
    assert result.reutilizados == 0

    for seed in CHAVES:
        chave = session.execute(
            select(DefValuesetChave).where(DefValuesetChave.codigo == seed.codigo)
        ).scalar_one()
        assert (chave.tipo, chave.grupo) == ("FERRAGEM", "FERRAGENS")

    for seed in REGRAS:
        assert session.execute(
            select(DefRegraQuantidade).where(
                DefRegraQuantidade.codigo == seed.codigo
            )
        ).scalar_one().ativo is True


def test_perfis_ao_metro_sao_pecas_fisicas(session) -> None:
    seed_ferragens_spp(session)

    for codigo in ("PERFIL_LL", "RODAPE_PVC/ALUM", "PUX_GOLA_C", "PUX_GOLA_J"):
        perfil = _peca(session, codigo)
        # Como o varão: leva comprimento e paga-se ao metro linear.
        assert perfil.natureza == MATERIAL
        assert perfil.tipo_peca == SIMPLES
        assert perfil.orientacao == NEUTRA
        assert perfil.grupo == GRUPO_FERRAGENS
        assert perfil.sem_material is False
        assert perfil.chave_valueset_material is not None
        assert "{SPP}" in (perfil.nome_biblioteca or "")

    # As que se contam à unidade não são peças físicas.
    for codigo in (
        "TERMINAIS_PERFIL_LL",
        "GRAMPAS_RDP",
        "CANTO_RDP_PVC",
        "ESQUADRO_L_PUX_GOLA",
    ):
        assert _peca(session, codigo).natureza == FERRAGEM


def test_subfamilias_das_ferragens_novas(session) -> None:
    seed_ferragens_spp(session)

    assert _peca(session, "PERFIL_LL").subgrupo == "COZINHAS"
    assert _peca(session, "RODAPE_PVC/ALUM").subgrupo == "COZINHAS"
    assert _peca(session, "CANTO_RDP_PVC").subgrupo == "COZINHAS"
    assert _peca(session, "PUX_GOLA_C").subgrupo == "PUXADORES"
    assert _peca(session, "ESQUADRO_L_PUX_GOLA").subgrupo == "PUXADORES"


def test_conjunto_do_perfil_lava_louca(session) -> None:
    seed_ferragens_spp(session)

    conjunto = _peca(session, "PERFIL_LL+TERMINAIS")
    assert conjunto.tipo_peca == COMPOSTA
    assert conjunto.natureza == CONJUNTO
    assert conjunto.sem_material is True

    perfil, terminais = _componentes(session, "PERFIL_LL+TERMINAIS")
    # O perfil traz a medida do módulo; é dele que a regra lê o COMP.
    assert perfil.formula_comp == "LM"
    assert perfil.quantidade == Decimal("1.000")
    assert perfil.def_regra_quantidade_id is None
    assert terminais.quantidade == Decimal("2.000")
    assert terminais.def_regra_quantidade_id is not None


def test_conjuntos_do_rodape_e_das_golas(session) -> None:
    seed_ferragens_spp(session)

    regras_por_id = {
        regra.id: regra.codigo
        for regra in session.execute(select(DefRegraQuantidade)).scalars()
    }

    rodape, grampas = _componentes(session, "RODAPE_PVC/ALUM+GRAMPAS")
    assert rodape.formula_comp == "LM"
    assert regras_por_id[grampas.def_regra_quantidade_id] == "GRAMPAS_RODAPE_650"

    for codigo_conjunto in ("PUX_GOLA_C+L", "PUX_GOLA_J+L"):
        gola, esquadros = _componentes(session, codigo_conjunto)
        assert gola.formula_comp == "LM"
        assert (
            regras_por_id[esquadros.def_regra_quantidade_id]
            == "ESQUADROS_PUX_GOLA_650"
        )


def test_seed_e_idempotente(session) -> None:
    seed_ferragens_spp(session)
    result = seed_ferragens_spp(session)

    assert result.chaves_criadas == 0
    assert result.regras_criadas == 0
    assert result.pecas_criadas == 0
    assert result.conjuntos_criados == 0
    assert result.componentes_criados == 0
    assert result.reutilizados == len(PECAS) + len(CONJUNTOS)

    assert len(_componentes(session, "PERFIL_LL+TERMINAIS")) == 2
