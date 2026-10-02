"""Folha de horas do mês em PDF (a que segue para a contabilidade).

Copia a folha em papel que o Paulo usava: Dia, Entrada/Saída duas vezes (o 2.º
período é o das horas feitas em casa) e as observações — mas com as horas
normais e as extra em colunas separadas, porque é essa a separação que a
contabilidade precisa para pagar. No fim, o resumo do mês com as extra por
tipo de dia (dias úteis, sábados, domingos, feriados, férias): a lei paga-as
de forma diferente, e é por aí que um dia entram os valores em euros.

Segue o padrão reportlab de `pedido_material_woodstore_pdf.py`.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape

from app.domain import registo_horas as regra

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
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

#: Cores do manual de marca da Lança Encanto.
_CASTANHO = "#593621"
_BEGE = "#F4EBDC"
_CINZA = "#D9CFC2"
_FIM_SEMANA = "#F7F2EA"
_VERMELHO = "#7A231C"
_RODAPE = (
    "LANÇA ENCANTO · Rua dos Bombeiros Voluntários de Ourém nº 14, Vilar dos "
    "Prazeres · 2490-755 Ourém · www.lancaencanto.pt"
)
#: Proporção do LE_Logotipo.png (4271 × 1732).
_LOGO_RACIO = 1732 / 4271


def _t(texto: str) -> str:
    """O Helvetica do PDF não tem o «−» tipográfico: vai o hífen."""
    return escape((texto or "").replace(regra.MENOS, "-"))


def _extra_folha(dia: regra.LinhaDia) -> str:
    if dia.tipo == regra.TIPO_FOLGA:
        return f"{regra.MENOS}{regra.formatar_horas(-dia.extra)}"
    if dia.tipo == regra.TIPO_UTIL:
        if dia.extra > 0:
            return f"+{regra.formatar_horas(dia.extra)}"
        if dia.extra < 0:
            return f"{regra.MENOS}{regra.formatar_horas(-dia.extra)}"
        return ""
    return regra.formatar_horas(dia.extra) if dia.extra > 0 else ""


def gerar_folha_pdf(
    caminho: Path | str,
    *,
    nome: str,
    ano: int,
    mes: int,
    dias: list[regra.LinhaDia],
    em_falta: list[date] | None = None,
    logo: Path | str | None = None,
    gerado_em: datetime | None = None,
) -> Path:
    if not REPORTLAB_DISPONIVEL:
        raise RuntimeError("O reportlab não está instalado; não é possível gerar o PDF.")
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    por_dia = {d.data: d for d in dias}
    resumo = regra.resumir_mes(dias)

    base = ParagraphStyle("base", fontName="Helvetica", fontSize=8, leading=10)
    celula = ParagraphStyle("celula", parent=base, fontSize=7.5, leading=9)
    titulo = ParagraphStyle(
        "titulo", parent=base, fontSize=18, leading=22, textColor=colors.HexColor(_CASTANHO),
        alignment=2,
    )
    campo = ParagraphStyle("campo", parent=base, fontSize=10, leading=13)
    rodape = ParagraphStyle(
        "rodape", parent=base, fontSize=7, leading=9, textColor=colors.HexColor(_CASTANHO),
        alignment=1,
    )

    historia = []
    esquerda = ""
    if logo is not None and Path(logo).is_file():
        largura = 45 * mm
        esquerda = Image(str(logo), width=largura, height=largura * _LOGO_RACIO)
        esquerda.hAlign = "LEFT"
    topo = Table(
        [[esquerda, Paragraph("Folha de <b>Horas</b>", titulo)]],
        colWidths=[90 * mm, 90 * mm],
    )
    topo.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    historia.append(topo)
    historia.append(Spacer(1, 4 * mm))
    campos = Table(
        [[
            Paragraph(f"Nome: <b>{_t(nome)}</b>", campo),
            Paragraph(f"Mês: <b>{_t(regra.MESES[mes - 1].capitalize())} – {ano}</b>", campo),
        ]],
        colWidths=[110 * mm, 70 * mm],
    )
    campos.setStyle(
        TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 0.6, colors.HexColor(_CASTANHO)),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    historia.append(campos)
    historia.append(Spacer(1, 4 * mm))

    cabecalho = ["Dia", "", "Entrada", "Saída", "Entrada", "Saída", "Normais", "Extra", "Observações"]
    linhas = [cabecalho]
    estilos = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_CASTANHO)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor(_CINZA)),
        ("ALIGN", (0, 0), (-2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]
    for indice, dia_data in enumerate(regra.dias_do_mes(ano, mes), start=1):
        dia = por_dia.get(dia_data)
        nome_feriado = regra.feriado(dia_data)
        if dia is None:
            obs = f"Feriado – {nome_feriado}" if nome_feriado else ""
            if em_falta and dia_data in em_falta:
                obs = "Por registar"
                estilos.append(("TEXTCOLOR", (8, indice), (8, indice), colors.HexColor(_VERMELHO)))
            linha = [str(dia_data.day), regra.SEMANA_CURTO[dia_data.weekday()], "", "", "", "", "", "", Paragraph(_t(obs), celula)]
        else:
            util = dia.tipo == regra.TIPO_UTIL
            segundo = util and dia.entrada2 is not None
            obs = dia.observacoes_folha()
            if nome_feriado and dia.tipo == regra.TIPO_FERIADO:
                obs = " – ".join(p for p in (f"Feriado ({nome_feriado})", dia.observacoes) if p)
            linha = [
                str(dia_data.day),
                regra.SEMANA_CURTO[dia_data.weekday()],
                regra.formatar_hora(dia.entrada).upper() if util else "",
                regra.formatar_hora(dia.saida).upper() if util else "",
                regra.formatar_hora(dia.entrada2).upper() if segundo else "",
                regra.formatar_hora(dia.saida2).upper() if segundo else "",
                regra.formatar_horas(dia.normais) if dia.normais else "",
                _t(_extra_folha(dia)),
                Paragraph(_t(obs), celula),
            ]
            if dia.extra < 0:
                estilos.append(("TEXTCOLOR", (7, indice), (7, indice), colors.HexColor(_VERMELHO)))
        if regra.e_fim_de_semana(dia_data) or nome_feriado:
            estilos.append(("BACKGROUND", (0, indice), (-1, indice), colors.HexColor(_FIM_SEMANA)))
        linhas.append(linha)
    tabela = Table(
        linhas,
        colWidths=[9 * mm, 9 * mm, 16 * mm, 16 * mm, 16 * mm, 16 * mm, 15 * mm, 15 * mm, 68 * mm],
        repeatRows=1,
    )
    tabela.setStyle(TableStyle(estilos))
    historia.append(tabela)
    historia.append(Spacer(1, 5 * mm))

    totais = [[Paragraph(_t(rotulo), base), Paragraph(f"<b>{_t(valor)}</b>", base)] for rotulo, valor in resumo.linhas()]
    quadro = Table(totais, colWidths=[70 * mm, 25 * mm], hAlign="LEFT")
    quadro.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor(_CINZA)),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor(_BEGE)),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ])
    )
    contagens = (
        f"Dias registados: {resumo.dias_registados} · dias úteis trabalhados: "
        f"{resumo.dias_uteis} · férias: {resumo.dias_ferias} · feriados: "
        f"{resumo.dias_feriado} · folgas: {resumo.dias_folga}"
    )
    notas = [Paragraph(_t(contagens), base), Spacer(1, 2 * mm)]
    if em_falta:
        dias_txt = ", ".join(str(d.day) for d in em_falta)
        notas.append(Paragraph(f"<font color='{_VERMELHO}'>Dias úteis sem registo: {_t(dias_txt)}</font>", base))
        notas.append(Spacer(1, 2 * mm))
    notas.append(Paragraph(_t("Cada mês fecha por si: o saldo não passa para o mês seguinte."), base))
    lado = Table([[quadro, notas]], colWidths=[100 * mm, 80 * mm])
    lado.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (0, 0), 0)]))
    historia.append(lado)
    historia.append(Spacer(1, 6 * mm))
    quando = (gerado_em or datetime.now()).strftime("%d/%m/%Y %H:%M")
    historia.append(Paragraph(f"<b>{_t(_RODAPE)}</b>", rodape))
    historia.append(Paragraph(_t(f"Gerado pelo Martelo em {quando}"), rodape))

    documento = SimpleDocTemplate(
        str(destino),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Folha de horas — {nome} — {regra.nome_mes(ano, mes)}",
        author=nome,
    )
    documento.build(historia)
    return destino
