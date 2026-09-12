"""Arrumar as linhas de um modelo ValueSet por grupo e por chave.

Um modelo tem hoje ~100 linhas e vai para ~200. Ordenadas pelo código da chave
como texto, as chaves do mesmo assunto ficam espalhadas (``FERRAGEM_VARAO`` longe
de ``FERRAGEM_SUPORTE_LATERAL_VARAO``), e encontrar uma obriga a percorrer a
lista toda.

O vocabulário (``def_valueset_chaves``) já diz a que **grupo** pertence cada
chave e por que **ordem** ela deve aparecer dentro do grupo. Este módulo é só a
parte que arruma — sem Qt e sem base de dados, para poder ser testada tal como é
usada.

Uma chave que já não exista no vocabulário (renomeada, apagada) não desaparece:
cai no grupo "Sem grupo", à vista, porque é exatamente a que dá problemas no
custeio (ver ``valueset_compat``).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

#: Grupo onde caem as chaves que o vocabulário já não conhece.
SEM_GRUPO = ""

#: Ordem por que os grupos aparecem — a de quem orça, não a alfabética.
ORDEM_GRUPO: tuple[str, ...] = (
    "MATERIAIS",
    "FERRAGENS",
    "SISTEMAS_CORRER",
    "ILUMINACAO",
    "ORLAS",
    "ACABAMENTOS",
    "ACESSORIOS",
    "OUTROS",
)

ROTULO_GRUPO: dict[str, str] = {
    "MATERIAIS": "Materiais",
    "FERRAGENS": "Ferragens",
    "SISTEMAS_CORRER": "Sistemas de correr",
    "ILUMINACAO": "Iluminação",
    "ORLAS": "Orlas",
    "ACABAMENTOS": "Acabamentos",
    "ACESSORIOS": "Acessórios",
    "OUTROS": "Outros",
    SEM_GRUPO: "Sem grupo",
}

#: Ordem de uma chave que o vocabulário não conhece: vai para o fim do grupo.
ORDEM_DESCONHECIDA = 9_999


@dataclass(frozen=True)
class MetaChave:
    """O que o vocabulário sabe sobre uma chave: nome, grupo e ordem."""

    codigo: str
    nome: str
    grupo: str = SEM_GRUPO
    ordem: int = ORDEM_DESCONHECIDA


@dataclass(frozen=True)
class NoChave:
    """Uma chave e as linhas do modelo que lhe pertencem."""

    codigo: str
    nome: str
    ordem: int
    linhas: list[Any] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Quantas linhas tem esta chave."""
        return len(self.linhas)


