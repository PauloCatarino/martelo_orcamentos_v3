"""Per-user AI profile: the vocabulary and preferences each person teaches.

Nada aqui é usado para escrever nos dados das obras — serve só para o
assistente perceber melhor as perguntas de quem as faz.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ia_perfil import IaPerfilEntrada


@dataclass(frozen=True)
class TipoEntrada:
    """One kind of profile line, matching a table of the questionnaire."""

    chave: str
    titulo: str
    rotulo_expressao: str
    rotulo_significado: str
    usa_campos: bool
    ajuda: str


#: Os quadros do questionário, pela ordem em que fazem sentido preencher.
TIPOS_ENTRADA: tuple[TipoEntrada, ...] = (
    TipoEntrada(
        "pergunta",
        "Perguntas que faço",
        "Pergunta",
        "O que esperava que aparecesse",
        False,
        "As perguntas que farias a um colega. É a parte que mais ensina o "
        "assistente.",
    ),
    TipoEntrada(
        "movel",
        "Tipos de trabalho e de móvel",
        "Palavra que uso",
        "Outras formas de dizer o mesmo",
        True,
        "Roupeiro, closet, canto cego… e onde é que essa palavra aparece na obra.",
    ),
    TipoEntrada(
        "material",
        "Materiais e acabamentos",
        "Palavra que uso",
        "O que significa exatamente",
        True,
        "Lacado, sandwich, HPL, verniz… e o que quero dizer com isso.",
    ),
    TipoEntrada(
        "estado",
        "Estados da obra",
        "Expressão que digo",
        "A que estado corresponde",
        False,
        "«Está na máquina» = Produção. Lembrete: «obra fechada» = Arquivado.",
    ),
    TipoEntrada(
        "pessoa",
        "Pessoas",
        "Como lhe chamo",
        "Nome que está no Martelo",
        False,
        "Alcunhas, apelidos e iniciais. Os acentos já não são problema.",
    ),
    TipoEntrada(
        "cliente",
        "Clientes",
        "Como digo",
        "Nome completo do cliente",
        False,
        "Abreviaturas e nomes curtos dos clientes com que mais trabalho.",
    ),
    TipoEntrada(
        "tempo",
        "Tempo e urgência",
        "Expressão",
        "O que significa em dias",
        True,
        "«Urgente» são quantos dias? A partir de que data conta?",
    ),
    TipoEntrada(
        "ambigua",
        "Palavras que podem confundir",
        "Palavra",
        "O que ele deve perguntar",
        False,
        "Palavras com dois sentidos. O assistente deve perguntar, não adivinhar.",
    ),
    TipoEntrada(
        "aviso",
        "Avisos que me davam jeito",
        "Aviso",
        "De quanto em quanto tempo",
        False,
        "O que gostavas que o Martelo te lembrasse, e com que frequência.",
    ),
    TipoEntrada(
        "nao_quero",
        "O que NÃO quero ver",
        "Isto não quero que apareça",
        "Porquê",
        False,
        "O que te irritaria ou te daria a sensação de estares a ser vigiado. "
        "O que escreveres aqui passa a ser regra.",
    ),
)

TIPOS_POR_CHAVE = {tipo.chave: tipo for tipo in TIPOS_ENTRADA}


def listar_entradas(
    session: Session,
    user_id: int,
    tipo: str | None = None,
) -> list[IaPerfilEntrada]:
    """List one user's profile lines, optionally filtered by kind."""
    statement = select(IaPerfilEntrada).where(IaPerfilEntrada.user_id == user_id)
    if tipo:
        statement = statement.where(IaPerfilEntrada.tipo == tipo)
    statement = statement.order_by(
        IaPerfilEntrada.tipo,
        IaPerfilEntrada.expressao,
    )
    return list(session.scalars(statement).all())


def contar_por_tipo(session: Session, user_id: int) -> dict[str, int]:
    """Return how many lines this user wrote for each kind."""
    contagem: dict[str, int] = {}
    for entrada in listar_entradas(session, user_id):
        contagem[entrada.tipo] = contagem.get(entrada.tipo, 0) + 1
    return contagem


def criar_entrada(
    session: Session,
    *,
    user_id: int,
    tipo: str,
    expressao: str,
    significado: str = "",
    campos: str = "",
) -> IaPerfilEntrada:
    """Add one profile line, validating the kind and the expression."""
    tipo = (tipo or "").strip()
    if tipo not in TIPOS_POR_CHAVE:
        raise ValueError(f"Tipo de entrada desconhecido: {tipo!r}")

    expressao = (expressao or "").strip()
    if not expressao:
        raise ValueError("Escreva a expressão antes de gravar.")

    entrada = IaPerfilEntrada(
        user_id=user_id,
        tipo=tipo,
        expressao=expressao,
        significado=(significado or "").strip() or None,
        campos=(campos or "").strip() or None,
    )
    session.add(entrada)
    session.flush()
    return entrada


def atualizar_entrada(
    session: Session,
    entrada_id: int,
    *,
    user_id: int,
    expressao: str,
    significado: str = "",
    campos: str = "",
) -> IaPerfilEntrada:
    """Update one line, refusing to touch another user's profile."""
    entrada = session.get(IaPerfilEntrada, entrada_id)
    if entrada is None or entrada.user_id != user_id:
        raise ValueError("Entrada não encontrada no seu perfil.")

    expressao = (expressao or "").strip()
    if not expressao:
        raise ValueError("Escreva a expressão antes de gravar.")

    entrada.expressao = expressao
    entrada.significado = (significado or "").strip() or None
    entrada.campos = (campos or "").strip() or None
    session.flush()
    return entrada


def eliminar_entrada(session: Session, entrada_id: int, *, user_id: int) -> None:
    """Delete one line of this user's own profile."""
    entrada = session.get(IaPerfilEntrada, entrada_id)
    if entrada is None or entrada.user_id != user_id:
        raise ValueError("Entrada não encontrada no seu perfil.")
    session.delete(entrada)
    session.flush()
