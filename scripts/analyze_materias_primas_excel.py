"""Analyze the materias-primas Excel file and write a Markdown report.

This script is read-only: it never touches the database, models or UI. It reads
the materias-primas workbook, summarises its structure, and writes a report to
``docs/06_fase_6_analise_excel_materias_primas.md``.

openpyxl is imported lazily inside ``analyze_workbook`` so that this module (and
its pure helper functions) can be imported and unit tested without openpyxl
installed and without the real Excel file present.

Usage:
    python scripts/analyze_materias_primas_excel.py
    python scripts/analyze_materias_primas_excel.py "C:/path/TAB_MATERIAS_PRIMAS(3).xlsm"
"""

from __future__ import annotations

import sys
import unicodedata
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_FILENAME = "TAB_MATERIAS_PRIMAS(3).xlsm"
CANDIDATE_FILENAMES = (
    "TAB_MATERIAS_PRIMAS(3).xlsm",
    "TAB_MATERIAS_PRIMAS.xlsm",
    "TAB_MATERIAS_PRIMAS.xlsx",
)
SEARCH_DIRECTORIES = (".", "data", "tabelas", "scripts")
REPORT_PATH = PROJECT_ROOT / "docs" / "06_fase_6_analise_excel_materias_primas.md"

HEADER_SCAN_LIMIT = 15
HEADER_MIN_NONEMPTY = 3
SAMPLE_ROWS = 5
SAMPLE_COLS = 10
MAX_UNIQUE_VALUES = 60
CELL_MAX_LEN = 22

CATEGORICAL_HEADERS = ("TIPO", "FAMILIA", "UND", "COR", "CATEGORIA", "GRUPO")

# Keyword -> Martelo V3 category. First match wins, so order matters.
V3_CATEGORY_KEYWORDS = (
    ("orlas", ("ORLA", "ORL", "FITA")),
    ("iluminacao", ("LED", "ILUMIN", "TRANSFORMADOR")),
    ("ferragens", ("FERRAG", "DOBRADIC", "CORREDIC", "CALHA", "FECHO", "BATENTE", "CHARNEIRA")),
    ("acessorios", ("ACESSORIO", "PUXADOR", "SUPORTE", "PES", "RODAPE", "PERNA")),
    ("spp", ("SPP", "BARRA", "VARAO", "TUBO", "PERFIL")),
    ("paineis", ("AGLOMERADO", "MDF", "PLACA", "MELAMIN", "HIDROFUG", "CONTRAPLAC", "OSB", "FOLHEAD", "REMATE")),
)

V3_CATEGORY_ORDER = ("paineis", "orlas", "ferragens", "acessorios", "spp", "iluminacao", "outros")

V3_CATEGORY_LABELS = {
    "paineis": "Materias-primas de painel",
    "orlas": "Orlas",
    "ferragens": "Ferragens",
    "acessorios": "Acessorios",
    "spp": "SPP / barras / ML",
    "iluminacao": "Iluminacao / LEDs",
    "outros": "Outros (a rever)",
}


def normalize_text(value: object) -> str:
    """Return an upper-case, accent-free version of a value for matching."""
    if value is None:
        return ""

    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return text.strip().upper()


def clean_cell(value: object) -> str:
    """Return a trimmed string representation of one cell."""
    if value is None:
        return ""

    return str(value).strip()


def detect_header_row(rows: list, min_nonempty: int = HEADER_MIN_NONEMPTY) -> int:
    """Return the index of the first row that looks like a header."""
    for index, row in enumerate(rows):
        nonempty = sum(1 for cell in row if clean_cell(cell))
        if nonempty >= min_nonempty:
            return index

    return 0


def classify_tipo(value: object) -> str:
    """Classify one Excel tipo/familia value into a Martelo V3 category."""
    norm = normalize_text(value)
    if not norm:
        return "outros"

    for category, keywords in V3_CATEGORY_KEYWORDS:
        for keyword in keywords:
            if keyword in norm:
                return category

    return "outros"


