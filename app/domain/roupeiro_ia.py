"""Contratos e constantes do piloto de IA para roupeiros de abrir."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

TIPO_ITEM_ROUPEIRO_ABRIR = "ROUPEIRO_ABRIR"
POSICAO_QUALQUER = "QUALQUER"
POSICAO_ESQUERDA = "ESQUERDA"
POSICAO_CENTRO = "CENTRO"
POSICAO_DIREITA = "DIREITA"
POSICAO_CANTO = "CANTO"
POSICAO_REMATE = "REMATE"
POSICOES_MODULO = (
    POSICAO_QUALQUER, POSICAO_ESQUERDA, POSICAO_CENTRO,
    POSICAO_DIREITA, POSICAO_CANTO, POSICAO_REMATE,
)
CARACTERISTICAS_ROUPEIRO = (
    "PORTAS", "GAVETAS", "PRATELEIRAS", "VAROES", "NICHOS",
    "CANTO", "REMATE", "ESTANTE_ABERTA", "PILAR",
)


@dataclass(frozen=True)
class ZonaDocumento:
    pagina: int
    x: float
    y: float
    largura: float
    altura: float


@dataclass(frozen=True)
class MedidaReconhecida:
    valor: Decimal | None
    unidade: str | None = None
    confianca: float = 0.0
    texto_origem: str | None = None


@dataclass(frozen=True)
class ModuloElegivel:
    id: int
    codigo: str
    nome: str
    largura_min_mm: Decimal | None = None
    largura_preferida_mm: Decimal | None = None
    largura_max_mm: Decimal | None = None
    posicao: str = POSICAO_QUALQUER
    permite_espelhar: bool = False
    caracteristicas: dict[str, Decimal] = field(default_factory=dict)


@dataclass(frozen=True)
class PedidoAnaliseRoupeiro:
    pdf_path: str
    item_id: int
    user_id: int
    pagina: int
    zona: ZonaDocumento | None
    recorte_png: bytes | None
    perfil: tuple[dict[str, str | None], ...]
    catalogo: tuple[ModuloElegivel, ...]
    respostas_utilizador: str = ""


@dataclass(frozen=True)
class AnaliseRoupeiro:
    referencia: str | None
    altura: MedidaReconhecida
    largura: MedidaReconhecida
    profundidade: MedidaReconhecida
    caracteristicas: dict[str, Decimal]
    restricoes: tuple[str, ...] = ()
    perguntas: tuple[str, ...] = ()
    confianca: float = 0.0
    explicacao: str = ""
    resultado_bruto: dict | None = None


@dataclass(frozen=True)
class PropostaModulo:
    def_modulo_id: int
    codigo: str
    nome: str
    ordem: int
    largura_mm: Decimal
    espelhado: bool = False


@dataclass(frozen=True)
class PropostaComposicao:
    modulos: tuple[PropostaModulo, ...]
    pontuacao: float
    explicacao: str
    largura_total_mm: Decimal


class VisionProvider(Protocol):
    nome: str
    modelo: str

    def analisar(self, pedido: PedidoAnaliseRoupeiro) -> AnaliseRoupeiro:
        ...


def medida_para_mm(valor: Decimal | str | int | float | None, unidade: str | None) -> Decimal | None:
    """Converte uma medida provável para mm; a confirmação humana continua obrigatória."""
    if valor is None:
        return None
    numero = Decimal(str(valor).strip().replace(" ", "").replace(",", "."))
    unidade_normalizada = (unidade or "mm").strip().lower()
    fatores = {"mm": Decimal("1"), "cm": Decimal("10"), "m": Decimal("1000")}
    if unidade_normalizada not in fatores:
        raise ValueError(f"Unidade de medida não suportada: {unidade}")
    return (numero * fatores[unidade_normalizada]).quantize(Decimal("0.001"))
