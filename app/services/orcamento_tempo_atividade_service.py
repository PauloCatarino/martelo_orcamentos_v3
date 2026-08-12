"""Persistência do tempo ativo dos orçamentos."""

from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import OrcamentoTempoAtividade


class OrcamentoTempoAtividadeService:
    """Accumulate small, periodic time slices without keeping open sessions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def adicionar_segundos(
        self, orcamento_versao_id: int, user_id: int, segundos: int
    ) -> int:
        """Atomically add positive seconds and return the version total."""
        versao_id = int(orcamento_versao_id)
        utilizador_id = int(user_id)
        incremento = int(segundos)
        if versao_id <= 0 or utilizador_id <= 0:
            raise ValueError("Versão e utilizador são obrigatórios.")
        if incremento <= 0:
            return self.total_da_versao(versao_id)

        resultado = self.session.execute(
            update(OrcamentoTempoAtividade)
            .where(
                OrcamentoTempoAtividade.orcamento_versao_id == versao_id,
                OrcamentoTempoAtividade.user_id == utilizador_id,
            )
            .values(
                segundos_ativos=(
                    OrcamentoTempoAtividade.segundos_ativos + incremento
                )
            )
        )
        if not resultado.rowcount:
            self.session.add(
                OrcamentoTempoAtividade(
                    orcamento_versao_id=versao_id,
                    user_id=utilizador_id,
                    segundos_ativos=incremento,
                )
            )
            try:
                self.session.flush()
            except IntegrityError:
                # Dois postos podem iniciar a mesma versão ao mesmo tempo.
                # A restrição única decide; depois somamos na linha vencedora.
                self.session.rollback()
                self.session.execute(
                    update(OrcamentoTempoAtividade)
                    .where(
                        OrcamentoTempoAtividade.orcamento_versao_id == versao_id,
                        OrcamentoTempoAtividade.user_id == utilizador_id,
                    )
                    .values(
                        segundos_ativos=(
                            OrcamentoTempoAtividade.segundos_ativos + incremento
                        )
                    )
                )

        self.session.commit()
        return self.total_da_versao(versao_id)

    def total_da_versao(self, orcamento_versao_id: int) -> int:
        total = self.session.execute(
            select(func.coalesce(func.sum(OrcamentoTempoAtividade.segundos_ativos), 0))
            .where(
                OrcamentoTempoAtividade.orcamento_versao_id
                == int(orcamento_versao_id)
            )
        ).scalar_one()
        return int(total or 0)
