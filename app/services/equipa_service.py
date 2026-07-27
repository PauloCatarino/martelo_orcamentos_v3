"""A equipa: quem pode ficar responsável por um ticket e onde o receber.

Não são as contas do V3 — quem monta, corta ou prepara não entra no programa,
mas tem de receber o ticket no chat. O ``email`` é o endereço do Microsoft
Teams; sem ele, o ticket só se copia para a área de transferência.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.pesquisa_texto import normalizar
from app.models.equipa_membro import EquipaMembro
from app.models.producao import Producao
from app.models.user import User


def listar_membros(session: Session, *, incluir_inativos: bool = False) -> list[EquipaMembro]:
    """Team members, by ordem then nome."""
    statement = select(EquipaMembro).order_by(EquipaMembro.ordem, EquipaMembro.nome)
    if not incluir_inativos:
        statement = statement.where(EquipaMembro.ativo.is_(True))
    return list(session.scalars(statement).all())


def obter_por_nome(session: Session, nome: str | None) -> EquipaMembro | None:
    """Find a member by name (case-insensitive) — None if there is no match."""
    alvo = (nome or "").strip()
    if not alvo:
        return None
    statement = select(EquipaMembro).where(
        func.lower(EquipaMembro.nome) == alvo.lower()
    )
    return session.scalars(statement).first()


def criar_membro(
    session: Session, *, nome: str, email: str | None = None, ordem: int = 0
) -> EquipaMembro:
    """Add someone to the team."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Escreva o nome da pessoa.")
    if obter_por_nome(session, nome) is not None:
        raise ValueError(f"'{nome}' já está na equipa.")

    membro = EquipaMembro(
        nome=nome[:120],
        email=(email or "").strip()[:255] or None,
        ativo=True,
        ordem=ordem,
    )
    session.add(membro)
    session.flush()
    return membro


def atualizar_membro(
    session: Session,
    membro_id: int,
    *,
    nome: str | None = None,
    email: str | None = None,
    ativo: bool | None = None,
) -> EquipaMembro:
    """Change a team member's name, Teams address or activity."""
    membro = session.get(EquipaMembro, membro_id)
    if membro is None:
        raise ValueError("Pessoa não encontrada.")

    if nome is not None:
        novo = nome.strip()
        if not novo:
            raise ValueError("Escreva o nome da pessoa.")
        existente = obter_por_nome(session, novo)
        if existente is not None and existente.id != membro.id:
            raise ValueError(f"'{novo}' já está na equipa.")
        membro.nome = novo[:120]
    if email is not None:
        membro.email = email.strip()[:255] or None
    if ativo is not None:
        membro.ativo = bool(ativo)

    session.flush()
    return membro


def eliminar_membro(session: Session, membro_id: int) -> None:
    """Remove someone from the team (os tickets antigos guardam o nome)."""
    membro = session.get(EquipaMembro, membro_id)
    if membro is None:
        raise ValueError("Pessoa não encontrada.")
    session.delete(membro)
    session.flush()


def semear_de_producao(session: Session) -> int:
    """Create members from the names already used as responsável das obras.

    Poupa ao Paulo escrever de novo uma lista que o programa já conhece; os
    emails do Teams ficam por preencher, que é o que só ele sabe.
    """
    nomes = {
        (nome or "").strip()
        for (nome,) in session.execute(
            select(Producao.responsavel).where(Producao.responsavel.isnot(None))
        ).all()
        if (nome or "").strip()
    }
    existentes = {
        (membro.nome or "").strip().lower()
        for membro in listar_membros(session, incluir_inativos=True)
    }

    criados = 0
    for nome in sorted(nomes):
        if nome.lower() in existentes:
            continue
        session.add(EquipaMembro(nome=nome[:120], ativo=True, ordem=0))
        criados += 1

    if criados:
        session.flush()
    return criados


def preencher_emails_de_users(session: Session) -> int:
    """Fill the empty addresses with the email of the matching V3 account.

    Os nomes vindos das obras são quase sempre o primeiro nome ("Elsa"), e as
    contas do V3 têm o nome completo ("Elsa Belo") — daí procurar-se também
    pelo primeiro nome e pelo username. Um primeiro nome que sirva a duas
    contas é deixado em branco de propósito: mandar o ticket à pessoa errada é
    pior do que não o mandar.

    Nunca escreve por cima de um endereço já preenchido à mão.
    """
    indice = _indice_de_contas(session)
    if not indice:
        return 0

    preenchidos = 0
    for membro in listar_membros(session, incluir_inativos=True):
        if (membro.email or "").strip():
            continue
        email = indice.get(normalizar(membro.nome))
        if email:
            membro.email = email[:255]
            preenchidos += 1

    if preenchidos:
        session.flush()
    return preenchidos


def identificar_membro(
    membros,
    *,
    nome: str | None = None,
    username: str | None = None,
    email: str | None = None,
) -> int | None:
    """Which team member is this person? None when there is no safe match.

    Função pura (recebe a lista já lida) para o diálogo poder saber quem está a
    enviar sem voltar à base de dados. O endereço manda, porque é único; o nome
    só serve de recurso, e um primeiro nome que sirva a duas pessoas não conta —
    mais vale não identificar ninguém do que identificar a pessoa errada.
    """
    lista = list(membros or ())

    endereco = (email or "").strip().lower()
    if endereco:
        for membro in lista:
            if (getattr(membro, "email", "") or "").strip().lower() == endereco:
                return int(membro.id)

    procurados = {normalizar(valor) for valor in (nome, username) if valor}
    nome_normalizado = normalizar(nome)
    if nome_normalizado:
        procurados.add(nome_normalizado.split(" ")[0])
    procurados.discard("")
    if not procurados:
        return None

    encontrados = [
        int(membro.id)
        for membro in lista
        if normalizar(getattr(membro, "nome", "")) in procurados
        or normalizar(getattr(membro, "nome", "")).split(" ")[0] in procurados
    ]
    return encontrados[0] if len(encontrados) == 1 else None


def _indice_de_contas(session: Session) -> dict[str, str]:
    """Map name/username to the account email, dropping ambiguous keys."""
    candidatos: dict[str, set[str]] = {}
    for utilizador in session.scalars(select(User)).all():
        email = (utilizador.email or "").strip()
        if not email:
            continue
        for chave in _chaves_da_conta(utilizador):
            if chave:
                candidatos.setdefault(chave, set()).add(email)

    return {
        chave: next(iter(emails))
        for chave, emails in candidatos.items()
        if len(emails) == 1
    }


def _chaves_da_conta(utilizador: User) -> tuple[str, ...]:
    """Ways of naming one account: full name, first name and username."""
    nome = normalizar(utilizador.nome)
    primeiro = nome.split(" ")[0] if nome else ""
    return (nome, primeiro, normalizar(utilizador.username))
