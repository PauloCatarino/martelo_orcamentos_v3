"""Service that syncs PHC customers into the Martelo DB (phase 10.5.1)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.clientes_phc import normalizar_linha_phc
from app.repositories.cliente_repository import ClienteRepository
from app.services import phc_sql


@dataclass(frozen=True)
class ResumoSincronizacaoPHC:
    """Summary of one PHC sync run."""

    total_phc: int
    criados: int
    atualizados: int
    ignorados: int


class ClientePhcSyncService:
    """Read PHC dbo.CL (read-only) and upsert into Martelo customers."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ClienteRepository(session)

    def sincronizar(self) -> ResumoSincronizacaoPHC:
        linhas = phc_sql.query_phc_clients(self.session)

        dados = []
        ignorados = 0
        for linha in linhas:
            normalizada = (
                normalizar_linha_phc(linha) if isinstance(linha, dict) else None
            )
            if normalizada is None:
                ignorados += 1
            else:
                dados.append(normalizada)

        criados, atualizados = self.repository.sincronizar_phc(dados)
        self.session.commit()

        return ResumoSincronizacaoPHC(
            total_phc=len(linhas),
            criados=criados,
            atualizados=atualizados,
            ignorados=ignorados,
        )
