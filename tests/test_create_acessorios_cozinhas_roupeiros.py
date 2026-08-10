"""Testes do seed de acessórios para cozinhas e roupeiros."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.peca_funcao_types import FERRAGEM as FUNCAO_FERRAGEM
from app.domain.peca_natureza_types import FERRAGEM as NATUREZA_FERRAGEM, NEUTRA
from app.domain.peca_types import SIMPLES
from app.models import DefPeca, DefValuesetChave
from scripts.create_acessorios_cozinhas_roupeiros import (
    CHAVES,
    CHAVE_ACESSORIOS_COZINHA,
    CHAVE_ACESSORIOS_ROUPEIROS,
    CHAVE_BALDE_LIXO,
    CHAVE_CANTOS,
    CHAVE_PORTA_TALHERES,
    PECAS,
    seed_acessorios_cozinhas_roupeiros,
)


def _peca(session, codigo: str) -> DefPeca:
    return session.execute(
        select(DefPeca).where(DefPeca.codigo == codigo)
    ).scalar_one()


def test_seed_tem_as_cinco_chaves_e_as_seis_pecas_pedidas() -> None:
    assert {seed.codigo for seed in CHAVES} == {
        CHAVE_BALDE_LIXO,
        CHAVE_CANTOS,
        CHAVE_PORTA_TALHERES,
        CHAVE_ACESSORIOS_COZINHA,
        CHAVE_ACESSORIOS_ROUPEIROS,
    }
    assert {seed.nome for seed in PECAS} == {
        "Balde Lixo",
        "Porta Talheres",
        "Cantos",
        "Fundo Alumínio",
        "Grelha Veludo",
        "Porta Calças",
    }
    assert len({seed.codigo for seed in PECAS}) == 6


def test_seed_cria_chaves_e_pecas_com_as_ligacoes_certas(session) -> None:
    result = seed_acessorios_cozinhas_roupeiros(session)

    assert result.chaves_criadas == 5
    assert result.chaves_reutilizadas == 0
    assert result.pecas_criadas == 6
    assert result.pecas_reutilizadas == 0
    assert result.pecas_corrigidas == 0

    chaves = session.execute(select(DefValuesetChave)).scalars().all()
    assert {chave.codigo for chave in chaves} == {seed.codigo for seed in CHAVES}
    assert all(
        (chave.tipo, chave.grupo, chave.sistema, chave.ativo)
        == ("FERRAGEM", "FERRAGENS", True, True)
        for chave in chaves
    )
    assert [chave.ordem for chave in chaves] == [1, 2, 3, 4, 5]

    for seed in PECAS:
        peca = _peca(session, seed.codigo)
        assert peca.nome == seed.nome
        assert (peca.grupo, peca.subgrupo) == ("FERRAGENS", seed.subfamilia)
        assert peca.chave_valueset_material == seed.chave_material
        assert peca.tipo_peca == SIMPLES
        assert peca.natureza == NATUREZA_FERRAGEM
        assert peca.orientacao == NEUTRA
        assert peca.funcao == FUNCAO_FERRAGEM
        assert peca.usa_orlas is False
        assert peca.permite_acabamento is False
        assert peca.sem_material is False
        assert peca.ativo is True


def test_fundo_e_acessorios_de_roupeiro_usam_chaves_genericas(session) -> None:
    seed_acessorios_cozinhas_roupeiros(session)

    assert (
        _peca(session, "ACESSORIOS_FUNDO_ALUMINIO").chave_valueset_material
        == CHAVE_ACESSORIOS_COZINHA
    )
    for codigo in ("ACESSORIOS_GRELHA_VELUDO", "ACESSORIOS_PORTA_CALCAS"):
        peca = _peca(session, codigo)
        assert peca.subgrupo == "ROUPEIROS"
        assert peca.chave_valueset_material == CHAVE_ACESSORIOS_ROUPEIROS


def test_seed_aproveita_e_corrige_balde_lixo_ja_existente(session) -> None:
    session.add(
        DefPeca(
            codigo="ACESSORIOS_BALDE_LIXO",
            nome="Balde Lixo",
            descricao="Definição criada anteriormente no V3.",
            grupo="FERRAGENS",
            subgrupo="COZINHAS",
            tipo_peca=SIMPLES,
            natureza=NATUREZA_FERRAGEM,
            orientacao=NEUTRA,
            funcao=FUNCAO_FERRAGEM,
            usa_orlas=False,
            chave_valueset_material="FERRAGEM_GRAMPAS_RODAPE",
            permite_acabamento=False,
            sem_material=False,
            ativo=True,
        )
    )
    session.flush()

    result = seed_acessorios_cozinhas_roupeiros(session)

    assert result.pecas_criadas == 5
    assert result.pecas_reutilizadas == 1
    assert result.pecas_corrigidas == 1
    baldes = session.execute(
        select(DefPeca).where(DefPeca.nome == "Balde Lixo")
    ).scalars().all()
    assert len(baldes) == 1
    assert baldes[0].codigo == "ACESSORIOS_BALDE_LIXO"
    assert baldes[0].chave_valueset_material == CHAVE_BALDE_LIXO


def test_seed_e_idempotente(session) -> None:
    seed_acessorios_cozinhas_roupeiros(session)
    result = seed_acessorios_cozinhas_roupeiros(session)

    assert result.chaves_criadas == 0
    assert result.chaves_reutilizadas == 5
    assert result.pecas_criadas == 0
    assert result.pecas_reutilizadas == 6
    assert result.pecas_corrigidas == 0
    assert len(session.execute(select(DefValuesetChave)).scalars().all()) == 5
    assert len(session.execute(select(DefPeca)).scalars().all()) == 6
