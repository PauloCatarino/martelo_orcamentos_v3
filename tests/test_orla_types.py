"""Tests for edge banding type helpers."""

from __future__ import annotations

from app.domain.orla_types import (
    ORLA_FINA,
    ORLA_GROSSA,
    SEM_ORLA,
    format_orla_code,
    get_orla_type_label,
    get_orla_type_options,
    normalize_orla_type,
)


def test_normalize_orla_type_defaults_to_sem_orla() -> None:
    assert normalize_orla_type(None) == SEM_ORLA
    assert normalize_orla_type("") == SEM_ORLA
    assert normalize_orla_type("desconhecido") == SEM_ORLA
    assert normalize_orla_type(9) == SEM_ORLA


def test_normalize_orla_type_accepts_known_values() -> None:
    assert normalize_orla_type(0) == SEM_ORLA
    assert normalize_orla_type(1) == ORLA_FINA
    assert normalize_orla_type(2) == ORLA_GROSSA
    assert normalize_orla_type("0") == SEM_ORLA
    assert normalize_orla_type("1") == ORLA_FINA
    assert normalize_orla_type("2") == ORLA_GROSSA


def test_orla_type_labels_and_options() -> None:
    assert get_orla_type_label(SEM_ORLA) == "Sem orla"
    assert get_orla_type_label(ORLA_FINA) == "Orla fina"
    assert get_orla_type_label(ORLA_GROSSA) == "Orla grossa"
    assert (SEM_ORLA, "Sem orla") in get_orla_type_options()
    assert (ORLA_GROSSA, "Orla grossa") in get_orla_type_options()


def test_format_orla_code() -> None:
    assert format_orla_code(0, 0, 0, 0) == "[0000]"
    assert format_orla_code(2, 2, 0, 0) == "[2200]"
    assert format_orla_code(2, 2, 2, 2) == "[2222]"
    assert format_orla_code("2", "1", "0", "1") == "[2101]"
    assert format_orla_code(None, "x", 2, 9) == "[0020]"
