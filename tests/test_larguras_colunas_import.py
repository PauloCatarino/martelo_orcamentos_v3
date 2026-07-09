"""Import check for the column-width persistence helper."""

from __future__ import annotations

from types import SimpleNamespace


def test_helper_importa() -> None:
    from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras

    assert callable(ligar_persistencia_larguras)


def test_utilizador_atual_sem_sessao(monkeypatch) -> None:
    from app.core.session import app_session
    from app.ui.widgets.larguras_colunas import _utilizador_atual

    monkeypatch.setattr(app_session, "current_user", None)

    assert _utilizador_atual() == "default"


def test_utilizador_atual_com_sessao(monkeypatch) -> None:
    from app.core.session import app_session
    from app.ui.widgets.larguras_colunas import _utilizador_atual

    monkeypatch.setattr(app_session, "current_user", SimpleNamespace(username="paulo"))

    assert _utilizador_atual() == "paulo"


def test_chave_larguras_inclui_utilizador(monkeypatch) -> None:
    from app.core.session import app_session
    from app.ui.widgets.larguras_colunas import _chave_larguras

    monkeypatch.setattr(app_session, "current_user", SimpleNamespace(username="paulo"))
    assert _chave_larguras("valueset_item", 3) == "larguras/paulo/valueset_item/3"

    monkeypatch.setattr(app_session, "current_user", None)
    assert _chave_larguras("valueset_item", 3) == "larguras/default/valueset_item/3"
