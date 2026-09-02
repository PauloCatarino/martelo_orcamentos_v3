"""Espreitadela ao PHC que alimenta o aviso diário (não escreve nada)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.models import Cliente
from app.services import cliente_phc_sync_service as service_module
from app.services.cliente_phc_sync_service import ClientePhcSyncService


def _linha(num, nome, **campos) -> dict:
    base = {
        "Num_PHC": num,
        "Nome": nome,
        "Simplex": "",
        "Morada": None,
        "Email": None,
        "WEB": None,
        "Telefone": None,
        "Telemovel": None,
        "Info_1": None,
    }
    base.update(campos)
    return base


def _phc(monkeypatch, linhas) -> None:
    monkeypatch.setattr(
        service_module.phc_sql, "query_phc_clients", lambda _s: linhas
    )


def test_deteta_novos_e_editados(monkeypatch, session) -> None:
    session.add(
        Cliente(
            nome="Igual",
            num_cliente_phc="100",
            is_temporary=False,
            source_system="phc",
        )
    )
    session.add(
        Cliente(
            nome="Nome Antigo",
            num_cliente_phc="200",
            is_temporary=False,
            source_system="phc",
        )
    )
    session.flush()
    _phc(
        monkeypatch,
        [
            _linha(100, "Igual"),
            _linha(200, "Nome Novo"),
            _linha(300, "Cliente Novo"),
        ],
    )

    diferencas = ClientePhcSyncService(session).verificar_alteracoes()

    assert diferencas.novos == ("300 — Cliente Novo",)
    assert diferencas.alterados == ("200 — Nome Novo",)
    assert diferencas.total == 2
    assert bool(diferencas) is True


def test_sem_novidades_nao_avisa(monkeypatch, session) -> None:
    session.add(
        Cliente(
            nome="Igual",
            num_cliente_phc="100",
            is_temporary=False,
            source_system="phc",
            telefone="244000000",
        )
    )
    session.flush()
    _phc(monkeypatch, [_linha(100, "Igual", Telefone="244000000")])

    diferencas = ClientePhcSyncService(session).verificar_alteracoes()

    assert diferencas.total == 0
    assert bool(diferencas) is False


def test_vazio_no_phc_e_none_no_martelo_nao_e_alteracao(monkeypatch, session) -> None:
    session.add(
        Cliente(
            nome="Igual",
            num_cliente_phc="100",
            is_temporary=False,
            source_system="phc",
            morada=None,
        )
    )
    session.flush()
    _phc(monkeypatch, [_linha(100, "Igual", Morada="   ")])

    assert ClientePhcSyncService(session).verificar_alteracoes().total == 0


def test_verificar_nao_escreve_nada(monkeypatch, session) -> None:
    _phc(monkeypatch, [_linha(300, "Cliente Novo")])

    ClientePhcSyncService(session).verificar_alteracoes()

    assert session.query(Cliente).count() == 0


def test_temporarios_nao_entram_na_comparacao(monkeypatch, session) -> None:
    # Um temporário com o mesmo número não deve mascarar um cliente novo do PHC.
    session.add(
        Cliente(
            nome="Temporário",
            num_cliente_phc="300",
            is_temporary=True,
            source_system="manual",
        )
    )
    session.flush()
    _phc(monkeypatch, [_linha(300, "Cliente Novo")])

    diferencas = ClientePhcSyncService(session).verificar_alteracoes()

    assert diferencas.novos == ("300 — Cliente Novo",)
