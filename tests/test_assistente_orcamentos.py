"""Assistente dos Orçamentos: resumo diário das 8h30 (F2)."""

from __future__ import annotations

import inspect
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from PySide6.QtWidgets import QApplication

from app.domain import assistente_orcamentos as regra
from app.models import User
from app.repositories.orcamento_repository import OrcamentoResumo
from app.services.assistente_orcamentos_service import (
    AssistenteOrcamentosService,
    _versoes,
)

HOJE = date(2026, 10, 19)  # segunda-feira
DONO = 7


def _v(
    orcamento_id: int,
    versao_id: int,
    estado: str,
    *,
    numero: int = 1,
    dono: int = DONO,
    criado: date = date(2026, 9, 1),
    entrou: date | None = None,
    email: date | None = None,
) -> regra.VersaoOrcamento:
    return regra.VersaoOrcamento(
        orcamento_id=orcamento_id,
        versao_id=versao_id,
        numero_versao=numero,
        codigo=f"2608{orcamento_id:02d}_{numero:02d}",
        estado=estado,
        dono_id=dono,
        cliente="MÓVEIS J.F. VIVA",
        obra="COZINHA",
        ref_cliente="",
        preco=Decimal("1000"),
        criado_em=datetime.combine(criado, datetime.min.time()),
        entrou_no_estado=datetime.combine(entrou, datetime.min.time()) if entrou else None,
        ultimo_email=datetime.combine(email, datetime.min.time()) if email else None,
    )


# ---- regra ------------------------------------------------------------------

def test_so_dias_uteis_a_partir_das_8h30_e_uma_vez_por_dia() -> None:
    segunda = datetime(2026, 10, 19, 8, 29)
    assert regra.deve_mostrar(segunda, None) is False
    assert regra.deve_mostrar(segunda.replace(minute=30), None) is True
    assert regra.deve_mostrar(segunda.replace(hour=14), segunda.date()) is False
    assert regra.deve_mostrar(datetime(2026, 10, 18, 10, 0), None) is False  # domingo


def test_enviado_ha_30_dias_sem_resposta_entra_e_29_nao() -> None:
    versoes = [
        _v(1, 11, "Enviado", entrou=HOJE - timedelta(days=30)),
        _v(2, 12, "Enviado", entrou=HOJE - timedelta(days=29)),
    ]
    resumo = regra.levantar_lembretes(versoes, dono_id=DONO, hoje=HOJE)
    assert [(l.versao_id, l.dias) for l in resumo.sem_resposta] == [(11, 30)]
    assert resumo.sem_resposta[0].enviado_em == HOJE - timedelta(days=30)


def test_falta_orcamentar_ha_15_dias() -> None:
    versoes = [
        _v(1, 11, "Falta Orçamentar", criado=HOJE - timedelta(days=15)),
        _v(2, 12, "Falta Orçamentar", criado=HOJE - timedelta(days=14)),
    ]
    resumo = regra.levantar_lembretes(versoes, dono_id=DONO, hoje=HOJE)
    assert [l.versao_id for l in resumo.falta_orcamentar] == [11]
    assert resumo.sem_resposta == ()


def test_so_os_orcamentos_da_propria_pessoa() -> None:
    velho = HOJE - timedelta(days=60)
    versoes = [_v(1, 11, "Enviado", entrou=velho), _v(2, 12, "Enviado", dono=8, entrou=velho)]
    resumo = regra.levantar_lembretes(versoes, dono_id=DONO, hoje=HOJE)
    assert [l.versao_id for l in resumo.sem_resposta] == [11]


def test_versao_antiga_esquecida_nao_conta_se_o_orcamento_ja_teve_resposta() -> None:
    velho = HOJE - timedelta(days=60)
    versoes = [
        _v(1, 11, "Enviado", numero=1, entrou=velho),
        _v(1, 12, "Adjudicado", numero=2, entrou=velho),
        _v(2, 21, "Enviado", numero=1, entrou=velho),
        _v(2, 22, "Enviado", numero=2, entrou=velho),
    ]
    resumo = regra.levantar_lembretes(versoes, dono_id=DONO, hoje=HOJE)
    # O 1 está ganho; do 2 só aparece a versão mais recente.
    assert [l.versao_id for l in resumo.sem_resposta] == [22]


def test_email_de_seguimento_recomeca_a_contagem() -> None:
    versoes = [
        _v(1, 11, "Enviado", entrou=HOJE - timedelta(days=45), email=HOJE - timedelta(days=5))
    ]
    assert regra.levantar_lembretes(versoes, dono_id=DONO, hoje=HOJE).vazio


