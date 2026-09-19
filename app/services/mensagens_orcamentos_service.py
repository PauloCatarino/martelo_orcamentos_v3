"""Mensagens do Assistente: dá pelas mudanças para Adjudicado/Não Adjudicado.

Não há ganchos espalhados pelos sítios onde o estado muda (lista, Editar
Orçamento, sugestão da encomenda PHC, assistente…): todos deixam o evento
«Estado: A → B» no histórico, e é esse histórico que se lê. Assim a dona do
orçamento recebe a mensagem mesmo quando foi outra pessoa a mudar o estado —
na próxima vez que o Martelo olhar (ao abrir, de 10 em 10 minutos, ou logo a
seguir a recarregar a lista de Orçamentos).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain import mensagens_orcamentos as regra
from app.domain.assistente_orcamentos import estado_alvo
from app.models import User
from app.models.orcamento_versao_evento import OrcamentoVersaoEvento
from app.repositories.orcamento_repository import OrcamentoResumo
from app.services.orcamento_service import OrcamentoService
from app.services.user_pref_service import UserPrefService

CHAVE_ULTIMO_EVENTO = "assistente_orcamentos_ultimo_evento"
CHAVE_ULTIMA_FRASE = "assistente_orcamentos_ultima_frase"
ESTADOS_COM_MENSAGEM = frozenset({regra.ADJUDICADO, regra.NAO_ADJUDICADO})


@dataclass(frozen=True)
class EventoEstado:
    evento_id: int
    versao_id: int
    estado: str
    quando: datetime
    user_id: int | None


def historico_v3(resumos: list[OrcamentoResumo]) -> list[regra.OrcamentoHistorico]:
    return [
        regra.OrcamentoHistorico(
            numero=str(r.num_orcamento),
            versao=int(r.numero_versao or 0),
            cliente=r.cliente_nome or "",
            estado=r.estado or "",
            ano=int(r.ano or 0),
            valor=r.preco_total,
            utilizador=r.utilizador or "",
            origem="V3",
        )
        for r in resumos
    ]


def historico_v2(linhas, numeros_v3: set[str]) -> list[regra.OrcamentoHistorico]:
    """Linhas do Arquivo V2 que o V3 ainda não tem (o V3 manda nos repetidos)."""
    resultado = []
    for linha in linhas:
        numero = str(getattr(linha, "numero", "") or "").strip()
        if not numero or numero in numeros_v3:
            continue
        try:
            versao = int(str(getattr(linha, "versao", "") or "0"))
        except ValueError:
            versao = 0
        try:
            valor = Decimal(str(linha.total)) if linha.total not in (None, "") else None
        except Exception:  # noqa: BLE001 - valor estranho no V2: sem valor
            valor = None
        resultado.append(
            regra.OrcamentoHistorico(
                numero=numero,
                versao=versao,
                cliente=getattr(linha, "cliente", "") or "",
                estado=getattr(linha, "estado", "") or "",
                ano=regra.ano_de(getattr(linha, "data", None)),
                valor=valor,
                utilizador=getattr(linha, "utilizador", "") or "",
                origem="V2",
            )
        )
    return resultado


def ler_historico_v2() -> list:
    """Todas as versões do Arquivo V2 (só leitura). Pode falhar: rede/conta."""
    from app.services.v2_arquivo_service import V2ArquivoService, criar_engine_v2

    engine = criar_engine_v2()
    try:
        return V2ArquivoService(engine).listar_orcamentos(limite=5000)
    finally:
        engine.dispose()


class MensagensOrcamentosService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.prefs = UserPrefService(session)

    # ---- que mudanças há para mim ---------------------------------------
    def eventos_novos(self, user_id: int) -> list[EventoEstado]:
        """Mudanças para (Não) Adjudicado nos MEUS orçamentos ainda não vistas.

        Na primeira vez só marca onde está o histórico: não se despejam as
        adjudicações antigas todas de uma vez.
        """
        ultimo_texto = self.prefs.obter_valor(user_id, CHAVE_ULTIMO_EVENTO)
        maximo = self.session.execute(select(func.max(OrcamentoVersaoEvento.id))).scalar()
        if ultimo_texto is None or not str(ultimo_texto).isdigit():
            self.prefs.guardar_valor(user_id, CHAVE_ULTIMO_EVENTO, str(maximo or 0))
            return []
        ultimo = int(ultimo_texto)
        if not maximo or maximo <= ultimo:
            return []

        from app.models.orcamento_versao import OrcamentoVersao

        linhas = self.session.execute(
            select(
                OrcamentoVersaoEvento.id,
                OrcamentoVersaoEvento.orcamento_versao_id,
                OrcamentoVersaoEvento.descricao,
                OrcamentoVersaoEvento.created_at,
                OrcamentoVersaoEvento.user_id,
                OrcamentoVersao.estado,
                OrcamentoVersao.created_by_id,
            )
            .join(OrcamentoVersao, OrcamentoVersao.id == OrcamentoVersaoEvento.orcamento_versao_id)
            .where(
                OrcamentoVersaoEvento.id > ultimo,
                OrcamentoVersaoEvento.tipo == "estado",
            )
            .order_by(OrcamentoVersaoEvento.id)
        ).all()
        self.prefs.guardar_valor(user_id, CHAVE_ULTIMO_EVENTO, str(maximo))

        eventos: dict[int, EventoEstado] = {}
        for evento_id, versao_id, descricao, quando, quem, estado_atual, dono in linhas:
            alvo = estado_alvo(descricao)
            if alvo not in ESTADOS_COM_MENSAGEM or dono != user_id:
                continue
            if estado_atual != alvo:
                continue  # mudou e voltou atrás entretanto
            # Uma mensagem por versão: vale a última mudança.
            eventos[versao_id] = EventoEstado(evento_id, versao_id, alvo, quando, quem)
        return sorted(eventos.values(), key=lambda e: e.evento_id)

    # ---- compor ----------------------------------------------------------
    def compor(
        self,
        evento: EventoEstado,
        *,
        user_id: int,
        username: str,
        nome: str,
        historico_v2_linhas: list | None = None,
        hoje: date | None = None,
    ) -> regra.Mensagem | None:
        resumos = OrcamentoService(self.session).list_orcamentos()
        resumo = next((r for r in resumos if r.orcamento_versao_id == evento.versao_id), None)
        if resumo is None:
            return None
        historico = historico_v3(resumos)
        if historico_v2_linhas:
            historico += historico_v2(historico_v2_linhas, {h.numero for h in historico})

        ano = (hoje or date.today()).year
        mudado_por = ""
        if evento.user_id and evento.user_id != user_id:
            quem = self.session.get(User, evento.user_id)
            mudado_por = (quem.nome or quem.username) if quem is not None else ""

        orcamento = regra.OrcamentoMudado(
            codigo=resumo.codigo_versao,
            numero=str(resumo.num_orcamento),
            numero_versao=int(resumo.numero_versao or 1),
            cliente=resumo.cliente_nome or "",
            obra=resumo.obra or resumo.descricao or "",
            valor=resumo.preco_total,
            estado=evento.estado,
            dias_decisao=self._dias_decisao(evento),
            mudado_por=mudado_por,
        )
        cliente = regra.resumo_cliente(historico, orcamento.cliente)
        utilizador = regra.resumo_utilizador(
            historico, username, ano, excluir_numero=orcamento.numero
        )
        ultima = self.prefs.obter_valor(user_id, CHAVE_ULTIMA_FRASE) or ""
        mensagem = regra.compor_mensagem(
            orcamento,
            cliente,
            utilizador,
            nome=nome,
            semente=evento.evento_id,
            ultima_frase=ultima,
        )
        self.prefs.guardar_valor(user_id, CHAVE_ULTIMA_FRASE, mensagem.frase)
        return mensagem

    def _dias_decisao(self, evento: EventoEstado) -> int | None:
        envios = self.session.execute(
            select(OrcamentoVersaoEvento.descricao, OrcamentoVersaoEvento.created_at).where(
                OrcamentoVersaoEvento.orcamento_versao_id == evento.versao_id,
                OrcamentoVersaoEvento.tipo == "estado",
                OrcamentoVersaoEvento.id < evento.evento_id,
            )
        ).all()
        datas = [quando for descricao, quando in envios if estado_alvo(descricao) == "Enviado" and quando]
        if not datas or evento.quando is None:
            return None
        return max(0, (evento.quando.date() - max(datas).date()).days)
