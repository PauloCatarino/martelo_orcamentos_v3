"""No "Importar Modelo ValueSet", o separador Utilizador é só de quem entrou.

Relatado pelo Paulo (2026-08-05): com sessão de `paulo`, a lista mostrava
também o modelo do `admin`. O diálogo chamava um `listar_modelos_utilizador()`
que, apesar do nome, devolvia os modelos não-globais de toda a gente.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _modelo(id_: int, codigo: str, user_id: int | None, *, ambito="UTILIZADOR"):
    return SimpleNamespace(
        id=id_,
        codigo=codigo,
        nome=codigo,
        descricao="",
        observacoes="",
        tipo="ROUPEIRO",
        ambito=ambito,
        user_id=user_id,
        username="",
        visivel_para_todos=ambito == "GLOBAL",
        ativo=True,
    )


# Como no print do Paulo: dois modelos dele (id 7) e um do admin (id 1).
MODELOS = [
    _modelo(1, "ROUP_STANDARD", 7),
    _modelo(2, "ROUP_STD", 7),
    _modelo(3, "ROUPEIRO_INOV_POSITIVA", 1),
    _modelo(4, "PARA_TODOS", 1, ambito="GLOBAL"),
]


def _abrir_dialogo(monkeypatch, _app, *, user_id: int | None):
    """O diálogo a sério, com o serviço verdadeiro sobre dados de teste."""
    from app.services import def_valueset_modelo_service as service_module
    from app.ui.dialogs import importar_valueset_modelo_dialog as modulo

    class _FakeSession:
        def __enter__(self):
            return None

        def __exit__(self, *_args):
            return False

    class _FakeRepository:
        def __init__(self, session=None):
            pass

        def list_active(self):
            return list(MODELOS)

    monkeypatch.setattr(modulo, "SessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(
        service_module, "DefValuesetModeloRepository", _FakeRepository
    )
    monkeypatch.setattr(
        modulo.app_session, "current_user", SimpleNamespace(id=user_id), raising=False
    )
    return modulo.ImportarValuesetModeloDialog()


def _codigos(dialogo, aba: str) -> list[str]:
    return [modelo.codigo for modelo in dialogo._abas[aba]["modelos"]]


def test_utilizador_ve_so_os_seus(monkeypatch, _app) -> None:
    dialogo = _abrir_dialogo(monkeypatch, _app, user_id=7)

    assert _codigos(dialogo, "user") == ["ROUP_STANDARD", "ROUP_STD"]


def test_o_modelo_do_administrador_nao_aparece(monkeypatch, _app) -> None:
    dialogo = _abrir_dialogo(monkeypatch, _app, user_id=7)

    assert "ROUPEIRO_INOV_POSITIVA" not in _codigos(dialogo, "user")


def test_os_globais_continuam_a_aparecer_a_todos(monkeypatch, _app) -> None:
    # O que é para toda a gente vive no separador "Global" — e continua lá.
    dialogo = _abrir_dialogo(monkeypatch, _app, user_id=7)

    assert _codigos(dialogo, "global") == ["PARA_TODOS"]


def test_o_administrador_tambem_ve_so_os_seus(monkeypatch, _app) -> None:
    # Aqui importa-se para um orçamento; a gestão dos modelos de todos faz-se
    # na página Modelos ValueSet, que é outra coisa.
    dialogo = _abrir_dialogo(monkeypatch, _app, user_id=1)

    assert _codigos(dialogo, "user") == ["ROUPEIRO_INOV_POSITIVA"]


def test_sem_sessao_o_separador_fica_vazio(monkeypatch, _app) -> None:
    dialogo = _abrir_dialogo(monkeypatch, _app, user_id=None)

    assert _codigos(dialogo, "user") == []
    assert _codigos(dialogo, "global") == ["PARA_TODOS"]
