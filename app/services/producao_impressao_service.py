"""List and print the documents of one obra folder, in the user's own order.

Porte da ideia do "Imprimir" do Martelo V2: ler os PDFs da pasta da obra,
classificá-los por categoria e imprimi-los por ordem de prioridade. A
novidade do V3 é a ordem ficar guardada **por utilizador** — cada um imprime
pela ordem que quer, e essa ordem serve para as obras seguintes.
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class CategoriaImpressao:
    """Print defaults for one document category."""

    nome: str
    prioridade: int
    papel: str
    orientacao: str
    quantidade: int
    padrao: Optional[re.Pattern[str]] = None


CATEGORIAS: tuple[CategoriaImpressao, ...] = (
    CategoriaImpressao(CATEGORIA_CUT_RITE, 0, "A3", ORIENTACAO_HORIZONTAL, 1),
    CategoriaImpressao(
        CATEGORIA_FERRAGENS,
        1,
        "A4",
        ORIENTACAO_VERTICAL,
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
        "A4",
        ORIENTACAO_VERTICAL,
        1,
        re.compile(r"^3_resumo_geral", re.IGNORECASE),
    ),
    CategoriaImpressao(CATEGORIA_MATERIAIS, 4, "A3", ORIENTACAO_HORIZONTAL, 1),
    CategoriaImpressao(
        CATEGORIA_ETIQUETA,
        5,
        "A4",
        ORIENTACAO_VERTICAL,
        3,
        re.compile(r"^5_etiqueta", re.IGNORECASE),
    ),
    CategoriaImpressao(
        CATEGORIA_RESUMO_ML,
        6,
        "A4",
        ORIENTACAO_HORIZONTAL,
        1,
        re.compile(r"^6_resumo_ml", re.IGNORECASE),
    ),
    CategoriaImpressao(CATEGORIA_AUTOCAD, 7, "A3", ORIENTACAO_HORIZONTAL, 1),
    CategoriaImpressao(CATEGORIA_OUTROS, 8, "A4", ORIENTACAO_VERTICAL, 1),
)

CATEGORIAS_POR_NOME = {categoria.nome: categoria for categoria in CATEGORIAS}
NOMES_CATEGORIAS = tuple(categoria.nome for categoria in CATEGORIAS)

#: Subpastas que nunca entram na lista de impressão.
PASTAS_IGNORADAS = {"mails", "imagens", "excels"}


@dataclass
class DocumentoImpressao:
    """One printable document found in the obra folder."""

    caminho: Path
    nome: str
    categoria: str
    prioridade: int
    origem: str
    papel_ficheiro: str
    papel: str
    orientacao: str
    quantidade: int
    duplex: bool = False
    cor: str = "cor"
    paginas: str = "todas"
    selecionado: bool = True
    tamanho: int = 0

    @property
    def papel_diferente(self) -> bool:
        """True when the PDF page size is not the paper it will print on."""
        if not self.papel_ficheiro or not self.papel:
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
    avisos: list[str] = []
    for documento in documentos:
        caminho = str(documento.caminho)
        if not caminho:
            continue
        if sumatra:
            _imprimir_com_sumatra(sumatra, documento)
            continue
        if documento.papel_diferente:
            avisos.append(
                f"{documento.nome}: está em {documento.papel_ficheiro} e vai "
                f"para {documento.papel} sem ajuste (SumatraPDF não encontrado)."
            )
        _imprimir_com_aplicacao_default(documento)
    return avisos


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
    return DocumentoImpressao(
        caminho=caminho,
        nome=caminho.name,
        categoria=categoria_nome,
        prioridade=int(prioridades.get(categoria_nome, categoria.prioridade)),
        origem=origem,
        papel_ficheiro=detetar_papel(caminho) or "",
        papel=categoria.papel,
        orientacao=categoria.orientacao,
        quantidade=categoria.quantidade,
        tamanho=_tamanho(caminho),
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


def detetar_papel(caminho: Path) -> Optional[str]:
    """Return A4/A3 read from the PDF page box, when recognisable."""
    texto = _cabecalho_pdf(caminho)
    if not texto:
        return None
    encontrado = _RE_MEDIA_BOX.search(texto)
    if not encontrado:
        return None
    try:
        x1, y1, x2, y2 = (float(encontrado.group(indice)) for indice in range(1, 5))
    except (TypeError, ValueError):
        return None

    curto = min(abs(x2 - x1), abs(y2 - y1))
    longo = max(abs(x2 - x1), abs(y2 - y1))
    if _perto(curto, 595) and _perto(longo, 842):
        return "A4"
    if _perto(curto, 842) and _perto(longo, 1191):
        return "A3"
    return None


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


def _imprimir_com_sumatra(sumatra: str, documento: DocumentoImpressao) -> None:
    definicoes = [f"paper={documento.papel}"]
    definicoes.append(
        "landscape"
        if documento.orientacao.casefold().startswith("h")
        else "portrait"
    )
    if documento.papel_diferente:
        definicoes.append("fit")
    if documento.duplex:
        definicoes.append("duplex")
    if documento.cor.casefold() in {"pb", "monocromatico", "monochrome"}:
        definicoes.append("monochrome")

    for _ in range(max(1, int(documento.quantidade or 1))):
        subprocess.run(
            [
                sumatra,
                "-print-to-default",
                "-silent",
                "-exit-when-done",
                "-print-settings",
                ",".join(definicoes),
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
