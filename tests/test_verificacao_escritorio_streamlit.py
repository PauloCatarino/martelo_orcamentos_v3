"""Aviso do Escritório do Streamlit (parte Qt e memória das recusas)."""

from __future__ import annotations

import sys
from datetime import date

import pytest
from PySide6.QtWidgets import QApplication

from app.domain import escritorio_streamlit as regras
from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog
from app.ui.helpers import verificacao_escritorio_streamlit as modulo
from app.ui.helpers.verificacao_escritorio_streamlit import (
    VerificadorEscritorioStreamlit,
    juntar_vistos,
    ler_vistos,
)


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication(sys.argv)


def _sugestao(id_: int = 1) -> dict:
    return {
        "id": id_,
        "codigo": f"26.109{id_}_01_01_STHINK",
        "num_enc_phc": f"109{id_}",
        "cliente": "STHINK",
        "ref_cliente": "",
        "responsavel": "Pedro",
        "data_entrega": "",
        "estado_martelo": "Desenho",
        "estado_sugerido": "Producao",
        "estado_phc_raw": "Libertado para a fábrica desde 22/10/2026 16:05 (dulce.faria)",
        "fonte": "Escritório",
        "bd_key": f"2026_109{id_}_01_01",
        "marca": f"2026_109{id_}_01_01|LIBERTADA",
    }


def test_desligado_nao_vai_ao_streamlit(_app) -> None:
    objeto = VerificadorEscritorioStreamlit(user_id=1, responsavel="Pedro", ativo=False)
    pedidos: list[object] = []
    objeto.pedir_verificacao.connect(pedidos.append)
    objeto.verificar()
    assert pedidos == []
    objeto.parar()


def test_sem_utilizador_fica_desligado(_app) -> None:
    objeto = VerificadorEscritorioStreamlit(user_id=None, ativo=True)
    pedidos: list[object] = []
    objeto.pedir_verificacao.connect(pedidos.append)
    objeto.verificar()
    assert pedidos == []
    objeto.parar()


def test_primeira_volta_do_dia_e_completa(_app) -> None:
    objeto = VerificadorEscritorioStreamlit(user_id=1, responsavel="Pedro", ativo=False)
    objeto._ativo = True
    objeto._ultimo_token = 140
    pedidos: list[object] = []
    objeto.pedir_verificacao.connect(pedidos.append)

    objeto.verificar()  # primeira do dia: sem token, vai buscar tudo
    objeto._a_trabalhar = False
    objeto.verificar()  # depois: só pergunta se o token mudou

    assert pedidos == [None, 140]
    objeto.parar()


def test_trabalho_nao_repete_quando_nada_mudou(monkeypatch) -> None:
    monkeypatch.setattr(modulo.leitura, "ler_token", lambda _s: 140)
    monkeypatch.setattr(
        modulo.leitura,
        "levantar_sugestoes",
        lambda *_a, **_k: pytest.fail("não devia ir buscar as versões"),
    )
    trabalho = modulo._TrabalhoEscritorio("Pedro")
    sinais: list[str] = []
    trabalho.sem_novidades.connect(lambda: sinais.append("nada"))
    trabalho.verificar(140)
    assert sinais == ["nada"]


def test_trabalho_so_procura_as_obras_de_quem_esta_no_martelo(monkeypatch) -> None:
    pedidos: list[object] = []

    def falso(_session, *, responsavel=None):
        pedidos.append(responsavel)
        return 141, []

    monkeypatch.setattr(modulo.leitura, "levantar_sugestoes", falso)
    trabalho = modulo._TrabalhoEscritorio("Pedro")
    trabalho.verificar(None)
    assert pedidos == ["Pedro"]


def test_streamlit_em_baixo_so_fica_no_diario_uma_vez(_app, monkeypatch) -> None:
    objeto = VerificadorEscritorioStreamlit(user_id=1, ativo=False)
    erros: list[str] = []
    monkeypatch.setattr(modulo.diario_bordo, "registar_erro", lambda *a, **k: erros.append(a[0]))
    objeto._on_falhou("timeout")
    objeto._on_falhou("timeout")
    assert len(erros) == 1
    objeto.parar()


