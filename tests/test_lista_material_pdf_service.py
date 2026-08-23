from __future__ import annotations

from openpyxl import Workbook

from app.models.lista_material_assistente import ListaMaterialPdfDocumento
from app.services.lista_material_pdf_service import (
    DEFAULT_DOCUMENTS,
    _export_sheets_to_pdf,
    collision_free_path,
    document_filename,
    inspect_pdf_documents,
    normalize_pdf_identifiers,
    read_nome_enc_imos_ix,
    sync_pdf_document_registry,
)


def test_exportacao_agrupada_seleciona_ferragens_purch_e_spp(tmp_path) -> None:
    events: list[tuple[object, ...]] = []

    class _Sheet:
        def __init__(self, name: str) -> None:
            self.name = name

        def Select(self, replace: bool) -> None:
            events.append(("select", self.name, replace))

    class _Worksheets:
        def Item(self, name: str) -> _Sheet:
            return _Sheet(name)

    class _Workbook:
        Worksheets = _Worksheets()

    class _ActiveSheet:
        def ExportAsFixedFormat(self, kind: int, output: str) -> None:
            events.append(("export", kind, output))

    class _Excel:
        ActiveSheet = _ActiveSheet()

    output = tmp_path / "2_Lista_Ferragens_1449_01_26_JF_VIVA.pdf"
    _export_sheets_to_pdf(
        _Excel(),
        _Workbook(),
        ("1_FERRAGENS", "2_PURCH", "3_SPP"),
        output,
    )

    assert events == [
        ("select", "1_FERRAGENS", True),
        ("select", "2_PURCH", False),
        ("select", "3_SPP", False),
        ("export", 0, str(output)),
    ]


def test_inventario_pdf_mostra_disponiveis_e_indisponiveis(tmp_path) -> None:
    path = tmp_path / "lista.xlsx"
    workbook = Workbook()
    workbook.active.title = "DEFENICOES"
    workbook.active["E3"] = "1449_01_26_JF_VIVA"
    workbook.create_sheet("1_FERRAGENS")["A1"] = "Ferragens"
    workbook.create_sheet("2_PURCH")["A1"] = "Purch"
    workbook.save(path)

    states = {item.document.identifier: item for item in inspect_pdf_documents(path)}

    assert states["ferragens"].available is True
    assert states["ferragens"].export_sheets == ("1_FERRAGENS", "2_PURCH")
    assert "3_SPP" in states["ferragens"].reason
    assert "caderno_encargos" not in states
    assert "rosto" not in states
    assert "purch" not in states
    assert "spp" not in states
    assert "listagem_cutrite" not in states


def test_nomes_pdf_incluem_nome_enc_imos_ix(tmp_path) -> None:
    path = tmp_path / "lista.xlsx"
    workbook = Workbook()
    workbook.active.title = "DEFENICOES"
    workbook.active["E3"] = "1449_01_26_JF_VIVA"
    workbook.save(path)

    by_id = {document.identifier: document for document in DEFAULT_DOCUMENTS}
    nome_enc = read_nome_enc_imos_ix(path)

    assert nome_enc == "1449_01_26_JF_VIVA"
    assert document_filename(by_id["ferragens"], nome_enc) == (
        "2_Lista_Ferragens_1449_01_26_JF_VIVA.pdf"
    )
    assert document_filename(by_id["resumo_orlas"], nome_enc) == (
        "4_Resumo_Orlas_1449_01_26_JF_VIVA.pdf"
    )
    assert document_filename(by_id["etiqueta_palete"], nome_enc) == (
        "5_Etiqueta_Palete_1449_01_26_JF_VIVA.pdf"
    )
    assert document_filename(by_id["listagem_artigo"], nome_enc) == (
        "6_Lista_Material_1449_01_26_JF_VIVA.pdf"
    )


def test_preset_antigo_de_ferragens_e_normalizado() -> None:
    assert normalize_pdf_identifiers(["purch", "spp"]) == {"ferragens"}
    assert normalize_pdf_identifiers(
        ["caderno_encargos", "listagem_cutrite", "relatorio"]
    ) == {"relatorio"}


def test_colisao_de_nome_nunca_sobrescreve(tmp_path) -> None:
    existing = tmp_path / "2_Lista_Ferragens_1449_01_26_JF_VIVA.pdf"
    existing.write_bytes(b"existente")

    result = collision_free_path(
        tmp_path, "2_Lista_Ferragens_1449_01_26_JF_VIVA.pdf"
    )

    assert result.name == "2_Lista_Ferragens_1449_01_26_JF_VIVA_2.pdf"
    assert existing.read_bytes() == b"existente"


def test_registo_pdf_e_sincronizado_sem_apagar_personalizados(session) -> None:
    session.add(
        ListaMaterialPdfDocumento(
            identificador="personalizado",
            nome="Meu documento",
            categoria="Produção",
            origem_tipo="folha",
            origem_valor="MINHA_FOLHA",
            nome_ficheiro="Meu.pdf",
        )
    )
    session.commit()

    assert sync_pdf_document_registry(session) == len(DEFAULT_DOCUMENTS)
    assert session.query(ListaMaterialPdfDocumento).count() == len(DEFAULT_DOCUMENTS) + 1
    assert session.query(ListaMaterialPdfDocumento).filter_by(identificador="personalizado").one()


def test_registo_desativa_documentos_retirados_do_centro(session) -> None:
    session.add(
        ListaMaterialPdfDocumento(
            identificador="listagem_cutrite",
            nome="Listagem CUT-RITE",
            categoria="CUT-RITE",
            origem_tipo="folha",
            origem_valor="LISTAGEM_CUT_RITE",
            nome_ficheiro="Listagem_CUT_RITE.pdf",
            ativo=True,
        )
    )
    session.commit()

    sync_pdf_document_registry(session)

    retired = session.query(ListaMaterialPdfDocumento).filter_by(
        identificador="listagem_cutrite"
    ).one()
    assert retired.ativo is False
