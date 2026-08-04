"""Aligeirar um PDF sem estragar a impressão.

O ``CONJ.pdf`` que vem do iMos traz as imagens do projeto na resolução máxima
com que foram desenhadas. Ao copiar as páginas para o ``2_Projeto_Producao.pdf``
essa resolução vai atrás, e duas páginas chegam a ocupar mais de 20 MB — peso
que não se vê na folha impressa (uma A4 aproveita 200 dpi e mais nada) mas que
chega para o email ser recusado pelo servidor.

Este serviço volta a gravar essas imagens à resolução que a página realmente
usa, em JPEG. O ficheiro continua a ser um só: o mesmo que se imprime é o que
segue por email.

Três travões, para nunca piorar o que já está bom:

* o ficheiro só é substituído se o resultado ficar mesmo mais pequeno;
* imagens com transparência ficam intactas — passá-las a JPEG daria fundos
  pretos;
* qualquer falha a tratar uma imagem deixa-a como estava e o trabalho segue.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import logging
from pathlib import Path

from app.domain.anexos_email import formatar_tamanho

logger = logging.getLogger(__name__)

#: Resolução alvo das imagens. Uma A4 impressa não distingue mais do que isto.
DPI_IMPRESSAO = 200

#: Qualidade do JPEG. 80 é o ponto onde a olho nu não se nota a diferença.
QUALIDADE_JPEG = 80

#: Abaixo deste peso uma imagem não paga o risco de lhe mexer (logótipos,
#: ícones, tramas) — e re-gravá-la até a podia engordar.
MINIMO_BYTES_IMAGEM = 100 * 1024

#: Modos de imagem com canal de transparência: não se tocam.
MODOS_COM_TRANSPARENCIA = frozenset({"RGBA", "LA", "PA", "P"})


@dataclass(frozen=True)
class ResultadoCompressao:
    """O que a passagem pelo PDF deu."""

    bytes_antes: int
    bytes_depois: int
    imagens_tratadas: int
    aplicado: bool
    motivo: str = ""

    @property
    def poupanca_bytes(self) -> int:
        return max(0, self.bytes_antes - self.bytes_depois)

    @property
    def poupanca_pct(self) -> float:
        if self.bytes_antes <= 0:
            return 0.0
        return 100.0 * self.poupanca_bytes / self.bytes_antes

    def resumo(self) -> str:
        """Frase para o log/estado: ``23,1 MB -> 1,8 MB (-92%)``."""
        if not self.aplicado:
            return (
                f"{formatar_tamanho(self.bytes_antes)} mantido"
                + (f" ({self.motivo})" if self.motivo else "")
            )
        return (
            f"{formatar_tamanho(self.bytes_antes)} -> "
            f"{formatar_tamanho(self.bytes_depois)} "
            f"(-{self.poupanca_pct:.0f}%, {self.imagens_tratadas} imagem(ns))"
        )


def comprimir_pdf(
    caminho: Path,
    *,
    dpi: int = DPI_IMPRESSAO,
    qualidade: int = QUALIDADE_JPEG,
) -> ResultadoCompressao:
    """Reescrever ``caminho`` com as imagens à resolução de impressão.

    Devolve sempre um resultado — nunca levanta. Se não houver nada a ganhar,
    o ficheiro fica exatamente como estava.
    """
    caminho = Path(caminho)
    try:
        original = caminho.read_bytes()
    except OSError as erro:
        logger.info("Não foi possível ler o PDF para comprimir: %s", erro)
        return ResultadoCompressao(0, 0, 0, False, "ficheiro ilegível")

    try:
        novos_bytes, tratadas = _reescrever(original, dpi=dpi, qualidade=qualidade)
    except Exception as erro:  # noqa: BLE001 - depende do PDF de origem
        logger.warning("Compressão do PDF %s não foi possível: %s", caminho.name, erro)
        return ResultadoCompressao(len(original), len(original), 0, False, str(erro))

    if len(novos_bytes) >= len(original):
        return ResultadoCompressao(
            len(original), len(original), tratadas, False, "já estava otimizado"
        )

    try:
        caminho.write_bytes(novos_bytes)
    except OSError as erro:
        logger.warning("Não foi possível gravar o PDF comprimido: %s", erro)
        return ResultadoCompressao(
            len(original), len(original), tratadas, False, "gravação falhou"
        )

    return ResultadoCompressao(len(original), len(novos_bytes), tratadas, True)


def _reescrever(original: bytes, *, dpi: int, qualidade: int) -> tuple[bytes, int]:
    """Devolver os bytes do PDF já tratado e quantas imagens se mexeram."""
    from pypdf import PdfReader, PdfWriter

    escritor = PdfWriter(clone_from=PdfReader(BytesIO(original)))

    tratadas = 0
    # Duas páginas do CONJ.pdf partilham muitas vezes a mesma imagem. Sem esta
    # memória, a segunda passagem gravaria JPEG por cima de JPEG e só tirava
    # qualidade — o tamanho já tinha sido ganho à primeira.
    ja_vistas: set[int] = set()
    for pagina in escritor.pages:
        lado_maximo = _lado_maximo_da_pagina(pagina, dpi)
        for imagem in _imagens_da_pagina(pagina):
            chave = _identificador(imagem)
            if chave is not None and chave in ja_vistas:
                continue
            if _tratar_imagem(imagem, lado_maximo, qualidade):
                tratadas += 1
                if chave is not None:
                    ja_vistas.add(chave)
        try:
            pagina.compress_content_streams()
        except Exception as erro:  # noqa: BLE001 - conteúdo já comprimido/estranho
            logger.debug("Conteúdo da página não foi comprimido: %s", erro)

    saida = BytesIO()
    escritor.write(saida)
    return saida.getvalue(), tratadas


def _imagens_da_pagina(pagina) -> list:
    """As imagens da página, incluindo as que estão dentro de formulários."""
    try:
        return list(pagina.images)
    except Exception as erro:  # noqa: BLE001 - página sem recursos legíveis
        logger.debug("Página sem imagens legíveis: %s", erro)
        return []


def _identificador(imagem) -> int | None:
    """Número do objeto no PDF — o que diz se duas páginas usam a mesma imagem."""
    referencia = getattr(imagem, "indirect_reference", None)
    numero = getattr(referencia, "idnum", None)
    return int(numero) if numero is not None else None


def _lado_maximo_da_pagina(pagina, dpi: int) -> int:
    """Quantos pixéis chegam para o maior lado da página, ao dpi pedido."""
    try:
        largura = float(pagina.mediabox.width)
        altura = float(pagina.mediabox.height)
    except Exception:  # noqa: BLE001 - mediabox inválida
        largura = altura = 842.0  # A4 ao comprido, em pontos
    pontos = max(largura, altura, 1.0)
    return max(600, int(pontos / 72.0 * max(72, int(dpi))))


def _tratar_imagem(imagem, lado_maximo: int, qualidade: int) -> bool:
    """Reduzir uma imagem. Devolve True se lhe mexeu mesmo."""
    if getattr(imagem, "is_inline", False):
        return False
    if len(getattr(imagem, "data", b"") or b"") < MINIMO_BYTES_IMAGEM:
        return False
    if _tem_transparencia(imagem):
        return False

    original = getattr(imagem, "image", None)
    if original is None:
        return False

    try:
        from PIL import Image

        nova = original
        largura, altura = nova.size
        maior = max(largura, altura)
        if maior > lado_maximo:
            escala = lado_maximo / float(maior)
            nova = nova.resize(
                (max(1, round(largura * escala)), max(1, round(altura * escala))),
                Image.LANCZOS,
            )
        if nova.mode not in {"RGB", "L"}:
            nova = nova.convert("RGB")

        imagem.replace(nova, quality=int(qualidade), optimize=True)
    except Exception as erro:  # noqa: BLE001 - imagem fica como estava
        logger.debug("Imagem %s não foi reduzida: %s", getattr(imagem, "name", "?"), erro)
        return False
    return True


def _tem_transparencia(imagem) -> bool:
    """Ver se a imagem tem canal alfa — no PIL ou na máscara do próprio PDF."""
    pil = getattr(imagem, "image", None)
    if pil is not None and getattr(pil, "mode", "") in MODOS_COM_TRANSPARENCIA:
        return True

    referencia = getattr(imagem, "indirect_reference", None)
    if referencia is None:
        return False
    try:
        objeto = referencia.get_object()
        return "/SMask" in objeto or "/Mask" in objeto
    except Exception:  # noqa: BLE001 - sem forma de saber -> não mexer
        return True
