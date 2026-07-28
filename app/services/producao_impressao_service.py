"""List and print the documents of one obra folder, in the user's own order.

Porte da ideia do "Imprimir" do Martelo V2: ler os PDFs da pasta da obra,
classificá-los por categoria e imprimi-los por ordem de prioridade. A
novidade do V3 é a ordem ficar guardada **por utilizador** — cada um imprime
pela ordem que quer, e essa ordem serve para as obras seguintes.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
import json
import logging
import os
from pathlib import Path
import re
import subprocess
from typing import Iterable, Optional, Sequence

from sqlalchemy.orm import Session

from app.services.system_setting_service import SystemSettingService


logger = logging.getLogger(__name__)


KEY_SUMATRA_PDF = "executavel_sumatra_pdf"
SUMATRA_CAMINHOS_DEFAULT = (
    r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
    r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
)

CATEGORIA_CUT_RITE = "CUT-RITE PLANO CORTE"
CATEGORIA_FERRAGENS = "FERRAGENS"
CATEGORIA_PROJETO = "PROJETO PRODUÇÃO"
CATEGORIA_RESUMO_GERAL = "RESUMO GERAL"
CATEGORIA_MATERIAIS = "LISTA PEÇAS/MATERIAIS"
CATEGORIA_ETIQUETA = "ETIQUETA PALETE"
CATEGORIA_RESUMO_ML = "RESUMO ML ORLAS"
CATEGORIA_AUTOCAD = "AUTOCAD/IMOS IX"
CATEGORIA_OUTROS = "OUTROS"

ORIENTACAO_HORIZONTAL = "Horizontal"
ORIENTACAO_VERTICAL = "Vertical"

#: Valor que diz "imprime como o PDF foi gravado" (papel e orientação).
DO_PDF = "Do PDF"

PAPEIS = (DO_PDF, "A4", "A3")
ORIENTACOES = (DO_PDF, ORIENTACAO_HORIZONTAL, ORIENTACAO_VERTICAL)


@dataclass(frozen=True)
class CategoriaImpressao:
    """Print defaults for one document category."""

    nome: str
    prioridade: int
    papel: str
    orientacao: str
    quantidade: int
    padrao: Optional[re.Pattern[str]] = None


# Por defeito imprime-se no formato em que o PDF foi gravado (DO_PDF). Só as
# categorias que o Paulo quer sempre num formato fixo é que o forçam.
CATEGORIAS: tuple[CategoriaImpressao, ...] = (
    CategoriaImpressao(CATEGORIA_CUT_RITE, 0, DO_PDF, DO_PDF, 1),
    CategoriaImpressao(
        CATEGORIA_FERRAGENS,
        1,
        DO_PDF,
        DO_PDF,
        3,
        re.compile(r"^1_list_ferr", re.IGNORECASE),
    ),
    CategoriaImpressao(
        CATEGORIA_PROJETO,
        2,
        "A4",
        ORIENTACAO_HORIZONTAL,
        2,
        re.compile(r"^2_proj", re.IGNORECASE),
    ),
    CategoriaImpressao(
        CATEGORIA_RESUMO_GERAL,
        3,
        DO_PDF,
        DO_PDF,
        1,
        re.compile(r"^3_resumo_geral", re.IGNORECASE),
    ),
    CategoriaImpressao(CATEGORIA_MATERIAIS, 4, "A3", ORIENTACAO_HORIZONTAL, 1),
    CategoriaImpressao(
        CATEGORIA_ETIQUETA,
        5,
        DO_PDF,
        DO_PDF,
        3,
        re.compile(r"^5_etiqueta", re.IGNORECASE),
    ),
    CategoriaImpressao(
        CATEGORIA_RESUMO_ML,
        6,
        DO_PDF,
        DO_PDF,
        1,
        re.compile(r"^6_resumo_ml", re.IGNORECASE),
    ),
    CategoriaImpressao(CATEGORIA_AUTOCAD, 7, DO_PDF, DO_PDF, 1),
    CategoriaImpressao(CATEGORIA_OUTROS, 8, DO_PDF, DO_PDF, 1),
)

CATEGORIAS_POR_NOME = {categoria.nome: categoria for categoria in CATEGORIAS}
NOMES_CATEGORIAS = tuple(categoria.nome for categoria in CATEGORIAS)

#: Subpastas que nunca entram na lista de impressão.
PASTAS_IGNORADAS = {"mails", "imagens", "excels"}

#: Números standard do Windows para os formatos (DMPAPER_A4 / DMPAPER_A3).
#: Manda-se o número e não o nome: cada driver chama-lhe o que quer — a EPSON
#: ET-16650, por exemplo, chama "A3 297 x 420 mm" ao A3, e aí o SumatraPDF não
#: encontrava o formato pelo nome e imprimia no papel por defeito.
IDS_PAPEL_WINDOWS = {"A4": 9, "A3": 8}

#: Windows: DC_PAPERNAMES e DC_PAPERS nas capacidades do driver.
_DC_PAPERS = 2
_DC_PAPERNAMES = 16


@dataclass(frozen=True)
class GeometriaPagina:
    """Paper size and orientation of one PDF page, rotation included."""

    papel: str
    orientacao: str

    def __str__(self) -> str:
        papel = self.papel or "tamanho próprio"
        return f"{papel} {self.orientacao.casefold()}"


@dataclass
class DocumentoImpressao:
    """One printable document found in the obra folder."""

    caminho: Path
    nome: str
    categoria: str
    prioridade: int
    origem: str
    papel_ficheiro: str
    orientacao_ficheiro: str
    resumo_paginas: str
    papel: str
    orientacao: str
    quantidade: int
    duplex: bool = False
    cor: str = "cor"
    paginas: str = "todas"
    selecionado: bool = True
    tamanho: int = 0
    geometria_paginas: list[GeometriaPagina] = dataclass_field(default_factory=list)

    @property
    def segue_o_pdf(self) -> bool:
        """True when the document prints exactly as it was saved."""
        return self.papel == DO_PDF

    @property
    def papel_diferente(self) -> bool:
        """True when the forced paper is not the paper inside the PDF."""
        if self.segue_o_pdf or not self.papel_ficheiro:
            return False
        return self.papel_ficheiro.upper() != self.papel.upper()


def chave_prioridades_utilizador(user_id: object) -> str:
    """Return the per-user system-setting key for the print order."""
    return f"producao_impressao_prioridades:{user_id or 'default'}"


def prioridades_default() -> dict[str, int]:
    """Return the factory print order, by category."""
    return {categoria.nome: categoria.prioridade for categoria in CATEGORIAS}


def obter_prioridades_utilizador(session: Session, user_id: object) -> dict[str, int]:
    """Return this user's print order (the factory one, when never saved)."""
    prioridades = prioridades_default()
    valor = SystemSettingService(session).obter_valor(
        chave_prioridades_utilizador(user_id), None
    )
    if not valor:
        return prioridades

    try:
        guardadas = json.loads(valor)
    except (TypeError, ValueError):
        logger.warning("Ordem de impressão ilegível para user_id=%s", user_id)
        return prioridades

    if not isinstance(guardadas, dict):
        return prioridades

    for nome, prioridade in guardadas.items():
        if nome not in prioridades:
            continue
        try:
            prioridades[nome] = int(prioridade)
        except (TypeError, ValueError):
            continue
    return prioridades


