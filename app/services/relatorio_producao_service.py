"""Relatório PDF da lista de obras (ação do IA Martelo).

Ação SEGURA: só lê os dados que já estão na lista e escreve um PDF local — nada
sai para fora, nada é alterado. O IA Martelo faz a pesquisa; este serviço põe
as obras encontradas num relatório apresentável.

Segue o padrão de ``plano_corte_pdf_export.py``: import do reportlab protegido
(``REPORTLAB_DISPONIVEL``), cores hardcoded, A4 landscape.
"""

from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape

from app.domain.datas import normalizar_data

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
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
    colors = A4 = landscape = mm = ImageReader = None
    Image = ParagraphStyle = Paragraph = SimpleDocTemplate = Spacer = Table = TableStyle = None

# Tons do Martelo (castanho/bege), iguais ao tema da app (hardcoded aqui para o
# PDF não depender de app.ui.tema).
_CASTANHO = "#5A3E2B"      # castanho escuro: cabeçalhos e títulos
_CASTANHO_MEDIO = "#8B6F4E"
_BEGE = "#F7F2EA"          # bege claro: linhas alternadas
_BEGE_AREIA = "#EFE7DA"
_CINZA = "#D9CFC2"         # cinza-castanho: grelha
_TEXTO = "#2E2A26"

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
        "titulo", fontName="Helvetica-Bold", fontSize=15, textColor=colors.HexColor(_CASTANHO)
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
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_CASTANHO)),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(_CINZA)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for linha in range(1, n_linhas):
        if linha % 2 == 0:
            comandos.append(
                ("BACKGROUND", (0, linha), (-1, linha), colors.HexColor(_BEGE))
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


def gerar_dossier_obra_pdf(dossier, *, caminho: str | Path, gerado_em: str = "") -> Path:
    """PDF do ponto de situação de UMA obra (para o cliente).

    Espelha o resumo aprovado: dados da obra + estado + fases de produção.
    NÃO inclui notas internas nem preço (são internos, não vão para o cliente).
    ``gerado_em`` (data) é passado por quem chama, para ser determinístico.
    """
    if not REPORTLAB_DISPONIVEL:
        raise RuntimeError(
            "O reportlab não está instalado; não é possível gerar o PDF."
        )

    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)

    titulo = ParagraphStyle(
        "t", fontName="Helvetica-Bold", fontSize=16, leading=20,
        textColor=colors.HexColor(_CASTANHO), spaceAfter=6,
    )
    sub = ParagraphStyle(
        "s", fontName="Helvetica", fontSize=9, leading=12,
        textColor=colors.HexColor("#6B5A48"),
    )
    h = ParagraphStyle(
        "h", fontName="Helvetica-Bold", fontSize=11, leading=14,
        textColor=colors.HexColor(_CASTANHO), spaceBefore=10, spaceAfter=4,
    )
    cel = ParagraphStyle("c", fontName="Helvetica", fontSize=9.5, leading=13)
    rot = ParagraphStyle(
        "r", fontName="Helvetica-Bold", fontSize=9.5, leading=13,
        textColor=colors.HexColor(_TEXTO),
    )

    identidade = dossier.codigo or (f"Obra {dossier.enc}" if dossier.enc else "Obra")
    if dossier.cliente:
        identidade += f"  —  {dossier.cliente}"

    def _linha(rotulo: str, valor: str):
        return [Paragraph(rotulo, rot), Paragraph(escape(valor or "—"), cel)]

    info = []
    if dossier.obra:
        info.append(_linha("Obra:", dossier.obra))
    if dossier.ref_cliente:
        info.append(_linha("Ref. cliente:", dossier.ref_cliente))
    if dossier.localizacao:
        info.append(_linha("Localização:", dossier.localizacao))
    info += [
        _linha("Estado:", dossier.estado_local),
        _linha("Responsável:", dossier.responsavel),
        _linha("Início:", dossier.data_inicio),
        _linha("Entrega prevista:", dossier.data_entrega),
    ]
    if dossier.enc:
        info.append(_linha("Nº encomenda:", dossier.enc))

    tabela_info = Table(info, colWidths=[35 * mm, None])
    tabela_info.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story = [Paragraph("Ponto de Situação da Obra", titulo)]
    story.append(Spacer(1, 1 * mm))
    story.append(Paragraph(escape(identidade), sub))
    if gerado_em:
        story.append(Paragraph(f"Gerado em {escape(gerado_em)}", sub))
    story += [Spacer(1, 6 * mm), tabela_info]

    imagem = _imagem_flowable(getattr(dossier, "imagem_path", ""), 150 * mm, 95 * mm)
    if imagem is not None:
        story += [Spacer(1, 5 * mm), imagem]

    if dossier.descricao_producao:
        story += [
            Paragraph("Descrição", h),
            Paragraph(escape(dossier.descricao_producao), cel),
        ]

    versoes = getattr(dossier, "versoes", ()) or ()
    if versoes:
        story.append(Paragraph("Versões da obra e planos de corte", h))
        story.append(_tabela_versoes(versoes))

    # A tabela de fases é intitulada com o PROCESSO (nem todas as versões de
    # CUT-RITE têm o mesmo estado, por isso identifica-se qual é).
    titulo_fases = dossier.codigo or "Produção"
    story.append(Paragraph(f"Produção · {escape(titulo_fases)}", h))
    if dossier.encontrado_streamlit and dossier.fases:
        global_txt = _estado_global_limpo(dossier.estado_global)
        if global_txt:
            story.append(Paragraph(f"Estado global: {escape(global_txt)}", cel))
        story.append(Spacer(1, 2 * mm))
        story.append(_tabela_fases(dossier.fases))
    else:
        story.append(
            Paragraph("Estado detalhado de produção indisponível de momento.", cel)
        )

    doc = SimpleDocTemplate(
        str(destino), pagesize=A4,
        leftMargin=11 * mm, rightMargin=11 * mm, topMargin=10 * mm, bottomMargin=10 * mm,
        title="Ponto de Situação da Obra",
    )
    doc.build(story)
    return destino


