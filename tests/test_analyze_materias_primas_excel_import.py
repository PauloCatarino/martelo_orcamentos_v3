"""Import and pure-helper checks for the materias-primas Excel analyzer.

These tests must not depend on the real Excel file nor on openpyxl being
installed. They only import the script module and exercise its pure helpers.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "analyze_materias_primas_excel.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "analyze_materias_primas_excel", _SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_module_imports() -> None:
    module = _load_module()

    assert hasattr(module, "analyze_workbook")
    assert hasattr(module, "build_markdown_report")
    assert hasattr(module, "main")


def test_clean_cell_and_normalize_text() -> None:
    module = _load_module()

    assert module.clean_cell(None) == ""
    assert module.clean_cell("  AGL  ") == "AGL"
    assert module.normalize_text(None) == ""
    assert module.normalize_text(" Iluminação ") == "ILUMINACAO"


def test_detect_header_row_skips_empty_rows() -> None:
    module = _load_module()

    rows = [
        (None, None, None),
        ("", "", ""),
        ("ID_MP", "DESCRICAO", "TIPO"),
        ("1", "AGL 19MM", "AGLOMERADO"),
    ]
    assert module.detect_header_row(rows) == 2


def test_classify_tipo_into_v3_categories() -> None:
    module = _load_module()

    assert module.classify_tipo("AGLOMERADO") == "paineis"
    assert module.classify_tipo("MDF HIDROFUGO") == "paineis"
    assert module.classify_tipo("ORLA") == "orlas"
    assert module.classify_tipo("DOBRADICAS") == "ferragens"
    assert module.classify_tipo("PUXADOR") == "acessorios"
    assert module.classify_tipo("SPP") == "spp"
    assert module.classify_tipo("LEDS") == "iluminacao"
    assert module.classify_tipo("QUALQUER COISA RARA") == "outros"
    assert module.classify_tipo(None) == "outros"


def test_propose_mapping_groups_by_category() -> None:
    module = _load_module()

    mapping = module.propose_mapping(["AGLOMERADO", "ORLA", "DOBRADICAS", "AGLOMERADO", ""])

    assert "AGLOMERADO" in mapping["paineis"]
    assert mapping["paineis"].count("AGLOMERADO") == 1
    assert "ORLA" in mapping["orlas"]
    assert "DOBRADICAS" in mapping["ferragens"]


def test_build_markdown_report_with_fake_analysis() -> None:
    module = _load_module()

    analysis = {
        "source": "fake/TAB_MATERIAS_PRIMAS.xlsm",
        "sheets": [
            {
                "title": "Tab_Materias_Primas",
                "n_rows": 10,
                "n_cols": 3,
                "header_index": 1,
                "headers": ["ID_MP", "DESCRICAO", "TIPO"],
                "data_row_count": 2,
                "sample": [["1", "AGL 19MM", "AGLOMERADO"]],
                "categorical": {"TIPO": {"AGLOMERADO": 1, "ORLA": 1}},
            }
        ],
    }

    report = module.build_markdown_report(analysis)

    assert "# Fase 6 - Analise do Excel de materias-primas" in report
    assert "Tab_Materias_Primas" in report
    assert "Proposta inicial de mapeamento" in report
    assert "nem todos os tipos do excel" in report.lower()


def test_candidate_paths_prefers_override() -> None:
    module = _load_module()

    paths = module.candidate_paths("X.xlsm")

    assert paths[0] == Path("X.xlsm")
    assert len(paths) > 1
    names = {p.name for p in paths}
    assert "TAB_MATERIAS_PRIMAS.xlsm" in names


def test_resolve_excel_path_finds_existing_override() -> None:
    module = _load_module()

    # An override pointing at an existing file is resolved to that file.
    assert module.resolve_excel_path(__file__) == Path(__file__)
    # An override that does not exist falls back to other candidates.
    assert module.resolve_excel_path("caminho/que/nao/existe.xlsm") != Path(
        "caminho/que/nao/existe.xlsm"
    )
