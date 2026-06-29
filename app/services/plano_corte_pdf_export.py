"""Gerador do PDF do plano de corte (C3.3) — moderno e legível.

Consome os ``GrupoCorte`` (C3.2) e o otimizador ``empacotar`` (C3.1, com
``rotacao=True``) e produz um PDF A4 LANDSCAPE com:

- uma página de RESUMO que compara as PLACAS DO ORÇAMENTO com as PLACAS DO
  OTIMIZADOR (a feature nova);
- uma página por cada placa de cada grupo, com o desenho à escala das peças;
- uma página por grupo com peças não alocadas, quando existam.

O ``import`` do reportlab é protegido (``REPORTLAB_DISPONIVEL``), como em
``orcamento_pdf_export.py``; a função levanta ``RuntimeError`` se for chamada sem
ele. Cores hardcoded (não importa ``app.ui.tema``).
"""

from __future__ import annotations

from functools import partial
from pathlib import Path
from xml.sax.saxutils import escape

from app.domain.plano_corte_dados import (
    construir_resumo_corte,
    empacotar_grupos,
)

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        Flowable,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_DISPONIVEL = True
except ImportError:  # pragma: no cover - depende da instalação do ambiente
    REPORTLAB_DISPONIVEL = False
    colors = A4 = landscape = mm = canvas = None
    ParagraphStyle = Flowable = PageBreak = Paragraph = None
    SimpleDocTemplate = Spacer = Table = TableStyle = None
    TA_CENTER = TA_LEFT = None


# Paleta Lança Encanto (hardcoded): azul escuro de cabeçalho, realce/zebra clara,
# verde/vermelho para a diferença de placas.
_AZUL_ESCURO = "#1F3864"
_AZUL_REALCE = "#EAF1FB"
_VERDE = "#1E7B34"
_VERMELHO = "#C00000"
_CINZA_GRELHA = "#9AA5B1"
_PLACA_FUNDO = "#F5F6F8"
_PLACA_BORDO = "#333333"
_PECA_BORDO = "#37474F"

# Paleta suave (ciclada) para o preenchimento das peças.
_PALETA_PECAS = (
    "#BBDEFB", "#C8E6C9", "#FFE0B2", "#F8BBD0",
    "#D1C4E9", "#B2EBF2", "#DCEDC8", "#FFF9C4",
)

_COLUNAS_RESUMO = (
    ("Material", 70),
    ("Esp (mm)", 22),
    ("Dimensão (mm)", 36),
    ("Placas Orçamento", 33),
    ("Placas Otimizador", 33),
    ("Δ", 16),
    ("Aproveitamento %", 35),
    ("Não alocadas", 28),
)


def _area_pecas_placa(placa) -> float:
    return sum(peca.comp * peca.larg for peca in placa.pecas)


def _aproveitamento_placa(placa) -> float:
    area_placa = (placa.comp or 0) * (placa.larg or 0)
    if area_placa <= 0:
        return 0.0
    return round(_area_pecas_placa(placa) / area_placa * 100, 1)


if REPORTLAB_DISPONIVEL:

    class NumberedCanvas(canvas.Canvas):
        """Canvas com rodapé "Plano de Corte {versão} | Pág X de Y".

        Padrão de dois passos do reportlab (igual ao de
        ``orcamento_pdf_export.py``): guarda o estado de cada página e só desenha
        o rodapé no ``save`` final, quando o total já é conhecido.
        """

        def __init__(self, *args, **kwargs) -> None:
            self._rodape_esquerda = kwargs.pop("rodape_esquerda", "Plano de Corte")
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
            largura, _altura = landscape(A4)
            self.setFont("Helvetica", 7)
            self.setFillColor(colors.grey)
            self.drawString(10 * mm, 6 * mm, self._rodape_esquerda)
            self.drawRightString(
                largura - 10 * mm,
                6 * mm,
                f"Pág {self._pageNumber} de {total_paginas}",
            )

    class _PlacaFlowable(Flowable):
        """Desenha uma placa à escala com as peças colocadas."""

        def __init__(self, placa) -> None:
            super().__init__()
            self.placa = placa
            self._largura = 0.0
            self._altura = 0.0

        def wrap(self, availWidth, availHeight):  # noqa: N803 (API reportlab)
            self._largura = availWidth
            self._altura = availHeight
            return availWidth, availHeight

        def draw(self) -> None:
            _desenhar_placa(self.canv, self._largura, self._altura, self.placa)

else:  # pragma: no cover - sem reportlab as classes não existem
    NumberedCanvas = None
    _PlacaFlowable = None


