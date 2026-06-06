"""Tests for the raw materials Excel import helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from scripts import import_materias_primas_excel as importer


def test_import_script_imports() -> None:
    assert importer.DEFAULT_FILENAME == "TAB_MATERIAS_PRIMAS.xlsm"
    assert importer.ORIGEM_DADOS == "EXCEL"


def test_normalize_header_accepts_spaces_case_and_accents() -> None:
    assert importer.normalize_header(" Ref_LE ") == "refle"
    assert importer.normalize_header("DESCRI\u00c7\u00c3O no OR\u00c7AMENTO") == "descricaonoorcamento"
    assert importer.normalize_header("PRE\u00c7O TABELA") == "precotabela"
    assert importer.normalize_header("MRG_(+)") == "mrg"


def test_to_decimal_accepts_common_excel_formats() -> None:
    assert importer.to_decimal(None) is None
    assert importer.to_decimal("") is None
    assert importer.to_decimal("24,87") == Decimal("24.87")
    assert importer.to_decimal("1.234,56") == Decimal("1234.56")
    assert importer.to_decimal("1,234.56") == Decimal("1234.56")
    assert importer.to_decimal("19.896") == Decimal("19.896")
    assert importer.to_decimal("bad") is None


def test_detect_header_row_prefers_ref_le_and_description() -> None:
    rows = [
        ("Notas", "com", "varios", "valores"),
        ("REF_FORNECEDOR", "Ref_LE", "DESCRICAO_no_ORCAMENTO", "PRECO_TABELA"),
    ]

    assert importer.detect_header_row(rows) == 1


def test_build_column_map_and_extract_row() -> None:
    headers = [
        "REF_FORNECEDOR",
        "Ref_LE",
        "DESCRICAO_no_ORCAMENTO",
        "TIPO",
        "FAMILIA",
        "UND",
        "PRECO_TABELA",
        "DESC2_(-)",
        "MRG_(+)",
        "PLIQ",
        "COMP_MP",
        "LARG_MP",
        "ESP_MP",
        "NOME_FORNECEDOR",
    ]
    row = (
        "FORN-01",
        "PLC0001",
        "Material teste",
        "AGLOMERADO",
        "PLACAS",
        "M2",
        "24,87",
        "0,2",
        "0,1",
        "19,896",
        "2800",
        "2070",
        "19",
        "Fornecedor",
    )

    values = importer.extract_row(row, importer.build_column_map(headers))

    assert values["ref_le"] == "PLC0001"
    assert values["referencia_fornecedor"] == "FORN-01"
    assert values["descricao"] == "Material teste"
    assert values["tipo_original_excel"] == "AGLOMERADO"
    assert values["familia_original_excel"] == "PLACAS"
    assert values["unidade"] == "M2"
    assert values["preco_tabela"] == Decimal("24.87")
    assert values["desconto"] == Decimal("0.2")
    assert values["margem"] == Decimal("0.1")
    assert values["preco_liquido"] == Decimal("19.896")
    assert values["comprimento"] == Decimal("2800")
    assert values["largura"] == Decimal("2070")
    assert values["espessura"] == Decimal("19")
    assert values["fornecedor"] == "Fornecedor"


@dataclass
class _ExistingMateria:
    id: int
    tipo_martelo: str | None = None
    familia_martelo: str | None = None
    ativo: bool = True


class _FakeService:
    def __init__(self) -> None:
        self.existing_by_ref = {"PLC0002": _ExistingMateria(id=2)}
        self.created = []
        self.updated = []

    def obter_por_ref_le(self, ref_le: str):
        return self.existing_by_ref.get(ref_le)

    def criar_materia_prima(self, data) -> None:
        self.created.append(data)

    def editar_materia_prima(self, id: int, data) -> None:
        self.updated.append((id, data))


class _FakeSystemSettingService:
    value: str | None = None

    def __init__(self, _session: object) -> None:
        pass

    def obter_valor(self, chave: str, default: str | None = None) -> str | None:
        assert chave == importer.SYSTEM_SETTING_PASTA_MATERIAS_PRIMAS
        return self.value if self.value is not None else default


def test_run_import_creates_updates_and_ignores_missing_ref_le() -> None:
    headers = ["Ref_LE", "DESCRICAO_no_ORCAMENTO", "PRECO_TABELA"]
    rows = [
        ("PLC0001", "Material novo", "10,50"),
        ("PLC0002", "Material existente", "11,25"),
        ("", "Sem ref", "1"),
    ]
    service = _FakeService()

    summary = importer.run_import(service, headers, rows, dry_run=False)

    assert summary.total == 3
    assert summary.criadas == 1
    assert summary.atualizadas == 1
    assert summary.ignoradas_sem_ref_le == 1
    assert summary.erros == 0
    assert service.created[0].ref_le == "PLC0001"
    assert service.created[0].origem_dados == "EXCEL"
    assert service.created[0].ativo is True
    assert service.updated[0][0] == 2


def test_run_import_dry_run_does_not_write() -> None:
    headers = ["Ref_LE", "DESCRICAO_no_ORCAMENTO"]
    rows = [("PLC0001", "Material novo"), ("PLC0002", "Material existente")]
    service = _FakeService()

    summary = importer.run_import(service, headers, rows, dry_run=True)

    assert summary.criadas == 1
    assert summary.atualizadas == 1
    assert service.created == []
    assert service.updated == []


def test_resolve_excel_path_manual_has_priority(tmp_path: Path) -> None:
    manual_file = tmp_path / "manual.xlsm"
    manual_file.write_text("x")

    resolution = importer.resolve_excel_path(session=object(), override=manual_file)

    assert resolution is not None
    assert resolution.path == manual_file
    assert resolution.source == importer.PATH_SOURCE_MANUAL


def test_resolve_excel_path_uses_configured_folder(monkeypatch, tmp_path: Path) -> None:
    from app.services import system_setting_service

    configured_folder = tmp_path / "materias"
    configured_folder.mkdir()
    expected_file = configured_folder / importer.DEFAULT_FILENAME
    expected_file.write_text("x")
    _FakeSystemSettingService.value = str(configured_folder)
    monkeypatch.setattr(
        system_setting_service,
        "SystemSettingService",
        _FakeSystemSettingService,
    )

    resolution = importer.resolve_excel_path(session=object())

    assert resolution is not None
    assert resolution.path == expected_file
    assert resolution.source == importer.PATH_SOURCE_SYSTEM_SETTING
    assert importer.get_default_excel_path(object()) == expected_file


def test_resolve_excel_path_falls_back_to_cwd(monkeypatch, tmp_path: Path) -> None:
    from app.services import system_setting_service

    fallback_file = tmp_path / importer.DEFAULT_FILENAME
    fallback_file.write_text("x")
    monkeypatch.chdir(tmp_path)
    _FakeSystemSettingService.value = None
    monkeypatch.setattr(
        system_setting_service,
        "SystemSettingService",
        _FakeSystemSettingService,
    )

    resolution = importer.resolve_excel_path(session=object())

    assert resolution is not None
    assert resolution.path == fallback_file
    assert resolution.source == importer.PATH_SOURCE_FALLBACK


def test_resolve_excel_path_empty_config_falls_back_to_cwd(monkeypatch, tmp_path: Path) -> None:
    from app.services import system_setting_service

    fallback_file = tmp_path / importer.DEFAULT_FILENAME
    fallback_file.write_text("x")
    monkeypatch.chdir(tmp_path)
    _FakeSystemSettingService.value = "   "
    monkeypatch.setattr(
        system_setting_service,
        "SystemSettingService",
        _FakeSystemSettingService,
    )

    resolution = importer.resolve_excel_path(session=object())

    assert resolution is not None
    assert resolution.path == fallback_file
    assert resolution.source == importer.PATH_SOURCE_FALLBACK