def test_lembrar_daqui_a_7_dias() -> None:
    versoes = [_v(1, 11, "Enviado", entrou=HOJE - timedelta(days=40))]
    adiados = regra.adiar({}, 11, HOJE)
    assert adiados == {11: HOJE + timedelta(days=7)}
    escondido = regra.levantar_lembretes(versoes, dono_id=DONO, hoje=HOJE, adiados=adiados)
    assert escondido.vazio and escondido.adiados == 1
    volta = regra.levantar_lembretes(
        versoes, dono_id=DONO, hoje=HOJE + timedelta(days=7), adiados=adiados
    )
    assert [l.versao_id for l in volta.sem_resposta] == [11]
    # Guardado e lido das preferências; os que já passaram são deitados fora.
    texto = regra.escrever_adiados(regra.adiar(adiados, 12, HOJE + timedelta(days=8)))
    assert regra.ler_adiados(texto) == {12: HOJE + timedelta(days=15)}
    assert regra.ler_adiados("lixo") == {}


def test_mais_parados_primeiro() -> None:
    versoes = [
        _v(1, 11, "Enviado", entrou=HOJE - timedelta(days=31)),
        _v(2, 12, "Enviado", entrou=HOJE - timedelta(days=50)),
    ]
    resumo = regra.levantar_lembretes(versoes, dono_id=DONO, hoje=HOJE)
    assert [l.dias for l in resumo.sem_resposta] == [50, 31]


def test_estado_de_chegada_dos_eventos() -> None:
    assert regra.estado_alvo("Estado: Falta Orçamentar → Enviado") == "Enviado"
    assert regra.estado_alvo(
        "Estado: Falta Orçamentar → Enviado (email para o cliente)"
    ) == "Enviado"
    assert regra.estado_alvo("Estado: Enviado → Sem Interesse (lista de orçamentos)") == (
        "Sem Interesse"
    )
    assert regra.estado_alvo("Orçamento enviado para x@y.pt") == ""


def test_email_de_seguimento_pergunta_se_ja_analisou() -> None:
    corpo = regra.corpo_email_seguimento(
        cliente="ALMENDRE & FILHOS",
        num_orcamento="260878",
        versao="01",
        obra="BARQUINHA",
        enviado_em=date(2026, 9, 4),
        momento=datetime(2026, 10, 19, 9, 0),
    )
    assert corpo.startswith("<div")
    assert "Bom dia" in corpo
    assert "04-09-2026" in corpo and "260878_01" in corpo
    assert "ALMENDRE &amp; FILHOS" in corpo
    assert "já teve oportunidade" in corpo
    assert "{{assinatura}}" in corpo


# ---- serviço ----------------------------------------------------------------

def _resumo(versao_id: int, estado: str, criado: datetime) -> OrcamentoResumo:
    return OrcamentoResumo(
        orcamento_id=1,
        orcamento_versao_id=versao_id,
        ano=2026,
        num_orcamento="260878",
        numero_versao=1,
        codigo_versao="260878_01",
        cliente_nome="ALMENDRE",
        obra="BARQUINHA",
        descricao=None,
        localizacao=None,
        ref_cliente=None,
        estado=estado,
        preco_total=Decimal("21419.08"),
        created_at=criado,
        utilizador_id=DONO,
    )


def test_servico_le_do_historico_quando_passou_a_enviado() -> None:
    criado = datetime(2026, 9, 1, 10, 0)
    eventos = [
        (5, "estado", "Estado: Falta Orçamentar → Enviado", datetime(2026, 9, 4, 12, 0)),
        (5, "email", "Orçamento enviado para x@y.pt", datetime(2026, 9, 4, 12, 0)),
        (5, "estado", "Estado: Enviado → Falta Orçamentar", datetime(2026, 9, 2)),
    ]
    [versao] = _versoes([_resumo(5, "Enviado", criado)], eventos)
    assert versao.entrou_no_estado == datetime(2026, 9, 4, 12, 0)
    assert versao.ultimo_email == datetime(2026, 9, 4, 12, 0)
    assert versao.obra == "BARQUINHA" and versao.dono_id == DONO


