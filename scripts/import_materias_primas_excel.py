"""Import / synchronise raw materials from the Excel file into def_materias_primas.

The Excel file is, for now, the external source of raw materials. This script
reads ``TAB_MATERIAS_PRIMAS.xlsm`` and creates or updates rows in the internal
``def_materias_primas`` table, using ``ref_le`` as the synchronisation key.

It supports a ``--dry-run`` mode that analyses the file without writing.

openpyxl and the database session/settings are imported lazily, so the pure
helper functions (and this module) can be imported and unit tested without
openpyxl, without the real Excel file and without a database.

Usage:
    python scripts/import_materias_primas_excel.py --dry-run
    python scripts/import_materias_primas_excel.py
    python scripts/import_materias_primas_excel.py --excel-path "C:/path/TAB_MATERIAS_PRIMAS.xlsm"
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from app.services.def_materia_prima_service import (  # noqa: E402
    CriarDefMateriaPrimaData,
    DefMateriaPrimaService,
    EditarDefMateriaPrimaData,
)

DEFAULT_FILENAME = "TAB_MATERIAS_PRIMAS.xlsm"
SYSTEM_SETTING_PASTA_MATERIAS_PRIMAS = "pasta_materias_primas"
PATH_SOURCE_MANUAL = "argumento manual"
PATH_SOURCE_SYSTEM_SETTING = "configuracao do sistema"
PATH_SOURCE_FALLBACK = "fallback"
HEADER_SCAN_LIMIT = 15
HEADER_MIN_NONEMPTY = 3
ORIGEM_DADOS = "EXCEL"

# Each model field maps to one or more normalized Excel header names, in order
# of preference. Header names come from docs/06_fase_6_analise_excel_materias_primas.md.
COLUMN_ALIASES = {
    "ref_le": ("refle",),
    "referencia_fornecedor": ("reffornecedor", "referenciafornecedor"),
    "descricao": ("descricaonoorcamento", "descricao"),
    "descricao_phc": ("descricaodophc",),
    "tipo_original_excel": ("tipo",),
    "familia_original_excel": ("familia",),
    "unidade": ("und", "unidade", "un"),
    "preco_tabela": ("precotabela", "preco"),
    "desconto": ("desc2", "desconto", "desc"),
    "margem": ("mrg", "margem"),
    "preco_liquido": ("pliq", "precoliquido"),
    "comprimento": ("compmp", "comprimento", "comp"),
    "largura": ("largmp", "largura", "larg"),
    "espessura": ("espmp", "espessura", "esp"),
    "fornecedor": ("nomefornecedor", "fornecedor"),
}


@dataclass
class ImportSummary:
    """Counters for one import / sync run."""

    total: int = 0
    criadas: int = 0
    atualizadas: int = 0
    ignoradas_sem_ref_le: int = 0
    erros: int = 0
    avisos: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExcelPathResolution:
    """Selected Excel path and the source that provided it."""

    path: Path
    source: str


def normalize_header(name: object) -> str:
    """Normalize a header name to an accent-free, alphanumeric-only key."""
    if name is None:
        return ""

    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]", "", text.lower())


def to_text(value: object) -> str | None:
    """Return a trimmed string, or None when empty."""
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def to_decimal(value: object) -> Decimal | None:
    """Convert a cell value into a Decimal, or None when not parseable."""
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None

    text = str(value).strip()
    if not text:
        return None

    text = text.replace(" ", "").replace("\u20ac", "").replace("%", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    else:
        text = text.replace(",", ".")

    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def detect_header_row(rows: list, min_nonempty: int = HEADER_MIN_NONEMPTY) -> int:
    """Return the index of the first row that looks like a header."""
    fallback_index: int | None = None
    ref_aliases = set(COLUMN_ALIASES["ref_le"])
    description_aliases = set(COLUMN_ALIASES["descricao"]) | set(COLUMN_ALIASES["descricao_phc"])

    for index, row in enumerate(rows):
        nonempty = sum(1 for cell in row if to_text(cell))
        normalized = {normalize_header(cell) for cell in row if to_text(cell)}

        if ref_aliases & normalized and description_aliases & normalized:
            return index

        if nonempty >= min_nonempty:
            fallback_index = index if fallback_index is None else fallback_index

    return fallback_index or 0


def build_column_map(headers: list) -> dict:
    """Map each model field to the index of its Excel column (or None)."""
    normalized = [normalize_header(header) for header in headers]
    column_map: dict[str, int | None] = {}

    for field_name, aliases in COLUMN_ALIASES.items():
        index = None
        for alias in aliases:
            if alias in normalized:
                index = normalized.index(alias)
                break
        column_map[field_name] = index

    return column_map


def extract_row(row: tuple, column_map: dict) -> dict:
    """Extract the mapped values from one Excel data row."""

    def cell(field_name: str) -> object:
        index = column_map.get(field_name)
        if index is None or index >= len(row):
            return None
        return row[index]

    descricao = to_text(cell("descricao")) or to_text(cell("descricao_phc"))

    return {
        "ref_le": to_text(cell("ref_le")),
        "referencia_fornecedor": to_text(cell("referencia_fornecedor")),
        "descricao": descricao,
        "tipo_original_excel": to_text(cell("tipo_original_excel")),
        "familia_original_excel": to_text(cell("familia_original_excel")),
        "unidade": to_text(cell("unidade")),
        "preco_tabela": to_decimal(cell("preco_tabela")),
        "desconto": to_decimal(cell("desconto")),
        "margem": to_decimal(cell("margem")),
        "preco_liquido": to_decimal(cell("preco_liquido")),
        "comprimento": to_decimal(cell("comprimento")),
        "largura": to_decimal(cell("largura")),
        "espessura": to_decimal(cell("espessura")),
        "fornecedor": to_text(cell("fornecedor")),
    }


def run_import(service, headers: list, data_rows: list, dry_run: bool) -> ImportSummary:
    """Create or update raw materials from the rows, using ref_le as key.

    tipo_martelo and familia_martelo are intentionally left empty in this phase,
    for a later cleanup/mapping phase.
    """
    summary = ImportSummary()
    column_map = build_column_map(headers)

    for row in data_rows:
        summary.total += 1
        values = extract_row(row, column_map)
        ref_le = values["ref_le"]

        if not ref_le:
            summary.ignoradas_sem_ref_le += 1
            continue

        if not values["descricao"]:
            summary.erros += 1
            summary.avisos.append(f"ref_le {ref_le}: sem descricao, linha ignorada")
            continue

        try:
            existing = service.obter_por_ref_le(ref_le)

            if dry_run:
                if existing is not None:
                    summary.atualizadas += 1
                else:
                    summary.criadas += 1
                continue

            if existing is not None:
                service.editar_materia_prima(existing.id, _editar_data(values, existing))
                summary.atualizadas += 1
            else:
                service.criar_materia_prima(_criar_data(values))
                summary.criadas += 1
        except (ValueError, SQLAlchemyError) as error:
            summary.erros += 1
            summary.avisos.append(f"ref_le {ref_le}: {error}")

    return summary


def get_default_excel_path(session) -> Path:
    """Return the configured Excel path, or the current-directory fallback."""
    return get_default_excel_path_resolution(session).path


def get_default_excel_path_resolution(session) -> ExcelPathResolution:
    """Return the default Excel path and its source."""
    from app.services.system_setting_service import SystemSettingService

    configured_folder = SystemSettingService(session).obter_valor(
        SYSTEM_SETTING_PASTA_MATERIAS_PRIMAS,
        default=None,
    )
    configured_folder = (configured_folder or "").strip()

    if configured_folder:
        return ExcelPathResolution(
            path=Path(configured_folder) / DEFAULT_FILENAME,
            source=PATH_SOURCE_SYSTEM_SETTING,
        )

    return ExcelPathResolution(
        path=Path.cwd() / DEFAULT_FILENAME,
        source=PATH_SOURCE_FALLBACK,
    )


def resolve_excel_path(
    session=None,
    override: str | Path | None = None,
) -> ExcelPathResolution | None:
    """Return the selected existing Excel path, or None when it is missing."""
    if override:
        resolution = ExcelPathResolution(path=Path(override), source=PATH_SOURCE_MANUAL)
    elif session is not None:
        resolution = get_default_excel_path_resolution(session)
    else:
        resolution = ExcelPathResolution(
            path=Path.cwd() / DEFAULT_FILENAME,
            source=PATH_SOURCE_FALLBACK,
        )

    if resolution.path.is_file():
        return resolution

    return None


def read_rows(path: str | Path) -> tuple[list, list]:
    """Read the workbook and return (headers, data_rows)."""
    openpyxl = _require_openpyxl()
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook.worksheets[0]
        all_rows = [tuple(row) for row in worksheet.iter_rows(values_only=True)]
    finally:
        workbook.close()

    if not all_rows:
        return [], []

    header_index = detect_header_row(all_rows[:HEADER_SCAN_LIMIT])
    headers = [to_text(cell) or "" for cell in all_rows[header_index]]
    data_rows = [
        row for row in all_rows[header_index + 1 :] if any(to_text(cell) for cell in row)
    ]
    return headers, data_rows


def print_summary(summary: ImportSummary, dry_run: bool) -> None:
    """Print the final user-facing import summary."""
    modo = "DRY-RUN (sem gravar)" if dry_run else "IMPORTACAO REAL"
    print(f"Modo: {modo}")
    print(f"Total de linhas lidas: {summary.total}")
    print(f"Criadas: {summary.criadas}")
    print(f"Atualizadas: {summary.atualizadas}")
    print(f"Ignoradas (sem ref_le): {summary.ignoradas_sem_ref_le}")
    print(f"Erros/avisos: {summary.erros}")
    for aviso in summary.avisos[:20]:
        print(f"  - {aviso}")
    if len(summary.avisos) > 20:
        print(f"  ... e mais {len(summary.avisos) - 20} avisos")


def parse_args(argv: list | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the import script."""
    parser = argparse.ArgumentParser(
        description="Importar materias-primas do Excel para def_materias_primas.",
    )
    parser.add_argument(
        "legacy_excel_path",
        nargs="?",
        help="Caminho manual do Excel, mantido por compatibilidade.",
    )
    parser.add_argument(
        "--excel-path",
        dest="excel_path",
        help="Caminho manual do ficheiro TAB_MATERIAS_PRIMAS.xlsm.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analisa o ficheiro sem gravar na base de dados.",
    )
    return parser.parse_args(sys.argv[1:] if argv is None else argv)