def _tabela_fases(fases) -> Table:
    cel = ParagraphStyle("fc", fontName="Helvetica", fontSize=9.5)
    cab = ParagraphStyle("fh", fontName="Helvetica-Bold", fontSize=9.5, textColor=colors.white)
    linhas = [[Paragraph("Setor", cab), Paragraph("Conclusão", cab)]]
    for nome, pct, concluido in fases:
        texto = f"{pct:.0f}%" + (" — concluído" if concluido else "")
        linhas.append([Paragraph(escape(str(nome)), cel), Paragraph(texto, cel)])

    tabela = Table(linhas, colWidths=[60 * mm, 50 * mm], repeatRows=1)
    comandos = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_CASTANHO)),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(_CINZA)),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(linhas)):
        if i % 2 == 0:
            comandos.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor(_BEGE)))
    tabela.setStyle(TableStyle(comandos))
    return tabela


def _tabela_versoes(versoes) -> Table:
    """Tabela das versões da obra: V. Obra | Plano de corte | Estado | Produção."""
    cel = ParagraphStyle("vc", fontName="Helvetica", fontSize=9)
    cab = ParagraphStyle("vh", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)
    titulos = ["Versão de obra", "Plano de corte", "Estado", "Produção"]
    linhas = [[Paragraph(t, cab) for t in titulos]]
    for versao in versoes:
        producao = _estado_global_limpo(versao.estado_global) or "—"
        linhas.append(
            [
                Paragraph(escape(versao.versao_obra or "—"), cel),
                Paragraph(escape(versao.versao_plano or "—"), cel),
                Paragraph(escape(versao.estado_local or "—"), cel),
                Paragraph(escape(producao), cel),
            ]
        )

    tabela = Table(linhas, colWidths=[32 * mm, 32 * mm, 34 * mm, None], repeatRows=1)
    comandos = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_CASTANHO_MEDIO)),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(_CINZA)),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(linhas)):
        if i % 2 == 0:
            comandos.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor(_BEGE)))
    tabela.setStyle(TableStyle(comandos))
    return tabela


def _imagem_flowable(caminho: str, max_w: float, max_h: float):
    """Imagem IMOS à escala (mantém proporção); None se não existir/falhar."""
    if not caminho:
        return None
    try:
        if not Path(caminho).is_file():
            return None
        largura, altura = ImageReader(caminho).getSize()
        if largura <= 0 or altura <= 0:
            return None
        escala = min(max_w / largura, max_h / altura)
        imagem = Image(caminho, width=largura * escala, height=altura * escala)
        imagem.hAlign = "CENTER"
        return imagem
    except Exception:  # noqa: BLE001 - imagem é acessória
        return None


def _estado_global_limpo(etiqueta: str) -> str:
    """Tira o emoji do início da etiqueta («🔄 28.6% (2/7)» -> «28.6% (2/7)»)."""
    return re.sub(r"^[^0-9]*", "", etiqueta or "").strip()
