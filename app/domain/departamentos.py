"""Departamentos (áreas de trabalho) dos utilizadores do Martelo.

A lista é uma sugestão, não uma prisão: o campo é texto livre e o combo é
editável, para se poder acrescentar uma área nova sem migração nenhuma.
"""

from __future__ import annotations


#: Sugestões apresentadas no combo, pela ordem em que fazem sentido no fluxo.
DEPARTAMENTOS: tuple[str, ...] = (
    "Orçamentação",
    "Preparação (desenhos)",
    "Assistente de produção",
    "Produção",
    "Expedição",
    "Montagem",
    "Compras",
    "Administrativa",
    "Direção",
)

#: Departamentos cujo trabalho vive sobretudo no menu Produção. Serve para o
#: assistente saber que perguntas fazem sentido a cada pessoa.
DEPARTAMENTOS_PRODUCAO: frozenset[str] = frozenset(
    {
        "preparacao (desenhos)",
        "assistente de producao",
        "producao",
        "expedicao",
        "montagem",
    }
)

#: Departamentos cujo trabalho vive sobretudo no menu Orçamentos.
DEPARTAMENTOS_ORCAMENTOS: frozenset[str] = frozenset({"orcamentacao"})


def normalizar_departamento(valor: object) -> str:
    """Return the department as stored: trimmed, or empty when unset."""
    return "" if valor is None else str(valor).strip()


def _chave(valor: object) -> str:
    import unicodedata

    texto = unicodedata.normalize("NFKD", normalizar_departamento(valor).lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def e_de_producao(departamento: object) -> bool:
    """True when this department works mostly in the Produção menu."""
    return _chave(departamento) in DEPARTAMENTOS_PRODUCAO


def e_de_orcamentos(departamento: object) -> bool:
    """True when this department works mostly in the Orçamentos menu."""
    return _chave(departamento) in DEPARTAMENTOS_ORCAMENTOS
