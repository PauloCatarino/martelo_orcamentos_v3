"""Tests for the hardware sub-family tidy-up seed."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.peca_natureza_types import FERRAGEM, NEUTRA
from app.domain.peca_subgrupo_types import (
    GRUPO_FERRAGENS,
    SUBGRUPOS_FERRAGENS,
    get_subgrupo_options,
    normalize_subgrupo,
)
from app.domain.peca_types import SIMPLES
from app.models import DefPeca
from scripts.organizar_subfamilias_ferragens import (
    GRUPOS_QUE_VIRAM_SUBFAMILIA,
    SUBFAMILIA_POR_CODIGO,
    organizar_subfamilias,
)


def _criar_peca(session, codigo: str, grupo: str) -> None:
    session.add(
        DefPeca(
            codigo=codigo,
            nome=codigo.title(),
            grupo=grupo,
            tipo_peca=SIMPLES,
            natureza=FERRAGEM,
            orientacao=NEUTRA,
            ativo=True,
        )
    )


def _peca(session, codigo: str) -> DefPeca:
    return session.execute(
        select(DefPeca).where(DefPeca.codigo == codigo)
    ).scalar_one()


def test_subfamilias_do_seed_sao_conhecidas() -> None:
    # Nenhuma sub-familia do seed pode ser inventada fora da lista do domínio.
    usadas = set(SUBFAMILIA_POR_CODIGO.values()) | set(
        GRUPOS_QUE_VIRAM_SUBFAMILIA.values()
    )
    assert usadas <= set(SUBGRUPOS_FERRAGENS)


def test_normalize_subgrupo() -> None:
    assert normalize_subgrupo("  dobradicas  ") == "DOBRADICAS"
    assert normalize_subgrupo("sistemas   correr") == "SISTEMAS CORRER"
    assert normalize_subgrupo("   ") is None
    assert normalize_subgrupo(None) is None


def test_opcoes_de_subgrupo() -> None:
    assert get_subgrupo_options(GRUPO_FERRAGENS) == SUBGRUPOS_FERRAGENS
    # Um grupo sem lista própria recebe as mesmas sugestões.
    assert get_subgrupo_options("LATERAIS") == SUBGRUPOS_FERRAGENS


def test_seed_arruma_ferragens_e_traz_os_grupos(session) -> None:
    _criar_peca(session, "DOBRADICA", GRUPO_FERRAGENS)
    _criar_peca(session, "VARAO", GRUPO_FERRAGENS)
    _criar_peca(session, "FITA_LED", "ILUMINACAO")
    _criar_peca(session, "RODAS_PORTA_CORRER_SUP", "SISTEMAS_CORRER")
    session.flush()

    result = organizar_subfamilias(session)

    assert result.ferragens_arrumadas == 2
    assert result.pecas_movidas_de_grupo == 2
    assert result.ja_arrumadas == 0
    # Os códigos do mapa que não existem nesta base são apenas ignorados.
    assert "PES" in result.codigos_em_falta

    assert _peca(session, "DOBRADICA").subgrupo == "DOBRADICAS"
    assert _peca(session, "VARAO").subgrupo == "ROUPEIROS"

    fita = _peca(session, "FITA_LED")
    assert (fita.grupo, fita.subgrupo) == (GRUPO_FERRAGENS, "ILUMINACAO")

    rodas = _peca(session, "RODAS_PORTA_CORRER_SUP")
    assert (rodas.grupo, rodas.subgrupo) == (GRUPO_FERRAGENS, "SISTEMAS CORRER")


def test_seed_nao_escreve_por_cima_do_que_foi_arrumado_a_mao(session) -> None:
    _criar_peca(session, "DOBRADICA", GRUPO_FERRAGENS)
    session.flush()
    _peca(session, "DOBRADICA").subgrupo = "COZINHAS"
    session.flush()

    result = organizar_subfamilias(session)

    assert result.ferragens_arrumadas == 0
    assert result.ja_arrumadas == 1
    assert _peca(session, "DOBRADICA").subgrupo == "COZINHAS"


def test_seed_e_idempotente(session) -> None:
    _criar_peca(session, "PUXADOR", GRUPO_FERRAGENS)
    _criar_peca(session, "CALHA_LED", "ILUMINACAO")
    session.flush()

    organizar_subfamilias(session)
    result = organizar_subfamilias(session)

    assert result.ferragens_arrumadas == 0
    assert result.pecas_movidas_de_grupo == 0
    assert _peca(session, "PUXADOR").subgrupo == "PUXADORES"
    assert _peca(session, "CALHA_LED").grupo == GRUPO_FERRAGENS
