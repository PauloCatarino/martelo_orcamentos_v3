"""Create or update the initial application users."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402


ADMIN_USERNAME = "admin"
ADMIN_NOME = "Administrador Martelo"
ADMIN_EMAIL = "admin@martelo.local"
ADMIN_ROLE = "admin"
ADMIN_PASSWORD_ENV = "ADMIN_INITIAL_PASSWORD"
DEFAULT_ADMIN_PASSWORD = "admin"

PAULO_USERNAME = "paulo"
PAULO_NOME = "Paulo Catarino"
PAULO_EMAIL = "projetos@lancaencanto.pt"
PAULO_ROLE = "user"
PAULO_PASSWORD_ENV = "PAULO_INITIAL_PASSWORD"
DEFAULT_PAULO_PASSWORD = "paulo"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass(frozen=True)
class InitialUsersResult:
    """Result of the initial user seed."""

    admin_status: str
    paulo_status: str


def get_initial_password(env_name: str, fallback: str) -> str:
    """Return an initial password from the environment or a fallback."""
    return os.getenv(env_name) or fallback


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a stored hash."""
    return pwd_context.verify(password, password_hash)


def get_user_by_username(session: Session, username: str) -> User | None:
    """Find a user by username."""
    return session.execute(select(User).where(User.username == username)).scalar_one_or_none()


def ensure_admin_user(session: Session, password: str | None = None) -> str:
    """Create the technical admin user or update its public fields."""
    admin_user = get_user_by_username(session, ADMIN_USERNAME)

    if admin_user is not None:
        admin_user.nome = ADMIN_NOME
        admin_user.email = ADMIN_EMAIL
        admin_user.role = ADMIN_ROLE
        admin_user.is_active = True
        session.flush()
        return "updated"

    admin_user = User(
        username=ADMIN_USERNAME,
        nome=ADMIN_NOME,
        email=ADMIN_EMAIL,
        password_hash=hash_password(
            password or get_initial_password(ADMIN_PASSWORD_ENV, DEFAULT_ADMIN_PASSWORD)
        ),
        role=ADMIN_ROLE,
        is_active=True,
    )
    session.add(admin_user)
    session.flush()

    return "created"


def ensure_paulo_user(session: Session, password: str | None = None) -> str:
    """Create the Paulo work user if it does not already exist."""
    paulo_user = get_user_by_username(session, PAULO_USERNAME)

    if paulo_user is not None:
        paulo_user.role = PAULO_ROLE
        paulo_user.is_active = True
        session.flush()
        return "exists"

    paulo_user = User(
        username=PAULO_USERNAME,
        nome=PAULO_NOME,
        email=PAULO_EMAIL,
        password_hash=hash_password(
            password or get_initial_password(PAULO_PASSWORD_ENV, DEFAULT_PAULO_PASSWORD)
        ),
        role=PAULO_ROLE,
        is_active=True,
    )
    session.add(paulo_user)
    session.flush()

    return "created"


def ensure_initial_users(
    session: Session,
    admin_password: str | None = None,
    paulo_password: str | None = None,
) -> InitialUsersResult:
    """Create or update the initial users in one transaction."""
    result = InitialUsersResult(
        admin_status=ensure_admin_user(session, password=admin_password),
        paulo_status=ensure_paulo_user(session, password=paulo_password),
    )
    session.commit()

    return result


def print_result(result: InitialUsersResult) -> None:
    """Print the user-facing result messages."""
    if result.admin_status == "updated":
        print("Utilizador admin atualizado")
    else:
        print("Utilizador admin criado")

    if result.paulo_status == "exists":
        print("Utilizador paulo j\u00e1 existe")
    else:
        print("Utilizador paulo criado")


def main() -> int:
    """Create or update the initial users."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = ensure_initial_users(session)

    print_result(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
