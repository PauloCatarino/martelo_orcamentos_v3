"""File checks for the brush icon asset."""

from __future__ import annotations

from pathlib import Path


def test_icone_pincel_existe() -> None:
    icon_path = Path("app/ui/assets/icons/pincel.svg")

    assert icon_path.exists()
    assert icon_path.stat().st_size > 0
