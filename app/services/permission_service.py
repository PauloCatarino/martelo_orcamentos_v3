"""Role and per-user permission rules."""

from __future__ import annotations

from collections import OrderedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserPermission


MENU_PERMISSIONS: OrderedDict[str, str] = OrderedDict(
    (
        ("menu.orcamentos", "Orçamentos"),
        ("menu.materias_primas", "Matérias-Primas"),
        ("menu.pesquisa_ia", "Pesquisa IA"),
        ("menu.clientes", "Clientes"),
        ("menu.producao", "Produção"),
        ("menu.encomendas_phc", "Encomendas PHC"),
        ("menu.ponto_situacao", "Ponto de Situação"),
        ("menu.configuracoes", "Configurações técnicas"),
    )
)

LEGACY_FEATURE_KEYS = (
    "feature_pdf_manager",
    "feature_producao_preparacao",
    "feature_lista_material_audit",
)

DEFAULT_USER_PERMISSIONS = {
    key: key != "menu.configuracoes" for key in MENU_PERMISSIONS
}


def is_admin(user: User | None) -> bool:
    """Return whether the account has full application access."""
    return bool(user is not None and (user.role or "").strip().lower() == "admin")


def permissions_for_user(session: Session, user: User | None) -> dict[str, bool]:
    """Resolve defaults and explicit overrides for one user."""
    if user is None:
        return {key: False for key in MENU_PERMISSIONS}
    if is_admin(user):
        return {key: True for key in MENU_PERMISSIONS}

    resolved = dict(DEFAULT_USER_PERMISSIONS)
    rows = session.execute(
        select(UserPermission).where(UserPermission.user_id == user.id)
    ).scalars()
    for row in rows:
        if row.permission_key in MENU_PERMISSIONS:
            resolved[row.permission_key] = bool(row.enabled)
    return resolved


def set_user_permissions(
    session: Session,
    user_id: int,
    permissions: dict[str, bool],
) -> None:
    """Create or update the supplied permission overrides."""
    existing = {
        row.permission_key: row
        for row in session.execute(
            select(UserPermission).where(UserPermission.user_id == user_id)
        ).scalars()
    }
    for key, enabled in permissions.items():
        if key not in MENU_PERMISSIONS and key not in LEGACY_FEATURE_KEYS:
            continue
        row = existing.get(key)
        if row is None:
            session.add(
                UserPermission(
                    user_id=user_id,
                    permission_key=key,
                    enabled=bool(enabled),
                )
            )
        else:
            row.enabled = bool(enabled)