def propose_mapping(tipos: list) -> dict:
    """Group a list of tipo/familia codes into Martelo V3 categories."""
    mapping: dict[str, list[str]] = {category: [] for category in V3_CATEGORY_ORDER}

    for tipo in sorted({clean_cell(t) for t in tipos if clean_cell(t)}):
        category = classify_tipo(tipo)
        if tipo not in mapping[category]:
            mapping[category].append(tipo)

    return mapping


def analyze_workbook(path: str | Path) -> dict:
    """Read the workbook and return a structural analysis dictionary."""
    openpyxl = _require_openpyxl()
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)

    sheets = []
    try:
        for worksheet in workbook.worksheets:
            sheets.append(_analyze_sheet(worksheet))
    finally:
        workbook.close()

    return {"source": str(path), "sheets": sheets}


def build_markdown_report(analysis: dict) -> str:
    """Build the Markdown report text from an analysis dictionary."""
    sheets = analysis.get("sheets", [])
    lines: list[str] = []

    lines.append("# Fase 6 - Analise do Excel de materias-primas")
    lines.append("")
    lines.append("## Origem")
    lines.append("")
    lines.append(f"- ficheiro analisado: `{analysis.get('source', '')}`")
    lines.append(
        "- nota: o nome de referencia da fase e "
        f"`{DEFAULT_FILENAME}`; o `(3)` indica apenas uma copia descarregada. "
        "A estrutura analisada e a mesma tabela de materias-primas."
    )
    lines.append(
        "- este relatorio foi gerado automaticamente pelo script "
        "`scripts/analyze_materias_primas_excel.py` e e apenas analise."
    )
    lines.append("")

    lines.append("## Resumo das folhas encontradas")
    lines.append("")
    lines.append("| Folha | Linhas | Colunas | Linhas de dados |")
    lines.append("| --- | --- | --- | --- |")
    for sheet in sheets:
        lines.append(
            f"| `{sheet['title']}` | {sheet['n_rows']} | {sheet['n_cols']} | "
            f"{sheet['data_row_count']} |"
        )
    lines.append("")

    main_sheet = _main_sheet(sheets)
    if main_sheet is None:
        lines.append("Nao foram encontradas folhas com dados.")
        lines.append("")
        return "\n".join(lines)

    lines.extend(_render_main_sheet(main_sheet))
    lines.extend(_render_categorical(main_sheet))
    lines.extend(_render_mapping(main_sheet))
    lines.extend(_render_observations(main_sheet))
    lines.extend(_render_pending())

    return "\n".join(lines)


def main(argv: list | None = None) -> int:
    """Resolve the Excel file, analyse it and write the report."""
    args = list(sys.argv[1:] if argv is None else argv)
    override = args[0] if args else None

    excel_path = resolve_excel_path(override)
    if excel_path is None:
        _print_not_found(override)
        return 1

    try:
        analysis = analyze_workbook(excel_path)
    except RuntimeError as error:
        print(str(error))
        return 1

    report = build_markdown_report(analysis)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print(f"Ficheiro analisado: {excel_path}")
    print(f"Folhas analisadas: {len(analysis['sheets'])}")
    print(f"Relatorio escrito em: {REPORT_PATH}")
    return 0


def candidate_paths(override: str | Path | None = None) -> list[Path]:
    """Return the ordered list of paths where the Excel file is searched."""
    paths: list[Path] = []
    if override:
        paths.append(Path(override))

    for directory in SEARCH_DIRECTORIES:
        base = PROJECT_ROOT if directory == "." else PROJECT_ROOT / directory
        for filename in CANDIDATE_FILENAMES:
            paths.append(base / filename)

    return paths


def resolve_excel_path(override: str | Path | None = None) -> Path | None:
    """Return the first existing candidate path, or None."""
    for path in candidate_paths(override):
        if path.is_file():
            return path

    return None


def _require_openpyxl():
    try:
        import openpyxl
    except ImportError as error:
        raise RuntimeError(
            "openpyxl nao esta instalado. Instale com: pip install openpyxl"
        ) from error

    return openpyxl