def test_preferencias_ficam_por_utilizador(session) -> None:
    session.add(User(id=DONO, username="elisabete", nome="Elisabete", email="e@x", password_hash="x", role="user"))
    session.commit()
    servico = AssistenteOrcamentosService(session)
    assert servico.ultimo_resumo(DONO) is None
    servico.marcar_resumo(DONO, HOJE)
    assert servico.ultimo_resumo(DONO) == HOJE
    assert servico.adiar(DONO, 31, HOJE) == HOJE + timedelta(days=7)
    assert servico.adiados(DONO) == {31: HOJE + timedelta(days=7)}


# ---- janela -----------------------------------------------------------------

class _Controlador:
    def __init__(self, resumo: regra.ResumoDiario) -> None:
        self._resumo = resumo
        self.chamadas: list[tuple] = []

    def resumo(self):
        return self._resumo

    def adiar(self, versao_id):
        self.chamadas.append(("adiar", versao_id))
        return HOJE + timedelta(days=7)

    def ver_na_lista(self, versao_id):
        self.chamadas.append(("ver", versao_id))
        return True

    def mudar_estado(self, versao_id, estado):
        self.chamadas.append(("estado", versao_id, estado))

    def email_seguimento(self, lembrete):
        self.chamadas.append(("email", lembrete.versao_id))
        return True


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def _lembrete(versao_id: int, tipo: str = regra.TIPO_SEM_RESPOSTA) -> regra.Lembrete:
    return regra.Lembrete(
        tipo, versao_id, f"2608{versao_id}_01", "CLIENTE", "OBRA", "OBRA",
        Decimal("2484.55"), date(2026, 9, 4), 35, date(2026, 9, 4),
    )


def test_janela_mostra_so_o_que_ha_e_limita_as_linhas(qapp) -> None:
    from app.ui.dialogs.assistente_orcamentos_dialog import AssistenteOrcamentosDialog

    resumo = regra.ResumoDiario(
        sem_resposta=tuple(_lembrete(i) for i in range(10)),
    )
    dialogo = AssistenteOrcamentosDialog(_Controlador(resumo), nome="Elisabete Silva", automatico=True)

    assert dialogo.saudacao.text().endswith("Elisabete.")
    assert dialogo.tabela_sem_resposta.rowCount() == regra.MAX_LINHAS
    assert "mais 2" in dialogo.mais_sem_resposta.text()
    assert dialogo.caixa_falta.isHidden()
    assert "10 orçamento(s)" in dialogo.frase.text()
    # Obra e Ref. Cliente iguais não se repetem; valor com milhares.
    assert dialogo.tabela_sem_resposta.item(0, 2).text() == "OBRA"
    assert dialogo.tabela_sem_resposta.item(0, 5).text() == "2.484,55 €"


def test_janela_so_faz_o_que_se_pede(qapp) -> None:
    from app.ui.dialogs.assistente_orcamentos_dialog import AssistenteOrcamentosDialog

    controlador = _Controlador(
        regra.ResumoDiario(
            sem_resposta=(_lembrete(1),),
            falta_orcamentar=(_lembrete(2, regra.TIPO_FALTA_ORCAMENTAR),),
        )
    )
    dialogo = AssistenteOrcamentosDialog(controlador)
    assert controlador.chamadas == []

    dialogo._email()
    dialogo._adiar(regra.TIPO_FALTA_ORCAMENTAR)
    dialogo._ver(regra.TIPO_SEM_RESPOSTA)
    assert controlador.chamadas == [("email", 1), ("adiar", 2), ("ver", 1)]


def test_resumo_vazio_diz_que_esta_tudo_em_dia(qapp) -> None:
    from app.ui.dialogs.assistente_orcamentos_dialog import AssistenteOrcamentosDialog

    dialogo = AssistenteOrcamentosDialog(_Controlador(regra.ResumoDiario()))
    assert "tudo em dia" in dialogo.frase.text()
    assert dialogo.caixa_sem_resposta.isHidden() and dialogo.caixa_falta.isHidden()


def test_so_arranca_com_o_acesso_e_nunca_envia_sozinho() -> None:
    from app.ui import main_window
    from app.ui.helpers import assistente_orcamentos as helper

    fonte = inspect.getsource(main_window.MainWindow.__init__)
    assert "PERMISSAO_ASSISTENTE_ORCAMENTOS" in fonte
    assert "ativar_assistente" in fonte
    envio = inspect.getsource(helper.preparar_email_seguimento)
    assert envio.index("dialogo.exec()") < envio.index("enviar_email(")
    assert '"email"' in envio  # fica no histórico e recomeça os 30 dias
