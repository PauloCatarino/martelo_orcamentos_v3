"""Shared vocabulary of the raw-material catalog.

Kept in one place so the model, the validation rules, the import and the
screens all speak the same language. Change a value here and it changes
everywhere.
"""

from __future__ import annotations

from datetime import date, datetime

# --- Tipo de preço ---------------------------------------------------------
# TABELA: o preço vem da tabela do fornecedor e é usado tal como está.
# LIVRE: material de rascunho (PLACAS LIVRES, FERRAGEM LIVRE, LACAGEM LIVRE,
# ORLA LIVRE) que entra no orçamento sem preço, para o utilizador escrever o
# valor dessa obra. Não ter preço aqui é o comportamento esperado, não um erro.
TIPO_PRECO_TABELA = "TABELA"
TIPO_PRECO_LIVRE = "LIVRE"
TIPOS_PRECO_VALIDOS = (TIPO_PRECO_TABELA, TIPO_PRECO_LIVRE)

# --- Origem de um preço no histórico ---------------------------------------
ORIGEM_PRECO_EXCEL = "EXCEL"
ORIGEM_PRECO_MANUAL = "MANUAL"
ORIGEM_PRECO_FORNECEDOR = "FORNECEDOR"
ORIGENS_PRECO_VALIDAS = (
    ORIGEM_PRECO_EXCEL,
    ORIGEM_PRECO_MANUAL,
    ORIGEM_PRECO_FORNECEDOR,
)

# --- Classificação ---------------------------------------------------------
FAMILIA_ACABAMENTOS = "ACABAMENTOS"
FAMILIA_FERRAGENS = "FERRAGENS"
FAMILIA_ORLA = "ORLA"
FAMILIA_PLACAS = "PLACAS"
FAMILIAS_VALIDAS = (
    FAMILIA_ACABAMENTOS,
    FAMILIA_FERRAGENS,
    FAMILIA_ORLA,
    FAMILIA_PLACAS,
)

UNIDADES_VALIDAS = ("M2", "ML", "UND")

# Prefixo da Ref LE por família, com quatro dígitos (PLC0001, FER0157, ...).
# É a mesma regra da macro `Atualizar_ID_e_Ref` do Excel, para as referências
# geradas no V3 continuarem a sair iguais às de sempre.
PREFIXOS_REF_LE = {
    FAMILIA_ACABAMENTOS: "ACB",
    FAMILIA_FERRAGENS: "FER",
    FAMILIA_ORLA: "ORL",
    FAMILIA_PLACAS: "PLC",
}
DIGITOS_REF_LE = 4

# Um preço com esta idade (em meses) passa a pedir revisão.
MESES_PRECO_DESATUALIZADO = 12


def prefixo_da_familia(familia: str | None) -> str | None:
    """Prefixo da Ref LE para uma família, ou None quando não há regra."""
    if familia is None:
        return None

    return PREFIXOS_REF_LE.get(familia.strip().upper())


def formatar_ref_le(prefixo: str, numero: int) -> str:
    """Montar uma Ref LE a partir do prefixo e do número (PLC + 121 -> PLC0121)."""
    return f"{prefixo}{numero:0{DIGITOS_REF_LE}d}"


def meses_desde(valor: date | datetime | None, hoje: date | None = None) -> int | None:
    """Meses inteiros entre uma data e hoje, ou None quando não há data."""
    if valor is None:
        return None

    if isinstance(valor, datetime):
        valor = valor.date()

    hoje = hoje or date.today()
    meses = (hoje.year - valor.year) * 12 + (hoje.month - valor.month)
    if hoje.day < valor.day:
        meses -= 1

    return max(meses, 0)


def preco_em_falta(materia) -> bool:
    """True quando o material devia ter preço e não tem.

    Materiais de preço livre não contam: não terem preço é o que se espera.
    """
    if getattr(materia, "tipo_preco", TIPO_PRECO_TABELA) == TIPO_PRECO_LIVRE:
        return False

    return not getattr(materia, "preco_liquido", None)


def preco_desatualizado(
    materia,
    hoje: date | None = None,
    meses_limite: int = MESES_PRECO_DESATUALIZADO,
) -> bool:
    """True quando o preço já pede revisão.

    Sem data também conta: não se sabe de quando é o preço. Materiais de preço
    livre e materiais ainda sem preço ficam de fora — esses têm outro aviso.
    """
    if getattr(materia, "tipo_preco", TIPO_PRECO_TABELA) == TIPO_PRECO_LIVRE:
        return False

    if not getattr(materia, "preco_liquido", None):
        return False

    meses = meses_desde(getattr(materia, "data_ultimo_preco", None), hoje)
    return meses is None or meses >= meses_limite
