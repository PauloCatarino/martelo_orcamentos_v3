"""Registo e exportação assistida dos PDFs da Lista Material.

O inventário é explícito: documentos sem folha/macro conhecida aparecem como
indisponíveis, em vez de se adivinharem intervalos de impressão.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Iterable

from openpyxl import load_workbook
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.lista_material_assistente import (
    ListaMaterialPdfDocumento,
    ListaMaterialPdfPreset,
)
from app.services.lista_material_acabamentos_service import (
    FOLHA_LACAGEM,
    AnaliseAcabamentos,
    abrir_em_calculo_manual,
    analisar_acabamentos,
    preparar_separador_lacagem,
)


@dataclass(frozen=True)
class PdfDocument:
    identifier: str
    name: str
    category: str
    sheets: tuple[str, ...]
    filename: str
    order: int
    combinable: bool = True
    unavailable_reason: str = ""
    # Documentos com o mesmo `group` sao vistos separados no menu (cada um
    # mostra se o seu separador existe e tem dados), mas saem num unico PDF.
    group: str = ""
    group_label: str = ""


@dataclass(frozen=True)
class PdfDocumentState:
    document: PdfDocument
    available: bool
    reason: str = ""
    export_sheets: tuple[str, ...] = ()


@dataclass(frozen=True)
class PdfExportResult:
    files: tuple[Path, ...]
    package: Path | None
    errors: tuple[str, ...]


# Separadores com data no nome: «Custo_V3_*» quer dizer o mais recente.
PREFIXO_CUSTO_V3 = "Custo_V3_"
XL_PAPER_A3, XL_LANDSCAPE = 8, 2


def folha_mais_recente(sheetnames: Iterable[str], pattern: str) -> str | None:
    """«Custo_V3_*» → o Custo_V3_<aammdd_hhmmss>_xxx mais recente (o nome traz a data)."""
    if not pattern.endswith("*"):
        return pattern if pattern in sheetnames else None
    candidatas = [name for name in sheetnames if name.startswith(pattern[:-1])]
    return max(candidatas) if candidatas else None


DEFAULT_DOCUMENTS = (
    PdfDocument(
        "lista_ferragens",
        "Ferragens",
        "Ferragens",
        ("1_FERRAGENS",),
        "2_Lista_Ferragens_{nome_enc_imos}.pdf",
        20,
        group="ferragens",
        group_label="Ferragens + Purch + SPP",
    ),
    PdfDocument(
        "lista_purch",
        "Purch (Objectos Comprados)",
        "Ferragens",
        ("2_PURCH",),
        "2_Lista_Ferragens_{nome_enc_imos}.pdf",
        21,
        group="ferragens",
        group_label="Ferragens + Purch + SPP",
    ),
    PdfDocument(
        "lista_spp",
        "SPP (Stretchable Purchased Part)",
        "Ferragens",
        ("3_SPP",),
        "2_Lista_Ferragens_{nome_enc_imos}.pdf",
        22,
        group="ferragens",
        group_label="Ferragens + Purch + SPP",
    ),
    PdfDocument(
        "resumo_orlas",
        "Resumo de Orlas",
        "Orlas",
        ("ResumoOrlas",),
        "4_Resumo_Orlas_{nome_enc_imos}.pdf",
        40,
    ),
    PdfDocument(
        "etiqueta_palete",
        "Etiqueta Palete",
        "Etiquetas e paletes",
        ("5_ETIQUETA_PALETE",),
        "5_Etiqueta_Palete_{nome_enc_imos}.pdf",
        50,
    ),
    PdfDocument(
        "listagem_artigo",
        "Listagem por Artigo",
        "Listagens",
        ("LISTAGEM_por_Artigo",),
        "6_Lista_Material_{nome_enc_imos}.pdf",
        60,
    ),
    PdfDocument(
        # Pedido do Paulo (22-09-2026): o relatório geral da obra é o separador
        # de custo que a Análise da Lista Material exporta (Custo_V3_<data>),
        # o mais recente, em A3 ao baixo — tem muita informação e fica na obra.
        "relatorio",
        "Relatório geral",
        "Relatórios gerais",
        (PREFIXO_CUSTO_V3 + "*",),
        "5_Custo_Obra_Relatorio.pdf",
        80,
    ),
    PdfDocument(
        "listagem_acabamentos",
        "Listagem Acabamentos",
        "Acabamentos",
        (FOLHA_LACAGEM,),
        "3_Lacagem_{nome_enc_imos}.pdf",
        90,
    ),
)

# Só as peças com Tipo_Lacagem saem; o separador é preparado antes de exportar.
ACABAMENTOS_DOCUMENT_ID = "listagem_acabamentos"

RETIRED_DOCUMENT_IDS = frozenset(
    {"caderno_encargos", "rosto", "ferragens", "purch", "spp", "listagem_cutrite"}
)
# Presets antigos guardavam um unico documento com as tres folhas juntas.
FERRAGENS_LEGACY_IDS = frozenset({"ferragens", "purch", "spp"})
FERRAGENS_DOCUMENT_IDS = ("lista_ferragens", "lista_purch", "lista_spp")


class PdfExportCancelled(Exception):
    """O utilizador cancelou a exportacao na pergunta de substituicao."""


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
        row.origem_tipo = "folhas" if len(document.sheets) > 1 else "folha"
        row.origem_valor = "|".join(document.sheets)
        row.nome_ficheiro = document.filename
        row.combinavel = document.combinable
        row.ordem = document.order
        row.ativo = True
        row.prerequisitos_json = json.dumps(
            {"indisponivel": document.unavailable_reason}, ensure_ascii=False
        )
    session.execute(
        update(ListaMaterialPdfDocumento)
        .where(ListaMaterialPdfDocumento.identificador.in_(RETIRED_DOCUMENT_IDS))
        .values(ativo=False)
    )
    session.commit()
    return changed


def _estado_acabamentos(
    document: PdfDocument, analise: AnaliseAcabamentos
) -> PdfDocumentState:
    if not analise.disponivel:
        return PdfDocumentState(document, False, analise.motivo)
    return PdfDocumentState(document, True, analise.motivo, document.sheets)


def inspect_pdf_documents(
    workbook_path: Path, *, analise_acabamentos: AnaliseAcabamentos | None = None
) -> list[PdfDocumentState]:
    workbook = load_workbook(Path(workbook_path), read_only=True, data_only=True)
    try:
        sheets = set(workbook.sheetnames)
        result: list[PdfDocumentState] = []
        for document in sorted(DEFAULT_DOCUMENTS, key=lambda item: item.order):
            if document.unavailable_reason:
                result.append(PdfDocumentState(document, False, document.unavailable_reason))
                continue
            if document.identifier == ACABAMENTOS_DOCUMENT_ID:
                if analise_acabamentos is None:
                    try:
                        analise_acabamentos = analisar_acabamentos(workbook_path)
                    except Exception as exc:
                        result.append(
                            PdfDocumentState(
                                document,
                                False,
                                f"Não foi possível ler o separador {FOLHA_LACAGEM}: {exc}",
                            )
                        )
                        continue
                result.append(_estado_acabamentos(document, analise_acabamentos))
                continue

            export_sheets: list[str] = []
            unavailable_sheets: list[str] = []
            for pattern in document.sheets:
                sheet_name = folha_mais_recente(sheets, pattern)
                if sheet_name is None:
                    unavailable_sheets.append(pattern)
                    continue
                sheet = workbook[sheet_name]
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
                if has_data:
                    export_sheets.append(sheet_name)
                else:
                    unavailable_sheets.append(sheet_name)

            available = bool(export_sheets)
            if len(document.sheets) == 1 and document.sheets[0].endswith("*"):
                reason = (
                    f"Sai o separador {export_sheets[0]} (o mais recente), em A3 ao baixo."
                    if available
                    else "Ainda não há separador de custo neste Excel: na Análise da Lista "
                    "Material use «Exportar custo para o Excel»."
                )
            elif len(document.sheets) == 1:
                folha = document.sheets[0]
                reason = (
                    f"O separador {folha} existe e tem dados."
                    if available
                    else f"O separador {folha} não existe ou está vazio neste Excel."
                )
            elif available and unavailable_sheets:
                reason = (
                    "Serão incluídos os separadores com dados: "
                    f"{', '.join(export_sheets)}. Sem dados: "
                    f"{', '.join(unavailable_sheets)}."
                )
            elif available:
                reason = f"Separadores incluídos: {', '.join(export_sheets)}."
            else:
                reason = (
                    "Nenhum dos separadores necessários contém dados: "
                    f"{', '.join(document.sheets)}."
                )
            result.append(
                PdfDocumentState(
                    document,
                    available,
                    reason,
                    tuple(export_sheets),
                )
            )
        return result
    finally:
        workbook.close()


def resolve_output_path(folder: Path, filename: str, *, overwrite: bool) -> Path:
    """Devolve o caminho final: substitui o existente ou cria o _2, _3, ..."""
    if overwrite:
        return Path(folder) / filename
    return collision_free_path(folder, filename)


def collision_free_path(folder: Path, filename: str) -> Path:
    base = Path(folder) / filename
    if not base.exists():
        return base
    for number in range(2, 10_000):
        candidate = base.with_name(f"{base.stem}_{number}{base.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Não foi possível criar um nome livre para {base.name}.")


def normalize_pdf_identifiers(identifiers: Iterable[str]) -> set[str]:
    """Mapeia presets antigos para o catálogo atual sem reativar documentos removidos."""
    selected = {str(identifier) for identifier in identifiers}
    if selected & FERRAGENS_LEGACY_IDS:
        selected.update(FERRAGENS_DOCUMENT_IDS)
    selected.difference_update(RETIRED_DOCUMENT_IDS)
    return selected


def document_filename(document: PdfDocument, nome_enc_imos: str = "") -> str:
    """Resolve o nome final de um PDF, protegendo o fragmento vindo do Excel."""
    if "{nome_enc_imos}" not in document.filename:
        return document.filename
    nome = str(nome_enc_imos or "").strip()
    if not nome:
        raise ValueError(
            "Nome Enc IMOS IX em falta no Excel (DEFENICOES!E3)."
        )
    invalidos = '<>:"/\\|?*'
    nome_seguro = "".join(
        "_" if char in invalidos or ord(char) < 32 else char for char in nome
    )
    nome_seguro = nome_seguro.strip(" .")
    if not nome_seguro:
        raise ValueError("Nome Enc IMOS IX inválido para criar o nome do PDF.")
    return document.filename.format(nome_enc_imos=nome_seguro)


def read_nome_enc_imos_ix(workbook_path: Path) -> str:
    """Lê o Nome Enc IMOS IX do contrato estável DEFENICOES!E3."""
    workbook = load_workbook(Path(workbook_path), read_only=True, data_only=True)
    try:
        if "DEFENICOES" not in workbook.sheetnames:
            return ""
        return str(workbook["DEFENICOES"]["E3"].value or "").strip()
    finally:
        workbook.close()


def _unique_sheet_names(states: Iterable[PdfDocumentState]) -> tuple[str, ...]:
    result: list[str] = []
    for state in states:
        for sheet_name in state.export_sheets:
            if sheet_name not in result:
                result.append(sheet_name)
    return tuple(result)


def agrupar_para_exportacao(
    states: Iterable[PdfDocumentState], nome_enc_imos: str = ""
) -> list[tuple[str, str, tuple[str, ...]]]:
    """Junta num só PDF os documentos que partilham `group`.

    Devolve (rótulo, nome do ficheiro, folhas a exportar) pela ordem do
    catálogo. As folhas de um grupo saem no mesmo PDF, como estavam antes de
    Ferragens/Purch/SPP passarem a ter visto próprio no menu.
    """
    grupos: dict[str, list[PdfDocumentState]] = {}
    ordem: list[str] = []
    for state in states:
        chave = state.document.group or state.document.identifier
        if chave not in grupos:
            grupos[chave] = []
            ordem.append(chave)
        grupos[chave].append(state)

    resultado: list[tuple[str, str, tuple[str, ...]]] = []
    for chave in ordem:
        membros = grupos[chave]
        primeiro = membros[0].document
        rotulo = primeiro.group_label or primeiro.name
        folhas: list[str] = []
        for membro in membros:
            for folha in membro.export_sheets:
                if folha not in folhas:
                    folhas.append(folha)
        resultado.append(
            (rotulo, document_filename(primeiro, nome_enc_imos), tuple(folhas))
        )
    return resultado


def _remover_ficheiro_a_substituir(output: Path, overwrite: bool) -> None:
    """Apaga o PDF antigo antes de o Excel escrever por cima."""
    if not overwrite or not output.exists():
        return
    try:
        output.unlink()
    except OSError as exc:
        raise RuntimeError(
            f"nao foi possivel substituir {output.name}; "
            f"confirme se o PDF esta aberto noutro programa ({exc})"
        ) from exc


def _pagina_a3_ao_baixo(sheet) -> None:
    """A3 horizontal, uma página de largura (o livro está aberto só para leitura)."""
    setup = sheet.PageSetup
    try:
        setup.PaperSize = XL_PAPER_A3
    except Exception:
        pass  # impressora predefinida sem A3: sai no papel dela, mas ao baixo
    setup.Orientation = XL_LANDSCAPE
    setup.Zoom = False
    setup.FitToPagesWide = 1
    setup.FitToPagesTall = False


def _export_sheets_to_pdf(
    excel, workbook, sheet_names: tuple[str, ...], output: Path
) -> None:
    if not sheet_names:
        raise ValueError("Não existem separadores com dados para exportar.")
    for sheet_name in sheet_names:
        if sheet_name.startswith(PREFIXO_CUSTO_V3):
            _pagina_a3_ao_baixo(workbook.Worksheets.Item(sheet_name))
    if len(sheet_names) == 1:
        workbook.Worksheets.Item(sheet_names[0]).ExportAsFixedFormat(0, str(output))
        return
    workbook.Worksheets.Item(sheet_names[0]).Select(True)
    for sheet_name in sheet_names[1:]:
        workbook.Worksheets.Item(sheet_name).Select(False)
    excel.ActiveSheet.ExportAsFixedFormat(0, str(output))


def export_pdf_documents(
    workbook_path: Path,
    destination: Path,
    identifiers: Iterable[str],
    *,
    export_separate: bool = True,
    create_package: bool = False,
    package_name: str = "Documentacao_Producao.pdf",
    progress_callback: Callable[[str, int, int], None] | None = None,
    conflict_resolver: Callable[[tuple[Path, ...]], bool] | None = None,
    obra_nome: str = "",
) -> PdfExportResult:
    selected_ids = normalize_pdf_identifiers(identifiers)
    analise = None
    if ACABAMENTOS_DOCUMENT_ID in selected_ids:
        analise = analisar_acabamentos(workbook_path)
    states = {
        state.document.identifier: state
        for state in inspect_pdf_documents(workbook_path, analise_acabamentos=analise)
    }
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

    nome_enc_imos = ""
    if analise is not None or any(
        "{nome_enc_imos}" in state.document.filename for state in selected
    ):
        nome_enc_imos = read_nome_enc_imos_ix(workbook_path)

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    planned: list[tuple[str, str, tuple[str, ...]]] = []
    if export_separate:
        planned = agrupar_para_exportacao(selected, nome_enc_imos)
    existing = [
        destination / filename
        for _, filename, _ in planned
        if (destination / filename).exists()
    ]
    if create_package and (destination / package_name).exists():
        existing.append(destination / package_name)

    # Sem quem responda a pergunta, o comportamento seguro mantem-se:
    # nunca substituir, criar o _2.
    overwrite = False
    if existing and conflict_resolver is not None:
        overwrite = bool(conflict_resolver(tuple(existing)))

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
        if analise is not None:
            abrir_em_calculo_manual(excel)
        workbook = excel.Workbooks.Open(str(Path(workbook_path).resolve()), ReadOnly=True)
        package_sheets = _unique_sheet_names(selected)
        if analise is not None and analise.plano is not None:
            if progress_callback:
                progress_callback("A preparar a Listagem Acabamentos…", 0, 1)
            try:
                visiveis = preparar_separador_lacagem(
                    excel,
                    workbook,
                    analise.plano,
                    obra=obra_nome or nome_enc_imos,
                    dia=date.today(),
                )
                if visiveis != len(analise.pecas):
                    errors.append(
                        f"Listagem Acabamentos: o PDF tem {visiveis} linha(s) "
                        f"mas a LISTAGEM_CUT_RITE tem {len(analise.pecas)} peça(s) "
                        "com Tipo_Lacagem. Confirme o separador Lacagem."
                    )
            except Exception as exc:
                # As outras listas saem na mesma; esta fica de fora.
                errors.append(f"Listagem Acabamentos: {exc}")
                planned = [item for item in planned if item[2] != (FOLHA_LACAGEM,)]
                package_sheets = tuple(
                    folha for folha in package_sheets if folha != FOLHA_LACAGEM
                )
        total = max(len(planned), 1)
        if export_separate:
            for index, (rotulo, filename, folhas) in enumerate(planned, start=1):
                if progress_callback:
                    progress_callback(f"A exportar {rotulo}…", index - 1, total)
                output = resolve_output_path(destination, filename, overwrite=overwrite)
                try:
                    _remover_ficheiro_a_substituir(output, overwrite)
                    _export_sheets_to_pdf(excel, workbook, folhas, output)
                    outputs.append(output)
                except Exception as exc:
                    errors.append(f"{rotulo}: {exc}")
        if create_package and package_sheets:
            if progress_callback:
                progress_callback("A criar o pacote combinado…", total, total)
            package = resolve_output_path(destination, package_name, overwrite=overwrite)
            _remover_ficheiro_a_substituir(package, overwrite)
            _export_sheets_to_pdf(excel, workbook, package_sheets, package)
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
                .order_by(
                    ListaMaterialPdfPreset.predefinido.desc(),
                    ListaMaterialPdfPreset.ultimo_usado.desc(),
                    ListaMaterialPdfPreset.nome,
                )
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
        make_default: bool = False,
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
        if make_default:
            # Só pode existir um preset predefinido por utilizador/cliente.
            # A filtragem pelo user_id impede que esta escolha altere ou
            # exponha presets pertencentes a outro utilizador.
            self.session.execute(
                update(ListaMaterialPdfPreset)
                .where(
                    ListaMaterialPdfPreset.user_id == int(user_id),
                    ListaMaterialPdfPreset.cliente_chave == key,
                )
                .values(predefinido=False)
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
        row.predefinido = bool(make_default)
        self.session.commit()
        return row


def _client_key(value: str) -> str:
    from app.services.lista_material_assistente_service import client_key

    return client_key(value)
