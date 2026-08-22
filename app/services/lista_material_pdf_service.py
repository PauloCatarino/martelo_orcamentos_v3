"""Registo e exportação assistida dos PDFs da Lista Material.

O inventário é explícito: documentos sem folha/macro conhecida aparecem como
indisponíveis, em vez de se adivinharem intervalos de impressão.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from openpyxl import load_workbook
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.lista_material_assistente import (
    ListaMaterialPdfDocumento,
    ListaMaterialPdfPreset,
)


@dataclass(frozen=True)
class PdfDocument:
    identifier: str
    name: str
    category: str
    sheet: str | None
    filename: str
    order: int
    combinable: bool = True
    unavailable_reason: str = ""


@dataclass(frozen=True)
class PdfDocumentState:
    document: PdfDocument
    available: bool
    reason: str = ""


@dataclass(frozen=True)
class PdfExportResult:
    files: tuple[Path, ...]
    package: Path | None
    errors: tuple[str, ...]


DEFAULT_DOCUMENTS = (
    PdfDocument("caderno_encargos", "Caderno de Encargos", "Caderno de Encargos", "2_CAD_ENCARGOS", "Caderno_de_Encargos.pdf", 10),
    PdfDocument("rosto", "Rosto", "Caderno de Encargos", "2_ROSTO", "Rosto_Caderno_Encargos.pdf", 15),
    PdfDocument("ferragens", "Ferragens", "Ferragens", "1_FERRAGENS", "Ferragens.pdf", 30),
    PdfDocument("purch", "Purch", "Ferragens", None, "Purch.pdf", 31, unavailable_reason="O modelo atual só contém Purch dentro da macro agrupada; falta inventariar uma origem separada."),
    PdfDocument("spp", "SPP", "Ferragens", "3_SPP", "SPP.pdf", 32),
    PdfDocument("etiqueta_palete", "Etiqueta Palete", "Etiquetas e paletes", "5_ETIQUETA_PALETE", "Etiqueta_Palete.pdf", 40),
    PdfDocument("resumo_orlas", "Resumo de Orlas", "Orlas", "ResumoOrlas", "Resumo_Orlas.pdf", 50),
    PdfDocument("listagem_artigo", "Listagem por Artigo", "Listagens", "LISTAGEM_por_Artigo", "Listagem_por_Artigo.pdf", 60),
    PdfDocument("listagem_cutrite", "Listagem CUT-RITE", "CUT-RITE", "LISTAGEM_CUT_RITE", "Listagem_CUT_RITE.pdf", 70),
    PdfDocument("relatorio", "Relatório geral", "Relatórios gerais", "RELATORIO", "Relatorio_Geral.pdf", 80),
)


def sync_pdf_document_registry(session: Session) -> int:
    """Regista o inventário conhecido sem remover definições personalizadas."""
    changed = 0
    for document in DEFAULT_DOCUMENTS:
        row = session.execute(
            select(ListaMaterialPdfDocumento).where(
                ListaMaterialPdfDocumento.identificador == document.identifier
            )
        ).scalar_one_or_none()
        if row is None:
            row = ListaMaterialPdfDocumento(identificador=document.identifier)
            session.add(row)
            changed += 1
        row.nome = document.name
        row.categoria = document.category
        row.origem_tipo = "folha" if document.sheet else "pendente"
        row.origem_valor = document.sheet or ""
        row.nome_ficheiro = document.filename
        row.combinavel = document.combinable
        row.ordem = document.order
        row.ativo = True
        row.prerequisitos_json = json.dumps(
            {"indisponivel": document.unavailable_reason}, ensure_ascii=False
        )
    session.commit()
    return changed


def inspect_pdf_documents(workbook_path: Path) -> list[PdfDocumentState]:
    workbook = load_workbook(Path(workbook_path), read_only=True, data_only=True)
    try:
        sheets = set(workbook.sheetnames)
        result: list[PdfDocumentState] = []
        for document in sorted(DEFAULT_DOCUMENTS, key=lambda item: item.order):
            if document.unavailable_reason:
                result.append(PdfDocumentState(document, False, document.unavailable_reason))
            elif document.sheet not in sheets:
                result.append(PdfDocumentState(document, False, f"Folha '{document.sheet}' não existe neste livro."))
            else:
                sheet = workbook[document.sheet]
                has_data = any(
                    cell.value not in (None, "")
                    for row in sheet.iter_rows(
                        min_row=1,
                        max_row=min(sheet.max_row, 25),
                        min_col=1,
                        max_col=min(sheet.max_column, 25),
                    )
                    for cell in row
                )
                result.append(
                    PdfDocumentState(
                        document,
                        has_data,
                        "" if has_data else "A folha existe, mas não contém dados para exportar.",
                    )
                )
        return result
    finally:
        workbook.close()


def collision_free_path(folder: Path, filename: str) -> Path:
    base = Path(folder) / filename
    if not base.exists():
        return base
    for number in range(2, 10_000):
        candidate = base.with_name(f"{base.stem}_{number}{base.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Não foi possível criar um nome livre para {base.name}.")


def export_pdf_documents(
    workbook_path: Path,
    destination: Path,
    identifiers: Iterable[str],
    *,
    export_separate: bool = True,
    create_package: bool = False,
    package_name: str = "Documentacao_Producao.pdf",
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> PdfExportResult:
    selected_ids = set(identifiers)
    states = {state.document.identifier: state for state in inspect_pdf_documents(workbook_path)}
    selected = [
        states[item.identifier]
        for item in DEFAULT_DOCUMENTS
        if item.identifier in selected_ids and item.identifier in states
    ]
    unavailable = [state for state in selected if not state.available]
    if unavailable:
        details = "\n".join(f"- {item.document.name}: {item.reason}" for item in unavailable)
        raise ValueError("Existem documentos indisponíveis:\n" + details)
    if not selected:
        raise ValueError("Selecione pelo menos um documento disponível.")

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    try:
        import win32com.client as win32_client
    except ImportError as exc:
        raise RuntimeError("A exportação necessita do Microsoft Excel e do pywin32.") from exc

    excel = None
    workbook = None
    outputs: list[Path] = []
    errors: list[str] = []
    package: Path | None = None
    try:
        excel = win32_client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        try:
            excel.AutomationSecurity = 3
        except Exception:
            pass
        workbook = excel.Workbooks.Open(str(Path(workbook_path).resolve()), ReadOnly=True)
        total = len(selected)
        if export_separate:
            for index, state in enumerate(selected, start=1):
                document = state.document
                if progress_callback:
                    progress_callback(f"A exportar {document.name}…", index - 1, total)
                output = collision_free_path(destination, document.filename)
                try:
                    sheet = workbook.Worksheets.Item(document.sheet)
                    sheet.ExportAsFixedFormat(0, str(output))
                    outputs.append(output)
                except Exception as exc:
                    errors.append(f"{document.name}: {exc}")
        if create_package:
            if progress_callback:
                progress_callback("A criar o pacote combinado…", total, total)
            package = collision_free_path(destination, package_name)
            workbook.Worksheets.Item(selected[0].document.sheet).Select(True)
            for state in selected[1:]:
                workbook.Worksheets.Item(state.document.sheet).Select(False)
            excel.ActiveSheet.ExportAsFixedFormat(0, str(package))
        if progress_callback:
            progress_callback("Exportação concluída.", total, total)
    finally:
        if workbook is not None:
            try:
                workbook.Close(False)
            except Exception:
                pass
        if excel is not None:
            try:
                excel.Quit()
            except Exception:
                pass

    return PdfExportResult(tuple(outputs), package, tuple(errors))


class PdfPresetService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, *, user_id: int, client: str) -> list[ListaMaterialPdfPreset]:
        key = _client_key(client)
        return list(
            self.session.execute(
                select(ListaMaterialPdfPreset)
                .where(
                    ListaMaterialPdfPreset.user_id == int(user_id),
                    ListaMaterialPdfPreset.cliente_chave == key,
                )
                .order_by(ListaMaterialPdfPreset.ultimo_usado.desc(), ListaMaterialPdfPreset.nome)
            ).scalars()
        )

    def save(
        self,
        *,
        user_id: int,
        client: str,
        name: str,
        identifiers: Iterable[str],
        export_separate: bool,
        create_package: bool,
    ) -> ListaMaterialPdfPreset:
        name = str(name or "").strip()
        if not name:
            raise ValueError("Indique um nome para o preset.")
        key = _client_key(client)
        self.session.execute(
            update(ListaMaterialPdfPreset)
            .where(
                ListaMaterialPdfPreset.user_id == int(user_id),
                ListaMaterialPdfPreset.cliente_chave == key,
            )
            .values(ultimo_usado=False)
        )
        row = self.session.execute(
            select(ListaMaterialPdfPreset).where(
                ListaMaterialPdfPreset.user_id == int(user_id),
                ListaMaterialPdfPreset.cliente_chave == key,
                ListaMaterialPdfPreset.nome == name,
            )
        ).scalar_one_or_none()
        if row is None:
            row = ListaMaterialPdfPreset(user_id=int(user_id), cliente_chave=key, nome=name)
            self.session.add(row)
        row.documentos_json = json.dumps(list(identifiers), ensure_ascii=False)
        row.exportar_separados = bool(export_separate)
        row.criar_pacote = bool(create_package)
        row.ultimo_usado = True
        self.session.commit()
        return row


def _client_key(value: str) -> str:
    from app.services.lista_material_assistente_service import client_key

    return client_key(value)