def _desenhar_placa(c, area_w, area_h, placa) -> None:
    """Desenha a placa (retângulo escalado + cotas + peças) na área dada."""
    cota_esq = 14 * mm
    cota_baixo = 11 * mm
    pad_topo = 6 * mm
    pad_dir = 6 * mm

    placa_comp = float(placa.comp or 0)
    placa_larg = float(placa.larg or 0)
    if placa_comp <= 0 or placa_larg <= 0:
        return

    drawable_w = max(area_w - cota_esq - pad_dir, 1)
    drawable_h = max(area_h - cota_baixo - pad_topo, 1)
    escala = min(drawable_w / placa_comp, drawable_h / placa_larg)

    placa_w = placa_comp * escala
    placa_h = placa_larg * escala
    ox = cota_esq + (drawable_w - placa_w) / 2
    oy = cota_baixo + (drawable_h - placa_h) / 2

    # Retângulo da placa.
    c.setLineWidth(1)
    c.setStrokeColor(colors.HexColor(_PLACA_BORDO))
    c.setFillColor(colors.HexColor(_PLACA_FUNDO))
    c.rect(ox, oy, placa_w, placa_h, stroke=1, fill=1)

    # Peças.
    for indice, peca in enumerate(placa.pecas):
        px = ox + float(peca.x) * escala
        py = oy + float(peca.y) * escala
        pw = float(peca.comp) * escala
        ph = float(peca.larg) * escala
        cor = _PALETA_PECAS[indice % len(_PALETA_PECAS)]
        c.setFillColor(colors.HexColor(cor))
        c.setStrokeColor(colors.HexColor(_PECA_BORDO))
        c.setLineWidth(0.4)
        c.rect(px, py, pw, ph, stroke=1, fill=1)
        _etiqueta_peca(c, peca, px, py, pw, ph)

    # Cotas.
    c.setFillColor(colors.HexColor(_PLACA_BORDO))
    c.setFont("Helvetica", 7)
    c.drawCentredString(
        ox + placa_w / 2,
        max(oy - 7 * mm, 3 * mm),
        f"XX (Comp): {int(placa_comp)} mm",
    )
    c.saveState()
    c.translate(max(ox - 7 * mm, 4 * mm), oy + placa_h / 2)
    c.rotate(90)
    c.drawCentredString(0, 0, f"YY (Larg): {int(placa_larg)} mm")
    c.restoreState()


def _etiqueta_peca(c, peca, px, py, pw, ph) -> None:
    """Escreve a etiqueta da peça se couber (senão encurta ou omite)."""
    fonte = "Helvetica"
    tamanho = 6.5
    if ph < tamanho + 2 or pw < 10:
        return
    completa = f"{peca.desc} ({int(peca.comp)}x{int(peca.larg)})"
    curta = f"{int(peca.comp)}x{int(peca.larg)}"
    texto = None
    if c.stringWidth(completa, fonte, tamanho) <= pw - 3:
        texto = completa
    elif c.stringWidth(curta, fonte, tamanho) <= pw - 3:
        texto = curta
    if texto is None:
        return
    c.setFillColor(colors.HexColor("#1A1A1A"))
    c.setFont(fonte, tamanho)
    c.drawCentredString(px + pw / 2, py + ph / 2 - tamanho / 2, texto)


def gerar_pdf_plano_corte(
    output_path,
    *,
    grupos,
    num_versao: str = "",
    kerf: float = 3.0,
    rotacao: bool = True,
) -> Path:
    """Gera o PDF do plano de corte em ``output_path`` e devolve o ``Path``."""
    if not REPORTLAB_DISPONIVEL:
        raise RuntimeError("reportlab não está instalado")

    output_path = Path(output_path)

    resultados = empacotar_grupos(grupos, kerf=kerf, rotacao=rotacao)
    linhas = construir_resumo_corte(resultados)

    story: list = []
    story.extend(_pagina_resumo(linhas, num_versao))

    for item in resultados:
        grupo = item.grupo
        placas = item.resultado.placas
        total = len(placas)
        for indice, placa in enumerate(placas, start=1):
            story.extend(_pagina_placa(grupo, placa, indice, total))
        if item.resultado.nao_alocadas:
            story.extend(_pagina_nao_alocadas(grupo, item.resultado.nao_alocadas))

    rodape = f"Plano de Corte {num_versao}".strip()
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=14 * mm,
        title="Plano de Corte",
    )
    doc.build(story, canvasmaker=partial(NumberedCanvas, rodape_esquerda=rodape))

    return output_path


