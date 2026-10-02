"""Ler e gravar o registo de horas de cada pessoa.

As regras (contas, feriados, resumos, agenda) estão em
:mod:`app.domain.registo_horas`; aqui fica só o que toca na base de dados.

Quem vê o quê: cada pessoa só lê e grava as suas horas; o administrador lê as
de todos (para consultar e imprimir), mas não as altera — as horas de cada um
são declaradas pelo próprio.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain import registo_horas as regra
from app.models import User, UserPermission
from app.models.registo_horas import RegistoHorasDia, RegistoHorasEnvio
from app.services.system_setting_service import SystemSettingService
from app.services.user_pref_service import UserPrefService

PERMISSAO_MENU = "menu.registo_horas"
CHAVE_CONFIG = "registo_horas.config"
CHAVE_ULTIMO_LEMBRETE = "registo_horas.ultimo_lembrete"
CHAVE_ENVIO_ADIADO = "registo_horas.envio_adiado"
CHAVE_EMAIL_CONTABILIDADE = "registo_horas_email_contabilidade"

ORIGEM_MARTELO = "martelo"
ORIGEM_APP_ANTIGA = "app_antiga"


@dataclass(frozen=True)
class Colaborador:
    """Uma pessoa com folha de horas (para o administrador escolher)."""

    user_id: int
    nome: str
    username: str


@dataclass(frozen=True)
class EnvioMes:
    enviado_em: datetime
    destinatario: str
    normais: int
    extra: int


def linha_de(registo: RegistoHorasDia) -> regra.LinhaDia:
    return regra.LinhaDia(
        data=registo.data,
        tipo=registo.tipo,
        entrada=registo.entrada_min,
        saida=registo.saida_min,
        entrada2=registo.entrada2_min,
        saida2=registo.saida2_min,
        almoco=bool(registo.desconto_almoco),
        jantar=bool(registo.desconto_jantar),
        acerto=int(registo.acerto_min or 0),
        horas=int(registo.horas_min or 0),
        trabalhado=int(registo.trabalhado_min or 0),
        normais=int(registo.normais_min or 0),
        extra=int(registo.extra_min or 0),
        observacoes=registo.observacoes or "",
        origem=registo.origem or ORIGEM_MARTELO,
    )


class RegistoHorasService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ---- dias ------------------------------------------------------------
    def _registo(self, user_id: int, dia: date) -> RegistoHorasDia | None:
        return self.session.execute(
            select(RegistoHorasDia).where(
                RegistoHorasDia.user_id == user_id, RegistoHorasDia.data == dia
            )
        ).scalar_one_or_none()

    def obter_dia(self, user_id: int, dia: date) -> regra.LinhaDia | None:
        registo = self._registo(user_id, dia)
        return linha_de(registo) if registo is not None else None

    def listar_mes(self, user_id: int, ano: int, mes: int) -> list[regra.LinhaDia]:
        dias = regra.dias_do_mes(ano, mes)
        return self.listar_periodo(user_id, dias[0], dias[-1])

    def listar_periodo(self, user_id: int, desde: date, ate: date) -> list[regra.LinhaDia]:
        """Dias registados entre ``desde`` e ``ate`` (os dois incluídos)."""
        registos = self.session.execute(
            select(RegistoHorasDia)
            .where(
                RegistoHorasDia.user_id == user_id,
                RegistoHorasDia.data >= desde,
                RegistoHorasDia.data <= ate,
            )
            .order_by(RegistoHorasDia.data)
        ).scalars()
        return [linha_de(r) for r in registos]

    def guardar_dia(
        self,
        user_id: int,
        dia: date,
        dados: regra.DadosDia,
        *,
        observacoes: str = "",
        config: regra.ConfigHoras | None = None,
    ) -> regra.LinhaDia:
        """Cria ou substitui o dia (um registo por dia); faz as contas aqui."""
        config = config or self.config(user_id)
        observacoes = (observacoes or "").strip()
        if len(observacoes) > 255:
            raise regra.ErroRegistoHoras(
                "Observações demasiado longas (máximo 255 caracteres)."
            )
        calculo = regra.calcular_dia(
            dados, horas_normais=config.horas_normais_dia, pausa=config.pausa_almoco
        )
        util = dados.tipo == regra.TIPO_UTIL
        registo = self._registo(user_id, dia)
        if registo is None:
            registo = RegistoHorasDia(user_id=user_id, data=dia)
            self.session.add(registo)
        registo.tipo = dados.tipo
        registo.entrada_min = dados.entrada % regra.MINUTOS_DIA if util else None
        registo.saida_min = calculo.saida if util else None
        registo.entrada2_min = calculo.entrada2 if util else None
        registo.saida2_min = calculo.saida2 if util else None
        registo.desconto_almoco = bool(util and dados.almoco)
        registo.desconto_jantar = bool(util and dados.jantar)
        registo.acerto_min = dados.acerto if util else 0
        registo.horas_min = 0 if util else dados.horas
        registo.trabalhado_min = calculo.trabalhado
        registo.normais_min = calculo.normais
        registo.extra_min = calculo.extra
        registo.horas_normais_dia_min = config.horas_normais_dia
        registo.observacoes = observacoes
        registo.origem = ORIGEM_MARTELO
        self.session.commit()
        return linha_de(registo)

    def apagar_dia(self, user_id: int, dia: date) -> bool:
        registo = self._registo(user_id, dia)
        if registo is None:
            return False
        self.session.delete(registo)
        self.session.commit()
        return True

    def datas_registadas(self, user_id: int, desde: date, ate: date) -> set[date]:
        return set(
            self.session.execute(
                select(RegistoHorasDia.data).where(
                    RegistoHorasDia.user_id == user_id,
                    RegistoHorasDia.data >= desde,
                    RegistoHorasDia.data <= ate,
                )
            ).scalars()
        )

    def meses_com_registos(self, user_id: int) -> list[tuple[int, int]]:
        datas = self.session.execute(
            select(RegistoHorasDia.data).where(RegistoHorasDia.user_id == user_id)
        ).scalars()
        return sorted({(d.year, d.month) for d in datas})

    def totais_por_mes(self, user_id: int) -> list[tuple[int, int, regra.ResumoMes]]:
        """Resumo de cada mês com registos, do mais antigo para o mais recente."""
        por_mes: dict[tuple[int, int], list[regra.LinhaDia]] = {}
        registos = self.session.execute(
            select(RegistoHorasDia)
            .where(RegistoHorasDia.user_id == user_id)
            .order_by(RegistoHorasDia.data)
        ).scalars()
        for registo in registos:
            por_mes.setdefault((registo.data.year, registo.data.month), []).append(
                linha_de(registo)
            )
        return [
            (ano, mes, regra.resumir_mes(linhas))
            for (ano, mes), linhas in sorted(por_mes.items())
        ]

    def dias_em_falta(self, user_id: int, hoje: date, config: regra.ConfigHoras) -> list[date]:
        """Dias úteis por registar, do início do registo oficial até ontem."""
        desde = max(
            config.inicio_registo,
            date.fromordinal(hoje.toordinal() - regra.JANELA_LEMBRETE_DIAS),
        )
        if desde >= hoje:
            return []
        feitos = self.datas_registadas(user_id, desde, hoje)
        return regra.dias_em_falta(feitos, desde=desde, ate=hoje)

    # ---- histórico importado ---------------------------------------------
    def importar_dias(
        self, user_id: int, dias: Iterable[regra.LinhaDia]
    ) -> tuple[int, list[date]]:
        """Junta dias já calculados (app antiga). Nunca substitui o que já existe.

        Devolve (quantos entraram, datas que já estavam no Martelo).
        """
        existentes = set(
            self.session.execute(
                select(RegistoHorasDia.data).where(RegistoHorasDia.user_id == user_id)
            ).scalars()
        )
        entraram = 0
        ja_existiam: list[date] = []
        for dia in dias:
            if dia.data in existentes:
                ja_existiam.append(dia.data)
                continue
            self.session.add(
                RegistoHorasDia(
                    user_id=user_id,
                    data=dia.data,
                    tipo=dia.tipo,
                    entrada_min=dia.entrada,
                    saida_min=dia.saida,
                    entrada2_min=dia.entrada2,
                    saida2_min=dia.saida2,
                    desconto_almoco=dia.almoco,
                    desconto_jantar=dia.jantar,
                    acerto_min=dia.acerto,
                    horas_min=dia.horas,
                    trabalhado_min=dia.trabalhado,
                    normais_min=dia.normais,
                    extra_min=dia.extra,
                    horas_normais_dia_min=regra.HORAS_NORMAIS_PADRAO,
                    observacoes=(dia.observacoes or "")[:255],
                    origem=ORIGEM_APP_ANTIGA,
                )
            )
            existentes.add(dia.data)
            entraram += 1
        self.session.commit()
        return entraram, ja_existiam

    # ---- definições ------------------------------------------------------
    def config(self, user_id: int) -> regra.ConfigHoras:
        return regra.ConfigHoras.de_json(
            UserPrefService(self.session).obter_valor(user_id, CHAVE_CONFIG)
        )

    def guardar_config(self, user_id: int, config: regra.ConfigHoras) -> None:
        UserPrefService(self.session).guardar_valor(user_id, CHAVE_CONFIG, config.para_json())

    def email_contabilidade(self) -> str:
        valor = SystemSettingService(self.session).obter_valor(CHAVE_EMAIL_CONTABILIDADE)
        return (valor or "").strip() or regra.EMAIL_CONTABILIDADE_PADRAO

    def guardar_email_contabilidade(self, email: str) -> None:
        """Só o administrador escreve nas configurações do sistema."""
        SystemSettingService(self.session).guardar_valor(
            CHAVE_EMAIL_CONTABILIDADE, (email or "").strip()
        )

    def _data_pref(self, user_id: int, chave: str) -> date | None:
        valor = UserPrefService(self.session).obter_valor(user_id, chave)
        try:
            return date.fromisoformat(str(valor)) if valor else None
        except ValueError:
            return None

    def ultimo_lembrete(self, user_id: int) -> date | None:
        return self._data_pref(user_id, CHAVE_ULTIMO_LEMBRETE)

    def marcar_lembrete(self, user_id: int, dia: date) -> None:
        UserPrefService(self.session).guardar_valor(
            user_id, CHAVE_ULTIMO_LEMBRETE, dia.isoformat()
        )

    def envio_adiado(self, user_id: int) -> date | None:
        """Dia em que a pessoa disse «mais tarde» ao envio do mês."""
        return self._data_pref(user_id, CHAVE_ENVIO_ADIADO)

    def adiar_envio(self, user_id: int, dia: date) -> None:
        UserPrefService(self.session).guardar_valor(
            user_id, CHAVE_ENVIO_ADIADO, dia.isoformat()
        )

    # ---- envios à contabilidade ------------------------------------------
    def registar_envio(
        self,
        user_id: int,
        ano: int,
        mes: int,
        *,
        destinatario: str,
        resumo: regra.ResumoMes,
        ficheiro: str = "",
        quando: datetime | None = None,
    ) -> None:
        self.session.add(
            RegistoHorasEnvio(
                user_id=user_id,
                ano=ano,
                mes=mes,
                enviado_em=quando or datetime.now(),
                destinatario=destinatario[:255],
                normais_min=resumo.normais,
                extra_min=resumo.total_extra,
                dias_registados=resumo.dias_registados,
                ficheiro=(ficheiro or "")[:500],
            )
        )
        self.session.commit()

    def ultimo_envio(self, user_id: int, ano: int, mes: int) -> EnvioMes | None:
        envio = self.session.execute(
            select(RegistoHorasEnvio)
            .where(
                RegistoHorasEnvio.user_id == user_id,
                RegistoHorasEnvio.ano == ano,
                RegistoHorasEnvio.mes == mes,
            )
            .order_by(RegistoHorasEnvio.enviado_em.desc(), RegistoHorasEnvio.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        if envio is None:
            return None
        return EnvioMes(
            enviado_em=envio.enviado_em,
            destinatario=envio.destinatario,
            normais=int(envio.normais_min or 0),
            extra=int(envio.extra_min or 0),
        )

    def meses_enviados(self, user_id: int) -> set[tuple[int, int]]:
        return {
            (int(ano), int(mes))
            for ano, mes in self.session.execute(
                select(RegistoHorasEnvio.ano, RegistoHorasEnvio.mes).where(
                    RegistoHorasEnvio.user_id == user_id
                )
            ).all()
        }

    def meses_por_enviar(
        self, user_id: int, agora: datetime, config: regra.ConfigHoras
    ) -> list[tuple[int, int]]:
        return regra.meses_por_enviar(
            agora,
            inicio_registo=config.inicio_registo,
            enviados=self.meses_enviados(user_id),
            com_registos=self.meses_com_registos(user_id),
        )

    # ---- quem tem folha de horas -----------------------------------------
    def colaboradores(self) -> list[Colaborador]:
        """Para o administrador: quem tem o menu ligado ou já tem horas."""
        com_menu = set(
            self.session.execute(
                select(UserPermission.user_id).where(
                    UserPermission.permission_key == PERMISSAO_MENU,
                    UserPermission.enabled.is_(True),
                )
            ).scalars()
        )
        com_horas = set(
            self.session.execute(
                select(RegistoHorasDia.user_id)
                .group_by(RegistoHorasDia.user_id)
                .having(func.count(RegistoHorasDia.id) > 0)
            ).scalars()
        )
        ids = com_menu | com_horas
        if not ids:
            return []
        utilizadores = self.session.execute(
            select(User).where(User.id.in_(ids)).order_by(User.nome)
        ).scalars()
        return [
            Colaborador(user_id=int(u.id), nome=u.nome or u.username, username=u.username)
            for u in utilizadores
        ]