def _analyze_sheet(worksheet) -> dict:
    all_rows = [tuple(row) for row in worksheet.iter_rows(values_only=True)]

    header_index = detect_header_row(all_rows[:HEADER_SCAN_LIMIT])
    header_row = all_rows[header_index] if all_rows else ()
    headers = [clean_cell(cell) for cell in header_row]

    data_rows = [
        row for row in all_rows[header_index + 1 :] if any(clean_cell(cell) for cell in row)
    ]

    sample = [[clean_cell(cell) for cell in row] for row in data_rows[:SAMPLE_ROWS]]

    categorical: dict[str, Counter] = {}
    for col_index, header in enumerate(headers):
        if header.upper() in CATEGORICAL_HEADERS:
            counter: Counter = Counter()
            for row in data_rows:
                value = clean_cell(row[col_index]) if col_index < len(row) else ""
                if value:
                    counter[value] += 1
            categorical[header] = counter

    return {
        "title": worksheet.title,
        "n_rows": len(all_rows),
        "n_cols": len(headers),
        "header_index": header_index,
        "headers": headers,
        "data_row_count": len(data_rows),
        "sample": sample,
        "categorical": categorical,
    }


def _main_sheet(sheets: list) -> dict | None:
    if not sheets:
        return None

    return max(sheets, key=lambda sheet: sheet.get("data_row_count", 0))


def _truncate(text: str) -> str:
    text = text.replace("|", "/").replace("\n", " ")
    if len(text) > CELL_MAX_LEN:
        return text[: CELL_MAX_LEN - 1] + "…"

    return text


def _render_main_sheet(sheet: dict) -> list[str]:
    lines = ["## Estrutura da folha principal", ""]
    lines.append(f"- folha: `{sheet['title']}`")
    lines.append(f"- linha de cabecalho detetada: linha {sheet['header_index'] + 1}")
    lines.append(f"- colunas: {sheet['n_cols']}")
    lines.append(f"- linhas de dados: {sheet['data_row_count']}")
    lines.append("")

    lines.append("### Lista de colunas")
    lines.append("")
    for index, header in enumerate(sheet["headers"], start=1):
        shown = header if header else "(sem nome)"
        lines.append(f"{index}. `{shown}`")
    lines.append("")

    lines.append("### Primeiras linhas de exemplo")
    lines.append("")
    headers = sheet["headers"][:SAMPLE_COLS]
    lines.append("| " + " | ".join(_truncate(h) for h in headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in sheet["sample"]:
        cells = [_truncate(cell) for cell in row[:SAMPLE_COLS]]
        cells += [""] * (len(headers) - len(cells))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    if sheet["n_cols"] > SAMPLE_COLS:
        lines.append(
            f"(mostradas as primeiras {SAMPLE_COLS} de {sheet['n_cols']} colunas, "
            "para evitar excesso de dados)"
        )
        lines.append("")

    return lines


def _render_categorical(sheet: dict) -> list[str]:
    lines = ["## Tipos e familias encontradas", ""]
    categorical = sheet.get("categorical", {})

    if not categorical:
        lines.append("Nao foram encontradas colunas categoricas conhecidas (TIPO, FAMILIA, etc.).")
        lines.append("")
        return lines

    for header, counter in categorical.items():
        lines.append(f"### Coluna `{header}`")
        lines.append("")
        if len(counter) > MAX_UNIQUE_VALUES:
            lines.append(
                f"- {len(counter)} valores unicos (demasiados para listar; provavelmente nao categorica)."
            )
            lines.append("")
            continue

        lines.append(f"- {len(counter)} valores unicos:")
        lines.append("")
        lines.append("| Valor | Ocorrencias |")
        lines.append("| --- | --- |")
        for value, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0]))):
            lines.append(f"| `{_truncate(value)}` | {count} |")
        lines.append("")

    return lines


