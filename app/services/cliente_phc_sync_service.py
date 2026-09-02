"""Service that syncs PHC customers into the Martelo DB (phase 10.5.1)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.clientes_phc import DadosClientePHC, normalizar_linha_phc
from app.repositories.cliente_repository import ClienteRepository, DiferencasPHC
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

    def verificar_alteracoes(self) -> DiferencasPHC:
        """Espreitar o PHC e dizer o que mudou, SEM gravar nada no Martelo.

        É o que alimenta o aviso diário: só vale a pena interromper o
        utilizador quando há mesmo clientes novos ou editados no PHC.
        """
        dados, _ignorados, _total = self._ler_phc()
        return self.repository.diferencas_phc(dados)

    def sincronizar(self) -> ResumoSincronizacaoPHC:
        dados, ignorados, total = self._ler_phc()

        criados, atualizados = self.repository.sincronizar_phc(dados)
        self.session.commit()

        return ResumoSincronizacaoPHC(
            total_phc=total,
            criados=criados,
            atualizados=atualizados,
            ignorados=ignorados,
        )

    def _ler_phc(self) -> tuple[list[DadosClientePHC], int, int]:
        """Ler o dbo.CL e normalizar: (dados, ignorados, total de linhas)."""
        linhas = phc_sql.query_phc_clients(self.session)

        dados: list[DadosClientePHC] = []
        ignorados = 0
        for linha in linhas:
            normalizada = (
                normalizar_linha_phc(linha) if isinstance(linha, dict) else None
            )
            if normalizada is None:
                ignorados += 1
            else:
                dados.append(normalizada)

        return dados, ignorados, len(linhas)
