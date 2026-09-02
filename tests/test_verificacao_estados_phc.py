"""Aviso diário das obras que o PHC/Streamlit já fechou (parte Qt)."""

from __future__ import annotations

import sys

import pytest
from PySide6.QtWidgets import QApplication

from app.services.producao_phc_sync_service import LevantamentoEstados
from app.ui.helpers import verificacao_estados_phc as modulo
from app.ui.helpers.verificacao_estados_phc import VerificadorEstadosPHC


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture()
def verificador(_app):
    objeto = VerificadorEstadosPHC(user_id=1, responsavel="Paulo", ativo=False)
    yield objeto
    objeto.parar()


def _diff(id_: int = 1, estado: str = "Arquivado") -> dict:
    return {
        "id": id_,
        "codigo": f"26.100{id_}_01_01_CLIENTE",
        "num_enc_phc": f"100{id_}",
        "cliente": "Cliente",
        "ref_cliente": "",
        "responsavel": "Paulo",
        "data_entrega": "",
        "estado_martelo": "Desenho",
        "estado_sugerido": estado,
        "estado_phc_raw": "7 - ARQUIVADO",
        "fonte": "PHC",
    }


def test_desligado_nao_vai_ao_phc(verificador) -> None:
    pedidos: list[int] = []
    verificador.pedir_verificacao.connect(lambda: pedidos.append(1))

    verificador.verificar_se_e_hora()

    assert pedidos == []


def test_quando_e_hora_pede_a_verificacao_e_marca_o_dia(monkeypatch, _app) -> None:
    """Marca o dia ANTES de ir ao PHC: se ele estiver em baixo, não insiste."""
    objeto = VerificadorEstadosPHC(user_id=1, responsavel="Paulo", ativo=True)
    dias: list[object] = []
    monkeypatch.setattr(modulo.agenda_diaria_phc, "deve_verificar", lambda *a: True)
    monkeypatch.setattr(objeto, "_ultima_verificacao", lambda: None)
    monkeypatch.setattr(objeto, "_guardar_verificacao", dias.append)
    pedidos: list[int] = []
    objeto.pedir_verificacao.connect(lambda: pedidos.append(1))

    objeto.verificar_se_e_hora()
    # Segunda passagem: já está a trabalhar, não repete o pedido.
    objeto.verificar_se_e_hora()

    assert pedidos == [1]
    assert len(dias) == 1
    objeto.parar()


def test_so_procura_as_obras_de_quem_esta_a_usar_o_martelo(monkeypatch) -> None:
    """Cada pessoa recebe o aviso das SUAS obras."""
    pedidos: list[dict] = []

    def falso_levantamento(_fabrica, *, responsavel=None):
        pedidos.append({"responsavel": responsavel})
        return LevantamentoEstados(diferencas=[])

    monkeypatch.setattr(modulo, "levantar_estados_de_fora", falso_levantamento)
    trabalho = modulo._TrabalhoEstados("Paulo")
    trabalho.verificar()

    assert pedidos == [{"responsavel": "Paulo"}]


def test_sem_nada_para_fechar_nao_incomoda_o_utilizador(
    monkeypatch, verificador
) -> None:
    caixas: list[int] = []
    monkeypatch.setattr(
        modulo.ProducaoPhcSyncDialog, "exec", lambda self: caixas.append(1)
    )

    verificador._on_verificado(LevantamentoEstados(diferencas=[]))

    assert caixas == []


def test_quando_ha_obras_mostra_a_caixa_a_apresentar_se(
    monkeypatch, verificador
) -> None:
    vistas: list[object] = []

    def _mostrar(caixa):
        vistas.append(caixa)
        return 0  # o utilizador fecha em "Ver depois"

    monkeypatch.setattr(modulo.ProducaoPhcSyncDialog, "exec", _mostrar)

    verificador._on_verificado(LevantamentoEstados(diferencas=[_diff()]))

    assert len(vistas) == 1
    assert "diário" in vistas[0].windowTitle()


def test_ver_depois_nao_grava_nada(monkeypatch, verificador) -> None:
    monkeypatch.setattr(modulo.ProducaoPhcSyncDialog, "exec", lambda self: 0)
    gravou: list[int] = []
    monkeypatch.setattr(
        modulo, "aplicar_estados", lambda *a, **k: gravou.append(1) or 1
    )

    verificador._on_verificado(LevantamentoEstados(diferencas=[_diff()]))

    assert gravou == []


def test_as_duas_fontes_em_baixo_ficam_no_diario_sem_caixa(
    monkeypatch, verificador
) -> None:
    """Isto corre sozinho: um erro de rede não pode saltar à cara de ninguém."""
    caixas: list[int] = []
    erros: list[str] = []
    monkeypatch.setattr(
        modulo.ProducaoPhcSyncDialog, "exec", lambda self: caixas.append(1)
    )
    monkeypatch.setattr(modulo.diario_bordo, "registar_erro", erros.append)

    verificador._on_verificado(
        LevantamentoEstados(
            diferencas=[],
            erro_phc="sem rede",
            erro_streamlit="sem rede",
        )
    )

    assert caixas == []
    assert len(erros) == 1
    assert "sem rede" in erros[0]


def test_uma_fonte_em_baixo_nao_esconde_a_outra(monkeypatch, verificador) -> None:
    vistas: list[object] = []
    erros: list[str] = []
    monkeypatch.setattr(
        modulo.ProducaoPhcSyncDialog, "exec", lambda self: vistas.append(1) or 0
    )
    monkeypatch.setattr(modulo.diario_bordo, "registar_erro", erros.append)

    verificador._on_verificado(
        LevantamentoEstados(diferencas=[_diff()], erro_streamlit="sem rede")
    )

    assert len(vistas) == 1
    assert any("Streamlit" in erro for erro in erros)


def test_a_chave_do_dia_e_diferente_da_dos_clientes() -> None:
    """Duas verificações diárias, dois registos: uma não desliga a outra."""
    from app.ui.helpers.verificacao_clientes_phc import (
        CHAVE_ULTIMA_VERIFICACAO as CHAVE_CLIENTES,
    )

    assert modulo.CHAVE_ULTIMA_VERIFICACAO != CHAVE_CLIENTES


def test_arranca_depois_da_dos_clientes() -> None:
    """As duas juntas no arranque punham dois PowerShell a falar com o PHC."""
    from app.ui.helpers.verificacao_clientes_phc import (
        ATRASO_ARRANQUE_MS as ATRASO_CLIENTES,
    )

    assert modulo.ATRASO_ARRANQUE_MS > ATRASO_CLIENTES