def guardar_prioridades_utilizador(
    session: Session, user_id: object, prioridades: dict[str, int]
) -> None:
    """Save this user's print order so the next obras follow it."""
    limpas = {
        str(nome): int(prioridade)
        for nome, prioridade in prioridades.items()
        if str(nome) in CATEGORIAS_POR_NOME
    }
    SystemSettingService(session).guardar_valor(
        chave_prioridades_utilizador(user_id),
        json.dumps(limpas, ensure_ascii=False, sort_keys=True),
    )


def listar_documentos(
    pasta_obra: str | Path,
    *,
    nome_plano_cut_rite: str = "",
    nome_enc_imos: str = "",
    prioridades: Optional[dict[str, int]] = None,
) -> list[DocumentoImpressao]:
    """Read the obra folder and return its PDFs, already in print order."""
    pasta = Path(pasta_obra)
    try:
        if not pasta.is_dir():
            return []
        ficheiros = sorted(
            caminho
            for caminho in pasta.iterdir()
            if caminho.is_file() and caminho.suffix.casefold() == ".pdf"
        )
    except OSError:
        # Servidor em baixo: lista vazia em vez de rebentar o diálogo.
        return []

    ordem = dict(prioridades or prioridades_default())
    documentos = [
        _documento(
            caminho,
            nome_plano_cut_rite=nome_plano_cut_rite,
            nome_enc_imos=nome_enc_imos,
            prioridades=ordem,
        )
        for caminho in ficheiros
    ]
    return ordenar_documentos(documentos)


