"""Service for the per-user costing piece library preferences."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories.def_peca_user_pref_repository import DefPecaUserPrefRepository


@dataclass(frozen=True)
class PreferenciasBibliotecaPecas:
    """One user's piece library preferences.

    ``personalizado`` False means the user never customized the library and
    sees every active piece; the id sets are only meaningful when True.
    """

    personalizado: bool
    selecionadas: frozenset[int]
    favoritas: frozenset[int]

    def peca_visivel(self, def_peca_id: int) -> bool:
        """Return whether one piece appears in this user's library."""
        return not self.personalizado or def_peca_id in self.selecionadas


SEM_PREFERENCIAS = PreferenciasBibliotecaPecas(
    personalizado=False, selecionadas=frozenset(), favoritas=frozenset()
)


class DefPecaUserPrefService:
    """Application service for per-user piece library preferences."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefPecaUserPrefRepository(session)

    def obter_preferencias(self, user_id: int | None) -> PreferenciasBibliotecaPecas:
        """Return one user's preferences (defaults without a user or rows)."""
        if user_id is None:
            return SEM_PREFERENCIAS

        rows = self.repository.list_by_user(user_id)
        if not rows:
            return SEM_PREFERENCIAS

        return PreferenciasBibliotecaPecas(
            personalizado=True,
            selecionadas=frozenset(row.def_peca_id for row in rows),
            favoritas=frozenset(row.def_peca_id for row in rows if row.favorito),
        )

    def guardar_preferencias(
        self, user_id: int, selecionadas: set[int], favoritas: set[int]
    ) -> PreferenciasBibliotecaPecas:
        """Replace one user's selection. Empty selection clears the customization.

        A favorite is always kept visible: favorites outside the selection are
        added to it.
        """
        selecionadas = set(selecionadas) | set(favoritas)
        if not selecionadas:
            return self.repor_preferencias(user_id)

        self.repository.replace_for_user(user_id, selecionadas, set(favoritas))
        self.session.commit()

        return PreferenciasBibliotecaPecas(
            personalizado=True,
            selecionadas=frozenset(selecionadas),
            favoritas=frozenset(favoritas),
        )

    def repor_preferencias(self, user_id: int) -> PreferenciasBibliotecaPecas:
        """Clear the customization so the user sees every active piece again."""
        self.repository.delete_for_user(user_id)
        self.session.commit()
        return SEM_PREFERENCIAS
