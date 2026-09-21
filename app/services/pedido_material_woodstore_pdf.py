"""PDF «Pedido de criação de material no Woodstore», para as compras.

Quem cria as placas no Woodstore é a pessoa das compras, no programa próprio
do Woodstore. O Martelo junta num PDF o que ela precisa de saber sobre cada
material que falta: o nome que a lista usa, a espessura, as peças e as orlas,
e os materiais mais parecidos que já existem (pode ser só o nome escrito de
outra forma). Segue o padrão reportlab de `relatorio_producao_service.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.sax.saxutils import escape

from app.domain.referencias_placa import referencias

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        KeepTogether,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_DISPONIVEL = True
except ImportError:  # pragma: no cover - depende da instalação do ambiente
    REPORTLAB_DISPONIVEL = False

_CASTANHO = "#5A3E2B"
_BEGE = "#F7F2EA"
_CINZA = "#D9CFC2"
_ORLAS = ("Orla ESQ", "Orla DIR", "Orla CIMA", "Orla BAIXO")


def _numero(valor) -> Decimal | None:
    try:
        numero = Decimal(str(valor).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    return numero if numero.is_finite() else None


def _texto_mm(valor: Decimal | None) -> str:
    if valor is None:
        return "—"
    return f"{valor.normalize():f}".replace(".", ",")


@dataclass
class MaterialPedido:
    nome: str
    pecas: int = 0
    linhas: int = 0
    espessuras: list[str] = field(default_factory=list)
    maior_comp: Decimal | None = None
    maior_larg: Decimal | None = None
    area_m2: Decimal = Decimal(0)
    orlas: list[str] = field(default_factory=list)
    descricoes: list[str] = field(default_factory=list)
    veio: list[str] = field(default_factory=list)
    referencias: list[str] = field(default_factory=list)
    parecidos_woodstore: list[str] = field(default_factory=list)


def resumir_material(nome: str, linhas: list[dict], parecidos: list[str] = ()) -> MaterialPedido:
    """`linhas` = valores das linhas da LISTAGEM_CUT_RITE deste material."""
    pedido = MaterialPedido(nome=nome, referencias=sorted(referencias(nome)),
                            parecidos_woodstore=list(parecidos))
    espessuras, orlas, descricoes, veio = set(), set(), set(), set()
    for valores in linhas:
        qt = _numero(valores.get("Qt")) or Decimal(0)
        comp, larg = _numero(valores.get("Comp")), _numero(valores.get("Larg"))
        pedido.pecas += int(qt)
        pedido.linhas += 1
        if comp is not None:
            pedido.maior_comp = max(pedido.maior_comp or comp, comp)
        if larg is not None:
            pedido.maior_larg = max(pedido.maior_larg or larg, larg)
        if comp is not None and larg is not None:
            pedido.area_m2 += comp * larg * qt / Decimal(1_000_000)
        esp = _numero(valores.get("Esp"))
        if esp is not None:
            # A Esp da lista traz a tolerância da máquina (30,2): pede-se a nominal.
            espessuras.add(_texto_mm(esp.quantize(Decimal("1"))))
        for lado in _ORLAS:
            orla = str(valores.get(lado) or "").strip()
            if orla and "CNC" not in orla.upper():
                orlas.add(orla)
        if valores.get("Descricao"):
            descricoes.add(str(valores["Descricao"]).strip())
        if valores.get("Veio"):
            veio.add(str(valores["Veio"]).strip())
    pedido.espessuras = sorted(espessuras)
    pedido.orlas = sorted(orlas)
    pedido.descricoes = sorted(descricoes)
    pedido.veio = sorted(veio)
    pedido.area_m2 = pedido.area_m2.quantize(Decimal("0.01"))
    return pedido


def gerar_pedido_pdf(
    caminho: Path | str,
    *,
    obra: dict,
    materiais: list[MaterialPedido],
    gerado_em: str,
    pedido_por: str,
) -> Path:
    if not REPORTLAB_DISPONIVEL:
        raise RuntimeError("O reportlab não está instalado; não é possível gerar o PDF.")
    if not materiais:
        raise ValueError("Nenhum material para pedir.")
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)

    titulo = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=16, leading=20,
                            textColor=colors.HexColor(_CASTANHO))
    sub = ParagraphStyle("s", fontName="Helvetica", fontSize=9, leading=12,
                         textColor=colors.HexColor("#6B5A48"))
    h = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=12, leading=15,
                       textColor=colors.HexColor(_CASTANHO), spaceBefore=8, spaceAfter=4)
    cel = ParagraphStyle("c", fontName="Helvetica", fontSize=9.5, leading=12.5)
    rot = ParagraphStyle("r", fontName="Helvetica-Bold", fontSize=9.5, leading=12.5)

    def tabela(pares):
        linhas = [[Paragraph(escape(a), rot), Paragraph(escape(b or "—"), cel)] for a, b in pares]
        t = Table(linhas, colWidths=[48 * mm, None])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(_CINZA)),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(_BEGE)),
        ]))
        return t

    story = [
        Paragraph("Pedido de criação de material no Woodstore", titulo),
        Paragraph(escape(f"Gerado em {gerado_em} por {pedido_por}"), sub),
        Spacer(1, 4 * mm),
        tabela([
            ("Obra / processo", obra.get("processo", "")),
            ("Cliente", obra.get("cliente", "")),
            ("Responsável", obra.get("responsavel", "")),
            ("Nº Enc PHC", obra.get("enc_phc", "")),
            ("Plano Cut-Rite", obra.get("plano", "")),
        ]),
        Spacer(1, 4 * mm),
        Paragraph(
            "Os materiais abaixo estão na Lista Material desta obra mas não existem "
            "no Woodstore; sem eles o Cut-Rite não corta estas peças. Pedimos que "
            "sejam criados com o nome indicado — ou que nos digam o nome certo, se "
            "o material já existir escrito de outra forma (ver «Parecidos no "
            "Woodstore»).",
            cel,
        ),
    ]
    for numero, m in enumerate(materiais, 1):
        bloco = [
            Paragraph(escape(f"{numero}. {m.nome}"), h),
            tabela([
                ("Nome a criar", m.nome),
                ("Referência(s) de decoração", ", ".join(m.referencias)),
                ("Espessura nominal (mm)", " / ".join(m.espessuras)),
                ("Peças / linhas", f"{m.pecas} / {m.linhas}"),
                ("Maior peça (comp × larg mm)",
                 f"{_texto_mm(m.maior_comp)} × {_texto_mm(m.maior_larg)}"),
                ("Área das peças", f"{_texto_mm(m.area_m2)} m²"),
                ("Veio", ", ".join(m.veio)),
                ("Orlas usadas", ", ".join(m.orlas)),
                ("Peças (descrição)", ", ".join(m.descricoes[:12])),
                ("Parecidos no Woodstore", ", ".join(m.parecidos_woodstore) or "nenhum"),
            ]),
        ]
        story.append(KeepTogether(bloco))

    doc = SimpleDocTemplate(
        str(destino), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
        title="Pedido de criação de material no Woodstore",
    )
    doc.build(story)
    return destino
