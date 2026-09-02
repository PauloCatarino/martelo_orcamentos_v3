"""Gerador do Excel do orçamento no FORMATO PHC (port do Martelo V2).

Reproduz a folha "PHC" do V2 (``_export_excel_phc_full``), confirmada pelo
modelo real ``260618_01_PHC.xlsx``, para ser importada pelo PHC.

Cada item gera uma linha principal (RefCliente/Referencia/Designacao + dimensões
numéricas + Qtd/Und/Venda) e, por cada linha extra da descrição, uma linha só
com a coluna ``Designacao`` (C) preenchida. A coluna ``Venda`` é escrita como
TEXTO ("1191,62", vírgula decimal) com formato ``"@"`` para o PHC a ler tal e
qual.

**Formato ``.xls`` (BIFF8), não ``.xlsx``**: é o que o PHC importa sem
reclamar. Daí o ``xlwt`` em vez do ``openpyxl`` usado no resto do programa.

**Designação partida aos 55 caracteres**: o PHC corta a designação nesse
comprimento e o que passa disso desaparece na importação, sem aviso. A regra da
quebra está em :mod:`app.domain.texto_phc`.

Recebe DADOS simples (read-models ou ``SimpleNamespace``), sem DB nem Qt, para
ser testável.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import xlwt

from app.domain.descricao_format import parse_descricao
from app.domain.texto_phc import quebrar_designacao

# Cabeçalho da folha "PHC" (colunas A..I), na ordem esperada pelo PHC.
_HEADERS = [
    "RefCliente",
    "Referencia",
    "Designacao",
    "XAltura",
    "YLargura",
    "ZEspessura",
    "Qtd",
    "Und",
    "Venda",
]
_PREFIXO = "COMP. MOB. - "
_REFERENCIA = "MOB"

#: Coluna (0-based) da designação e da venda.
_COL_DESIGNACAO = 2
_COL_VENDA = 8

#: Largura mínima/máxima das colunas, em caracteres (xlwt conta em 1/256 de
#: caractere).
_LARGURA_MIN = 10
_LARGURA_MAX = 60
_UNIDADE_LARGURA = 256


def _num(value) -> float | None:
    """Converte Decimal/número para float (None se vazio/inválido)."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _venda_texto(value) -> str | None:
    """Preço unitário -> texto "1191,62" (vírgula decimal, 2 casas).

    Devolve None quando o valor é vazio/inválido.
    """
    num = _num(value)
    if num is None:
        return None
    try:
        return f"{Decimal(str(num)):.2f}".replace(".", ",")
    except Exception:
        return None


def _texto_da_linha(linha) -> str:
    """A linha da descrição já com o prefixo que o PHC vê ("- ", "* ")."""
    if linha.tipo == "traco":
        return f"- {linha.texto}"
    if linha.tipo == "estrela":
        return f"* {linha.texto}"
    if linha.tipo == "titulo":
        return linha.texto.upper()
    return linha.texto


def linhas_do_item(item) -> list[list]:
    """As linhas da folha para UM item: a principal e as da descrição.

    Cada uma já cabe nos 55 caracteres da designação do PHC. Separado do
    ``xlwt`` de propósito, para se poder testar o conteúdo sem gravar ficheiro.
    """
    descricao = parse_descricao(getattr(item, "descricao", None))
    titulo = (
        descricao[0].texto
        if (descricao and descricao[0].tipo != "vazia")
        else ""
    )
    designacao = f"{_PREFIXO}{titulo.upper()}" if titulo else _PREFIXO.rstrip()

    und = (getattr(item, "unidade", "") or "").strip() or "un"
    und = "un" if und.lower() == "und" else und
    venda = _venda_texto(getattr(item, "preco_unitario", None))

    partidas = quebrar_designacao(designacao) or [""]
    linhas = [
        [
            getattr(item, "codigo", None) or "",
            _REFERENCIA,
            partidas[0],
            _num(getattr(item, "altura", None)),
            _num(getattr(item, "largura", None)),
            _num(getattr(item, "profundidade", None)),
            _num(getattr(item, "quantidade", None)),
            und,
            venda,
        ]
    ]
    # O resto do título continua em baixo, como qualquer linha de descrição.
    for continuacao in partidas[1:]:
        linhas.append(["", "", continuacao, None, None, None, None, None, None])

    for linha in descricao[1:]:
        if linha.tipo == "vazia":
            continue
        for pedaco in quebrar_designacao(_texto_da_linha(linha)):
            linhas.append(["", "", pedaco, None, None, None, None, None, None])

    return linhas


def gerar_excel_phc(output_path, *, orcamento, items) -> Path:
    """Gera o ficheiro ``.xls`` no formato PHC e devolve o ``Path``."""
    output_path = Path(output_path)

    livro = xlwt.Workbook(encoding="utf-8")
    folha = livro.add_sheet("PHC")
    estilo_texto = xlwt.easyxf(num_format_str="@")
    estilo_cabecalho = xlwt.easyxf("font: bold on")

    for coluna, titulo in enumerate(_HEADERS):
        folha.write(0, coluna, titulo, estilo_cabecalho)

    larguras = [len(titulo) for titulo in _HEADERS]
    indice = 1
    for item in items:
        for valores in linhas_do_item(item):
            for coluna, valor in enumerate(valores):
                if valor is None or valor == "":
                    continue
                if coluna == _COL_VENDA:
                    folha.write(indice, coluna, valor, estilo_texto)
                else:
                    folha.write(indice, coluna, valor)
                larguras[coluna] = max(larguras[coluna], len(str(valor)))
            indice += 1

    for coluna, largura in enumerate(larguras):
        folha.col(coluna).width = _UNIDADE_LARGURA * min(
            max(largura + 2, _LARGURA_MIN), _LARGURA_MAX
        )

    livro.save(str(output_path))

    return output_path
