from pathlib import Path

from app.services.imos_imagem_service import find_imos_ix_image_path


def test_find_imos_ix_image_path_returns_matching_png(tmp_path: Path) -> None:
    folder = tmp_path / "ENC001"
    folder.mkdir()
    image = folder / "ENC001.png"
    image.write_bytes(b"png")

    assert find_imos_ix_image_path(str(tmp_path), "ENC001") == image


def test_find_imos_ix_image_path_accepts_uppercase_extension(tmp_path: Path) -> None:
    folder = tmp_path / "ENC002"
    folder.mkdir()
    image = folder / "ENC002.PNG"
    image.write_bytes(b"png")

    assert find_imos_ix_image_path(str(tmp_path), "ENC002") == image


def test_find_imos_ix_image_path_returns_none_for_blank_or_missing(
    tmp_path: Path,
) -> None:
    assert find_imos_ix_image_path("", "ENC003") is None
    assert find_imos_ix_image_path(str(tmp_path), "") is None
    assert find_imos_ix_image_path(str(tmp_path), "ENC003") is None
