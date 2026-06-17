"""Gerador do PDF do orçamento para o cliente (fase 8W.4.1).

Reproduz o PDF A4 do Martelo V2 (título "Orçamento"): cabeçalho com logótipo +
dados do cliente à esquerda e identificação do orçamento à direita, linha
Ref./Obra, tabela de items e bloco de totais. O ``import`` do reportlab é
protegido (``REPORTLAB_DISPONIVEL``) para a aplicação arrancar mesmo sem a
biblioteca instalada; a função levanta ``RuntimeError`` se for chamada sem ela.

A função recebe DADOS simples (sem DB nem Qt) para ser testável.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path
from xml.sax.saxutils import escape

from app.utils.formatters import (
    format_currency,
    format_mm,
    format_quantity,
    format_version,
)

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        Image,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_DISPONIVEL = True
except ImportError:  # pragma: no cover - depende da instalação do ambiente
    REPORTLAB_DISPONIVEL = False
    colors = A4 = mm = canvas = None
    ParagraphStyle = Image = Paragraph = SimpleDocTemplate = None
    Spacer = Table = TableStyle = None
    TA_LEFT = TA_RIGHT = None


# Cores do estilo Lança Encanto (iguais ao V2): azul escuro para títulos/ref,
# vermelho para a obra, cinza para o cabeçalho da tabela.
_AZUL_ESCURO = "#1F3864"
_VERMELHO = "#C00000"
_CINZA_CABECALHO = "#D9D9D9"
_AZUL_REALCE = "#EAF1FB"

# Larguras (mm) das colunas da tabela de items — somam 200 (A4 menos margens).
_COLUNAS_ITEMS = (
    ("Item", 9),
    ("Código", 20),
    ("Descrição", 80),
    ("Alt", 10),
    ("Larg", 11),
    ("Prof", 11),
    ("Und", 11),
    ("Qt", 11),
    ("Preço Unit", 18),
    ("Preço Total", 19),
)


if REPORTLAB_DISPONIVEL:

    class NumberedCanvas(canvas.Canvas):
        """Canvas que escreve, em cada página, o rodapé "Pág. X de Y".

        Acrescenta o número e a data do orçamento à esquerda. Usa o padrão de
        dois passos do reportlab: guarda o estado de cada página em ``showPage``
        e só desenha o rodapé no ``save`` final, quando o total já é conhecido.
        """

        def __init__(self, *args, **kwargs) -> None:
            self._numero_orcamento = kwargs.pop("numero_orcamento", "")
            self._data_orcamento = kwargs.pop("data_orcamento", "")
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states: list[dict] = []

        def showPage(self) -> None:  # noqa: N802 (override do reportlab)
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self) -> None:
            total_paginas = len(self._saved_page_states)
            for estado in self._saved_page_states:
                self.__dict__.update(estado)
                self._desenhar_rodape(total_paginas)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

        def _desenhar_rodape(self, total_paginas: int) -> None:
            largura, _altura = A4
            self.setFont("Helvetica", 7)
            self.setFillColor(colors.grey)
            esquerda = f"Orçamento {self._numero_orcamento}".strip()
            if self._data_orcamento:
                esquerda = f"{esquerda}  |  {self._data_orcamento}"
            self.drawString(5 * mm, 6 * mm, esquerda)
            self.drawRightString(
                largura - 5 * mm,
                6 * mm,
                f"Pág. {self._pageNumber} de {total_paginas}",
            )

else:  # pragma: no cover - sem reportlab a classe não existe
    NumberedCanvas = None


def _format_data(value) -> str:
    """Formata a data do orçamento (datetime -> YYYY-MM-DD; senão str)."""
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _paragrafo_descricao(texto: str | None, estilo) -> Paragraph:
    """Descrição como Paragraph: escapa & < > e converte \\n em <br/>."""
    seguro = escape(texto or "").replace("\n", "<br/>")
    return Paragraph(seguro, estilo)


def gerar_pdf_orcamento(
    output_path,
    *,
    cliente,
    orcamento,
    items,
    totais,
    logo_path=None,
    titulo: str = "Orçamento",
):
    """Gera o PDF do orçamento em ``output_path`` e devolve o ``Path``.

    ``cliente``/``orcamento``/``items``/``totais`` são dados simples (read-models
    ou ``SimpleNamespace``), sem DB nem Qt. ``logo_path`` é opcional.
    """
    if not REPORTLAB_DISPONIVEL:
        raise RuntimeError("reportlab não está instalado")

    output_path = Path(output_path)

    estilo_nome = ParagraphStyle(
        "ClienteNome", fontName="Helvetica-Bold", fontSize=11, leading=13
    )
    estilo_contacto = ParagraphStyle(
        "Contacto", fontName="Helvetica", fontSize=8, leading=10
    )
    estilo_titulo = ParagraphStyle(
        "TituloGrande",
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=26,
        alignment=TA_RIGHT,
        textColor=colors.HexColor(_AZUL_ESCURO),
    )
    estilo_orc_direita = ParagraphStyle(
        "OrcDireita", fontName="Helvetica", fontSize=9, leading=12, alignment=TA_RIGHT
    )
    estilo_ref = ParagraphStyle(
        "Ref",
        fontName="Helvetica-Bold",
        fontSize=9,
        alignment=TA_LEFT,
        textColor=colors.HexColor(_AZUL_ESCURO),
    )
    estilo_obra = ParagraphStyle(
        "Obra",
        fontName="Helvetica-Bold",
        fontSize=9,
        alignment=TA_RIGHT,
        textColor=colors.HexColor(_VERMELHO),
    )
    estilo_desc = ParagraphStyle(
        "DescItem", fontName="Helvetica", fontSize=7, leading=8
    )

    story = []

    # a) CABEÇALHO (tabela 2 colunas): logo + cliente | título + nº + data.
    esquerda = []
    if logo_path is not None and Path(logo_path).exists():
        logo = Image(str(logo_path), width=32 * mm, height=10 * mm)
        logo.hAlign = "LEFT"
        esquerda.append(logo)
        esquerda.append(Spacer(1, 2 * mm))
    esquerda.append(Paragraph(escape(cliente.nome or ""), estilo_nome))
    if getattr(cliente, "morada", None):
        esquerda.append(Paragraph(escape(cliente.morada), estilo_contacto))
    if getattr(cliente, "email", None):
        esquerda.append(Paragraph(escape(cliente.email), estilo_contacto))
    linha_tel = (
        f"Telefone: {getattr(cliente, 'telefone', None) or '-'} | "
        f"N.º cliente PHC: {getattr(cliente, 'num_cliente', None) or '-'}"
    )
    esquerda.append(Paragraph(escape(linha_tel), estilo_contacto))

    num_versao_fmt = f"{orcamento.num_orcamento}_{format_version(orcamento.numero_versao)}"
    data_str = _format_data(getattr(orcamento, "created_at", None))
    direita = [
        Paragraph(escape(titulo), estilo_titulo),
        Paragraph(f"Nº Orçamento: {escape(num_versao_fmt)}", estilo_orc_direita),
        Paragraph(f"Data: {escape(data_str)}", estilo_orc_direita),
    ]

    cabecalho = Table([[esquerda, direita]], colWidths=[110 * mm, 90 * mm])
    cabecalho.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(cabecalho)
    story.append(Spacer(1, 4 * mm))

    # b) LINHA Ref. (azul, esquerda) / Obra (vermelho, direita).
    ref_txt = f"Ref.: {getattr(orcamento, 'ref_cliente', None) or '-'}"
    obra_txt = f"Obra: {getattr(orcamento, 'obra', None) or '-'}"
    ref_obra = Table(
        [[Paragraph(escape(ref_txt), estilo_ref), Paragraph(escape(obra_txt), estilo_obra)]],
        colWidths=[100 * mm, 100 * mm],
    )
    ref_obra.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(ref_obra)
    story.append(Spacer(1, 3 * mm))

    # c) TABELA DE ITEMS (cabeçalho cinza, grelha; Descrição com quebra de linha).
    larguras = [largura * mm for _nome, largura in _COLUNAS_ITEMS]
    dados = [[nome for nome, _largura in _COLUNAS_ITEMS]]
    for item in items:
        dados.append(
            [
                str(getattr(item, "ordem", "")),
                getattr(item, "codigo", None) or "",
                _paragrafo_descricao(
                    getattr(item, "descricao", None) or getattr(item, "item", None),
                    estilo_desc,
                ),
                format_mm(getattr(item, "altura", None)),
                format_mm(getattr(item, "largura", None)),
                format_mm(getattr(item, "profundidade", None)),
                getattr(item, "unidade", None) or "",
                format_quantity(getattr(item, "quantidade", None)),
                format_currency(getattr(item, "preco_unitario", None)),
                format_currency(getattr(item, "preco_total", None)),
            ]
        )

    tabela_items = Table(dados, colWidths=larguras, repeatRows=1)
    tabela_items.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_CINZA_CABECALHO)),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),     # Item
                ("ALIGN", (3, 0), (5, -1), "RIGHT"),      # Alt / Larg / Prof
                ("ALIGN", (6, 0), (6, -1), "CENTER"),     # Und
                ("ALIGN", (7, 0), (9, -1), "RIGHT"),      # Qt / preços
                ("FONTNAME", (9, 1), (9, -1), "Helvetica-Bold"),  # Preço Total negrito
            ]
        )
    )
    story.append(tabela_items)
    story.append(Spacer(1, 4 * mm))

    # d) TOTAIS (tabela à direita, com caixa/realce à volta do SubTotal).
    iva_label = f"IVA ({format_quantity(totais.iva_pct)}%):"
    dados_totais = [
        ["Total Qt.:", format_quantity(totais.total_qt)],
        ["SubTotal:", format_currency(totais.subtotal)],
        [iva_label, format_currency(totais.iva)],
        ["Total Geral:", format_currency(totais.total_geral)],
    ]
    tabela_totais = Table(dados_totais, colWidths=[35 * mm, 35 * mm])
    tabela_totais.hAlign = "RIGHT"
    tabela_totais.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),  # Total Geral
                ("LINEABOVE", (0, 3), (-1, 3), 0.5, colors.grey),
                # Caixa/realce à volta do valor do SubTotal (linha 1, coluna 1).
                ("BOX", (1, 1), (1, 1), 1, colors.HexColor(_AZUL_ESCURO)),
                ("BACKGROUND", (1, 1), (1, 1), colors.HexColor(_AZUL_REALCE)),
            ]
        )
    )
    story.append(tabela_totais)

    # e) Construir (A4, margens ~5mm; rodapé "Pág. X de Y" via NumberedCanvas).
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=5 * mm,
        rightMargin=5 * mm,
        topMargin=5 * mm,
        bottomMargin=12 * mm,
        title=titulo,
    )
    doc.build(
        story,
        canvasmaker=partial(
            NumberedCanvas,
            numero_orcamento=num_versao_fmt,
            data_orcamento=data_str,
        ),
    )

    return output_path
