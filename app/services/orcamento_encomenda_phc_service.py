"""Service for the PHC orders of a budget version (phase 5).

A budget version may have several PHC order numbers. Exactly one of them is
the principal order, mirrored into ``orcamento_versoes.enc_phc`` so existing
listings, reports and conversions keep working unchanged.

Versions created before the migration may still only have the legacy
``enc_phc`` value; reading falls back to it as a synthetic principal order.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.orcamento_versao import OrcamentoVersao
from app.models.orcamento_versao_encomenda_phc import OrcamentoVersaoEncomendaPhc


@dataclass(frozen=True)
class EncomendaPhcResumo:
    """Read model of one PHC order of a budget version."""

    numero: str
    is_principal: bool
    id: int | None = None


@dataclass(frozen=True)
class EncomendaPhcInput:
    """Input data for replacing the PHC orders of a budget version."""

    numero: str
    is_principal: bool = False


def normalizar_encomendas(
    encomendas: list[EncomendaPhcInput] | tuple[EncomendaPhcInput, ...],
) -> list[EncomendaPhcInput]:
    """Validate and normalize a set of PHC orders.

    Blank numbers are rejected, duplicated numbers (case-insensitive) are
    rejected and exactly one order ends up principal — when none is marked,
    the first one is promoted.
    """
    normalizadas: list[EncomendaPhcInput] = []
    vistos: set[str] = set()
    principais = 0

    for encomenda in encomendas:
        numero = (encomenda.numero or "").strip()
        if not numero:
            raise ValueError("O número da encomenda PHC não pode ficar vazio.")
        chave = numero.casefold()
        if chave in vistos:
            raise ValueError(
                f"A encomenda PHC '{numero}' está repetida nesta versão."
            )
        vistos.add(chave)
        if encomenda.is_principal:
            principais += 1
        normalizadas.append(
            EncomendaPhcInput(numero=numero, is_principal=encomenda.is_principal)
        )

    if principais > 1:
        raise ValueError("Só uma encomenda PHC pode ser a principal.")
    if normalizadas and principais == 0:
        normalizadas[0] = EncomendaPhcInput(
            numero=normalizadas[0].numero, is_principal=True
        )

    return normalizadas


class OrcamentoEncomendaPhcService:
    """Application service for the PHC orders of a budget version."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def listar_encomendas(
        self, orcamento_versao_id: int
    ) -> list[EncomendaPhcResumo]:
        """List the PHC orders of a version, principal first.

        Falls back to the legacy ``enc_phc`` value (as a synthetic principal
        order) for versions saved before the child table existed.
        """
        registos = self.session.execute(
            select(OrcamentoVersaoEncomendaPhc)
            .where(
                OrcamentoVersaoEncomendaPhc.orcamento_versao_id
                == orcamento_versao_id
            )
            .order_by(
                OrcamentoVersaoEncomendaPhc.is_principal.desc(),
                OrcamentoVersaoEncomendaPhc.id.asc(),
            )
        ).scalars().all()

        if registos:
            return [
                EncomendaPhcResumo(
                    numero=registo.numero,
                    is_principal=registo.is_principal,
                    id=registo.id,
                )
                for registo in registos
            ]

        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return []
        legado = (versao.enc_phc or "").strip()
        if not legado:
            return []
        return [EncomendaPhcResumo(numero=legado, is_principal=True)]

    def get_principal(self, orcamento_versao_id: int) -> str | None:
        """Return the principal PHC order number of a version (or None)."""
        for encomenda in self.listar_encomendas(orcamento_versao_id):
            if encomenda.is_principal:
                return encomenda.numero
        return None

    def substituir_encomendas(
        self,
        orcamento_versao_id: int,
        encomendas: list[EncomendaPhcInput] | tuple[EncomendaPhcInput, ...],
    ) -> list[EncomendaPhcResumo]:
        """Replace the full set of PHC orders of a version.

        Also mirrors the principal number into ``orcamento_versoes.enc_phc``
        for compatibility. Flushes without committing (caller commits).
        """
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            raise ValueError("Versão de orçamento não encontrada.")

        normalizadas = normalizar_encomendas(encomendas)

        existentes = self.session.execute(
            select(OrcamentoVersaoEncomendaPhc).where(
                OrcamentoVersaoEncomendaPhc.orcamento_versao_id
                == orcamento_versao_id
            )
        ).scalars().all()
        for registo in existentes:
            self.session.delete(registo)
        self.session.flush()

        principal: str | None = None
        for encomenda in normalizadas:
            self.session.add(
                OrcamentoVersaoEncomendaPhc(
                    orcamento_versao_id=orcamento_versao_id,
                    numero=encomenda.numero,
                    is_principal=encomenda.is_principal,
                )
            )
            if encomenda.is_principal:
                principal = encomenda.numero

        versao.enc_phc = principal
        self.session.flush()

        return self.listar_encomendas(orcamento_versao_id)

    def definir_principal(
        self, orcamento_versao_id: int, numero: str
    ) -> list[EncomendaPhcResumo]:
        """Mark one existing order as principal and mirror it into enc_phc."""
        atuais = self.listar_encomendas(orcamento_versao_id)
        alvo = (numero or "").strip().casefold()
        if alvo not in {enc.numero.casefold() for enc in atuais}:
            raise ValueError(
                f"A encomenda PHC '{numero}' não existe nesta versão."
            )
        return self.substituir_encomendas(
            orcamento_versao_id,
            [
                EncomendaPhcInput(
                    numero=enc.numero,
                    is_principal=enc.numero.casefold() == alvo,
                )
                for enc in atuais
            ],
        )
