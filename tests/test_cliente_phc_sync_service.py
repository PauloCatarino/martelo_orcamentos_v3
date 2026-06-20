"""Tests for the PHC sync service (phase 10.5.1)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Cliente
from app.services import cliente_phc_sync_service as service_module
from app.services.cliente_phc_sync_service import ClientePhcSyncService


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_sincronizar_cria_e_atualiza(monkeypatch) -> None:
    session = _session()
    # já existe um PHC (num 100) e um temporário (não deve ser tocado)
    session.add(Cliente(nome="Antigo", num_cliente_phc="100", is_temporary=False, source_system="phc"))
    session.add(Cliente(nome="Temp", is_temporary=True, source_system="manual"))
    session.flush()

    def _fake_query(_session):
        return [
            {"Num_PHC": 100, "Nome": "Novo Nome", "Simplex": "NN", "Morada": None,
             "Email": None, "WEB": None, "Telemovel": None, "Telefone": None, "Info_1": None},
            {"Num_PHC": 200, "Nome": "Outro", "Simplex": "", "Morada": None,
             "Email": None, "WEB": None, "Telemovel": None, "Telefone": None, "Info_1": None},
            {"Num_PHC": None, "Nome": "Sem Num", "Simplex": "X"},  # ignorado
        ]
    monkeypatch.setattr(service_module.phc_sql, "query_phc_clients", _fake_query)

    resumo = ClientePhcSyncService(session).sincronizar()

    assert resumo.total_phc == 3
    assert resumo.criados == 1
    assert resumo.atualizados == 1
    assert resumo.ignorados == 1

    # cliente 200 criado como PHC; 100 atualizado; temporário intacto
    criado = session.query(Cliente).filter_by(num_cliente_phc="200").one()
    assert criado.is_temporary is False and criado.source_system == "phc"
    atualizado = session.query(Cliente).filter_by(num_cliente_phc="100").one()
    assert atualizado.nome == "Novo Nome"
    assert session.query(Cliente).filter_by(is_temporary=True).count() == 1
