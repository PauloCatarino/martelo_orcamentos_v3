"""Assistente dos Orçamentos (F3): mensagens de Adjudicado / Não Adjudicado."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from app.domain import mensagens_orcamentos as regra
from app.models import Cliente, Orcamento, User
from app.models.orcamento_versao import OrcamentoVersao
from app.models.orcamento_versao_evento import OrcamentoVersaoEvento
from app.services.mensagens_orcamentos_service import (
    CHAVE_ULTIMO_EVENTO,
    MensagensOrcamentosService,
    historico_v2,
)


def _h(numero, estado, *, cliente="VIVA", versao=1, ano=2026, valor="1000", user="catia"):
    return regra.OrcamentoHistorico(
        numero, versao, cliente, estado, ano, Decimal(valor), user
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


# ---- regra ------------------------------------------------------------------

def test_estados_do_v2_sem_acentos_contam_como_os_do_v3() -> None:
    assert regra.estado_canonico("Nao Adjudicado") == "Não Adjudicado"
    assert regra.estado_canonico("Falta Orcamentar") == "Falta Orçamentar"
    assert regra.mesmo_nome("MÓVEIS J.F. VIVA", "moveis  j.f. viva")


def test_cada_orcamento_conta_uma_vez_e_ganho_se_alguma_versao_ganhou() -> None:
    historico = [
        _h("1", "Enviado", versao=1),
        _h("1", "Adjudicado", versao=2, valor="700"),
        _h("2", "Enviado"),
        _h("3", "Nao Adjudicado"),
        _h("4", "Adjudicado", cliente="OUTRO"),
    ]
    resumo = regra.resumo_cliente(historico, "viva")
    assert resumo.total == 3
    assert resumo.adjudicados == 1
    assert resumo.valor_adjudicado == Decimal("700")
    assert resumo.por_estado == {"Adjudicado": 1, "Enviado": 1, "Não Adjudicado": 1}


def test_destaque_primeiro_trabalho_com_o_cliente() -> None:
    cliente = regra.resumo_cliente([_h("260910", "Adjudicado")], "VIVA")
    utilizador = regra.resumo_utilizador([_h("260910", "Adjudicado")], "catia", 2026)
    assert "primeiro trabalho ganho" in regra.destaque_adjudicado(_mudado(), cliente, utilizador)


def test_destaque_maior_do_ano_versao_e_decisao_rapida() -> None:
    historico = [
        _h("1", "Adjudicado", valor="800"),
        _h("2", "Adjudicado", valor="900"),
        _h("260910", "Adjudicado", valor="5000"),
    ]
    cliente = regra.resumo_cliente(historico, "VIVA")
    utilizador = regra.resumo_utilizador(historico, "catia", 2026, excluir_numero="260910")
    maior = regra.destaque_adjudicado(_mudado(valor=Decimal("5000")), cliente, utilizador)
    assert "maior orçamento adjudicado de 2026" in maior and "5.000,00 €" in maior

    versao = regra.destaque_adjudicado(_mudado(numero_versao=3), cliente, utilizador)
    assert "3.º versão" in versao

    rapido = regra.destaque_adjudicado(_mudado(dias_decisao=2), cliente, utilizador)
    assert "2 dias" in rapido

    normal = regra.destaque_adjudicado(_mudado(), cliente, utilizador)
    assert normal == "É o seu 3.º orçamento adjudicado em 2026."


def test_frase_varia_e_nao_repete_a_ultima() -> None:
    frases = {
        regra._escolher(regra.ABERTURAS_ADJUDICADO, semente) for semente in range(40)
    }
    assert len(frases) >= 5
    ultima = regra._escolher(regra.ABERTURAS_ADJUDICADO, 7)
    assert regra._escolher(regra.ABERTURAS_ADJUDICADO, 7, ultima) != ultima


def test_nao_adjudicado_e_sempre_positivo() -> None:
    # Decisão do Paulo: nada de «repensar se vale a pena este cliente».
    proibidas = ("repensar", "vale a pena", "desist", "culpa", "falhou")
    for frase in regra.ABERTURAS_NAO_ADJUDICADO:
        assert not any(p in frase.casefold() for p in proibidas), frase
    historico = [_h("1", "Nao Adjudicado"), _h("2", "Adjudicado", cliente="X")]
    mensagem = regra.compor_mensagem(
        _mudado(estado=regra.NAO_ADJUDICADO, numero="1"),
        regra.resumo_cliente(historico, "VIVA"),
        regra.resumo_utilizador(historico, "catia", 2026),
        nome="Catia Santos",
        semente=3,
    )
    assert mensagem.titulo == "Desta vez não foi, Catia."
    assert "já ganhou 1 orçamento" in mensagem.destaque
    texto = " ".join((mensagem.frase, mensagem.destaque, *mensagem.factos)).casefold()
    assert not any(p in texto for p in proibidas)


def test_mensagem_de_adjudicado_tem_os_factos_e_o_grafico() -> None:
    historico = [_h("1", "Adjudicado"), _h("260910", "Adjudicado", valor="500")]
    mensagem = regra.compor_mensagem(
        _mudado(obra="3 ROUPEIROS\nPORTAS DE CORRER", mudado_por="Paulo Catarino"),
        regra.resumo_cliente(historico, "VIVA"),
        regra.resumo_utilizador(historico, "catia", 2026),
        nome="Catia",
        semente=1,
    )
    assert mensagem.titulo == "🎉 Parabéns, Catia!"
    assert mensagem.frase in regra.ABERTURAS_ADJUDICADO
    assert "3 ROUPEIROS PORTAS DE CORRER" in mensagem.factos[0]  # sem quebras de linha
    assert "estado mudado por Paulo Catarino" in mensagem.factos[0]
    assert mensagem.grafico == {"Adjudicado": 2}


def test_v2_so_acrescenta_os_numeros_que_o_v3_nao_tem() -> None:
    linhas = [
        SimpleNamespace(numero="260001", versao="01", cliente="VIVA", estado="Adjudicado",
                        data="2026-01-05", total=Decimal("10"), utilizador="Catia"),
        SimpleNamespace(numero="260910", versao="01", cliente="VIVA", estado="Enviado",
                        data="2026-09-01", total=None, utilizador="Catia"),
    ]
    resultado = historico_v2(linhas, {"260910"})
    assert [(h.numero, h.ano, h.origem) for h in resultado] == [("260001", 2026, "V2")]


# ---- serviço: só as mudanças dos MEUS orçamentos, uma vez ---------------------

@pytest.fixture
def base(session):
    session.add_all(
        [
            User(id=1, username="catia", nome="Catia", email="c@x", password_hash="x", role="user"),
            User(id=2, username="paulo", nome="Paulo Catarino", email="p@x", password_hash="x", role="user"),
            Cliente(id=1, nome="VIVA"),
        ]
    )
    session.flush()
    session.add(Orcamento(id=1, ano=2026, num_orcamento="260910", cliente_id=1))
    session.flush()
    session.add_all(
        [
            OrcamentoVersao(id=10, orcamento_id=1, numero_versao=1, codigo_versao="260910_01",
                            estado="Enviado", created_by_id=1),
            OrcamentoVersaoEvento(id=1, orcamento_versao_id=10, tipo="estado",
                                  descricao="Estado: Falta Orçamentar → Enviado",
                                  created_at=datetime(2026, 9, 10)),
        ]
    )
    session.commit()
    return session


def _mudar(session, estado: str, evento_id: int, quem: int = 2) -> None:
    versao = session.get(OrcamentoVersao, 10)
    anterior = versao.estado
    versao.estado = estado
    session.add(
        OrcamentoVersaoEvento(id=evento_id, orcamento_versao_id=10, tipo="estado",
                              descricao=f"Estado: {anterior} → {estado}", user_id=quem,
                              created_at=datetime(2026, 9, 12))
    )
    session.commit()


def test_primeira_vez_so_marca_e_depois_da_a_mensagem_so_a_dona(base) -> None:
    servico = MensagensOrcamentosService(base)
    assert servico.eventos_novos(1) == []  # primeira vez: marca onde está
    assert servico.prefs.obter_valor(1, CHAVE_ULTIMO_EVENTO) == "1"
    assert servico.eventos_novos(2) == []

    _mudar(base, "Adjudicado", 2, quem=2)  # o Paulo adjudicou o orçamento da Catia

    [evento] = servico.eventos_novos(1)
    assert (evento.versao_id, evento.estado, evento.user_id) == (10, "Adjudicado", 2)
    assert servico.eventos_novos(1) == []  # já vista
    assert servico.eventos_novos(2) == []  # o Paulo não é o dono

    mensagem = servico.compor(evento, user_id=1, username="catia", nome="Catia")
    assert mensagem.titulo == "🎉 Parabéns, Catia!"
    assert "estado mudado por Paulo Catarino" in mensagem.factos[0]
    assert "primeiro trabalho ganho" in mensagem.destaque
    assert "2 dias" not in mensagem.destaque  # o 1.º trabalho ganha à rapidez


def test_mudanca_desfeita_entretanto_nao_da_mensagem(base) -> None:
    servico = MensagensOrcamentosService(base)
    servico.eventos_novos(1)
    _mudar(base, "Não Adjudicado", 2)
    _mudar(base, "Enviado", 3)
    assert servico.eventos_novos(1) == []


# ---- janela -----------------------------------------------------------------

def test_janela_da_mensagem_com_grafico(qapp=None) -> None:
    QApplication.instance() or QApplication([])
    from app.ui.dialogs.mensagem_orcamento_dialog import MensagemOrcamentoDialog

    mensagem = regra.Mensagem(
        estado=regra.ADJUDICADO,
        titulo="🎉 Parabéns, Catia!",
        frase=regra.ABERTURAS_ADJUDICADO[0],
        destaque="É o primeiro trabalho ganho com o cliente VIVA.",
        factos=("Orçamento 260910_01 · VIVA",),
        grafico={"Adjudicado": 3, "Enviado": 5},
        cliente="VIVA",
    )
    dialogo = MensagemOrcamentoDialog(mensagem)
    assert dialogo.grafico is not None
    assert dialogo.grafico.contagem == {"Adjudicado": 3, "Enviado": 5}
    dialogo.grafico.resize(500, 80)
    assert not dialogo.grafico.grab().isNull()


def test_mensagem_aparece_logo_depois_de_a_lista_recarregar() -> None:
    import inspect

    from app.ui.helpers import assistente_orcamentos as helper
    from app.ui.pages import orcamentos_page

    assert hasattr(orcamentos_page.OrcamentosPage, "orcamentos_recarregados")
    assert "orcamentos_recarregados.emit()" in inspect.getsource(
        orcamentos_page.OrcamentosPage.carregar_orcamentos
    )
    fonte = inspect.getsource(helper.AssistenteOrcamentos.__init__)
    assert "orcamentos_recarregados.connect" in fonte
    # O V2 lê-se numa thread: rede lenta não prende a janela.
    assert "threading.Thread(target=self._carregar_v2" in fonte
