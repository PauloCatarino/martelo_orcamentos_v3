from __future__ import annotations

from openpyxl import Workbook

from app.models.lista_material_assistente import ListaMaterialPdfDocumento
from app.services.lista_material_pdf_service import (
    DEFAULT_DOCUMENTS,
    collision_free_path,
    inspect_pdf_documents,
    sync_pdf_document_registry,
)


def test_inventario_pdf_mostra_disponiveis_e_indisponiveis(tmp_path) -> None:
    path = tmp_path / "lista.xlsx"
    workbook = Workbook()
    workbook.active.title = "2_CAD_ENCARGOS"
    workbook.active["A1"] = "Caderno"
    workbook.create_sheet("1_FERRAGENS")["A1"] = "Ferragens"
    workbook.save(path)

    states = {item.document.identifier: item for item in inspect_pdf_documents(path)}

    assert states["caderno_encargos"].available is True
    assert states["ferragens"].available is True
    assert states["purch"].available is False
    assert "macro agrupada" in states["purch"].reason
    assert states["spp"].available is False


def test_colisao_de_nome_nunca_sobrescreve(tmp_path) -> None:
    existing = tmp_path / "Ferragens.pdf"
    existing.write_bytes(b"existente")

    result = collision_free_path(tmp_path, "Ferragens.pdf")

    assert result.name == "Ferragens_2.pdf"
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
