from sqlalchemy import select

from app.domain.peca_funcao_types import FERRAGEM as FUNCAO_FERRAGEM
from app.domain.peca_natureza_types import FERRAGEM as NATUREZA_FERRAGEM, NEUTRA
from app.domain.peca_types import SIMPLES
from app.models import DefPeca, DefValuesetChave
from scripts.create_tulha import CHAVE_TULHA, PECA_TULHA, seed_tulha


def _peca(session) -> DefPeca:
    return session.execute(
        select(DefPeca).where(DefPeca.codigo == PECA_TULHA)
    ).scalar_one()


def test_seed_cria_chave_e_peca_tulha(session) -> None:
    result = seed_tulha(session)

    assert result.chave_criada is True
    assert result.peca_criada is True
    chave = session.execute(
        select(DefValuesetChave).where(DefValuesetChave.codigo == CHAVE_TULHA)
    ).scalar_one()
    assert (chave.nome, chave.tipo, chave.grupo) == (
        "Tulha",
        "FERRAGEM",
        "FERRAGENS",
    )
    assert chave.sistema is True
    assert chave.ativo is True

    peca = _peca(session)
    assert peca.nome == "Tulha Gaveta"
    assert peca.nome_biblioteca == "Tulha Gaveta"
    assert (peca.grupo, peca.subgrupo) == ("FERRAGENS", "COZINHAS")
    assert peca.tipo_peca == SIMPLES
    assert peca.natureza == NATUREZA_FERRAGEM
    assert peca.orientacao == NEUTRA
    assert peca.funcao == FUNCAO_FERRAGEM
    assert peca.usa_orlas is False
    assert peca.chave_valueset_material == CHAVE_TULHA
    assert peca.permite_acabamento is False
    assert peca.sem_material is False
    assert peca.ativo is True


def test_seed_e_idempotente(session) -> None:
    seed_tulha(session)
    result = seed_tulha(session)

    assert result.chave_criada is False
    assert result.peca_criada is False
    assert result.peca_reutilizada is True
    assert result.chave_peca_corrigida is False
    assert len(session.execute(select(DefValuesetChave)).scalars().all()) == 1
    assert len(session.execute(select(DefPeca)).scalars().all()) == 1


def test_seed_corrige_apenas_a_chave_de_uma_tulha_existente(session) -> None:
    session.add(
        DefPeca(
            codigo=PECA_TULHA,
            nome="Tulha personalizada",
            grupo="FERRAGENS",
            subgrupo="COZINHAS",
            tipo_peca=SIMPLES,
            natureza=NATUREZA_FERRAGEM,
            orientacao=NEUTRA,
            funcao=FUNCAO_FERRAGEM,
            usa_orlas=False,
            chave_valueset_material="FERRAGEM_OUTRA",
            permite_acabamento=False,
            sem_material=False,
            ativo=True,
        )
    )
    session.flush()

    result = seed_tulha(session)

    assert result.peca_reutilizada is True
    assert result.chave_peca_corrigida is True
    assert _peca(session).nome == "Tulha personalizada"
    assert _peca(session).chave_valueset_material == CHAVE_TULHA