def ordenar_documentos(
    documentos: Sequence[DocumentoImpressao],
) -> list[DocumentoImpressao]:
    """Sort documents by priority, then by file name."""
    return sorted(documentos, key=lambda doc: (doc.prioridade, doc.nome.casefold()))


def prioridades_dos_documentos(
    documentos: Sequence[DocumentoImpressao],
) -> dict[str, int]:
    """Return the category order implied by the documents on screen."""
    prioridades = prioridades_default()
    for documento in documentos:
        if documento.categoria in prioridades:
            prioridades[documento.categoria] = int(documento.prioridade)
    return prioridades


def ordem_foi_alterada(
    documentos: Sequence[DocumentoImpressao], prioridades_guardadas: dict[str, int]
) -> bool:
    """True when the user changed the order of the categories on screen."""
    atuais = prioridades_dos_documentos(documentos)
    categorias_na_lista = {documento.categoria for documento in documentos}
    return any(
        atuais.get(nome) != prioridades_guardadas.get(nome)
        for nome in categorias_na_lista
    )


def categorizar(
    nome_ficheiro: str,
    *,
    nome_plano_cut_rite: str = "",
    nome_enc_imos: str = "",
    origem: str = "desconhecida",
) -> str:
    """Return the category of one document, from its name and origin."""
    nome = (nome_ficheiro or "").strip()
    minusculas = nome.casefold()

    plano = str(nome_plano_cut_rite or "").strip().casefold()
    if plano and minusculas == f"{plano}.pdf":
        return CATEGORIA_CUT_RITE

    enc_imos = str(nome_enc_imos or "").strip().casefold()
    if enc_imos and minusculas.startswith(f"lista_material_{enc_imos}"):
        return CATEGORIA_MATERIAIS
    if minusculas.startswith("lista_material"):
        return CATEGORIA_MATERIAIS

    for categoria in CATEGORIAS:
        if categoria.padrao is not None and categoria.padrao.match(nome):
            return categoria.nome

    if origem == "autocad":
        return CATEGORIA_AUTOCAD
    return CATEGORIA_OUTROS


def imprimir_documentos(
    session: Optional[Session],
    documentos: Iterable[DocumentoImpressao],
) -> list[str]:
    """Send the documents to the default printer, in the order given.

    Devolve os avisos que valem a pena mostrar (por exemplo, PDFs em A3 a
    imprimir em A4 sem o SumatraPDF instalado).
    """
    sumatra = resolver_sumatra(session)
    formatos = formatos_da_impressora() if sumatra else {}
    documentos = list(documentos)
    enviados = 0
    for documento in documentos:
        if not str(documento.caminho):
            continue
        if sumatra:
            _imprimir_com_sumatra(sumatra, documento, formatos)
        else:
            _imprimir_com_aplicacao_default(documento)
        enviados += 1

    if not enviados:
        return []
    if not sumatra:
        return [
            "SumatraPDF não encontrado: o papel e a orientação ficaram por "
            "conta do leitor de PDF do Windows. Instale o SumatraPDF (ou "
            "indique o caminho em Caminhos do Sistema) para o A3/A4 e a "
            "orientação serem respeitados."
        ]
    return _avisos_de_papel(documentos, formatos)


def _avisos_de_papel(
    documentos: Sequence[DocumentoImpressao], formatos: dict[str, int]
) -> list[str]:
    """Warn when the printer does not list a paper the documents need."""
    if not formatos:
        return []

    precisos = set()
    for documento in documentos:
        if documento.segue_o_pdf:
            precisos.update(
                pagina.papel for pagina in documento.geometria_paginas if pagina.papel
            )
        elif documento.papel != DO_PDF:
            precisos.add(documento.papel)

    em_falta = sorted(papel for papel in precisos if papel.upper() not in formatos)
    if not em_falta:
        return []
    return [
        f"A impressora predefinida não tem {' nem '.join(em_falta)} na lista "
        "de formatos: esses documentos saem no papel que ela tiver."
    ]


