"""Administrative user-management operations."""

from __future__ import annotations

from dataclasses import dataclass

from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.departamentos import normalizar_departamento
from app.models import User
from app.services.permission_service import MENU_PERMISSIONS, permissions_for_user, set_user_permissions


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass(frozen=True)
class ManagedUser:
    id: int
    username: str
    nome: str
    email: str
    role: str
    departamento: str
    is_active: bool
    permissions: dict[str, bool]


def list_managed_users(session: Session) -> list[ManagedUser]:
    users = session.execute(select(User).order_by(func.lower(User.username))).scalars()
    return [
        ManagedUser(
            id=user.id,
            username=user.username,
            nome=user.nome,
            email=user.email,
            role=user.role,
            departamento=normalizar_departamento(user.departamento),
            is_active=user.is_active,
            permissions=permissions_for_user(session, user),
        )
        for user in users
    ]


def create_user(
    session: Session,
    *,
    username: str,
    nome: str,
    email: str,
    password: str,
    departamento: str = "",
) -> User:
    username = username.strip()
    nome = nome.strip()
    email = email.strip().lower()
    if not username or not nome or not email or not password:
        raise ValueError("Preencha todos os campos.")
    if len(password) < 8:
        raise ValueError("A palavra-passe deve ter pelo menos 8 caracteres.")
    if "@" not in email:
        raise ValueError("Introduza um email válido.")
    duplicate = session.execute(
        select(User).where(
            (func.lower(User.username) == username.casefold())
            | (func.lower(User.email) == email.casefold())
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise ValueError("Já existe um utilizador com esse username ou email.")

    user = User(
        username=username,
        nome=nome,
        email=email,
        password_hash=pwd_context.hash(password),
        role="user",
        departamento=normalizar_departamento(departamento) or None,
        is_active=True,
    )
    session.add(user)
    session.flush()
    set_user_permissions(
        session,
        user.id,
        {key: key != "menu.configuracoes" for key in MENU_PERMISSIONS},
    )
    session.commit()
    return user


def update_user_access(
    session: Session,
    *,
    user_id: int,
    is_active: bool,
    permissions: dict[str, bool],
    departamento: str | None = None,
) -> None:
    user = session.get(User, user_id)
    if user is None:
        raise ValueError("Utilizador não encontrado.")
    if departamento is not None:
        # Texto livre: o combo sugere valores mas aceita areas novas.
        user.departamento = normalizar_departamento(departamento) or None
    if user.username.casefold() == "admin":
        user.role = "admin"
        user.is_active = True
        permissions = {key: True for key in MENU_PERMISSIONS}
    else:
        user.role = "user"
        user.is_active = bool(is_active)
    set_user_permissions(session, user.id, permissions)


def reset_password(session: Session, user_id: int, password: str) -> None:
    if len(password) < 8:
        raise ValueError("A palavra-passe deve ter pelo menos 8 caracteres.")
    user = session.get(User, user_id)
    if user is None:
        raise ValueError("Utilizador não encontrado.")
    user.password_hash = pwd_context.hash(password)
    session.commit()
