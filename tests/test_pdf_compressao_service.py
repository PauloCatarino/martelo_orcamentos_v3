"""Aligeirar o PDF sem estragar a impressão nem o ficheiro."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.pdf_compressao_service import (
    DPI_IMPRESSAO,
    comprimir_pdf,
)

pytest.importorskip("pypdf")
pytest.importorskip("PIL")


def _imagem_tipo_render(largura: int, altura: int):
    """Imagem com textura, como um render 3D: pesada em PNG, leve em JPEG."""
    import random

    from PIL import Image

    random.seed(11)
    imagem = Image.new("RGB", (largura, altura))
    pixeis = imagem.load()
    for y in range(altura):
        base = 120 + int(90 * y / altura)
        for x in range(largura):
            ruido = random.randint(-25, 25)
            pixeis[x, y] = (base + ruido, base - 20 + ruido, base - 45 + ruido)
    return imagem


def _pdf_com_imagem(destino: Path, imagem) -> Path:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    largura, altura = landscape(A4)
    pdf = canvas.Canvas(str(destino), pagesize=(largura, altura))
    pdf.drawImage(ImageReader(imagem), 0, 0, largura, altura)
    pdf.showPage()
    pdf.save()
    return destino


def test_pdf_pesado_fica_muito_mais_leve(tmp_path: Path) -> None:
    caminho = _pdf_com_imagem(
        tmp_path / "projeto.pdf", _imagem_tipo_render(2600, 1900)
    )
    antes = caminho.stat().st_size

    resultado = comprimir_pdf(caminho)

    assert resultado.aplicado
    assert resultado.imagens_tratadas == 1
    assert caminho.stat().st_size < antes / 2
    assert resultado.poupanca_pct > 50


def test_imagem_fica_na_resolucao_de_impressao(tmp_path: Path) -> None:
    from pypdf import PdfReader
    from reportlab.lib.pagesizes import A4, landscape

    caminho = _pdf_com_imagem(
        tmp_path / "projeto.pdf", _imagem_tipo_render(3000, 2100)
    )

    comprimir_pdf(caminho)

    imagem = PdfReader(str(caminho)).pages[0].images[0]
    lado_maximo = max(landscape(A4)) / 72.0 * DPI_IMPRESSAO
    assert max(imagem.image.size) <= lado_maximo + 1
    # E continua a ser grande o suficiente para imprimir bem.
    assert max(imagem.image.size) > 1500


def test_imagem_partilhada_por_duas_paginas_so_e_tratada_uma_vez(
    tmp_path: Path,
) -> None:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    # O CONJ.pdf costuma repetir a mesma imagem nas duas páginas; gravar JPEG
    # por cima de JPEG só tirava qualidade.
    imagem = _imagem_tipo_render(2400, 1700)
    caminho = tmp_path / "partilhada.pdf"
    largura, altura = landscape(A4)
    pdf = canvas.Canvas(str(caminho), pagesize=(largura, altura))
    leitor_imagem = ImageReader(imagem)
    for _pagina in range(2):
        pdf.drawImage(leitor_imagem, 0, 0, largura, altura)
        pdf.showPage()
    pdf.save()

    resultado = comprimir_pdf(caminho)

    assert resultado.aplicado
    assert resultado.imagens_tratadas == 1


def test_pdf_continua_a_abrir_com_as_paginas_todas(tmp_path: Path) -> None:
    from pypdf import PdfReader
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    caminho = tmp_path / "duas_paginas.pdf"
    largura, altura = landscape(A4)
    pdf = canvas.Canvas(str(caminho), pagesize=(largura, altura))
    for _pagina in range(2):
        pdf.drawImage(ImageReader(_imagem_tipo_render(2400, 1700)), 0, 0, largura, altura)
        pdf.showPage()
    pdf.save()

    comprimir_pdf(caminho)

    assert len(PdfReader(str(caminho)).pages) == 2


def test_pdf_sem_imagens_nao_mexe_em_imagem_nenhuma(tmp_path: Path) -> None:
    from pypdf import PdfReader
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas

    caminho = tmp_path / "so_texto.pdf"
    pdf = canvas.Canvas(str(caminho), pagesize=landscape(A4))
    pdf.drawString(80, 400, "Projeto de producao")
    pdf.save()

    resultado = comprimir_pdf(caminho)

    assert resultado.imagens_tratadas == 0
    assert "Projeto de producao" in PdfReader(str(caminho)).pages[0].extract_text()


def test_segunda_passagem_nao_engorda_o_ficheiro(tmp_path: Path) -> None:
    # Gerar o PDF duas vezes é banal (o utilizador carrega outra vez em
    # "Gerar"): a segunda passagem não pode piorar o que já está aligeirado.
    caminho = _pdf_com_imagem(
        tmp_path / "projeto.pdf", _imagem_tipo_render(2600, 1900)
    )
    comprimir_pdf(caminho)
    depois_da_primeira = caminho.stat().st_size

    comprimir_pdf(caminho)

    assert caminho.stat().st_size <= depois_da_primeira


def test_imagem_com_transparencia_nao_e_tocada() -> None:
    from types import SimpleNamespace

    from PIL import Image

    from app.services.pdf_compressao_service import _tem_transparencia

    opaca = SimpleNamespace(
        image=Image.new("RGB", (10, 10)),
        indirect_reference=SimpleNamespace(get_object=lambda: {"/Width": 10}),
    )
    com_alfa = SimpleNamespace(image=Image.new("RGBA", (10, 10)))
    com_mascara = SimpleNamespace(
        image=Image.new("RGB", (10, 10)),
        indirect_reference=SimpleNamespace(get_object=lambda: {"/SMask": object()}),
    )

    # Passar uma imagem transparente a JPEG daria fundos pretos na folha.
    assert not _tem_transparencia(opaca)
    assert _tem_transparencia(com_alfa)
    assert _tem_transparencia(com_mascara)


def test_ficheiro_inexistente_nao_rebenta(tmp_path: Path) -> None:
    resultado = comprimir_pdf(tmp_path / "nao_existe.pdf")

    assert not resultado.aplicado
    assert "ilegível" in resultado.motivo


def test_pdf_estragado_nao_rebenta_nem_e_alterado(tmp_path: Path) -> None:
    caminho = tmp_path / "estragado.pdf"
    caminho.write_bytes(b"isto nao e um PDF")

    resultado = comprimir_pdf(caminho)

    assert not resultado.aplicado
    assert caminho.read_bytes() == b"isto nao e um PDF"


def test_resumo_e_legivel(tmp_path: Path) -> None:
    caminho = _pdf_com_imagem(
        tmp_path / "projeto.pdf", _imagem_tipo_render(2600, 1900)
    )

    resumo = comprimir_pdf(caminho).resumo()

    assert "MB" in resumo or "KB" in resumo
    assert "->" in resumo