def resolver_sumatra(session: Optional[Session]) -> Optional[str]:
    """Return the SumatraPDF executable used for silent printing, if any."""
    if session is not None:
        configurado = (
            SystemSettingService(session).obter_valor(KEY_SUMATRA_PDF, "") or ""
        ).strip()
        if configurado and Path(configurado).is_file():
            return configurado
    for caminho in SUMATRA_CAMINHOS_DEFAULT:
        if Path(caminho).is_file():
            return caminho
    return None


def _documento(
    caminho: Path,
    *,
    nome_plano_cut_rite: str,
    nome_enc_imos: str,
    prioridades: dict[str, int],
) -> DocumentoImpressao:
    origem = detetar_origem(caminho)
    categoria_nome = categorizar(
        caminho.name,
        nome_plano_cut_rite=nome_plano_cut_rite,
        nome_enc_imos=nome_enc_imos,
        origem=origem,
    )
    categoria = CATEGORIAS_POR_NOME[categoria_nome]
    paginas = analisar_paginas(caminho)
    dominante = geometria_dominante(paginas)
    return DocumentoImpressao(
        caminho=caminho,
        nome=caminho.name,
        categoria=categoria_nome,
        prioridade=int(prioridades.get(categoria_nome, categoria.prioridade)),
        origem=origem,
        papel_ficheiro=dominante.papel if dominante else "",
        orientacao_ficheiro=dominante.orientacao if dominante else "",
        resumo_paginas=resumo_paginas(paginas),
        papel=categoria.papel,
        orientacao=categoria.orientacao,
        quantidade=categoria.quantidade,
        tamanho=_tamanho(caminho),
        geometria_paginas=paginas,
    )


_RE_PRODUTOR = re.compile(r"/Producer\s*\((.*?)\)", re.IGNORECASE | re.DOTALL)
_RE_CRIADOR = re.compile(r"/Creator\s*\((.*?)\)", re.IGNORECASE | re.DOTALL)
_RE_MEDIA_BOX = re.compile(
    r"/MediaBox\s*\[\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*\]",
    re.IGNORECASE,
)


def detetar_origem(caminho: Path) -> str:
    """Guess whether the PDF came from AutoCAD/IMOS or from Excel."""
    texto = _cabecalho_pdf(caminho)
    if not texto:
        return "desconhecida"
    minusculas = texto.lower()
    if "autocad" in minusculas or "imos" in minusculas or "/predictor" in minusculas:
        return "autocad"
    if "excel" in minusculas or "microsoft" in minusculas:
        return "excel"
    return "desconhecida"


def analisar_paginas(caminho: Path) -> list[GeometriaPagina]:
    """Return the paper and orientation of every page, rotation included.

    O plano CUT-RITE traz normalmente várias folhas A3 horizontais e uma A4
    horizontal — por isso interessa a geometria de cada página, não só da
    primeira.
    """
    try:
        from io import BytesIO

        from pypdf import PdfReader

        # Ler de uma vez só: na rede, muitos acessos pequenos são lentos.
        leitor = PdfReader(BytesIO(Path(caminho).read_bytes()))
        geometrias = []
        for pagina in leitor.pages:
            caixa = pagina.mediabox
            largura = float(caixa.width)
            altura = float(caixa.height)
            rodada = int(getattr(pagina, "rotation", 0) or 0) % 360
            if rodada in (90, 270):
                largura, altura = altura, largura
            geometrias.append(_geometria(largura, altura))
        if geometrias:
            return geometrias
    except Exception as exc:  # PDFs estranhos não podem parar a lista
        logger.debug("pypdf não leu %s (%s); uso o /MediaQBox em bruto", caminho, exc)

    return _paginas_por_regex(caminho)


def geometria_dominante(
    paginas: Sequence[GeometriaPagina],
) -> Optional[GeometriaPagina]:
    """Return the geometry most pages share (what the row shows by default)."""
    if not paginas:
        return None
    contagem: dict[GeometriaPagina, int] = {}
    for pagina in paginas:
        contagem[pagina] = contagem.get(pagina, 0) + 1
    return max(contagem, key=lambda geometria: contagem[geometria])


def resumo_paginas(paginas: Sequence[GeometriaPagina]) -> str:
    """Describe the pages of one PDF, for the tooltip in the print list."""
    if not paginas:
        return ""
    contagem: dict[GeometriaPagina, int] = {}
    for pagina in paginas:
        contagem[pagina] = contagem.get(pagina, 0) + 1
    partes = [
        f"{total} página{'s' if total > 1 else ''} {geometria}"
        for geometria, total in sorted(
            contagem.items(), key=lambda item: item[1], reverse=True
        )
    ]
    return " + ".join(partes)


