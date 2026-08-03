"""Passar as unioes nos topos das peças compostas para as peças simples FUNDO.

As unioes (cavilha em prioridade 1, parafuso em prioridade 2) pertencem ao
painel que e' unido — o fundo — e nao ao conjunto ``FUNDO+PES``. Quando o
conjunto entra num custeio, o motor expande tambem os associados da peça filha,
por isso as unioes continuam a aparecer; deixam e' de estar duplicadas em dois
sitios do catalogo.

O que este script faz, so' no grupo FUNDOS:

* garante as duas unioes nos fundos simples (``FUNDO_0000``, ``FUNDO_2000``,
  ``FUNDO_2111``, ``FUNDO_2200``, ``FUNDO_2222``), copiando a configuracao que o
  ``FUNDO_2000`` ja tinha montada a mao;
* **desativa** as unioes nos conjuntos que usam esses fundos, tal como ja estava
  feito a mao no ``FUNDO[2000]+PES``.

Desativar em vez de apagar: a linha fica no ecra, o utilizador ve que ali houve
uma decisao e pode voltar atras sem perder nada. Quem quiser a lista mesmo
limpa usa o botao "Remover Associado" no menu das definições de peças.

O seed e idempotente: correr duas vezes nao muda nada da segunda vez.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.domain.associado_types import DOIS_TOPOS, MEDIDA_TOPO, POR_TOPO  # noqa: E402
from app.domain.componente_types import PECA  # noqa: E402
from app.domain.regra_quantidade_types import FIXA as QUANTIDADE_FIXA  # noqa: E402
from app.models import DefPeca, DefPecaComponente, DefRegraQuantidade  # noqa: E402


CODIGO_PECA_UNIOES = "SISTEMAS_UNIAO"
REGRA_UNIOES = "UNIAO_TOPOS_128"

#: Fundos simples que devem levar as unioes nos dois topos.
FUNDOS_SIMPLES: tuple[str, ...] = (
    "FUNDO_0000",
    "FUNDO_2000",
    "FUNDO_2111",
    "FUNDO_2200",
    "FUNDO_2222",
)

#: As duas unioes, na ordem em que aparecem: descricao e prioridade ValueSet.
UNIOES: tuple[tuple[str, int], ...] = (
    ("Unioes para Modulos Cavilha", 1),
    ("Unioes para Modulos Parafusos", 2),
)


@dataclass(frozen=True)
class MoverUnioesResult:
    """Resumo do que mudou no catalogo."""

    unioes_criadas: int
    fundos_ja_certos: int
    unioes_desativadas: int
    conjuntos_ajustados: int


def get_peca(session: Session, codigo: str) -> DefPeca | None:
    """Devolver uma peca do catalogo pelo codigo."""
    return session.execute(
        select(DefPeca).where(DefPeca.codigo == codigo)
    ).scalar_one_or_none()


def get_regra_unioes_id(session: Session) -> int | None:
    """Devolver o id da regra de quantidade das unioes (None se faltar)."""
    regra = session.execute(
        select(DefRegraQuantidade).where(DefRegraQuantidade.codigo == REGRA_UNIOES)
    ).scalar_one_or_none()
    if regra is None:
        print(f"Aviso: regra {REGRA_UNIOES} nao existe; as unioes ficam sem regra")
        return None
    return regra.id


def componente_uniao(
    *,
    peca_pai_id: int,
    peca_unioes_id: int,
    descricao: str,
    prioridade: int,
    ordem: int,
    regra_id: int | None,
) -> DefPecaComponente:
    """Construir um associado de uniao nos dois topos."""
    return DefPecaComponente(
        def_peca_pai_id=peca_pai_id,
        tipo_componente=PECA,
        def_peca_componente_id=peca_unioes_id,
        descricao=descricao,
        ordem=ordem,
        quantidade=Decimal("1.000"),
        regra_quantidade=QUANTIDADE_FIXA,
        def_regra_quantidade_id=regra_id,
        obrigatorio=True,
        ativo=True,
        zona_aplicacao=DOIS_TOPOS,
        dimensao_referencia=MEDIDA_TOPO,
        numero_topos=2,
        modo_quantidade=POR_TOPO,
        prioridade_valueset=prioridade,
    )


def _associados(session: Session, peca_id: int) -> list[DefPecaComponente]:
    """Todos os associados de uma peca, por ordem."""
    return list(
        session.execute(
            select(DefPecaComponente)
            .where(DefPecaComponente.def_peca_pai_id == peca_id)
            .order_by(DefPecaComponente.ordem)
        ).scalars()
    )


def garantir_unioes_nos_fundos(session: Session) -> tuple[int, int]:
    """Pôr as unioes nos fundos simples. Devolve (criadas, ja certos)."""
    peca_unioes = get_peca(session, CODIGO_PECA_UNIOES)
    if peca_unioes is None:
        print(f"Aviso: peca {CODIGO_PECA_UNIOES} nao existe; nada a fazer nos fundos")
        return 0, 0

    regra_id = get_regra_unioes_id(session)
    criadas = 0
    ja_certos = 0

    for codigo in FUNDOS_SIMPLES:
        fundo = get_peca(session, codigo)
        if fundo is None:
            print(f"Fundo {codigo} nao existe nesta base; ignorado")
            continue

        associados = _associados(session, fundo.id)
        ja_tem = {
            componente.prioridade_valueset
            for componente in associados
            if componente.def_peca_componente_id == peca_unioes.id
        }
        em_falta = [
            (descricao, prioridade)
            for descricao, prioridade in UNIOES
            if prioridade not in ja_tem
        ]
        if not em_falta:
            ja_certos += 1
            print(f"Fundo {codigo} ja tem as unioes, mantido")
            continue

        proxima_ordem = max((componente.ordem for componente in associados), default=0) + 1
        for descricao, prioridade in em_falta:
            session.add(
                componente_uniao(
                    peca_pai_id=fundo.id,
                    peca_unioes_id=peca_unioes.id,
                    descricao=descricao,
                    prioridade=prioridade,
                    ordem=proxima_ordem,
                    regra_id=regra_id,
                )
            )
            proxima_ordem += 1
            criadas += 1
            print(f"Fundo {codigo}: uniao prioridade {prioridade} criada")

    session.flush()
    return criadas, ja_certos


def desativar_unioes_nos_conjuntos(session: Session) -> tuple[int, int]:
    """Desligar as unioes nos conjuntos que usam os fundos.

    Devolve ``(unioes_desativadas, conjuntos_ajustados)``.
    """
    peca_unioes = get_peca(session, CODIGO_PECA_UNIOES)
    if peca_unioes is None:
        return 0, 0

    fundos_ids = {
        fundo.id
        for fundo in (get_peca(session, codigo) for codigo in FUNDOS_SIMPLES)
        if fundo is not None
    }
    if not fundos_ids:
        return 0, 0

    # Quem tem um destes fundos como componente e' um conjunto FUNDO+PES (ou
    # equivalente): as unioes desse conjunto passam a vir do fundo la dentro.
    pais_ids = set(
        session.execute(
            select(DefPecaComponente.def_peca_pai_id).where(
                DefPecaComponente.def_peca_componente_id.in_(fundos_ids)
            )
        ).scalars()
    )

    desativadas = 0
    conjuntos = 0
    for pai_id in sorted(pais_ids):
        pai = session.get(DefPeca, pai_id)
        if pai is None:
            continue

        ativas = [
            componente
            for componente in _associados(session, pai_id)
            if componente.def_peca_componente_id == peca_unioes.id and componente.ativo
        ]
        if not ativas:
            continue

        for componente in ativas:
            componente.ativo = False
            desativadas += 1
        conjuntos += 1
        print(f"Conjunto {pai.codigo}: {len(ativas)} uniao/unioes desativada(s)")

    session.flush()
    return desativadas, conjuntos


def mover_unioes_topos_para_fundos(session: Session) -> MoverUnioesResult:
    """Aplicar as duas mudanças (idempotente)."""
    criadas, ja_certos = garantir_unioes_nos_fundos(session)
    desativadas, conjuntos = desativar_unioes_nos_conjuntos(session)

    session.commit()

    return MoverUnioesResult(
        unioes_criadas=criadas,
        fundos_ja_certos=ja_certos,
        unioes_desativadas=desativadas,
        conjuntos_ajustados=conjuntos,
    )


def print_summary(result: MoverUnioesResult) -> None:
    """Escrever o resumo final para o utilizador."""
    print("Resumo final")
    print(f"Unioes criadas nos fundos simples: {result.unioes_criadas}")
    print(f"Fundos que ja estavam certos: {result.fundos_ja_certos}")
    print(f"Unioes desativadas em conjuntos: {result.unioes_desativadas}")
    print(f"Conjuntos ajustados: {result.conjuntos_ajustados}")


def main() -> int:
    """Correr a mudança na base de dados configurada."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = mover_unioes_topos_para_fundos(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
