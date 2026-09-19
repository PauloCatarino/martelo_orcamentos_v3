"""Assistente dos Orçamentos: lê a base e guarda as escolhas de cada pessoa.

A regra (quem entra no resumo, quando, por quanto tempo se adia) vive em
``app/domain/assistente_orcamentos.py``; aqui só se junta a lista de
orçamentos com o histórico de estados e de emails de cada versão.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import assistente_orcamentos as regra
from app.models.orcamento_versao_evento import OrcamentoVersaoEvento
from app.repositories.orcamento_repository import OrcamentoResumo
from app.services.orcamento_service import OrcamentoService
from app.services.user_pref_service import UserPrefService

#: Preferências por utilizador (``user_prefs``), nunca ``system_settings``.
CHAVE_ULTIMO_RESUMO = "assistente_orcamentos_ultimo_resumo"
CHAVE_ADIADOS = "assistente_orcamentos_adiados"


def _versoes(
    resumos: list[OrcamentoResumo],
    eventos: list[tuple[int, str, str, datetime]],
) -> list[regra.VersaoOrcamento]:
    entrou: dict[tuple[int, str], datetime] = {}
    ultimo_email: dict[int, datetime] = {}
    for versao_id, tipo, descricao, quando in eventos:
        if quando is None:
            continue
        if tipo == "email":
            if versao_id not in ultimo_email or quando > ultimo_email[versao_id]:
                ultimo_email[versao_id] = quando
            continue
        alvo = regra.estado_alvo(descricao)
        if not alvo:
            continue
        chave = (versao_id, alvo)
        if chave not in entrou or quando > entrou[chave]:
            entrou[chave] = quando

    return [
        regra.VersaoOrcamento(
            orcamento_id=resumo.orcamento_id,
            versao_id=resumo.orcamento_versao_id,
            numero_versao=int(resumo.numero_versao or 0),
            codigo=resumo.codigo_versao,
            estado=resumo.estado or "",
            dono_id=resumo.utilizador_id,
            cliente=resumo.cliente_nome or "",
            obra=resumo.obra or resumo.descricao or "",
            ref_cliente=resumo.ref_cliente or "",
            preco=resumo.preco_total,
            criado_em=resumo.created_at,
            entrou_no_estado=entrou.get((resumo.orcamento_versao_id, resumo.estado)),
            ultimo_email=ultimo_email.get(resumo.orcamento_versao_id),
        )
        for resumo in resumos
    ]


class AssistenteOrcamentosService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.prefs = UserPrefService(session)

    def carregar_versoes(self) -> list[regra.VersaoOrcamento]:
        resumos = OrcamentoService(self.session).list_orcamentos()
        eventos = [
            (int(linha[0]), str(linha[1]), str(linha[2] or ""), linha[3])
            for linha in self.session.execute(
                select(
                    OrcamentoVersaoEvento.orcamento_versao_id,
                    OrcamentoVersaoEvento.tipo,
                    OrcamentoVersaoEvento.descricao,
                    OrcamentoVersaoEvento.created_at,
                ).where(OrcamentoVersaoEvento.tipo.in_(("estado", "email")))
            ).all()
        ]
        return _versoes(resumos, eventos)

    def resumo(self, user_id: int, hoje: date | None = None) -> regra.ResumoDiario:
        hoje = hoje or date.today()
        return regra.levantar_lembretes(
            self.carregar_versoes(),
            dono_id=int(user_id),
            hoje=hoje,
            adiados=self.adiados(user_id),
        )

    # ---- preferências da pessoa -----------------------------------------
    def adiados(self, user_id: int) -> dict[int, date]:
        return regra.ler_adiados(self.prefs.obter_valor(user_id, CHAVE_ADIADOS))

    def adiar(self, user_id: int, versao_id: int, hoje: date | None = None) -> date:
        novos = regra.adiar(self.adiados(user_id), versao_id, hoje or date.today())
        self.prefs.guardar_valor(user_id, CHAVE_ADIADOS, regra.escrever_adiados(novos))
        return novos[int(versao_id)]

    def ultimo_resumo(self, user_id: int) -> date | None:
        valor = self.prefs.obter_valor(user_id, CHAVE_ULTIMO_RESUMO)
        try:
            return date.fromisoformat(str(valor)) if valor else None
        except ValueError:
            return None

    def marcar_resumo(self, user_id: int, dia: date) -> None:
        self.prefs.guardar_valor(user_id, CHAVE_ULTIMO_RESUMO, dia.isoformat())