def detetar_papel(caminho: Path) -> Optional[str]:
    """Return the dominant paper (A4/A3) of one PDF, when recognisable."""
    dominante = geometria_dominante(analisar_paginas(caminho))
    if dominante is None or not dominante.papel:
        return None
    return dominante.papel


def _geometria(largura: float, altura: float) -> GeometriaPagina:
    orientacao = (
        ORIENTACAO_HORIZONTAL if largura > altura else ORIENTACAO_VERTICAL
    )
    curto = min(largura, altura)
    longo = max(largura, altura)
    if _perto(curto, 595) and _perto(longo, 842):
        return GeometriaPagina("A4", orientacao)
    if _perto(curto, 842) and _perto(longo, 1191):
        return GeometriaPagina("A3", orientacao)
    return GeometriaPagina("", orientacao)


def _paginas_por_regex(caminho: Path) -> list[GeometriaPagina]:
    """Fallback: read the /MediaBox entries straight from the PDF bytes."""
    texto = _cabecalho_pdf(caminho)
    if not texto:
        return []

    geometrias = []
    for encontrado in _RE_MEDIA_BOX.finditer(texto):
        try:
            x1, y1, x2, y2 = (
                float(encontrado.group(indice)) for indice in range(1, 5)
            )
        except (TypeError, ValueError):
            continue
        geometrias.append(_geometria(abs(x2 - x1), abs(y2 - y1)))
    return geometrias


def _perto(valor: float, alvo: float, tolerancia: float = 12.0) -> bool:
    return abs(valor - alvo) <= tolerancia


def _cabecalho_pdf(caminho: Path, max_bytes: int = 256 * 1024) -> str:
    try:
        with Path(caminho).open("rb") as ficheiro:
            return ficheiro.read(max_bytes).decode("latin-1", errors="ignore")
    except OSError:
        return ""


def _tamanho(caminho: Path) -> int:
    try:
        return int(caminho.stat().st_size)
    except OSError:
        return 0


def definicoes_sumatra(
    documento: DocumentoImpressao, formatos: Optional[dict[str, int]] = None
) -> list[str]:
    """Build the -print-settings strings SumatraPDF receives for one document.

    Com "Do PDF" cada bloco de páginas com a mesma geometria é impresso à
    parte, no papel e na orientação com que foi gravado — é assim que o plano
    CUT-RITE sai certo, com as folhas A3 em A3 e a folha A4 em A4. Quando se
    força um formato, vai um só comando com o papel, a orientação e ``fit``,
    para o desenho caber na folha escolhida.

    Vai sempre ``disable-auto-rotation``: por defeito o SumatraPDF roda a
    página para "encaixar" melhor no papel e essa rotação passa por cima da
    orientação pedida — era o que punha a folha A4 do plano na vertical.
    """
    extras = _extras_sumatra(documento)

    if not documento.segue_o_pdf:
        definicoes = []
        identificador = id_papel(documento.papel, formatos)
        if identificador is not None:
            definicoes.append(f"paperkind={identificador}")
        if documento.orientacao != DO_PDF:
            definicoes.append(_orientacao_sumatra(documento.orientacao))
        definicoes.append("fit")
        definicoes.append("disable-auto-rotation")
        return [",".join(definicoes + extras)]

    grupos = _grupos_de_paginas(documento.geometria_paginas)
    if not grupos:
        # Sem conseguir ler as páginas, deixa-se a rotação automática fazer o
        # seu trabalho: é melhor do que impor uma orientação às cegas.
        return [",".join(["shrink"] + extras)]

    comandos = []
    for intervalo, geometria in grupos:
        definicoes = [intervalo] if intervalo else []
        identificador = id_papel(geometria.papel, formatos)
        if identificador is not None:
            definicoes.append(f"paperkind={identificador}")
        definicoes.append(_orientacao_sumatra(geometria.orientacao))
        # "shrink" e não "noscale": mantém o tamanho original, mas encolhe o
        # necessário se o desenho bater nas margens que a impressora não pinta.
        definicoes.append("shrink")
        definicoes.append("disable-auto-rotation")
        comandos.append(",".join(definicoes + extras))
    return comandos


