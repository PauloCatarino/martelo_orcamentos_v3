"""Account roles, menu defaults, and V2 import planning."""

from __future__ import annotations

import pytest

from app.models import User
from app.services.permission_service import DEFAULT_USER_PERMISSIONS, is_admin
from scripts.import_users_from_v2 import SourceUser, plan_migration


class _ScalarRows:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)


class _Session:
    def __init__(self, users):
        self.users = users

    def execute(self, _statement):
        return _ScalarRows(self.users)


def _user(username: str, email: str, role: str = "user") -> User:
    return User(
        id=1,
        username=username,
        nome=username,
        email=email,
        password_hash="hash",
        role=role,
        is_active=True,
    )


def _source(username: str, email: str | None, source_id: int = 7) -> SourceUser:
    return SourceUser(
        id=source_id,
        username=username,
        email=email,
        password_hash="bcrypt-hash",
        role="admin",
        is_active=True,
    )


def test_only_admin_role_has_full_access() -> None:
    assert is_admin(_user("admin", "admin@example.test", role="admin")) is True
    assert is_admin(_user("Paulo", "paulo@example.test", role="user")) is False


def test_normal_user_defaults_exclude_technical_configuration() -> None:
    assert DEFAULT_USER_PERMISSIONS["menu.orcamentos"] is True
    assert DEFAULT_USER_PERMISSIONS["menu.producao"] is True
    assert DEFAULT_USER_PERMISSIONS["menu.configuracoes"] is False


def test_import_keeps_existing_identity_and_forces_non_admin_to_user() -> None:
    session = _Session([_user("paulo", "projetos@lancaencanto.pt", role="admin")])
    report = plan_migration(
        session,
        [_source("Paulo", "projetos@lancaencanto.pt", source_id=2)],
        permission_count=3,
    )
    assert report.creates == 0
    assert report.updates == 1
    assert report.users[0].role == "user"


def test_import_rejects_email_owned_by_another_v3_user() -> None:
    session = _Session([_user("existing", "same@example.test")])
    with pytest.raises(ValueError, match="já pertence"):
        plan_migration(
            session,
            [_source("new-user", "same@example.test")],
            permission_count=0,
        )


# --------------------------------------------------------------------------
# Permissões de ação (criar encomendas no iMos)
# --------------------------------------------------------------------------


def test_criar_encomenda_imos_nasce_desligada() -> None:
    """As ações são opt-in: dá-se a quem precisa, não se tira a quem não deve."""
    from app.services.permission_service import (
        DEFAULT_USER_PERMISSIONS,
        PERMISSAO_CRIAR_ENCOMENDA_IMOS,
    )

    assert DEFAULT_USER_PERMISSIONS[PERMISSAO_CRIAR_ENCOMENDA_IMOS] is False
    # Ao contrário dos menus, que nascem ligados (menos as Configurações).
    assert DEFAULT_USER_PERMISSIONS["menu.producao"] is True


def test_piloto_ia_roupeiros_nasce_desligado() -> None:
    from app.services.permission_service import (
        DEFAULT_USER_PERMISSIONS,
        PERMISSAO_ASSISTENTE_IA_ROUPEIROS,
    )

    assert DEFAULT_USER_PERMISSIONS[PERMISSAO_ASSISTENTE_IA_ROUPEIROS] is False


def test_grelha_de_acessos_lista_menus_e_accoes() -> None:
    from app.services.permission_service import (
        ACAO_PERMISSIONS,
        MENU_PERMISSIONS,
        PERMISSOES_EDITAVEIS,
    )

    assert set(PERMISSOES_EDITAVEIS) == set(MENU_PERMISSIONS) | set(ACAO_PERMISSIONS)
    # Os menus vêm primeiro, para a grelha não mudar de ordem.
    assert list(PERMISSOES_EDITAVEIS)[: len(MENU_PERMISSIONS)] == list(MENU_PERMISSIONS)
    assert PERMISSOES_EDITAVEIS["acao.criar_encomenda_imos"] == "Criar encomendas no iMos"


def test_utilizador_normal_nao_cria_encomendas_por_defeito(session) -> None:
    from app.services.permission_service import (
        PERMISSAO_CRIAR_ENCOMENDA_IMOS,
        permissions_for_user,
        pode,
    )

    utilizador = _user("pedro", "pedro@le.pt")
    session.add(utilizador)
    session.flush()

    permissoes = permissions_for_user(session, utilizador)

    assert pode(permissoes, PERMISSAO_CRIAR_ENCOMENDA_IMOS) is False


def test_permissao_atribuida_passa_a_valer(session) -> None:
    from app.services.permission_service import (
        PERMISSAO_CRIAR_ENCOMENDA_IMOS,
        permissions_for_user,
        pode,
        set_user_permissions,
    )

    utilizador = _user("pedro", "pedro@le.pt")
    session.add(utilizador)
    session.flush()

    set_user_permissions(
        session, utilizador.id, {PERMISSAO_CRIAR_ENCOMENDA_IMOS: True}
    )
    session.flush()

    assert pode(
        permissions_for_user(session, utilizador), PERMISSAO_CRIAR_ENCOMENDA_IMOS
    )


def test_admin_pode_criar_sempre(session) -> None:
    from app.services.permission_service import (
        PERMISSAO_CRIAR_ENCOMENDA_IMOS,
        permissions_for_user,
        pode,
    )

    admin = _user("admin", "admin@le.pt", role="admin")

    assert pode(permissions_for_user(session, admin), PERMISSAO_CRIAR_ENCOMENDA_IMOS)


def test_sem_sessao_nao_se_pode_nada(session) -> None:
    from app.services.permission_service import (
        PERMISSAO_CRIAR_ENCOMENDA_IMOS,
        permissions_for_user,
        pode,
    )

    assert not pode(permissions_for_user(session, None), PERMISSAO_CRIAR_ENCOMENDA_IMOS)


def test_pode_e_defensivo_perante_permissoes_em_falta() -> None:
    from app.services.permission_service import pode

    assert pode(None, "acao.qualquer") is False
    assert pode({}, "acao.criar_encomenda_imos") is False
