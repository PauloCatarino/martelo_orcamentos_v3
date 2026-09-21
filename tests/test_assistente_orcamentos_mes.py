"""Mais destaques nas mensagens e «O seu trabalho» (resumo mensal)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from PySide6.QtWidgets import QApplication

from app.domain import mensagens_orcamentos as regra
from app.models import Cliente, Orcamento, User
from app.models.orcamento_versao import OrcamentoVersao
from app.models.orcamento_versao_evento import OrcamentoVersaoEvento
from app.services.mensagens_orcamentos_service import MensagensOrcamentosService


def _h(numero, estado, *, cliente="VIVA", versao=1, ano=2026, mes=9, valor="1000", user="catia"):
    return regra.OrcamentoHistorico(
        numero, versao, cliente, estado, ano, Decimal(valor), user, mes=mes
    )


def _mudado(**extra):
    base = dict(
        codigo="260910_01",
        numero="260910",
        numero_versao=1,
        cliente="VIVA",
        obra="COZINHA",
        valor=Decimal("500"),
        estado=regra.ADJUDICADO,
    )
    base.update(extra)
    return regra.OrcamentoMudado(**base)


def _utilizador(**extra):
    base = dict(ano=2026, adjudicados=5, valor_adjudicado=Decimal("20000"),
                maior_outro=Decimal("9000"), adjudicados_mes=0, mes=9)
    base.update(extra)
    return regra.ResumoUtilizador(**base)


def _cliente(**extra):
    base = dict(cliente="VIVA", por_estado={}, total=8, adjudicados=4,
                valor_adjudicado=Decimal("30000"), primeiro_ano=2025,
                ultimo_ano_ganho=2026)
    base.update(extra)
    return regra.ResumoCliente(**base)


def _primeiro(orcamento, cliente, utilizador) -> str:
    return regra.destaques_adjudicado(orcamento, cliente, utilizador)[0][0]


# ---- destaques novos --------------------------------------------------------

def test_marco_de_contagem_ganha_a_tudo() -> None:
    destaque = _primeiro(_mudado(), _cliente(), _utilizador(adjudicados=100))
    assert destaque == "É o seu 100.º orçamento adjudicado de 2026. Que número!"


def test_marco_de_valor_do_ano() -> None:
    utilizador = _utilizador(adjudicados=30, valor_adjudicado=Decimal("103000"))
    destaque = _primeiro(_mudado(valor=Decimal("5000")), _cliente(), utilizador)
    assert "passou os 100.000,00 € adjudicados em 2026" in destaque
    # Sem cruzar nenhum marco, não se inventa festa.
    utilizador = _utilizador(adjudicados=30, valor_adjudicado=Decimal("99000"))
    assert "passou os" not in _primeiro(_mudado(valor=Decimal("5000")), _cliente(), utilizador)


def test_cliente_que_nao_fechava_desde_o_ano_passado() -> None:
    cliente = _cliente(ultimo_ano_ganho=2025)
    assert "não fechava nada connosco desde 2025" in _primeiro(_mudado(), cliente, _utilizador())


def test_obra_grande_e_orcamento_antigo_que_voltou() -> None:
    grande = _primeiro(_mudado(valor=Decimal("24254.60")), _cliente(), _utilizador(maior_outro=Decimal("99999")))
    assert "24.254,60 €" in grande and "obra grande" in grande.casefold()

    antigo = _primeiro(
        _mudado(valor=Decimal("100"), dias_decisao=60), _cliente(), _utilizador()
    )
    assert "60 dias" in antigo and "voltar" in antigo


def test_contagem_do_mes_vem_do_historico_de_estados() -> None:
    destaque = _primeiro(
        _mudado(valor=Decimal("100")), _cliente(), _utilizador(adjudicados_mes=6)
    )
    assert destaque == "É o seu 6.º orçamento adjudicado em setembro."
    primeiro_do_mes = _primeiro(
        _mudado(valor=Decimal("100")), _cliente(), _utilizador(adjudicados_mes=1)
    )
    assert "primeiro adjudicado de setembro" in primeiro_do_mes


def test_as_mensagens_repetem_se_pouco() -> None:
    cliente, utilizador = _cliente(), _utilizador()
    mensagens = {
        (m.frase, m.destaque)
        for m in (
            regra.compor_mensagem(
                _mudado(valor=Decimal("100")), cliente, utilizador, nome="Catia", semente=s
            )
            for s in range(30)
        )
    }
    # 22 aberturas x 2 maneiras de dizer o destaque.
    assert len(mensagens) >= 20
    assert len(regra.ABERTURAS_ADJUDICADO) >= 20
    assert len(regra.ABERTURAS_NAO_ADJUDICADO) >= 10


def test_o_facto_escolhido_e_sempre_o_mais_marcante() -> None:
    # Varia-se a MANEIRA de dizer, nunca se troca por um facto banal.
    cliente, utilizador = _cliente(adjudicados=0, total=1), _utilizador(adjudicados_mes=4)
    destaques = {
        regra.compor_mensagem(
            _mudado(dias_decisao=2), cliente, utilizador, nome="Catia", semente=s
        ).destaque
        for s in range(20)
    }
    assert destaques
    assert all("cliente VIVA" in d for d in destaques)


# ---- «O seu trabalho» -------------------------------------------------------

def _historico_ano() -> list[regra.OrcamentoHistorico]:
    return [
        _h("1", "Adjudicado", mes=8, valor="1000"),
        _h("2", "Enviado", mes=8),
        _h("3", "Adjudicado", mes=9, valor="2500"),
        _h("4", "Enviado", mes=9),
        _h("5", "Enviado", mes=9),
        _h("6", "Adjudicado", mes=9, valor="500", user="outra"),  # de outra pessoa
    ]


def test_resumo_mensal_conta_so_os_meus_e_por_mes_de_criacao() -> None:
    resumo = regra.resumo_mensal(_historico_ano(), "catia", ano=2026, mes=9, adjudicados_no_mes=4)

    assert (resumo.criados, resumo.ganhos) == (3, 1)
    assert resumo.valor_ganho == Decimal("2500")
    assert resumo.criados_no_ano == 5 and resumo.ganhos_no_ano == 2
    assert resumo.valor_ganho_no_ano == Decimal("3500")
    assert [m.rotulo for m in resumo.meses] == [
        "abr/26", "mai/26", "jun/26", "jul/26", "ago/26", "set/26"
    ]
    assert (resumo.mes_anterior.criados, resumo.mes_anterior.ganhos) == (2, 1)
    assert resumo.adjudicados_no_mes == 4


def test_frases_do_mes_comparam_com_o_mes_anterior() -> None:
    frases = regra.frases_do_mes(
        regra.resumo_mensal(_historico_ano(), "catia", ano=2026, mes=9, adjudicados_no_mes=4)
    )
    texto = "\n".join(frases)
    assert "Em setembro criou 3 orçamento(s)" in texto
    assert "1 desses já foram adjudicados (2.500,00 €)" in texto
    assert "Fechou 4 orçamento(s) em setembro" in texto
    assert "São mais 1 do que em agosto (2)." in texto
    assert "No total de 2026: 5 orçamentos criados, 2 ganhos (3.500,00 €)." in texto


def test_janeiro_vai_buscar_os_meses_do_ano_anterior() -> None:
    resumo = regra.resumo_mensal([], "catia", ano=2027, mes=1)
    assert [m.rotulo for m in resumo.meses] == [
        "ago/26", "set/26", "out/26", "nov/26", "dez/26", "jan/27"
    ]
    assert resumo.vazio is True


def test_mes_do_arquivo_v2() -> None:
    assert regra.mes_de("2026-08-21") == 8
    assert regra.mes_de(date(2026, 3, 4)) == 3
    assert regra.mes_de(None) == 0


@pytest.fixture
def base(session):
    session.add_all(
        [
            User(id=1, username="catia", nome="Catia", email="c@x", password_hash="x", role="user"),
            Cliente(id=1, nome="VIVA"),
        ]
    )
    session.flush()
    session.add(Orcamento(id=1, ano=2026, num_orcamento="260910", cliente_id=1))
    session.flush()
    session.add_all(
        [
            OrcamentoVersao(id=10, orcamento_id=1, numero_versao=1, codigo_versao="260910_01",
                            estado="Adjudicado", created_by_id=1),
            OrcamentoVersaoEvento(id=1, orcamento_versao_id=10, tipo="estado",
                                  descricao="Estado: Enviado → Adjudicado",
                                  created_at=datetime(2026, 9, 12)),
            OrcamentoVersaoEvento(id=2, orcamento_versao_id=10, tipo="estado",
                                  descricao="Estado: Enviado → Adjudicado",
                                  created_at=datetime(2026, 8, 30)),
            OrcamentoVersaoEvento(id=3, orcamento_versao_id=10, tipo="email",
                                  descricao="Orçamento enviado", created_at=datetime(2026, 9, 12)),
        ]
    )
    session.commit()
    return session


def test_adjudicados_no_mes_conta_versoes_e_so_as_minhas(base) -> None:
    servico = MensagensOrcamentosService(base)
    assert servico.adjudicados_no_mes(1, date(2026, 9, 21)) == 1  # uma versão, um evento
    assert servico.adjudicados_no_mes(1, date(2026, 8, 15)) == 1
    assert servico.adjudicados_no_mes(1, date(2026, 7, 15)) == 0
    assert servico.adjudicados_no_mes(2, date(2026, 9, 21)) == 0


def test_caixa_do_mes_aparece_no_assistente() -> None:
    QApplication.instance() or QApplication([])
    from app.ui.dialogs.assistente_orcamentos_dialog import AssistenteOrcamentosDialog
    from app.domain import assistente_orcamentos as diario

    mensal = regra.resumo_mensal(_historico_ano(), "catia", ano=2026, mes=9, adjudicados_no_mes=4)

    class _Controlador:
        def resumo(self):
            return diario.ResumoDiario()

        def resumo_mensal(self):
            return mensal

        def adiar(self, versao_id):
            return None

        def ver_na_lista(self, versao_id):
            return True

        def mudar_estado(self, versao_id, estado):
            pass

        def email_seguimento(self, lembrete):
            return True

    dialogo = AssistenteOrcamentosDialog(_Controlador(), nome="Catia")
    assert dialogo.caixa_mes.isVisible() or not dialogo.caixa_mes.isHidden()
    assert "Em setembro criou 3 orçamento(s)" in dialogo.frases_mes.text()
    assert len(dialogo.grafico_meses.meses) == 6
    dialogo.grafico_meses.resize(600, 150)
    assert not dialogo.grafico_meses.grab().isNull()


def test_sem_historico_a_caixa_do_mes_fica_escondida() -> None:
    QApplication.instance() or QApplication([])
    from app.ui.dialogs.assistente_orcamentos_dialog import AssistenteOrcamentosDialog
    from app.domain import assistente_orcamentos as diario

    class _SemMes:
        def resumo(self):
            return diario.ResumoDiario()

        def resumo_mensal(self):
            return None

        def adiar(self, versao_id):
            return None

        def ver_na_lista(self, versao_id):
            return True

        def mudar_estado(self, versao_id, estado):
            pass

        def email_seguimento(self, lembrete):
            return True

    dialogo = AssistenteOrcamentosDialog(_SemMes(), nome="Catia")
    assert dialogo.caixa_mes.isHidden()
