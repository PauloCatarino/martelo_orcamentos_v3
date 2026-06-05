"""Simple application session state."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import User


@dataclass
class AppSession:
    """Hold the current authenticated user."""

    current_user: User | None = None

    def set_current_user(self, user: User) -> None:
        """Store the current authenticated user."""
        self.current_user = user

    def clear_current_user(self) -> None:
        """Clear the current authenticated user."""
        self.current_user = None

    def is_authenticated(self) -> bool:
        """Return whether a user is currently authenticated."""
        return self.current_user is not None


app_session = AppSession()
