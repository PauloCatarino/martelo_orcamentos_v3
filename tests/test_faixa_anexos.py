"""Visual attachment strip used by occurrence tickets."""

from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from app.ui.widgets.faixa_anexos import FaixaAnexos


def test_galeria_somente_leitura_mostra_foto_e_nome(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    caminho = tmp_path / "trabalho.png"
    imagem = QImage(320, 180, QImage.Format.Format_RGB32)
    imagem.fill(QColor("#8B6F4E"))
    assert imagem.save(str(caminho))
    galeria = FaixaAnexos(
        altura=176,
        tamanho_icone=QSize(190, 128),
        mostrar_nomes=True,
        somente_leitura=True,
    )

    galeria.carregar(
        [SimpleNamespace(id=7, caminho=str(caminho), nome_original="trabalho.png")]
    )

    assert galeria.count() == 1
    assert galeria.item(0).text() == "trabalho.png"
    assert not galeria.item(0).icon().isNull()
    assert not galeria.acceptDrops()
    galeria.item(0).setSelected(True)
    galeria.remover_selecionados()
    assert galeria.total() == 1
    galeria.deleteLater()
    app.processEvents()


def _pdf_de_teste(caminho, texto: str = "Encomenda de placas") -> None:
    """Um PDF de uma página, como o orçamento que o fornecedor manda."""
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(str(caminho))
    pdf.drawString(100, 700, texto)
    pdf.save()


def test_pdf_mostra_miniatura_da_primeira_pagina(tmp_path) -> None:
    """Um PDF anexado ao ticket vê-se em miniatura, como as fotos."""
    app = QApplication.instance() or QApplication([])
    caminho = tmp_path / "4494.pdf"
    _pdf_de_teste(caminho)
    galeria = FaixaAnexos(
        altura=176,
        tamanho_icone=QSize(190, 128),
        mostrar_nomes=True,
        somente_leitura=True,
    )

    galeria.carregar(
        [SimpleNamespace(id=9, caminho=str(caminho), nome_original="4494.pdf")]
    )

    assert galeria.count() == 1
    assert galeria.item(0).text() == "4494.pdf"
    # A miniatura é a primeira página desenhada, não um ícone vazio.
    assert not galeria.item(0).icon().isNull()
    assert "PDF" in galeria.item(0).toolTip()
    galeria.deleteLater()
    app.processEvents()


def test_miniatura_do_pdf_nao_prende_o_ficheiro(tmp_path) -> None:
    """Ver o PDF no ticket não pode impedir que ele seja apagado depois."""
    app = QApplication.instance() or QApplication([])
    caminho = tmp_path / "orcamento.pdf"
    _pdf_de_teste(caminho)
    galeria = FaixaAnexos(somente_leitura=True)
    galeria.carregar([SimpleNamespace(id=3, caminho=str(caminho), nome_original="orcamento.pdf")])

    caminho.unlink()  # rebenta com PermissionError se ficou preso

    assert not caminho.exists()
    galeria.deleteLater()
    app.processEvents()


def test_pdf_estragado_nao_rebenta_a_faixa(tmp_path) -> None:
    """Um PDF ilegível fica sem miniatura, mas o ticket abre na mesma."""
    app = QApplication.instance() or QApplication([])
    caminho = tmp_path / "estragado.pdf"
    caminho.write_bytes(b"isto nao e um PDF")
    galeria = FaixaAnexos(somente_leitura=True)

    galeria.carregar(
        [SimpleNamespace(id=4, caminho=str(caminho), nome_original="estragado.pdf")]
    )

    assert galeria.count() == 1
    assert galeria.item(0).icon().isNull()
    galeria.deleteLater()
    app.processEvents()
