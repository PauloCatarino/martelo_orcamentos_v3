"""A equipa: quem pode ficar responsável por um ticket e onde o receber.

Não são as contas do V3 — quem monta, corta ou prepara não entra no programa,
mas tem de receber o ticket no chat. O ``email`` é o endereço do Microsoft
Teams; sem ele, o ticket só se copia para a área de transferência.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.equipa_membro import EquipaMembro
from app.models.producao import Producao


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
