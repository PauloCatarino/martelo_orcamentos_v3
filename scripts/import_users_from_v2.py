"""Import V2 accounts and permission flags into Martelo V3.

The command is a dry-run unless ``--apply`` is supplied. Existing V3 IDs are
kept so references from budgets and history remain valid.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sys

from dotenv import dotenv_values
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.models import User, UserPermission  # noqa: E402
from app.services.permission_service import (  # noqa: E402
    DEFAULT_USER_PERMISSIONS,
    MENU_PERMISSIONS,
    set_user_permissions,
)


DEFAULT_V2_ENV = PROJECT_ROOT.parent / "Martelo_Orcamentos_V2" / ".env"


@dataclass(frozen=True)
class SourceUser:
    id: int
    username: str
    email: str | None
    password_hash: str
    role: str
    is_active: bool


@dataclass(frozen=True)
class PlannedUser:
    source_id: int
    username: str
    action: str
    role: str
    is_active: bool
    email: str


@dataclass(frozen=True)
class MigrationReport:
    users: list[PlannedUser]
    permission_count: int

    @property
    def creates(self) -> int:
        return sum(row.action == "create" for row in self.users)

    @property
    def updates(self) -> int:
        return sum(row.action == "update" for row in self.users)


def _v2_database_url(env_path: Path) -> str:
    values = dotenv_values(env_path)
    url = values.get("DB_URI")
    if not url:
        raise RuntimeError(f"DB_URI não encontrada em {env_path}")
    return url


def read_v2(env_path: Path) -> tuple[list[SourceUser], dict[int, dict[str, bool]]]:
    """Read accounts and feature flags without exposing password hashes."""
    engine = create_engine(_v2_database_url(env_path), future=True)
    with engine.connect() as connection:
        users = [
            SourceUser(
                id=int(row.id),
                username=str(row.username).strip(),
                email=(str(row.email).strip().lower() if row.email else None),
                password_hash=str(row.pass_hash),
                role=str(row.role or "user"),
                is_active=bool(row.is_active),
            )
            for row in connection.execute(
                text(
                    "SELECT id, username, email, pass_hash, role, is_active "
                    "FROM users ORDER BY username"
                )
            )
        ]
        flags: dict[int, dict[str, bool]] = {}
        for row in connection.execute(
            text(
                "SELECT user_id, feature_key, enabled "
                "FROM user_feature_flags ORDER BY user_id, feature_key"
            )
        ):
            flags.setdefault(int(row.user_id), {})[str(row.feature_key)] = bool(row.enabled)
    engine.dispose()
    return users, flags


def _target_role(username: str) -> str:
    return "admin" if username.casefold() == "admin" else "user"


def _target_email(source: SourceUser, existing: User | None) -> str:
    if source.email:
        return source.email
    if existing is not None and existing.email:
        return existing.email
    return f"{source.username.casefold()}@martelo.local"


def plan_migration(session: Session, source_users: list[SourceUser], permission_count: int) -> MigrationReport:
    """Build a conflict-checked, side-effect-free migration plan."""
    existing_users = session.execute(select(User)).scalars().all()
    by_username = {user.username.casefold(): user for user in existing_users}
    emails = {
        user.email.casefold(): user.username.casefold()
        for user in existing_users
        if user.email
    }
    planned: list[PlannedUser] = []
    for source in source_users:
        key = source.username.casefold()
        existing = by_username.get(key)
        email = _target_email(source, existing)
        owner = emails.get(email.casefold())
        if owner is not None and owner != key:
            raise ValueError(
                f"Email {email!r} já pertence ao utilizador {owner!r} no V3."
            )
        emails[email.casefold()] = key
        planned.append(
            PlannedUser(
                source_id=source.id,
                username=source.username,
                action="update" if existing is not None else "create",
                role=_target_role(source.username),
                is_active=source.is_active,
                email=email,
            )
        )
    return MigrationReport(users=planned, permission_count=permission_count)


def _backup_v3(session: Session, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"users_v3_before_v2_import_{stamp}.json"
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "nome": user.nome,
                "email": user.email,
                "password_hash": user.password_hash,
                "role": user.role,
                "is_active": user.is_active,
            }
            for user in session.execute(select(User).order_by(User.id)).scalars()
        ],
        "permissions": [
            {
                "user_id": row.user_id,
                "permission_key": row.permission_key,
                "enabled": row.enabled,
            }
            for row in session.execute(
                select(UserPermission).order_by(
                    UserPermission.user_id, UserPermission.permission_key
                )
            ).scalars()
        ],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def apply_migration(
    session: Session,
    source_users: list[SourceUser],
    source_flags: dict[int, dict[str, bool]],
    backup_dir: Path,
) -> tuple[MigrationReport, Path]:
    """Apply the import in one transaction after creating a recovery export."""
    report = plan_migration(
        session,
        source_users,
        sum(len(flags) for flags in source_flags.values()),
    )
    backup = _backup_v3(session, backup_dir)
    by_username = {
        user.username.casefold(): user
        for user in session.execute(select(User)).scalars()
    }
    try:
        for source in source_users:
            key = source.username.casefold()
            user = by_username.get(key)
            if user is None:
                user = User(
                    username=source.username,
                    nome=source.username,
                    email=_target_email(source, None),
                    password_hash=source.password_hash,
                    role=_target_role(source.username),
                    is_active=source.is_active,
                )
                session.add(user)
                session.flush()
                by_username[key] = user
            else:
                user.email = _target_email(source, user)
                user.password_hash = source.password_hash
                user.role = _target_role(source.username)
                user.is_active = source.is_active
                if not user.nome:
                    user.nome = source.username

            menu_permissions = (
                {menu_key: True for menu_key in MENU_PERMISSIONS}
                if user.role == "admin"
                else dict(DEFAULT_USER_PERMISSIONS)
            )
            set_user_permissions(session, user.id, menu_permissions)
            set_user_permissions(session, user.id, source_flags.get(source.id, {}))
        session.commit()
    except Exception:
        session.rollback()
        raise
    return report, backup


def _print_report(report: MigrationReport, applied: bool, backup: Path | None = None) -> None:
    state = "APLICADA" if applied else "SIMULAÇÃO"
    print(f"Migração V2 -> V3: {state}")
    print(f"Contas a criar: {report.creates}")
    print(f"Contas a atualizar: {report.updates}")
    print(f"Permissões V2 encontradas: {report.permission_count}")
    for row in report.users:
        print(
            f"- {row.action}: {row.username} | role={row.role} | "
            f"ativo={row.is_active} | email={row.email}"
        )
    if backup is not None:
        print(f"Cópia de recuperação: {backup}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Gravar a migração no V3")
    parser.add_argument("--v2-env", type=Path, default=DEFAULT_V2_ENV)
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path.home() / "AppData" / "Local" / "Martelo_Orcamentos_V3" / "backups",
    )
    args = parser.parse_args()

    source_users, source_flags = read_v2(args.v2_env)
    with SessionLocal() as session:
        if args.apply:
            report, backup = apply_migration(
                session, source_users, source_flags, args.backup_dir
            )
            _print_report(report, applied=True, backup=backup)
        else:
            report = plan_migration(
                session,
                source_users,
                sum(len(flags) for flags in source_flags.values()),
            )
            _print_report(report, applied=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
