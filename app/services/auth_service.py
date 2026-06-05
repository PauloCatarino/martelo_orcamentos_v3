"""Authentication service logic."""

from __future__ import annotations

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationError(Exception):
    """Raised when user credentials are invalid."""


class InactiveUserError(AuthenticationError):
    """Raised when an inactive user attempts to authenticate."""


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plain password against a stored password hash."""
    return pwd_context.verify(plain_password, password_hash)


def authenticate_user(session: Session, username: str, password: str) -> User:
    """Authenticate a user by username and password."""
    user = session.execute(select(User).where(User.username == username)).scalar_one_or_none()

    if user is None:
        raise AuthenticationError("Invalid username or password")

    if not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid username or password")

    if not user.is_active:
        raise InactiveUserError("Inactive user")

    return user