@dataclass(frozen=True)
class NoGrupo:
    """Um grupo do vocabulário e as chaves que ele agrega."""

    codigo: str
    rotulo: str
    chaves: list[NoChave] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Quantas linhas tem o grupo todo."""
        return sum(chave.total for chave in self.chaves)


def rotulo_grupo(codigo: str | None) -> str:
    """Nome legível de um grupo ("Sem grupo" quando não há)."""
    normalizado = normalizar_grupo(codigo)
    return ROTULO_GRUPO.get(normalizado, normalizado or ROTULO_GRUPO[SEM_GRUPO])


def normalizar_grupo(codigo: str | None) -> str:
    """Grupo em maiúsculas e sem espaços; ``""`` quando vem vazio."""
    return (codigo or "").strip().upper()


def normalizar_chave(codigo: str | None) -> str:
    """Código de chave em maiúsculas e sem espaços."""
    return (codigo or "").strip().upper()


def indice_grupo(codigo: str | None) -> int:
    """Posição de um grupo na ordem de leitura.

    Um grupo que não esteja na lista fica logo antes do "Sem grupo": é um grupo
    novo de alguém, não uma chave órfã, e não deve ficar escondido no fim.
    """
    normalizado = normalizar_grupo(codigo)
    if normalizado in ORDEM_GRUPO:
        return ORDEM_GRUPO.index(normalizado)
    if normalizado == SEM_GRUPO:
        return len(ORDEM_GRUPO) + 1
    return len(ORDEM_GRUPO)


def metas_por_codigo(chaves: Iterable[Any]) -> dict[str, MetaChave]:
    """Converte os resumos de ``def_valueset_chaves`` em ``MetaChave``."""
    metas: dict[str, MetaChave] = {}
    for chave in chaves:
        codigo = normalizar_chave(getattr(chave, "codigo", None))
        if not codigo:
            continue
        ordem = getattr(chave, "ordem", None)
        metas[codigo] = MetaChave(
            codigo=codigo,
            nome=(getattr(chave, "nome", None) or codigo),
            grupo=normalizar_grupo(getattr(chave, "grupo", None)),
            ordem=ORDEM_DESCONHECIDA if ordem is None else int(ordem),
        )
    return metas


def meta_da_chave(
    codigo: str | None, metas: Mapping[str, MetaChave]
) -> MetaChave:
    """A ``MetaChave`` de uma chave, ou uma órfã ("Sem grupo") quando não existe."""
    normalizado = normalizar_chave(codigo)
    meta = metas.get(normalizado)
    if meta is not None:
        return meta
    return MetaChave(codigo=normalizado, nome=normalizado)


def agrupar_linhas(
    linhas: Sequence[Any], metas: Mapping[str, MetaChave]
) -> list[NoGrupo]:
    """Arruma as linhas em grupos → chaves, na ordem de leitura do vocabulário.

    Dentro de cada chave as linhas ficam pela ordem por que chegaram — ou seja,
    a ordem que o utilizador arrumou com as setas.
    """
    por_grupo: dict[str, dict[str, NoChave]] = {}

    for linha in linhas:
        meta = meta_da_chave(getattr(linha, "chave", None), metas)
        chaves = por_grupo.setdefault(meta.grupo, {})
        no = chaves.get(meta.codigo)
        if no is None:
            no = NoChave(codigo=meta.codigo, nome=meta.nome, ordem=meta.ordem)
            chaves[meta.codigo] = no
        no.linhas.append(linha)

    grupos: list[NoGrupo] = []
    for codigo_grupo in sorted(por_grupo, key=indice_grupo):
        chaves = por_grupo[codigo_grupo]
        ordenadas = sorted(
            chaves.values(), key=lambda no: (no.ordem, no.codigo)
        )
        grupos.append(
            NoGrupo(
                codigo=codigo_grupo,
                rotulo=rotulo_grupo(codigo_grupo),
                chaves=ordenadas,
            )
        )

    return grupos


def agrupar_linhas_contiguas(
    linhas: Sequence[Any], metas: Mapping[str, MetaChave]
) -> list[NoGrupo]:
    """Blocos de linhas SEGUIDAS do mesmo grupo e da mesma chave.

    É o que a tabela usa para pôr as faixas de separação. Ao contrário de
    :func:`agrupar_linhas`, não reordena nada: as linhas ficam exatamente na
    ordem em que o utilizador as arrumou com as setas, senão a seta "para cima"
    deixava de corresponder ao que se vê.

    Consequência: uma chave espalhada pela lista aparece em mais do que um
    bloco. É a verdade da coluna ``Ordem`` — e o sinal de que convém carregar em
    "Agrupar por chave".
    """
    grupos: list[NoGrupo] = []
    grupo_atual: str | None = None
    chave_atual: str | None = None

    for linha in linhas:
        meta = meta_da_chave(getattr(linha, "chave", None), metas)
        if not grupos or meta.grupo != grupo_atual:
            grupos.append(
                NoGrupo(codigo=meta.grupo, rotulo=rotulo_grupo(meta.grupo))
            )
            grupo_atual = meta.grupo
            chave_atual = None
        if meta.codigo != chave_atual:
            grupos[-1].chaves.append(
                NoChave(codigo=meta.codigo, nome=meta.nome, ordem=meta.ordem)
            )
            chave_atual = meta.codigo
        grupos[-1].chaves[-1].linhas.append(linha)

    return grupos


def ordenar_linhas_por_grupo_e_chave(
    linhas: Sequence[Any], metas: Mapping[str, MetaChave]
) -> list[Any]:
    """As linhas na ordem grupo → ordem da chave → prioridade.

    É o que o botão "Agrupar por chave" grava na coluna ``ordem``: a lista fica
    igual ao que se lê no navegador, em vez de alfabética pelo código da chave.
    """

    def ordenacao(linha: Any) -> tuple:
        meta = meta_da_chave(getattr(linha, "chave", None), metas)
        prioridade = getattr(linha, "prioridade", None)
        return (
            indice_grupo(meta.grupo),
            meta.ordem,
            meta.codigo,
            prioridade is None,
            prioridade or 0,
            getattr(linha, "id", 0) or 0,
        )

    return sorted(linhas, key=ordenacao)
