"""Resolve the production image stored in the IMOS iX folder."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.services.system_setting_service import SystemSettingService

KEY_PASTA_BASE_IMORDER = "pasta_base_imorder"


def find_imos_ix_image_path(base_dir: str, nome_enc: str) -> Path | None:
    """Find <base_dir>/<nome_enc>/<nome_enc>.png, accepting uppercase .PNG."""
    base = str(base_dir or "").strip()
    nome = str(nome_enc or "").strip()
    if not base or not nome:
        return None

    folder = Path(base) / nome
    for candidate in (folder / f"{nome}.png", folder / f"{nome}.PNG"):
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def resolver_imagem_imos(session: Session, *, nome_enc_imos: str) -> Path | None:
    """Read pasta_base_imorder and return the IMOS image path, when present."""
    base = (
        SystemSettingService(session).obter_valor(KEY_PASTA_BASE_IMORDER, "") or ""
    ).strip()
    if not base:
        return None

    return find_imos_ix_image_path(base, nome_enc_imos)
