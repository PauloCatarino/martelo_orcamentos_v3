"""O importador dos catálogos: repetir não faz estragos, e nada se apaga.

Uma importação corre-se muitas vezes — depois de corrigir o adaptador, quando
chega tabela nova, quando alguém não sabe se já a correu. O que estes testes
guardam é que a segunda vez é inofensiva e que o histórico de preços não se
perde pelo caminho: é dele que depende responder a «quanto subiu isto desde a
tabela do ano passado».
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.catalogos import SCHEMA_CATALOGOS, catalogos_metadata
from app.models.catalogos import (
    FornArtigo,
    FornArtigoAlias,
    FornArtigoPreco,
    FornTabelaPreco,
)
from app.services.catalogos.base import ArtigoCatalogo, TabelaCatalogo
from app.services.catalogos.importador import (
    ValorGrandeDemais,
    importar,
    importar_tabelas,
)


@pytest.fixture()
def session():
    """SQLite em memória com a base dos catálogos anexada (ver a Fase 1)."""
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _anexar(dbapi_connection, _record):  # noqa: ANN001
        dbapi_connection.execute(f"ATTACH DATABASE ':memory:' AS {SCHEMA_CATALOGOS}")

    catalogos_metadata.create_all(engine)
    try:
        with Session(engine) as db:
            yield db
    finally:
        engine.dispose()


def _artigo(espessura: str = "8mm", preco: str | None = "17.98", **extra):
    dados = dict(
        chave_natural=f"F037|ST76|PB STD|{espessura}",
        referencia="F037",
        descricao=f"EGGER F037 ST76 · Travertino Taormina · {espessura}",
        unidade="M2",
        nome_design="Travertino Taormina",
        substrato="PB STD",
        espessura_mm=Decimal(espessura.replace("mm", "")),
        acabamento="ST76",
        grupo="Grupo 8",
        preco=None if preco is None else Decimal(preco),
    )
    dados.update(extra)
    return ArtigoCatalogo(**dados)


def _tabela(*artigos, hash_="a" * 64, **extra) -> TabelaCatalogo:
    dados = dict(
        fornecedor="Balbino & Faustino",
        fabricante="EGGER",
        nome="EGGER Balbino & Faustino 2026",
        referencia_tabela="BF-82",
        data_tabela=date(2026, 4, 20),
        ficheiro_origem="12_Placas_Referencias_COMPLETO.xlsx#Stock_B&F_Egger",
        ficheiro_hash=hash_,
        unidade_preco="M2",
        artigos=artigos or (_artigo(),),
    )
    dados.update(extra)
    return TabelaCatalogo(**dados)


def _contar(session: Session, modelo) -> int:
    return session.scalar(select(func.count()).select_from(modelo))


# ---------------------------------------------------------------------------
# A primeira vez
# ---------------------------------------------------------------------------


def test_importa_a_tabela_os_artigos_e_os_precos(session: Session) -> None:
    resultado = importar(session, _tabela(_artigo("8mm"), _artigo("19mm", "21.02")))
    session.commit()

    assert not resultado.repetida
    assert resultado.artigos_novos == 2
    assert resultado.precos_novos == 2
    assert resultado.tabela_id is not None

    tabela = session.scalars(select(FornTabelaPreco)).one()
    assert tabela.fornecedor == "Balbino & Faustino"
    assert tabela.fabricante == "EGGER"
    assert tabela.referencia_tabela == "BF-82"
    assert tabela.data_tabela == date(2026, 4, 20)
    assert tabela.ativa is True
    assert tabela.importada_em is not None

    precos = session.scalars(select(FornArtigoPreco)).all()
    assert sorted(p.valor for p in precos) == [Decimal("17.98"), Decimal("21.02")]
    assert {p.unidade for p in precos} == {"M2"}
    assert {p.valido_de for p in precos} == {date(2026, 4, 20)}
    assert {p.tabela_preco_id for p in precos} == {tabela.id}


def test_os_avisos_do_adaptador_chegam_ao_resultado(session: Session) -> None:
    resultado = importar(session, _tabela(avisos=("a coluna Esp mudou de palavra",)))
    assert "a coluna Esp mudou de palavra" in resultado.avisos


def test_um_artigo_sem_preco_entra_mesmo_assim(session: Session) -> None:
    """A tabela lista o artigo e não lhe dá preço: fica o registo, sem valor."""
    importar(session, _tabela(_artigo(preco=None)))
    session.commit()

    assert session.scalars(select(FornArtigoPreco)).one().valor is None


def test_grava_os_aliases_que_o_adaptador_trouxe(session: Session) -> None:
    importar(session, _tabela(_artigo(aliases=(("EAN", "5601234567890"),))))
    session.commit()

    assert session.scalars(select(FornArtigoAlias)).one().valor == "5601234567890"


# ---------------------------------------------------------------------------
# A segunda vez
# ---------------------------------------------------------------------------


def test_reimportar_a_mesma_tabela_nao_faz_nada(session: Session) -> None:
    """É isto que permite correr a importação sem medo."""
    primeiro = importar(session, _tabela())
    session.commit()

    segundo = importar(session, _tabela())
    session.commit()

    assert segundo.repetida is True
    assert segundo.tabela_id == primeiro.tabela_id
    assert segundo.artigos_novos == 0
    assert segundo.precos_novos == 0
    assert _contar(session, FornTabelaPreco) == 1
    assert _contar(session, FornArtigo) == 1
    assert _contar(session, FornArtigoPreco) == 1


def test_tabela_nova_nao_duplica_artigos_e_acrescenta_preco(session: Session) -> None:
    """Uma atualização de preços gera só as diferenças — e guarda as duas."""
    importar(session, _tabela(_artigo(preco="17.98")))
    session.commit()

    resultado = importar(
        session,
        _tabela(_artigo(preco="18.50"), hash_="b" * 64, data_tabela=date(2026, 9, 1)),
    )
    session.commit()

    assert resultado.artigos_novos == 0
    assert resultado.artigos_inalterados == 1
    assert resultado.precos_novos == 1
    assert _contar(session, FornArtigo) == 1

    precos = session.scalars(
        select(FornArtigoPreco).order_by(FornArtigoPreco.id)
    ).all()
    assert [p.valor for p in precos] == [Decimal("17.98"), Decimal("18.50")]
    assert [p.valido_de for p in precos] == [date(2026, 4, 20), date(2026, 9, 1)]


def test_a_tabela_anterior_deixa_de_ser_a_ativa_mas_fica_ca(session: Session) -> None:
    importar(session, _tabela())
    session.commit()
    resultado = importar(session, _tabela(hash_="b" * 64))
    session.commit()

    assert resultado.tabelas_desativadas == 1
    tabelas = session.scalars(
        select(FornTabelaPreco).order_by(FornTabelaPreco.id)
    ).all()
    assert [t.ativa for t in tabelas] == [False, True]


def test_uma_descricao_corrigida_atualiza_o_artigo(session: Session) -> None:
    importar(session, _tabela())
    session.commit()

    resultado = importar(
        session,
        _tabela(_artigo(descricao="EGGER F037 ST76 · nome corrigido"), hash_="b" * 64),
    )
    session.commit()

    assert resultado.artigos_atualizados == 1
    assert resultado.artigos_novos == 0
    assert (
        session.scalars(select(FornArtigo)).one().descricao
        == "EGGER F037 ST76 · nome corrigido"
    )


def test_um_artigo_que_sai_da_tabela_nova_nao_e_apagado(session: Session) -> None:
    """O histórico de preços dele continua a valer. Nada se apaga."""
    importar(session, _tabela(_artigo("8mm"), _artigo("19mm", "21.02")))
    session.commit()

    importar(session, _tabela(_artigo("8mm"), hash_="b" * 64))
    session.commit()

    assert _contar(session, FornArtigo) == 2
    assert _contar(session, FornArtigoPreco) == 3


def test_forcar_importa_outra_vez_o_mesmo_hash(session: Session) -> None:
    """Para reimportar depois de se corrigir o adaptador.

    O ``ficheiro_hash`` é único, e é a linha antiga que tem direito ao hash
    daquele conteúdo: a forçada fica sem hash e com o hash escrito nas
    observações. Sem isto, o ``--forcar`` rebentava na restrição de unicidade —
    e a alternativa era apagar a linha antiga, o que aqui não se faz.
    """
    importar(session, _tabela())
    session.commit()

    resultado = importar(session, _tabela(), forcar=True)
    session.commit()

    assert resultado.repetida is False
    assert _contar(session, FornTabelaPreco) == 2
    assert _contar(session, FornArtigo) == 1
    assert _contar(session, FornArtigoPreco) == 2

    tabelas = session.scalars(
        select(FornTabelaPreco).order_by(FornTabelaPreco.id)
    ).all()
    assert tabelas[0].ficheiro_hash == "a" * 64
    assert tabelas[1].ficheiro_hash is None
    assert "Reimportação forçada" in (tabelas[1].observacoes or "")
    assert any("Reimportação forçada" in aviso for aviso in resultado.avisos)


# ---------------------------------------------------------------------------
# As fronteiras entre fornecedores e dentro do ficheiro
# ---------------------------------------------------------------------------


def test_a_mesma_referencia_em_dois_fornecedores_sao_dois_artigos(
    session: Session,
) -> None:
    """A B&F e a WoodSide vendem o mesmo EGGER a preços diferentes."""
    importar(session, _tabela())
    importar(
        session,
        _tabela(fornecedor="WoodSide", nome="EGGER WoodSide 2026", hash_="b" * 64),
    )
    session.commit()

    artigos = session.scalars(select(FornArtigo)).all()
    assert len(artigos) == 2
    assert {a.fornecedor for a in artigos} == {"Balbino & Faustino", "WoodSide"}


def test_o_fornecedor_de_outra_marca_nao_e_desativado(session: Session) -> None:
    """A B&F também vende Innovus: a tabela de EGGER não mexe na de Innovus."""
    importar(session, _tabela(fabricante="Innovus", nome="Innovus B&F", hash_="i" * 64))
    session.commit()

    resultado = importar(session, _tabela())
    session.commit()

    assert resultado.tabelas_desativadas == 0
    assert all(t.ativa for t in session.scalars(select(FornTabelaPreco)).all())


def test_duas_tabelas_da_mesma_marca_nao_se_desativam_uma_a_outra(
    session: Session,
) -> None:
    """A B&F vende Innovus em duas tabelas ao mesmo tempo: Brancos e Decorativos.

    Enquanto a regra foi «fornecedor + fabricante», importar a segunda desligava
    a primeira e metade dos preços de Innovus deixava de ser a que vale. O que
    identifica a tabela é o trio com o **nome** — e é por isso que o nome que o
    adaptador dá não leva o ano.
    """
    importar(
        session,
        _tabela(fabricante="Innovus", nome="Innovus Brancos E05", hash_="b" * 64),
    )
    session.commit()

    resultado = importar(
        session,
        _tabela(fabricante="Innovus", nome="Innovus Decorativos E05", hash_="d" * 64),
    )
    session.commit()

    assert resultado.tabelas_desativadas == 0
    tabelas = session.scalars(select(FornTabelaPreco)).all()
    assert len(tabelas) == 2
    assert all(t.ativa for t in tabelas)


def test_a_versao_nova_da_mesma_tabela_desativa_a_antiga(session: Session) -> None:
    importar(
        session,
        _tabela(fabricante="Innovus", nome="Innovus Brancos E05", hash_="b" * 64),
    )
    session.commit()

    resultado = importar(
        session,
        _tabela(
            fabricante="Innovus",
            nome="Innovus Brancos E05",
            hash_="b2" + "0" * 62,
            data_tabela=date(2027, 1, 15),
        ),
    )
    session.commit()

    assert resultado.tabelas_desativadas == 1
    tabelas = session.scalars(
        select(FornTabelaPreco).order_by(FornTabelaPreco.id)
    ).all()
    assert [t.ativa for t in tabelas] == [False, True]


def test_chave_natural_repetida_no_ficheiro_avisa_e_entra_uma_vez(
    session: Session,
) -> None:
    resultado = importar(session, _tabela(_artigo("8mm"), _artigo("8mm")))
    session.commit()

    assert resultado.artigos_novos == 1
    assert any("chave natural repetida" in aviso for aviso in resultado.avisos)
    assert _contar(session, FornArtigo) == 1


def test_importar_varias_tabelas_de_uma_vez(session: Session) -> None:
    resultados = importar_tabelas(
        session,
        [
            _tabela(),
            _tabela(fornecedor="WoodSide", nome="EGGER WoodSide 2026", hash_="b" * 64),
        ],
    )
    session.commit()

    assert [r.artigos_novos for r in resultados] == [1, 1]
    assert _contar(session, FornTabelaPreco) == 2


def test_um_campo_grande_demais_da_erro_que_se_percebe(session: Session) -> None:
    """Sem isto vinha um DataError do MySQL a meio de dezassete mil linhas.

    Foi mesmo o que quase aconteceu: a «Página PDF» do BLUM chega a 70
    caracteres e a coluna ``pagina`` aceita 20.
    """
    with pytest.raises(ValorGrandeDemais) as erro:
        importar(session, _tabela(_artigo(pagina="5 | 6 | 12 | 13 | 15 | 16 | 17 | 18")))

    mensagem = str(erro.value)
    assert "'pagina'" in mensagem
    assert "F037|ST76|PB STD|8mm" in mensagem
    assert "aceita 20" in mensagem


def test_uma_chave_natural_grande_demais_tambem(session: Session) -> None:
    with pytest.raises(ValorGrandeDemais, match="chave natural"):
        importar(session, _tabela(_artigo(chave_natural="x" * 301)))


def test_o_resumo_diz_o_que_aconteceu(session: Session) -> None:
    """O resumo é o que a pessoa lê no fim; tem de dizer a verdade."""
    resultado = importar(session, _tabela(_artigo("8mm"), _artigo("19mm", "21.02")))
    session.commit()
    assert "2 artigos (2 novos" in resultado.resumo()

    repetido = importar(session, _tabela())
    assert "já estava importada" in repetido.resumo()