def formatos_da_impressora(impressora: Optional[str] = None) -> dict[str, int]:
    """Return {"A4": id, "A3": id} as the default printer really names them."""
    try:
        import win32print
    except ImportError:  # pragma: no cover - só existe no Windows
        return {}

    try:
        nome_impressora = impressora or win32print.GetDefaultPrinter()
        nomes = win32print.DeviceCapabilities(
            nome_impressora, "", _DC_PAPERNAMES
        ) or []
        ids = win32print.DeviceCapabilities(nome_impressora, "", _DC_PAPERS) or []
    except Exception as exc:  # pragma: no cover - depende da impressora
        logger.debug("Não li os formatos da impressora: %s", exc)
        return {}

    formatos = [
        (str(nome).strip(), int(identificador))
        for nome, identificador in zip(nomes, ids)
    ]
    encontrados = {}
    for papel, id_standard in IDS_PAPEL_WINDOWS.items():
        identificador = _id_do_formato(formatos, papel, id_standard)
        if identificador is not None:
            encontrados[papel] = identificador
    return encontrados


def _id_do_formato(
    formatos: Sequence[tuple[str, int]], papel: str, id_standard: int
) -> Optional[int]:
    """Find the printer form for A4/A3 ("A3 297 x 420 mm" also counts)."""
    procurado = papel.casefold()
    for nome, identificador in formatos:
        if nome.casefold() == procurado:
            return identificador

    # Sem nome exato, aceita-se "A3 297 x 420 mm" mas nunca "A3+ 329 x 483 mm".
    candidatos = [
        identificador
        for nome, identificador in formatos
        if nome.split(" ")[0].casefold() == procurado
    ]
    if id_standard in candidatos:
        return id_standard
    return min(candidatos) if candidatos else None


def id_papel(papel: str, formatos: Optional[dict[str, int]] = None) -> Optional[int]:
    """Return the Windows paper number to send in ``paperkind=``."""
    if not papel:
        return None
    chave = papel.upper()
    if formatos and chave in formatos:
        return formatos[chave]
    return IDS_PAPEL_WINDOWS.get(chave)


def _orientacao_sumatra(orientacao: str) -> str:
    return "landscape" if orientacao.casefold().startswith("h") else "portrait"


def _extras_sumatra(documento: DocumentoImpressao) -> list[str]:
    extras = []
    if documento.duplex:
        extras.append("duplex")
    if documento.cor.casefold() in {"pb", "monocromatico", "monochrome"}:
        extras.append("monochrome")
    return extras


def _grupos_de_paginas(
    paginas: Sequence[GeometriaPagina],
) -> list[tuple[str, GeometriaPagina]]:
    """Group consecutive pages that share paper and orientation.

    Devolve pares (intervalo, geometria) — o intervalo vem vazio quando o PDF
    inteiro tem a mesma geometria, para não limitar as páginas sem necessidade.
    """
    if not paginas:
        return []
    if len(set(paginas)) == 1:
        return [("", paginas[0])]

    grupos: list[tuple[str, GeometriaPagina]] = []
    inicio = 0
    for indice in range(1, len(paginas) + 1):
        if indice < len(paginas) and paginas[indice] == paginas[inicio]:
            continue
        primeira, ultima = inicio + 1, indice
        intervalo = f"{primeira}" if primeira == ultima else f"{primeira}-{ultima}"
        grupos.append((intervalo, paginas[inicio]))
        inicio = indice
    return grupos


def _imprimir_com_sumatra(
    sumatra: str,
    documento: DocumentoImpressao,
    formatos: Optional[dict[str, int]] = None,
) -> None:
    comandos = definicoes_sumatra(documento, formatos)

    for _ in range(max(1, int(documento.quantidade or 1))):
        for definicoes in comandos:
            subprocess.run(
                [
                    sumatra,
                    "-print-to-default",
                    "-silent",
                    "-exit-when-done",
                    "-print-settings",
                    definicoes,
                    str(documento.caminho),
                ],
                check=False,
            )


def _imprimir_com_aplicacao_default(documento: DocumentoImpressao) -> None:
    for _ in range(max(1, int(documento.quantidade or 1))):
        try:
            os.startfile(str(documento.caminho), "print")  # noqa: S606 - Windows
        except OSError as exc:
            logger.warning("Falha a imprimir %s: %s", documento.caminho, exc)
            break