def main(argv: list | None = None) -> int:
    """Resolve the Excel file, read it and import / sync the rows."""
    args = parse_args(argv)
    override = args.excel_path or args.legacy_excel_path

    from app.config.settings import settings
    from app.db.session import SessionLocal

    _ = settings.database_url

    with SessionLocal() as session:
        resolution = resolve_excel_path(session=session, override=override)
        expected = (
            ExcelPathResolution(path=Path(override), source=PATH_SOURCE_MANUAL)
            if override
            else get_default_excel_path_resolution(session)
        )

        print(f"Origem do caminho Excel: {expected.source}")
        print(f"Caminho usado para procurar o Excel: {expected.path}")

        if resolution is None:
            print("Ficheiro Excel de materias-primas nao encontrado.")
            print(f"Procurado em: {expected.path}")
            print("Indique o caminho como argumento, por exemplo:")
            print(
                '  python scripts/import_materias_primas_excel.py '
                '--excel-path "C:/caminho/TAB_MATERIAS_PRIMAS.xlsm" --dry-run'
            )
            return 1

        try:
            headers, data_rows = read_rows(resolution.path)
        except RuntimeError as error:
            print(str(error))
            return 1

        service = DefMateriaPrimaService(session)
        summary = run_import(service, headers, data_rows, args.dry_run)

    print(f"Ficheiro: {resolution.path}")
    print_summary(summary, args.dry_run)
    return 0


