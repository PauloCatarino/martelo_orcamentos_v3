"""Tests for the per-user piece library preferences service."""

from __future__ import annotations

from app.models import DefPecaUserPref, User
from app.services.def_peca_service import CriarDefPecaData, DefPecaService
from app.services.def_peca_user_pref_service import DefPecaUserPrefService


def _criar_user(session, username: str = "paulo") -> User:
    user = User(
        username=username,
        nome=username.title(),
        email=f"{username}@teste.pt",
        password_hash="x",
        role="user",
    )
    session.add(user)
    session.flush()
    return user


def _criar_pecas(session, quantos: int = 3) -> list[int]:
    service = DefPecaService(session)
    ids = []
    for indice in range(quantos):
        peca = service.criar_peca(
            CriarDefPecaData(
                codigo=f"PECA_{indice}",
                nome=f"Peça {indice}",
                grupo="TESTES",
                natureza="MATERIAL",
            )
        )
        ids.append(peca.id)
    return ids


def test_sem_registos_ve_tudo(session) -> None:
    user = _criar_user(session)
    pecas = _criar_pecas(session)

    prefs = DefPecaUserPrefService(session).obter_preferencias(user.id)

    assert prefs.personalizado is False
    assert all(prefs.peca_visivel(peca_id) for peca_id in pecas)


def test_sem_utilizador_ve_tudo(session) -> None:
    pecas = _criar_pecas(session)

    prefs = DefPecaUserPrefService(session).obter_preferencias(None)

    assert prefs.personalizado is False
    assert all(prefs.peca_visivel(peca_id) for peca_id in pecas)


def test_guardar_preferencias_filtra_biblioteca(session) -> None:
    user = _criar_user(session)
    pecas = _criar_pecas(session)
    service = DefPecaUserPrefService(session)

    prefs = service.guardar_preferencias(
        user.id, {pecas[0], pecas[1]}, {pecas[1]}
    )

    assert prefs.personalizado is True
    assert prefs.peca_visivel(pecas[0]) is True
    assert prefs.peca_visivel(pecas[1]) is True
    assert prefs.peca_visivel(pecas[2]) is False
    assert prefs.favoritas == {pecas[1]}

    relidas = service.obter_preferencias(user.id)
    assert relidas == prefs


def test_favorito_fica_sempre_disponivel(session) -> None:
    user = _criar_user(session)
    pecas = _criar_pecas(session)
    service = DefPecaUserPrefService(session)

    prefs = service.guardar_preferencias(user.id, {pecas[0]}, {pecas[2]})

    assert prefs.peca_visivel(pecas[2]) is True
    assert pecas[2] in prefs.selecionadas


def test_guardar_substitui_selecao_anterior(session) -> None:
    user = _criar_user(session)
    pecas = _criar_pecas(session)
    service = DefPecaUserPrefService(session)

    service.guardar_preferencias(user.id, {pecas[0], pecas[1]}, {pecas[0]})
    prefs = service.guardar_preferencias(user.id, {pecas[2]}, set())

    assert prefs.selecionadas == {pecas[2]}
    assert prefs.favoritas == frozenset()
    total = session.query(DefPecaUserPref).filter_by(user_id=user.id).count()
    assert total == 1


def test_guardar_selecao_vazia_equivale_a_repor(session) -> None:
    user = _criar_user(session)
    pecas = _criar_pecas(session)
    service = DefPecaUserPrefService(session)

    service.guardar_preferencias(user.id, {pecas[0]}, set())
    prefs = service.guardar_preferencias(user.id, set(), set())

    assert prefs.personalizado is False
    assert session.query(DefPecaUserPref).filter_by(user_id=user.id).count() == 0


def test_repor_volta_a_mostrar_tudo(session) -> None:
    user = _criar_user(session)
    pecas = _criar_pecas(session)
    service = DefPecaUserPrefService(session)

    service.guardar_preferencias(user.id, {pecas[0]}, set())
    prefs = service.repor_preferencias(user.id)

    assert prefs.personalizado is False
    assert all(prefs.peca_visivel(peca_id) for peca_id in pecas)


def test_preferencias_sao_por_utilizador(session) -> None:
    user_a = _criar_user(session, "paulo")
    user_b = _criar_user(session, "admin")
    pecas = _criar_pecas(session)
    service = DefPecaUserPrefService(session)

    service.guardar_preferencias(user_a.id, {pecas[0]}, set())

    prefs_a = service.obter_preferencias(user_a.id)
    prefs_b = service.obter_preferencias(user_b.id)

    assert prefs_a.personalizado is True
    assert prefs_a.peca_visivel(pecas[1]) is False
    assert prefs_b.personalizado is False
    assert prefs_b.peca_visivel(pecas[1]) is True
