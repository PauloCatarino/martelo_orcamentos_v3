"""Create the initial admin user."""

from __future__ import annotations

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
ADMIN_EMAIL = "projetos@lancaencanto.pt"
ADMIN_ROLE = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_admin_password() -> str:
    """Return the initial admin password from the environment."""
    return os.getenv("ADMIN_INITIAL_PASSWORD") or DEFAULT_ADMIN_PASSWORD


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a stored hash."""
    return pwd_context.verify(password, password_hash)


def ensure_admin_user(session: Session, password: str | None = None) -> bool:
    """Create the admin user if it does not already exist."""
    existing_user = session.execute(
        select(User).where(User.username == ADMIN_USERNAME)
    ).scalar_one_or_none()

    if existing_user is not None:
        return False

    admin_user = User(
        username=ADMIN_USERNAME,
        nome=ADMIN_NOME,
        email=ADMIN_EMAIL,
        password_hash=hash_password(password or get_admin_password()),
        role=ADMIN_ROLE,
        is_active=True,
    )

    session.add(admin_user)
    session.commit()

    return True


def main() -> int:
    """Create the initial admin user."""
    _ = settings.database_url

    with SessionLocal() as session:
        created = ensure_admin_user(session)

    if created:
        print("Utilizador admin criado com sucesso")
    else:
        print("Utilizador admin j\u00e1 existe")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
