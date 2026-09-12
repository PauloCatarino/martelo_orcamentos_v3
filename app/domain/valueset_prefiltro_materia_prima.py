"""Que Tipo/Família propor ao abrir o catálogo a partir de uma linha ValueSet.

O catálogo tem ~1400 matérias-primas. Quando se acrescenta uma opção a uma
chave de ferragens, interessam umas dezenas — e o utilizador tinha de escolher
os dois filtros à mão de cada vez.

A linha que já está preenchida diz-nos logo o que queremos (é o snapshot dela).
Para uma linha nova não há snapshot nenhum, e aí olha-se para as **irmãs**: as
outras opções da mesma chave. Medido na base real (martelo_v3, 343 pares
modelo+chave com snapshot):

- família: 100% das chaves têm uma só família;
- tipo: 95%. Os 5% que divergem são legítimos — a mesma chave com AGLOMERADO e
  com MDF, que é precisamente para isso que serve haver várias opções.

Por isso o tipo escolhe-se pelo mais frequente e nunca é uma imposição: o
diálogo do catálogo mostra sempre os dois filtros e tem o "Limpar filtros".
O nível do modelo não serve para nada aqui — cada modelo tem 16 a 17 tipos.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

__all__ = ["sugerir_tipo_familia_da_chave"]


def _texto(valor: Any) -> str:
    return (valor or "").strip() if isinstance(valor, str) else ""


def _mais_frequente(valores: Iterable[str]) -> str | None:
    """O valor mais repetido; em caso de empate, o primeiro que apareceu."""
    contagem = Counter(v for v in valores if v)
    if not contagem:
        return None
    return contagem.most_common(1)[0][0]


def sugerir_tipo_familia_da_chave(
    linhas: Iterable[Any], chave: str | None
) -> tuple[str | None, str | None]:
    """Tipo e família a pré-preencher no catálogo, vindos das linhas irmãs.

    ``linhas`` são as linhas já carregadas do quadro (modelo, orçamento ou
    item): qualquer objeto com ``chave``, ``tipo_materia_prima``,
    ``familia_materia_prima`` e ``ativo`` serve. As inativas contam à mesma —
    desativar uma opção não muda o género de material que a chave usa.
    """
    if not chave:
        return None, None

    alvo = chave.strip().upper()
    if not alvo:
        return None, None

    tipos: list[str] = []
    familias: list[str] = []
    for linha in linhas:
        if _texto(getattr(linha, "chave", None)).upper() != alvo:
            continue
        tipos.append(_texto(getattr(linha, "tipo_materia_prima", None)))
        familias.append(_texto(getattr(linha, "familia_materia_prima", None)))

    return _mais_frequente(tipos), _mais_frequente(familias)