def _render_mapping(sheet: dict) -> list[str]:
    lines = ["## Proposta inicial de mapeamento para o Martelo V3", ""]
    lines.append(
        "Proposta automatica e provisoria, agrupando os valores de `TIPO` e `FAMILIA` "
        "por palavra-chave. Precisa de revisao humana."
    )
    lines.append("")

    tipos: list[str] = []
    for header in ("TIPO", "FAMILIA"):
        counter = sheet.get("categorical", {}).get(header)
        if counter:
            tipos.extend(counter.keys())

    mapping = propose_mapping(tipos)
    for category in V3_CATEGORY_ORDER:
        values = mapping.get(category, [])
        label = V3_CATEGORY_LABELS[category]
        if values:
            joined = ", ".join(f"`{value}`" for value in values)
            lines.append(f"- **{label}**: {joined}")
        else:
            lines.append(f"- **{label}**: (nenhum valor classificado automaticamente)")
    lines.append("")

    lines.append(
        "> Nem todos os tipos do Excel devem virar categorias finais do Martelo V3. "
        "Esta proposta serve apenas como ponto de partida; alguns tipos podem ser "
        "fundidos, renomeados ou descartados apos revisao tecnica."
    )
    lines.append("")
    return lines


def _render_observations(sheet: dict) -> list[str]:
    lines = ["## Observacoes sobre dados uteis", ""]
    lines.append(
        "- existem colunas de identificacao (por exemplo `ID_MP`, `REF_*`) que podem "
        "servir de codigo estavel no catalogo do V3;"
    )
    lines.append(
        "- existem colunas de preco, margem e desconto que alimentam o custeio futuro;"
    )
    lines.append(
        "- existem colunas de dimensao (comprimento, largura, espessura) compativeis com "
        "a logica de peca horizontal Comp / Larg / Esp do V3;"
    )
    lines.append(
        "- existem colunas de classificacao (`TIPO`, `FAMILIA`, `COR`) uteis para montar "
        "os grupos de material/ferragem."
    )
    lines.append("")

    lines.append("## Observacoes sobre dados que precisam de limpeza")
    lines.append("")
    if sheet["header_index"] > 0:
        lines.append(
            f"- o cabecalho nao esta na primeira linha (esta na linha "
            f"{sheet['header_index'] + 1}); a importacao deve saltar as linhas iniciais;"
        )
    lines.append(
        "- alguns valores de texto (descricoes, cores) podem ter problemas de codificacao "
        "de caracteres acentuados e precisam de revisao;"
    )
    lines.append(
        "- os valores de `TIPO` e `FAMILIA` devem ser normalizados (maiusculas, sem acentos, "
        "sem duplicados quase iguais) antes de virarem grupos finais;"
    )
    lines.append(
        "- podem existir linhas vazias, colunas auxiliares ou registos antigos que nao "
        "devem ser importados diretamente."
    )
    lines.append("")
    return lines


def _render_pending() -> list[str]:
    lines = ["## Proximos passos e decisoes pendentes", ""]
    lines.append("- que valores de `TIPO`/`FAMILIA` se tornam grupos finais do Martelo V3?")
    lines.append("- ferragens e acessorios ficam na mesma tabela ou em tabelas separadas?")
    lines.append("- SPP pertence a materiais ou a acessorios?")
    lines.append("- como mapear cada `TIPO` antigo para os grupos novos sem duplicar?")
    lines.append("- que colunas do Excel sao realmente necessarias no catalogo do V3?")
    lines.append("- como tratar a codificacao de caracteres ao importar?")
    lines.append("")
    lines.append(
        "Esta fase e apenas analise. Nao foram criadas tabelas, models, migrations nem "
        "importacao real de dados."
    )
    lines.append("")
    return lines


def _print_not_found(override: str | Path | None) -> None:
    print("Ficheiro Excel de materias-primas nao encontrado.")
    print(f"Nome esperado: {DEFAULT_FILENAME}")
    print("Caminhos procurados:")
    for path in candidate_paths(override):
        print(f"  - {path}")
    print("Indique o caminho do ficheiro como argumento, por exemplo:")
    print(
        '  python scripts/analyze_materias_primas_excel.py '
        '"C:/caminho/TAB_MATERIAS_PRIMAS(3).xlsm"'
    )


if __name__ == "__main__":
    raise SystemExit(main())