def _pagina_resumo(linhas, num_versao: str) -> list:
    """Página 1: banda de título + tabela comparativa orçamento vs otimizador."""
    largura_total = sum(largura for _nome, largura in _COLUNAS_RESUMO) * mm

    titulo_estilo = ParagraphStyle(
        "TituloBanda",
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.white,
    )
    titulo_txt = "Plano de Corte"
    if num_versao:
        titulo_txt += f" &nbsp;—&nbsp; Orçamento {escape(num_versao)}"
    banda = Table(
        [[Paragraph(titulo_txt, titulo_estilo)]], colWidths=[largura_total]
    )
    banda.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(_AZUL_ESCURO)),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    cabecalho_estilo = ParagraphStyle(
        "ResumoCab",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=9,
        alignment=TA_CENTER,
        textColor=colors.white,
    )
    dados = [[Paragraph(nome, cabecalho_estilo) for nome, _largura in _COLUNAS_RESUMO]]

    total_orc = 0
    total_otim = 0
    for linha in linhas:
        total_orc += linha.placas_orcamento
        total_otim += linha.placas_otimizador
        diferenca = f"+{linha.diferenca}" if linha.diferenca > 0 else str(linha.diferenca)
        dados.append(
            [
                linha.ref,
                _fmt_num(linha.esp),
                linha.dim_placa,
                str(linha.placas_orcamento),
                str(linha.placas_otimizador),
                diferenca,
                _fmt_num(linha.aproveitamento_pct),
                str(linha.nao_alocadas),
            ]
        )

    linha_totais = len(dados)
    dados.append(
        ["TOTAL", "", "", str(total_orc), str(total_otim), "", "", ""]
    )

    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_AZUL_ESCURO)),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(_CINZA_GRELHA)),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        # Linha de totais a negrito com realce.
        ("FONTNAME", (0, linha_totais), (-1, linha_totais), "Helvetica-Bold"),
        ("BACKGROUND", (0, linha_totais), (-1, linha_totais), colors.HexColor(_AZUL_REALCE)),
        ("LINEABOVE", (0, linha_totais), (-1, linha_totais), 1, colors.HexColor(_AZUL_ESCURO)),
    ]
    # Zebra clara nas linhas de dados.
    for indice in range(1, linha_totais):
        if indice % 2 == 1:
            estilo.append(
                ("BACKGROUND", (0, indice), (-1, indice), colors.HexColor(_AZUL_REALCE))
            )
    # Coluna Δ: verde se poupa (<0), vermelho se gasta mais (>0).
    for indice, linha in enumerate(linhas, start=1):
        if linha.diferenca < 0:
            cor = colors.HexColor(_VERDE)
        elif linha.diferenca > 0:
            cor = colors.HexColor(_VERMELHO)
        else:
            continue
        estilo.append(("TEXTCOLOR", (5, indice), (5, indice), cor))
        estilo.append(("FONTNAME", (5, indice), (5, indice), "Helvetica-Bold"))

    larguras = [largura * mm for _nome, largura in _COLUNAS_RESUMO]
    tabela = Table(dados, colWidths=larguras, repeatRows=1)
    tabela.setStyle(TableStyle(estilo))

    return [banda, Spacer(1, 6 * mm), tabela, PageBreak()]


def _pagina_placa(grupo, placa, indice: int, total: int) -> list:
    """Uma página por placa: cabeçalho + desenho à escala."""
    cabecalho_estilo = ParagraphStyle(
        "PlacaCab",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=13,
        alignment=TA_LEFT,
        textColor=colors.HexColor(_AZUL_ESCURO),
    )
    pct = _aproveitamento_placa(placa)
    texto = (
        f"{escape(str(grupo.ref))} &nbsp;|&nbsp; Esp {_fmt_num(grupo.esp)} "
        f"&nbsp;|&nbsp; Placa {indice}/{total} "
        f"&nbsp;|&nbsp; Aproveitamento {_fmt_num(pct)}%"
    )
    return [
        Paragraph(texto, cabecalho_estilo),
        Spacer(1, 3 * mm),
        _PlacaFlowable(placa),
        PageBreak(),
    ]


def _pagina_nao_alocadas(grupo, nao_alocadas) -> list:
    """Página com a lista de peças não alocadas de um grupo."""
    titulo_estilo = ParagraphStyle(
        "NaoAlocTitulo",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor(_VERMELHO),
    )
    item_estilo = ParagraphStyle(
        "NaoAlocItem", fontName="Helvetica", fontSize=9, leading=12
    )
    story = [
        Paragraph(f"Peças não alocadas — {escape(str(grupo.ref))}", titulo_estilo),
        Spacer(1, 3 * mm),
    ]
    for peca in nao_alocadas:
        story.append(
            Paragraph(
                f"• {escape(str(peca.desc))} "
                f"({int(peca.comp)} x {int(peca.larg)} mm)",
                item_estilo,
            )
        )
    story.append(PageBreak())
    return story


def _fmt_num(valor) -> str:
    """Formata um número: sem casas se inteiro, senão até 2 casas (vírgula)."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    if numero == int(numero):
        return str(int(numero))
    return f"{numero:.2f}".rstrip("0").rstrip(".").replace(".", ",")
