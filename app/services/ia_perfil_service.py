"""Per-user AI profile: the vocabulary and preferences each person teaches.

Nada aqui é usado para escrever nos dados das obras — serve só para o
assistente perceber melhor as perguntas de quem as faz.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.pesquisa_texto import normalizar
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
    #: Linhas prontas a acrescentar, para não se começar de uma folha em branco.
    #: Cada uma é (expressão, significado). Ver ``sugestoes_em_falta``.
    sugestoes: tuple[tuple[str, str], ...] = ()


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
        sugestoes=(
            ("Que obras estão atrasadas?", "As que já passaram da data de entrega"),
            ("O que tenho para entregar esta semana", "Obras com entrega nos próximos 7 dias"),
            ("Em que pé está a obra do Viva?", "Estado e fases de produção dessa obra"),
            ("Quais são as minhas obras?", "As obras de que sou responsável"),
            ("O que está em desenho?", "Obras no estado Desenho"),
        ),
    ),
    TipoEntrada(
        "movel",
        "Tipos de trabalho e de móvel",
        "Palavra que uso",
        "Outras formas de dizer o mesmo",
        True,
        "Roupeiro, closet, canto cego… e onde é que essa palavra aparece na obra.",
        sugestoes=(
            ("roupeiro", "closet, armário de quarto"),
            ("cozinha", "móveis de cozinha, bancada"),
            ("canto cego", "módulo de canto com ferragem especial"),
            ("painel ripado", "painel de réguas, ripado decorativo"),
        ),
    ),
    TipoEntrada(
        "material",
        "Materiais e acabamentos",
        "Palavra que uso",
        "O que significa exatamente",
        True,
        "Lacado, sandwich, HPL, verniz… e o que quero dizer com isso.",
        sugestoes=(
            ("lacado", "peça para pintar, material sem acabamento de fábrica"),
            ("sandwich", "duas faces coladas a um núcleo"),
            ("HPL", "laminado de alta pressão"),
            ("termolaminado", "folha termolaminada sobre MDF"),
        ),
    ),
    TipoEntrada(
        "estado",
        "Estados da obra",
        "Expressão que digo",
        "A que estado corresponde",
        False,
        "«Está na máquina» = Produção. Lembrete: «obra fechada» = Arquivado.",
        sugestoes=(
            ("está na máquina", "Produção"),
            ("obra fechada", "Arquivado"),
            ("está a ser desenhada", "Desenho"),
            ("já foi", "Entregue"),
        ),
    ),
    TipoEntrada(
        "pessoa",
        "Pessoas",
        "Como lhe chamo",
        "Nome que está no Martelo",
        False,
        "Alcunhas, apelidos e iniciais. Os acentos já não são problema.",
        sugestoes=(
            ("Elsa", "Elsa Belo"),
            ("Dulce", "Dulce Faria"),
            ("Pedro", "Pedro Reis"),
        ),
    ),
    TipoEntrada(
        "cliente",
        "Clientes",
        "Como digo",
        "Nome completo do cliente",
        False,
        "Abreviaturas e nomes curtos dos clientes com que mais trabalho.",
        sugestoes=(
            ("Viva", "MÓVEIS J.F. VIVA"),
            ("Sá Machado", "Sá Machado & Filhos"),
        ),
    ),
    TipoEntrada(
        "tempo",
        "Tempo e urgência",
        "Expressão",
        "O que significa em dias",
        True,
        "«Urgente» são quantos dias? A partir de que data conta?",
        sugestoes=(
            ("urgente", "entrega nos próximos 3 dias"),
            ("esta semana", "até sexta-feira desta semana"),
            ("para o mês que vem", "entrega no mês seguinte ao atual"),
        ),
    ),
    TipoEntrada(
        "ambigua",
        "Palavras que podem confundir",
        "Palavra",
        "O que ele deve perguntar",
        False,
        "Palavras com dois sentidos. O assistente deve perguntar, não adivinhar.",
        sugestoes=(
            ("porta", "Perguntar se é porta de roupeiro ou porta de entrada"),
            ("branco", "Perguntar se é a cor ou o material lacado branco"),
            ("Viva", "Perguntar se é o cliente J.F. Viva ou a obra da Viva"),
        ),
    ),
    TipoEntrada(
        "aviso",
        "Avisos que me davam jeito",
        "Aviso",
        "De quanto em quanto tempo",
        False,
        "O que gostavas que o Martelo te lembrasse, e com que frequência.",
        sugestoes=(
            ("Obras que entram em atraso", "Todas as manhãs"),
            ("Obras sem data de entrega definida", "Uma vez por semana"),
            ("Tickets abertos há mais de 15 dias", "Uma vez por semana"),
        ),
    ),
    TipoEntrada(
        "nao_quero",
        "O que NÃO quero ver",
        "Isto não quero que apareça",
        "Porquê",
        False,
        "O que te irritaria ou te daria a sensação de estares a ser vigiado. "
        "O que escreveres aqui passa a ser regra.",
        sugestoes=(
            ("Comparar o meu trabalho com o dos colegas", "Não é para isso que serve"),
            ("Mostrar preços a quem não os deve ver", "Informação reservada"),
            ("Inventar uma resposta quando não sabe", "Prefiro que diga que não sabe"),
        ),
    ),
    TipoEntrada(
        "instrucao_email",
        "Instruções para emails",
        "Instrução",
        "Detalhe (opcional)",
        False,
        "Como queres que o Martelo escreva os EMAILS ao cliente. Ex.: «Tom formal "
        "e simpático»; «Saudação conforme a hora (Bom dia/Boa tarde)»; «Explicar o "
        "estado em linguagem simples»; «Realçar a Ref. do cliente»; «Assinar 'Lança "
        "Encanto'»; «Nunca falar de preços».",
        sugestoes=(
            ("Tom formal e simpático", ""),
            ("Saudação conforme a hora (Bom dia / Boa tarde)", ""),
            ("Explicar o estado em linguagem simples", "Sem termos técnicos"),
            ("Realçar a Ref. do cliente", "É por ela que o cliente se orienta"),
            ("Nunca falar de preços", "Preços só por proposta formal"),
            ("Assinar 'Lança Encanto'", ""),
        ),
    ),
    TipoEntrada(
        "instrucao_pdf",
        "Instruções para o relatório PDF",
        "Instrução",
        "Detalhe (opcional)",
        False,
        "Como queres o RELATÓRIO PDF do ponto de situação. Ex.: «Não incluir preços "
        "nem notas internas»; «Mostrar a imagem da obra»; «Realçar a Ref. do "
        "cliente»; «Listar as fases de produção»; «Incluir as versões de CUT-RITE».",
        sugestoes=(
            ("Não incluir preços nem notas internas", "O PDF vai para o cliente"),
            ("Mostrar a imagem da obra", "A imagem do IMOS"),
            ("Realçar a Ref. do cliente", ""),
            ("Listar as fases de produção", ""),
            ("Incluir as versões de CUT-RITE", ""),
        ),
    ),
    TipoEntrada(
        "instrucao_ocorrencias",
        "Instruções para o relatório de ocorrências",
        "Instrução",
        "Detalhe (opcional)",
        False,
        "Como queres o RELATÓRIO DAS OCORRÊNCIAS (os tickets da obra). Ex.: "
        "«Incluir sempre as fotos»; «Separar os erros nossos dos pedidos do "
        "cliente»; «Mostrar quem ficou responsável»; «Não incluir os custos».",
        sugestoes=(
            ("Incluir sempre as fotos", "Uma imagem vale mais que um bom texto"),
            ("Separar os erros nossos dos pedidos do cliente", "É o que interessa no fim do ano"),
            ("Mostrar quem ficou responsável por cada ticket", ""),
            ("Não incluir os custos", "Quando o relatório sai para fora"),
            ("Pôr primeiro os tickets por resolver", ""),
        ),
    ),
    TipoEntrada(
        "instrucao_texto",
        "Instruções para texto (WhatsApp)",
        "Instrução",
        "Detalhe (opcional)",
        False,
        "Como queres o TEXTO para colar no WhatsApp. Ex.: «Curto e prático»; «Sem "
        "imagem, só texto»; «Estado e entrega no topo»; «Fases uma por linha»; «Sem "
        "a descrição de produção».",
        sugestoes=(
            ("Curto e prático", "Poucas linhas, para ler no telemóvel"),
            ("Estado e entrega logo no topo", ""),
            ("Fases uma por linha", ""),
            ("Sem a descrição de produção", "É demasiado comprida para o chat"),
        ),
    ),
)

TIPOS_POR_CHAVE = {tipo.chave: tipo for tipo in TIPOS_ENTRADA}


def sugestoes_do_tipo(tipo: str) -> tuple[tuple[str, str], ...]:
    """Ready-made lines for one quadro (empty tuple for unknown keys)."""
    entrada = TIPOS_POR_CHAVE.get((tipo or "").strip())
    return entrada.sugestoes if entrada is not None else ()


def sugestoes_em_falta(
    session: Session, user_id: int, tipo: str
) -> list[tuple[str, str]]:
    """Suggestions this user has not written yet.

    Uma folha em branco é o que mais trava quem nunca ensinou o assistente: o
    quadro passa a chegar com linhas prontas, e as que já foram acrescentadas
    desaparecem da lista para não se repetirem.
    """
    sugestoes = sugestoes_do_tipo(tipo)
    if not sugestoes:
        return []

    ja_escritas = {
        _chave_comparacao(entrada.expressao)
        for entrada in listar_entradas(session, user_id, tipo)
    }
    return [
        (expressao, significado)
        for expressao, significado in sugestoes
        if _chave_comparacao(expressao) not in ja_escritas
    ]


def acrescentar_sugestoes(
    session: Session, user_id: int, tipo: str, sugestoes=None
) -> int:
    """Add the missing suggestions at once; return how many were written."""
    pendentes = (
        list(sugestoes)
        if sugestoes is not None
        else sugestoes_em_falta(session, user_id, tipo)
    )

    criadas = 0
    for expressao, significado in pendentes:
        try:
            criar_entrada(
                session,
                user_id=user_id,
                tipo=tipo,
                expressao=expressao,
                significado=significado,
            )
        except ValueError:
            # Uma sugestão repetida não deve travar as restantes.
            continue
        criadas += 1
    return criadas


def _chave_comparacao(texto: str | None) -> str:
    """Compare suggestions by their normalized expression."""
    return normalizar(texto)


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
