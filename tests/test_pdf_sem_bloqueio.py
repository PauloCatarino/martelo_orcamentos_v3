"""Desenhar um PDF não pode deixar o ficheiro preso.

O Paulo gerou o plano de corte do CUT-RITE para a pasta da obra e depois não
conseguia apagá-lo: o Windows dizia que estava "aberto em Python". A culpa era
do QPdfDocument, que mantém o PDF aberto enquanto viver — bastava a
pré-visualização do Martelo ter passado por ele. Estes testes apagam o ficheiro
logo a seguir a desenhá-lo: no Windows isso só passa se ninguém o tiver aberto.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QLabel

import app.services.producao_preparacao_service as preparacao_svc
import app.ui.helpers.detalhe_obra_worker as worker_mod
from app.services.pdf_imagem_service import documento_pdf
from app.ui.dialogs.producao_impressao_dialog import ProducaoImpressaoDialog


@pytest.fixture(scope="module", autouse=True)
def _app():
    yield QApplication.instance() or QApplication([])


@pytest.fixture()
def plano_pdf(tmp_path) -> Path:
    """Um PDF de duas páginas, como o resumo que sai do CUT-RITE."""
    from reportlab.pdfgen import canvas

    caminho = tmp_path / "1349_01_01_26_NEXT_LEVEL.pdf"
    pdf = canvas.Canvas(str(caminho))
    pdf.drawString(100, 700, "Plano de corte")
    pdf.showPage()
    pdf.drawString(100, 700, "Resumo")
    pdf.save()
    return caminho


def _apaga(caminho: Path) -> None:
    """Apaga o ficheiro — rebenta com PermissionError se estiver preso."""
    caminho.unlink()


def test_documento_pdf_nao_prende_o_ficheiro(plano_pdf):
    with documento_pdf(plano_pdf) as documento:
        assert documento.pageCount() == 2
        assert not documento.render(0, documento.pagePointSize(0).toSize()).isNull()

    _apaga(plano_pdf)


def test_imagem_da_obra_nao_prende_o_pdf(plano_pdf):
    imagem = worker_mod._render_pdf(plano_pdf)

    assert imagem is not None and not imagem.isNull()
    _apaga(plano_pdf)


def test_pre_visualizacao_da_impressao_nao_prende_o_pdf(plano_pdf):
    # A janela inteira precisa de base de dados; o que interessa aqui é só o
    # método que desenha a primeira página.
    falso_dialogo = SimpleNamespace(imagem_label=QLabel())
    falso_dialogo.imagem_label.resize(480, 260)

    pixmap = ProducaoImpressaoDialog._primeira_pagina(falso_dialogo, plano_pdf)

    assert pixmap is not None and not pixmap.isNull()
    _apaga(plano_pdf)


def test_imagens_do_conj_nao_prendem_o_pdf(plano_pdf):
    imagens = preparacao_svc._imagens_do_conj(plano_pdf, 2)

    assert len(imagens) == 2
    _apaga(plano_pdf)


def test_pdf_ilegivel_nao_rebenta_a_pre_visualizacao(tmp_path):
    falso = tmp_path / "nao_e_pdf.pdf"
    falso.write_bytes(b"isto nao e um PDF")

    assert worker_mod._render_pdf(falso) is None
    _apaga(falso)