def _criar_data(values: dict) -> CriarDefMateriaPrimaData:
    return CriarDefMateriaPrimaData(
        descricao=values["descricao"],
        ref_le=values["ref_le"],
        referencia_fornecedor=values["referencia_fornecedor"],
        tipo_original_excel=values["tipo_original_excel"],
        familia_original_excel=values["familia_original_excel"],
        unidade=values["unidade"],
        preco_tabela=values["preco_tabela"],
        desconto=values["desconto"],
        margem=values["margem"],
        preco_liquido=values["preco_liquido"],
        comprimento=values["comprimento"],
        largura=values["largura"],
        espessura=values["espessura"],
        fornecedor=values["fornecedor"],
        origem_dados=ORIGEM_DADOS,
        ativo=True,
    )


def _editar_data(values: dict, existing) -> EditarDefMateriaPrimaData:
    return EditarDefMateriaPrimaData(
        descricao=values["descricao"],
        ref_le=values["ref_le"],
        referencia_fornecedor=values["referencia_fornecedor"],
        tipo_original_excel=values["tipo_original_excel"],
        familia_original_excel=values["familia_original_excel"],
        tipo_martelo=existing.tipo_martelo,
        familia_martelo=existing.familia_martelo,
        unidade=values["unidade"],
        preco_tabela=values["preco_tabela"],
        desconto=values["desconto"],
        margem=values["margem"],
        preco_liquido=values["preco_liquido"],
        comprimento=values["comprimento"],
        largura=values["largura"],
        espessura=values["espessura"],
        fornecedor=values["fornecedor"],
        origem_dados=ORIGEM_DADOS,
        ativo=existing.ativo,
    )


def _require_openpyxl():
    try:
        import openpyxl
    except ImportError as error:
        raise RuntimeError(
            "openpyxl nao esta instalado. Instale com: pip install openpyxl"
        ) from error

    return openpyxl


if __name__ == "__main__":
    raise SystemExit(main())
