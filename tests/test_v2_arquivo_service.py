from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text

from app.services.v2_arquivo_service import (
    V2ArquivoService,
    V2ArquivoWriteError,
    V2PrecoProtegidoError,
    _bloquear_escrita,
    _bloquear_operacoes_nao_controladas,
)


@pytest.fixture()
def engine():
    eng = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with eng.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE orcamentos ("
                "id INTEGER PRIMARY KEY, num_orcamento TEXT, versao TEXT, "
                "cliente TEXT, ref_cliente TEXT, obra TEXT, descricao TEXT, "
                "estado TEXT, data TEXT, preco_total NUMERIC, utilizador TEXT, "
                "enc_phc TEXT, preco_manual INTEGER)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO orcamentos VALUES "
                "(1, '260701', '01', 'Manual', 'R1', 'Obra', 'Desc', "
                "'Enviado', '2026-07-14', 100.00, 'ana', NULL, 1), "
                "(2, '260702', '01', 'Custeio', 'R2', 'Obra', 'Desc', "
                "'Enviado', '2026-07-14', 200.00, 'ana', NULL, 0)"
            )
        )
    try:
        yield eng
    finally:
        eng.dispose()


def test_lista_mapeia_enc_phc_e_origem_do_preco(engine):
    itens = V2ArquivoService(engine).listar_orcamentos()

    assert len(itens) == 2
    assert itens[0].origem_preco == "manual"
    assert itens[0].preco_editavel is True
    assert itens[1].origem_preco == "custeio"
    assert itens[1].preco_editavel is False


def test_sem_flag_expresso_protege_orcamento_com_items():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE orcamentos (id INTEGER PRIMARY KEY, num_orcamento TEXT, "
                    "versao TEXT, status TEXT, preco_total NUMERIC, enc_phc TEXT)"
                )
            )
            connection.execute(
                text(
                    "CREATE TABLE orcamento_items (id_item INTEGER PRIMARY KEY, "
                    "id_orcamento INTEGER)"
                )
            )
            connection.execute(
                text("INSERT INTO orcamentos VALUES (1, '260703', '01', 'Enviado', 300, NULL)")
            )
            connection.execute(text("INSERT INTO orcamento_items VALUES (10, 1)"))

        item = V2ArquivoService(engine).listar_orcamentos()[0]
        assert item.origem_preco == "custeio"
        assert item.origem_preco_inferida is True
        assert item.preco_editavel is False
    finally:
        engine.dispose()


def test_preco_de_custeio_fica_protegido(engine):
    itens = V2ArquivoService(engine).listar_orcamentos()
    custeio = next(item for item in itens if item.numero == "260702")

    with pytest.raises(V2PrecoProtegidoError, match="custeio"):
        V2ArquivoService(engine).atualizar_orcamento(
            custeio,
            estado="Adjudicado",
            enc_phc="1002",
            total=Decimal("250.00"),
        )


def test_preco_manual_estado_e_enc_sao_atualizados(engine):
    service = V2ArquivoService(engine)
    manual = next(item for item in service.listar_orcamentos() if item.numero == "260701")

    service.atualizar_orcamento(
        manual,
        estado="Adjudicado",
        enc_phc="1001",
        total=Decimal("125.50"),
    )

    atualizado = next(item for item in service.listar_orcamentos() if item.numero == "260701")
    assert atualizado.estado == "Adjudicado"
    assert atualizado.enc_phc == "1001"
    assert Decimal(str(atualizado.total)) == Decimal("125.5")


def test_concorrencia_nao_sobrescreve_alteracao_intermedia(engine):
    service = V2ArquivoService(engine)
    manual = next(item for item in service.listar_orcamentos() if item.numero == "260701")
    with engine.begin() as connection:
        connection.execute(text("UPDATE orcamentos SET estado='Cancelado' WHERE id=1"))

    with pytest.raises(V2ArquivoWriteError, match="mudou entretanto"):
        service.atualizar_orcamento(
            manual,
            estado="Adjudicado",
            enc_phc="1001",
            total=Decimal("125.50"),
        )


@pytest.mark.parametrize("sql", ["INSERT INTO x VALUES (1)", "DELETE FROM x", "DROP TABLE x"])
def test_ligacao_readonly_bloqueia_escrita(sql: str):
    with pytest.raises(PermissionError, match="apenas de leitura"):
        _bloquear_escrita(None, None, sql, None, None, False)


def test_ligacao_de_transicao_so_permite_update():
    _bloquear_operacoes_nao_controladas(None, None, "UPDATE orcamentos SET estado=?", None, None, False)
    with pytest.raises(PermissionError, match="atualizações controladas"):
        _bloquear_operacoes_nao_controladas(None, None, "DELETE FROM orcamentos", None, None, False)