def test_streamlit_que_volta_sem_novidades_deixa_registar_a_proxima_falha(_app, monkeypatch) -> None:
    # 28-10: falhou às 19:56 e o diário não podia dizer se as voltas seguintes correram.
    objeto = VerificadorEscritorioStreamlit(user_id=1, ativo=False)
    erros: list[str] = []
    monkeypatch.setattr(modulo.diario_bordo, "registar_erro", lambda *a, **k: erros.append(a[0]))
    objeto._on_falhou("timeout")
    objeto._on_sem_novidades()
    objeto._on_falhou("timeout")
    assert len(erros) == 2
    objeto.parar()


def test_vistos_guardam_recusas_e_esquecem_adiamentos_velhos() -> None:
    hoje = date(2026, 10, 28)
    vistos = {"a": "sempre", "b": "2026-10-27", "c": "2026-10-28"}
    juntos = juntar_vistos(vistos, {"d": "2026-10-28"}, hoje)
    assert juntos == {"a": "sempre", "c": "2026-10-28", "d": "2026-10-28"}


def test_vistos_tem_teto() -> None:
    hoje = date(2026, 10, 28)
    vistos = {f"m{i}": "sempre" for i in range(modulo.MAXIMO_VISTOS)}
    juntos = juntar_vistos(vistos, {"novo": "sempre"}, hoje)
    assert len(juntos) == modulo.MAXIMO_VISTOS
    assert "novo" in juntos and "m0" not in juntos


@pytest.mark.parametrize("texto", ["", None, "lixo", "[1, 2]"])
def test_ler_vistos_tolerante(texto) -> None:
    assert ler_vistos(texto) == {}


def test_caixa_do_analisador_mostra_o_escritorio(_app) -> None:
    caixa = ProducaoPhcSyncDialog(
        [_sugestao(1), _sugestao(2)],
        automatico=True,
        titulo=modulo.TITULO,
        apresentacao=modulo.APRESENTACAO,
        dica_ver_depois=modulo.DICA_VER_DEPOIS,
    )
    assert caixa.windowTitle() == modulo.TITULO
    assert caixa.selecionados() == [(1, "Producao"), (2, "Producao")]
    assert caixa.table.item(0, 8).text() == "Escritório"
    assert "Libertado para a fábrica" in caixa.table.item(0, 9).text()
    caixa.deleteLater()


def test_aceitar_grava_producao_e_lembra_as_desmarcadas(_app, monkeypatch) -> None:
    objeto = VerificadorEscritorioStreamlit(user_id=1, responsavel="Pedro", ativo=False)
    hoje = date(2026, 10, 28)
    guardados: list[dict] = []
    aplicados: list[list] = []
    emails: list[list] = []
    monkeypatch.setattr(objeto, "_guardar_vistos", guardados.append)
    monkeypatch.setattr(
        modulo, "aplicar_estados",
        lambda _s, pares, **_k: aplicados.append(list(pares)) or len(pares),
    )
    monkeypatch.setattr(modulo.QMessageBox, "information", lambda *a, **k: None)
    objeto.obras_em_producao.connect(emails.append)

    class _Caixa:
        def __init__(self, sugestoes, *_a, **_k):
            self.table = self
            self._sugestoes = sugestoes

        def exec(self):
            return True

        def selecionados(self):
            return [(1, "Producao")]

        def isRowHidden(self, _linha):
            return False

    monkeypatch.setattr(modulo, "ProducaoPhcSyncDialog", _Caixa)
    objeto._mostrar([_sugestao(1), _sugestao(2)], hoje)

    assert aplicados == [[(1, "Producao")]]
    assert guardados == [{"2026_1092_01_01|LIBERTADA": regras.VISTO_DE_VEZ}]
    assert emails == [[1]]
    objeto.parar()


def test_ver_depois_adia_para_amanha(_app, monkeypatch) -> None:
    objeto = VerificadorEscritorioStreamlit(user_id=1, ativo=False)
    hoje = date(2026, 10, 28)
    guardados: list[dict] = []
    monkeypatch.setattr(objeto, "_guardar_vistos", guardados.append)

    class _Caixa:
        def __init__(self, *_a, **_k):
            pass

        def exec(self):
            return False

    monkeypatch.setattr(modulo, "ProducaoPhcSyncDialog", _Caixa)
    objeto._mostrar([_sugestao(1)], hoje)
    assert guardados == [{"2026_1091_01_01|LIBERTADA": "2026-10-28"}]
    objeto.parar()
