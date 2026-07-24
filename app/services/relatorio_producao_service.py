"""Relatório PDF da lista de obras (ação do IA Martelo).

Ação SEGURA: só lê os dados que já estão na lista e escreve um PDF local — nada
sai para fora, nada é alterado. O IA Martelo faz a pesquisa; este serviço põe
as obras encontradas num relatório apresentável.

Segue o padrão de ``plano_corte_pdf_export.py``: import do reportlab protegido
(``REPORTLAB_DISPONIVEL``), cores hardcoded, A4 landscape.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from app.domain.datas import normalizar_data

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_DISPONIVEL = True
except ImportError:  # pragma: no cover - depende da instalação do ambiente
    REPORTLAB_DISPONIVEL = False
    colors = A4 = landscape = mm = None
    ParagraphStyle = Paragraph = SimpleDocTemplate = Spacer = Table = TableStyle = None

# Paleta Lança Encanto (hardcoded, como no plano de corte).
_AZUL_ESCURO = "#1F3864"
_AZUL_REALCE = "#EAF1FB"
_CINZA_GRELHA = "#9AA5B1"
_TEXTO = "#222222"

#: (título, atributo, largura mm). A descrição fica com o resto do espaço.
_COLUNAS: tuple[tuple[str, str, float], ...] = (
    ("Processo", "codigo_processo", 40),
    ("Cliente", "nome_cliente", 44),
    ("Estado", "estado", 22),
    ("Resp.", "responsavel", 22),
    ("Início", "data_inicio", 20),
    ("Entrega", "data_entrega", 20),
    ("Qt", "qt_artigos", 12),
    ("Preço", "preco_total", 24),
    ("Descrição produção", "descricao_producao", 72),
)


def gerar_relatorio_obras_pdf(
    processos,
    *,
    titulo: str,
    subtitulo: str,
    caminho: str | Path,
) -> Path:
    """Escreve um PDF com a lista de obras e devolve o caminho.

    ``processos`` são objetos com os atributos das obras (o read model da
    Produção). ``subtitulo`` é montado por quem chama (ex.: a pergunta feita e a
    contagem), para o serviço ficar determinístico e testável.
    """
    if not REPORTLAB_DISPONIVEL:
        raise RuntimeError(
            "O reportlab não está instalado; não é possível gerar o PDF."
        )

    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)

    estilo_titulo = ParagraphStyle(
        "titulo", fontName="Helvetica-Bold", fontSize=15, textColor=colors.HexColor(_AZUL_ESCURO)
    )
    estilo_sub = ParagraphStyle(
        "sub", fontName="Helvetica", fontSize=9, textColor=colors.HexColor(_TEXTO)
    )
    estilo_cel = ParagraphStyle(
        "cel", fontName="Helvetica", fontSize=7.5, leading=9, textColor=colors.HexColor(_TEXTO)
    )
    estilo_cab = ParagraphStyle(
        "cab", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white
    )

    largura_util = landscape(A4)[0] - 20 * mm
    larguras = _larguras_colunas(largura_util)

    cabecalho = [Paragraph(escape(nome), estilo_cab) for nome, _attr, _larg in _COLUNAS]
    linhas = [cabecalho]
    for processo in processos or []:
        linhas.append(
            [Paragraph(_valor(processo, attr), estilo_cel) for _titulo, attr, _larg in _COLUNAS]
        )

    tabela = Table(linhas, colWidths=larguras, repeatRows=1)
    tabela.setStyle(_estilo_tabela(len(linhas)))

    doc = SimpleDocTemplate(
        str(destino),
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=titulo,
    )
    story = [
        Paragraph(escape(titulo), estilo_titulo),
        Spacer(1, 3 * mm),
        Paragraph(escape(subtitulo), estilo_sub),
        Spacer(1, 5 * mm),
        tabela,
    ]
    doc.build(story)
    return destino


def _larguras_colunas(largura_util: float) -> list[float]:
    base = [larg * mm for _titulo, _attr, larg in _COLUNAS]
    total = sum(base)
    if total <= largura_util:
        # Dá o espaço que sobra à última coluna (descrição).
        base[-1] += largura_util - total
        return base
    # Encolhe proporcionalmente se não couber.
    fator = largura_util / total
    return [largura * fator for largura in base]


def _estilo_tabela(n_linhas: int) -> TableStyle:
    comandos = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_AZUL_ESCURO)),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(_CINZA_GRELHA)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for linha in range(1, n_linhas):
        if linha % 2 == 0:
            comandos.append(
                ("BACKGROUND", (0, linha), (-1, linha), colors.HexColor(_AZUL_REALCE))
            )
    return TableStyle(comandos)


def _valor(processo, atributo: str) -> str:
    valor = getattr(processo, atributo, None)
    if valor is None:
        return ""
    if atributo in {"data_inicio", "data_entrega"}:
        return escape(normalizar_data(valor) or "")
    if atributo == "preco_total":
        return escape(_preco(valor))
    return escape(str(valor).strip())


def _preco(valor) -> str:
    try:
        return f"{float(str(valor).replace(',', '.')):.2f} €"
    except (TypeError, ValueError):
        return str(valor).strip()
