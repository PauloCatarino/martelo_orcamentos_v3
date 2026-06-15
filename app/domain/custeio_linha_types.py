"""Cost line type constants, labels, and helpers."""

from __future__ import annotations

PECA = "PECA"
PECA_COMPOSTA = "PECA_COMPOSTA"
DIVISAO_INDEPENDENTE = "DIVISAO_INDEPENDENTE"
MATERIAL_PECA = "MATERIAL_PECA"
ORLA_PECA = "ORLA_PECA"
FERRAGEM = "FERRAGEM"
ACESSORIO = "ACESSORIO"
OPERACAO = "OPERACAO"
MAQUINA = "MAQUINA"
ACABAMENTO = "ACABAMENTO"
MAO_OBRA = "MAO_OBRA"
SETUP = "SETUP"
MANUAL = "MANUAL"
OPERACAO_MANUAL = "OPERACAO_MANUAL"
# Purely visual empty row to separate blocks for readability (phase 8V.3).
# Carries no def_peca/material/measures/costs and is ignored by every recompute
# and by the independent-division propagation (it never ends a division block).
SEPARADOR = "SEPARADOR"
OUTRO = "OUTRO"

CUSTEIO_LINHA_TYPE_LABELS = {
    PECA: "Peça",
    PECA_COMPOSTA: "Peça composta",
    DIVISAO_INDEPENDENTE: "Divisão independente",
    MATERIAL_PECA: "Material da peça",
    ORLA_PECA: "Orla da peça",
    FERRAGEM: "Ferragem",
    ACESSORIO: "Acessório",
    OPERACAO: "Operação",
    MAQUINA: "Máquina",
    ACABAMENTO: "Acabamento",
    MAO_OBRA: "Mão de obra",
    SETUP: "Setup",
    MANUAL: "Manual",
    OPERACAO_MANUAL: "Operação manual",
    SEPARADOR: "Separador",
    OUTRO: "Outro",
}


def get_custeio_linha_type_label(tipo: str | None) -> str:
    """Return a friendly label for a cost line type."""
    return CUSTEIO_LINHA_TYPE_LABELS[normalize_custeio_linha_type(tipo)]


def get_custeio_linha_type_options() -> tuple[tuple[str, str], ...]:
    """Return cost line type options as code/label pairs."""
    return tuple(CUSTEIO_LINHA_TYPE_LABELS.items())


def normalize_custeio_linha_type(tipo: str | None) -> str:
    """Normalize a cost line type code, falling back to OUTRO."""
    if not tipo:
        return OUTRO

    normalized = tipo.strip().upper()
    if normalized in CUSTEIO_LINHA_TYPE_LABELS:
        return normalized

    return OUTRO
