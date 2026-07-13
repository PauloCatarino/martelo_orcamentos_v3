from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from app.services.v2_arquivo_service import V2ArquivoService, _bloquear_escrita


def test_adaptador_descobre_tabela_e_mapeia_sem_escrever() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE orcamentos (num_orcamento TEXT, versao TEXT, cliente TEXT, "
            "ref_cliente TEXT, obra TEXT, descricao TEXT, estado TEXT, data TEXT, "
            "preco_total NUMERIC, utilizador TEXT)"
        ))
        conn.execute(text(
            "INSERT INTO orcamentos VALUES ('25001','02','Cliente','REF','Obra',"
            "'Descrição','Adjudicado','2025-05-01',123.45,'maria')"
        ))

    itens = V2ArquivoService(engine).listar_orcamentos()
    assert len(itens) == 1
    assert itens[0].numero == "25001"
    assert itens[0].cliente == "Cliente"
    assert itens[0].tabela_origem == "orcamentos"


@pytest.mark.parametrize("sql", ["INSERT INTO x VALUES (1)", "UPDATE x SET a=1", "DELETE FROM x", "DROP TABLE x"])
def test_guarda_read_only_bloqueia_escrita(sql: str) -> None:
    with pytest.raises(PermissionError, match="apenas de leitura"):
        _bloquear_escrita(None, None, sql, None, None, False)


@pytest.mark.parametrize("sql", ["SELECT 1", "SHOW TABLES", "DESCRIBE x", "WITH x AS (SELECT 1) SELECT * FROM x"])
def test_guarda_read_only_permite_consulta(sql: str) -> None:
    _bloquear_escrita(None, None, sql, None, None, False)
