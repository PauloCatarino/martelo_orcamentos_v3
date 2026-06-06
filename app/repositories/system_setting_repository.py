"""Repository for system settings reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SystemSetting


@dataclass(frozen=True)
class SystemSettingResumo:
    """Read model for one system setting."""

    id: int
    chave: str
    valor: str | None
    descricao: str | None
    tipo: str
    grupo: str | None
    ativo: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SystemSettingRepository:
    """Repository for SystemSetting operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[SystemSettingResumo]:
        """List all system settings."""
        statement = select(SystemSetting).order_by(
            SystemSetting.grupo.asc(),
            SystemSetting.chave.asc(),
        )
        settings = self.session.execute(statement).scalars().all()

        return [self._to_resumo(setting) for setting in settings]

    def list_by_group(self, grupo: str) -> list[SystemSettingResumo]:
        """List system settings for one group."""
        statement = (
            select(SystemSetting)
            .where(SystemSetting.grupo == grupo)
            .order_by(SystemSetting.chave.asc())
        )
        settings = self.session.execute(statement).scalars().all()

        return [self._to_resumo(setting) for setting in settings]

    def get_by_key(self, chave: str) -> SystemSettingResumo | None:
        """Get one system setting by key."""
        setting = self._get_model_by_key(chave)
        if setting is None:
            return None

        return self._to_resumo(setting)

    def upsert_setting(
        self,
        *,
        chave: str,
        valor: str | None,
        descricao: str | None = None,
        tipo: str = "texto",
        grupo: str | None = None,
        ativo: bool = True,
    ) -> SystemSettingResumo:
        """Create or update one system setting."""
        setting = self._get_model_by_key(chave)

        if setting is None:
            setting = SystemSetting(
                chave=chave,
                valor=valor,
                descricao=descricao,
                tipo=tipo,
                grupo=grupo,
                ativo=ativo,
            )
            self.session.add(setting)
        else:
            setting.valor = valor
            setting.descricao = descricao
            setting.tipo = tipo
            setting.grupo = grupo
            setting.ativo = ativo

        self.session.flush()

        return self._to_resumo(setting)

    def update_setting(self, chave: str, valor: str | None) -> SystemSettingResumo | None:
        """Update only the value for one system setting."""
        setting = self._get_model_by_key(chave)
        if setting is None:
            return None

        setting.valor = valor
        self.session.flush()

        return self._to_resumo(setting)

    def _get_model_by_key(self, chave: str) -> SystemSetting | None:
        statement = select(SystemSetting).where(SystemSetting.chave == chave)
        return self.session.execute(statement).scalars().first()

    def _to_resumo(self, setting: SystemSetting) -> SystemSettingResumo:
        """Convert an ORM system setting to the read model."""
        return SystemSettingResumo(
            id=setting.id,
            chave=setting.chave,
            valor=setting.valor,
            descricao=setting.descricao,
            tipo=setting.tipo,
            grupo=setting.grupo,
            ativo=setting.ativo,
            created_at=setting.created_at,
            updated_at=setting.updated_at,
        )
