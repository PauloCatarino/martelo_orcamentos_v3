"""Service for system setting workflows."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.system_setting_repository import (
    SystemSettingRepository,
    SystemSettingResumo,
)


class SystemSettingService:
    """Application service for system settings."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = SystemSettingRepository(session)

    def listar_configuracoes(self) -> list[SystemSettingResumo]:
        """List all system settings."""
        return self.repository.list_all()

    def listar_por_grupo(self, grupo: str) -> list[SystemSettingResumo]:
        """List settings for one group."""
        normalized_group = (grupo or "").strip()
        return self.repository.list_by_group(normalized_group)

    def obter_valor(self, chave: str, default: str | None = None) -> str | None:
        """Return the setting value for one key."""
        normalized_key = self._normalize_chave(chave)
        setting = self.repository.get_by_key(normalized_key)
        if setting is None or setting.valor is None:
            return default

        return setting.valor

    def guardar_valor(self, chave: str, valor: str | None) -> SystemSettingResumo:
        """Save one setting value."""
        normalized_key = self._normalize_chave(chave)
        result = self.repository.update_setting(normalized_key, self._normalize_valor(valor))

        if result is None:
            result = self.repository.upsert_setting(
                chave=normalized_key,
                valor=self._normalize_valor(valor),
            )

        self.session.commit()

        return result

    def guardar_varios(self, valores: dict[str, str | None]) -> list[SystemSettingResumo]:
        """Save multiple setting values."""
        results: list[SystemSettingResumo] = []

        for chave, valor in valores.items():
            normalized_key = self._normalize_chave(chave)
            normalized_value = self._normalize_valor(valor)
            result = self.repository.update_setting(normalized_key, normalized_value)

            if result is None:
                result = self.repository.upsert_setting(
                    chave=normalized_key,
                    valor=normalized_value,
                )

            results.append(result)

        self.session.commit()

        return results

    def _normalize_chave(self, chave: str) -> str:
        normalized = (chave or "").strip()
        if not normalized:
            raise ValueError("chave is required")

        return normalized

    def _normalize_valor(self, valor: str | None) -> str | None:
        if valor is None:
            return None

        return str(valor).strip()
