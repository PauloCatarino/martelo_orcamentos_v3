"""Pure helpers for the budget list page.

A pesquisa usa o mesmo motor da Produção (:mod:`app.domain.pesquisa_texto`):
acentos, pontuação, plurais portugueses e sinónimos do perfil do utilizador.
A ordenação por coluna calcula uma **chave comparável** por campo (nunca o
texto apresentado), incluindo a ordem de **entrada** (data de criação e, em
empate, o id da versão).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.domain import pesquisa_texto

#: Campos onde a pesquisa procura — cobre tudo o que a lista mostra.
#:
#: Além dos 12 campos originais entram ``ano``, ``codigo_versao`` e
#: ``preco_total``: assim procurar «2026», «260001_02» ou «1500» encontra a
#: linha certa, tal como a Produção passou a cobrir todos os campos do menu.
_CAMPOS_PESQUISA = (
    "ano",
    "num_orcamento",
    "codigo_versao",
    "cliente_nome",
    "ref_cliente",
    "obra",
    "localizacao",
    "descricao",
    "estado",
    "utilizador",
    "enc_phc",
    "enc_phc_todos",
    "preco_total",
    "info_1",
    "info_2",
)

_MENOR_DATA = datetime.min


def resumo_lista(orcamentos):
    """Return (count, total_price), ignoring missing prices in the total."""
    total = Decimal("0")
    contagem = 0
    for orcamento in orcamentos or []:
        contagem += 1
        preco = getattr(orcamento, "preco_total", None)
        if preco is not None:
            total += preco

    return contagem, total


# ---- pesquisa -----------------------------------------------------------
def termos_pesquisa(texto, sinonimos=None) -> list[frozenset[str]]:
    """Split the search text into the roots that satisfy each written word."""
    return pesquisa_texto.expandir_termos(texto, sinonimos)


def indice_orcamento(orcamento) -> frozenset[str]:
    """Root index of one budget, used to compare quickly."""
    return pesquisa_texto.indexar(
        getattr(orcamento, campo, None) for campo in _CAMPOS_PESQUISA
    )


def vocabulario_orcamentos(orcamentos) -> set[str]:
    """Every root present in a list, for the «quis dizer…» suggestion."""
    vocabulario: set[str] = set()
    for orcamento in orcamentos or []:
        vocabulario.update(indice_orcamento(orcamento))
    return vocabulario


def orcamento_corresponde(
    orcamento,
    *,
    termos=(),
    estado=None,
    cliente=None,
    utilizador=None,
    indice=None,
) -> bool:
    """Return True when one budget matches the current search and filters.

    ``indice`` permite reaproveitar as raízes já calculadas para este
    orçamento (a lista indexa uma vez por carregamento).
    """
    estado_norm = _normalizar_filtro(estado)
    cliente_norm = _normalizar_filtro(cliente)
    utilizador_norm = _normalizar_filtro(utilizador)

    if estado_norm and _texto(getattr(orcamento, "estado", None)) != estado_norm:
        return False
    if (
        cliente_norm
        and _texto(getattr(orcamento, "cliente_nome", None)) != cliente_norm
    ):
        return False
    if (
        utilizador_norm
        and _texto(getattr(orcamento, "utilizador", None)) != utilizador_norm
    ):
        return False

    if not termos:
        return True

    if indice is None:
        indice = indice_orcamento(orcamento)
    return pesquisa_texto.corresponde(indice, termos)


def filtrar_orcamentos(
    orcamentos,
    texto="",
    estado=None,
    cliente=None,
    utilizador=None,
    sinonimos=None,
):
    """Filter budget read models in memory, using the shared search motor."""
    termos = termos_pesquisa(texto, sinonimos)
    return [
        orcamento
        for orcamento in (orcamentos or [])
        if orcamento_corresponde(
            orcamento,
            termos=termos,
            estado=estado,
            cliente=cliente,
            utilizador=utilizador,
        )
    ]


# ---- ordenação ----------------------------------------------------------
def chave_ordenacao(orcamento, coluna: str):
    """Comparable value for one budget on one column (never displayed text)."""
    if coluna == "entrada":
        # Ordem de entrada: data de criação e, em empate, o id da versão.
        criada = getattr(orcamento, "created_at", None) or _MENOR_DATA
        return (criada, _chave_int(getattr(orcamento, "orcamento_versao_id", 0)))
    if coluna == "ano":
        return _chave_int(getattr(orcamento, "ano", 0))
    if coluna == "numero_versao":
        return _chave_int(getattr(orcamento, "numero_versao", 0))
    if coluna == "num_orcamento":
        return _chave_alfanumerica(getattr(orcamento, "num_orcamento", None))
    if coluna == "preco_total":
        return _chave_decimal(getattr(orcamento, "preco_total", None))
    return _texto(getattr(orcamento, coluna, None))


def ordenar_orcamentos(orcamentos, coluna: str | None = None, ascendente: bool = True):
    """Return the budgets sorted by one column key; source order if none.

    A ordenação é estável nos dois sentidos, por isso as versões do mesmo
    orçamento mantêm-se juntas dentro de empates (ex.: ordenar por Cliente).
    """
    if not coluna:
        return list(orcamentos or [])
    return sorted(
        orcamentos or [],
        key=lambda orcamento: chave_ordenacao(orcamento, coluna),
        reverse=not ascendente,
    )


def _normalizar_filtro(valor) -> str | None:
    texto = _texto(valor)
    if not texto or texto == "todos":
        return None
    return texto


def _texto(valor) -> str:
    """Normalise text for searching/sorting (delega no motor de pesquisa)."""
    return pesquisa_texto.normalizar(valor)


def _chave_int(valor) -> int:
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return 0


def _chave_alfanumerica(valor) -> tuple[int, int, str]:
    """Sort numbers as numbers («9» before «10») and text after, tolerantly."""
    texto = "" if valor is None else str(valor).strip()
    if texto.isdigit():
        return (0, int(texto), "")
    return (1, 0, texto.lower())


def _chave_decimal(valor) -> Decimal:
    """Sortable key for prices; empty values sort lowest."""
    if valor is None or valor == "":
        return Decimal("-Infinity")
    try:
        return Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("-Infinity")
