"""Contas de tamanho dos anexos de um email — feitas ANTES de tentar enviar.

Um anexo não viaja tal e qual como está no disco: vai codificado em texto, o
que o engorda cerca de um terço. É por isso que um ficheiro de 23 MB rebenta
num servidor que anuncia um limite de 25 MB — chega lá com uns 31 MB. Aqui
trabalha-se sempre com o tamanho **real** do ficheiro, e o limite configurado
já é o limite útil, com essa margem descontada.

Sem Qt e sem base de dados de propósito: é só aritmética sobre caminhos, para
o diálogo do email poder avisar a tempo e os testes correrem sem interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

#: Quanto engorda um anexo ao ser codificado para viajar (base64 + cabeçalhos).
FATOR_CODIFICACAO = 1.37

#: Limite útil por defeito, em MB de ficheiro real. Corresponde aos 25 MB que a
#: maioria dos servidores aceita, já com a margem da codificação descontada.
LIMITE_PADRAO_MB = 18.0

_MB = 1024 * 1024
_KB = 1024


def formatar_tamanho(n_bytes: int | float) -> str:
    """Tamanho legível, à portuguesa: ``23,1 MB``, ``812 KB``, ``0 KB``."""
    n_bytes = max(0, int(n_bytes or 0))
    if n_bytes >= _MB:
        return f"{_virgula(n_bytes / _MB)} MB"
    if n_bytes >= _KB:
        return f"{n_bytes / _KB:.0f} KB"
    return f"{n_bytes} bytes"


def _virgula(valor: float, casas: int = 1) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


@dataclass(frozen=True)
class AnexoTamanho:
    """Um anexo, já pesado."""

    caminho: str
    nome: str
    bytes_ficheiro: int
    existe: bool

    @property
    def etiqueta(self) -> str:
        """O que aparece na lista de anexos do diálogo."""
        if not self.existe:
            return f"{self.nome} — NÃO ENCONTRADO"
        return f"{self.nome} — {formatar_tamanho(self.bytes_ficheiro)}"


@dataclass(frozen=True)
class ResumoAnexos:
    """O peso de todos os anexos junto, comparado com o limite."""

    anexos: tuple[AnexoTamanho, ...]
    limite_mb: float

    @property
    def total_bytes(self) -> int:
        return sum(anexo.bytes_ficheiro for anexo in self.anexos if anexo.existe)

    @property
    def limite_bytes(self) -> int:
        return int(max(0.0, float(self.limite_mb)) * _MB)

    @property
    def excede(self) -> bool:
        return self.limite_bytes > 0 and self.total_bytes > self.limite_bytes

    @property
    def em_falta(self) -> tuple[AnexoTamanho, ...]:
        return tuple(anexo for anexo in self.anexos if not anexo.existe)

    @property
    def maiores(self) -> tuple[AnexoTamanho, ...]:
        """Os anexos que existem, do mais pesado para o mais leve."""
        presentes = [anexo for anexo in self.anexos if anexo.existe]
        return tuple(sorted(presentes, key=lambda a: a.bytes_ficheiro, reverse=True))

    @property
    def texto_barra(self) -> str:
        """Linha de estado por baixo da lista de anexos."""
        if not self.anexos:
            return "Sem anexos."

        quantos = len(self.anexos)
        palavra = "anexo" if quantos == 1 else "anexos"
        texto = (
            f"{quantos} {palavra} · {formatar_tamanho(self.total_bytes)} "
            f"de {_virgula(self.limite_mb, 0)} MB"
        )
        if self.excede:
            texto += " — demasiado grande para email"
        if self.em_falta:
            faltam = len(self.em_falta)
            texto += (
                f" · {faltam} ficheiro não encontrado"
                if faltam == 1
                else f" · {faltam} ficheiros não encontrados"
            )
        return texto

    def mensagem_aviso(self) -> str:
        """Aviso a mostrar a quem tenta enviar acima do limite."""
        linhas = [
            f"Os anexos somam {formatar_tamanho(self.total_bytes)}, acima do "
            f"limite de {_virgula(self.limite_mb, 0)} MB que os servidores de "
            "email costumam aceitar.",
            "",
            "Se enviar assim, o email tem grande probabilidade de voltar para "
            "trás com erro.",
            "",
            "Os maiores:",
        ]
        for anexo in self.maiores[:5]:
            linhas.append(
                f"   • {anexo.nome} — {formatar_tamanho(anexo.bytes_ficheiro)}"
            )
        linhas += [
            "",
            "O que pode fazer: retirar os anexos mais pesados e enviá-los à "
            "parte, ou partilhá-los por link (OneDrive) em vez de os anexar.",
        ]
        return "\n".join(linhas)


def medir_anexo(caminho: str | Path) -> AnexoTamanho:
    """Pesar um ficheiro. Nunca levanta: o que não se lê fica a zero."""
    texto = str(caminho or "").strip()
    try:
        alvo = Path(texto)
        nome = alvo.name or texto
        estado = alvo.stat()
    except (OSError, ValueError):
        return AnexoTamanho(
            caminho=texto, nome=Path(texto).name or texto, bytes_ficheiro=0, existe=False
        )
    return AnexoTamanho(
        caminho=texto, nome=nome, bytes_ficheiro=int(estado.st_size), existe=True
    )


def medir_anexos(caminhos: Iterable[str | Path]) -> tuple[AnexoTamanho, ...]:
    return tuple(medir_anexo(caminho) for caminho in caminhos or ())


def resumir_anexos(
    caminhos: Sequence[str | Path] | None,
    *,
    limite_mb: float = LIMITE_PADRAO_MB,
) -> ResumoAnexos:
    """Pesar todos os anexos e comparar o total com o limite."""
    return ResumoAnexos(anexos=medir_anexos(caminhos or ()), limite_mb=float(limite_mb))
