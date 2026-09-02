"""Pesquisa dedicada ao Nº Enc PHC na Produção, e o fim do botão «pincel».

A pesquisa geral não sabe se «1320» é uma encomenda ou um pedaço de texto num
campo qualquer, e devolve tudo o que apanha. Este filtro procura só na coluna
do número da encomenda.
"""

from __future__ import annotations

import inspect
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from app.services.producao_service import enc_phc_corresponde, processo_corresponde


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication(sys.argv)


# ---- a regra de correspondência --------------------------------------------


def test_campo_vazio_nao_filtra_nada() -> None:
    assert enc_phc_corresponde("1449", "") is True
    assert enc_phc_corresponde("1449", None) is True
    assert enc_phc_corresponde("1449", "   ") is True


def test_numero_completo_encontra_a_encomenda() -> None:
    assert enc_phc_corresponde("1449", "1449") is True
    assert enc_phc_corresponde("1499", "1449") is False


def test_vai_estreitando_a_medida_que_se_escreve() -> None:
    """«14» ainda apanha várias; «1449» deixa só uma."""
    encomendas = ["1449", "1463", "1494", "1050"]

    assert [e for e in encomendas if enc_phc_corresponde(e, "14")] == [
        "1449",
        "1463",
        "1494",
    ]
    assert [e for e in encomendas if enc_phc_corresponde(e, "1449")] == ["1449"]


def test_zeros_a_frente_sao_a_mesma_encomenda() -> None:
    assert enc_phc_corresponde("0100", "100") is True
    assert enc_phc_corresponde("100", "0100") is True
    assert enc_phc_corresponde("0705", "705") is True


def test_o_underscore_distingue_duas_encomendas_diferentes() -> None:
    """«_182» (Streamlit) e «182» (PHC) são obras diferentes."""
    assert enc_phc_corresponde("_182", "182") is False
    assert enc_phc_corresponde("182", "_182") is False
    assert enc_phc_corresponde("_182", "_182") is True
    assert enc_phc_corresponde("_182", "_18") is True


def test_nao_procura_no_meio_do_numero() -> None:
    """É pelo início: senão «44» apanhava 1449 e a pesquisa voltava a ser vaga."""
    assert enc_phc_corresponde("1449", "44") is False


def test_obra_sem_numero_de_encomenda_desaparece_quando_se_filtra() -> None:
    assert enc_phc_corresponde(None, "14") is False
    assert enc_phc_corresponde("", "14") is False
    # Sem filtro continua a aparecer.
    assert enc_phc_corresponde(None, "") is True


# ---- ligado ao filtro das obras --------------------------------------------


def _obra(**campos):
    base = {
        "num_enc_phc": "1449",
        "estado": "Desenho",
        "nome_cliente": "CRW",
        "responsavel": "Angela",
        "data_entrega": None,
    }
    base.update(campos)
    return SimpleNamespace(**base)


def test_o_filtro_entra_no_processo_corresponde() -> None:
    assert processo_corresponde(_obra(), enc_phc="1449") is True
    assert processo_corresponde(_obra(), enc_phc="1499") is False


def test_o_filtro_soma_se_aos_outros_e_nao_os_substitui() -> None:
    obra = _obra()

    # Número certo mas responsável errado: não passa.
    assert processo_corresponde(obra, enc_phc="1449", responsavel="Paulo") is False
    # Os dois certos: passa.
    assert processo_corresponde(obra, enc_phc="1449", responsavel="Angela") is True


# ---- a interface -----------------------------------------------------------


def test_a_producao_tem_um_campo_so_para_a_encomenda(_app) -> None:
    from app.ui.pages.producao_page import ProducaoPage

    fonte = inspect.getsource(ProducaoPage)

    assert 'setPlaceholderText("Nº Enc PHC")' in fonte
    # A pesquisa geral fica exatamente como estava, ao lado.
    assert "self.campo_pesquisa.pesquisa_mudou.connect(self._render)" in fonte
    assert "enc_phc=self.enc_phc_input.text()" in fonte


def test_limpar_filtros_tambem_limpa_a_encomenda() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    fonte = inspect.getsource(ProducaoPage._limpar_filtros)

    assert "self.enc_phc_input.clear()" in fonte


def test_as_vistas_guardadas_levam_a_encomenda() -> None:
    from app.ui.helpers.vistas_producao import (
        VistaProducao,
        desserializar_vistas,
        serializar_vistas,
    )

    vista = VistaProducao(nome="Cozinhas", texto="cozinha", enc_phc="1449")

    voltou = desserializar_vistas(serializar_vistas([vista]))[0]

    assert voltou.enc_phc == "1449"


def test_vistas_antigas_continuam_a_abrir() -> None:
    """Gravadas antes deste filtro existir: não trazem o campo."""
    from app.ui.helpers.vistas_producao import desserializar_vistas

    antiga = '[{"nome": "Antiga", "texto": "cozinha", "estado": "Desenho"}]'

    vista = desserializar_vistas(antiga)[0]

    assert vista.nome == "Antiga"
    assert vista.enc_phc == ""


# ---- o botão «pincel» -------------------------------------------------------


def test_o_campo_de_pesquisa_ja_nao_tem_pincel(_app) -> None:
    from PySide6.QtWidgets import QLineEdit, QToolButton

    from app.ui.widgets.barra_pesquisa import CampoPesquisa

    campo = CampoPesquisa()

    # Já não há botão ao LADO do campo. O X é um QToolButton também, mas vive
    # dentro do QLineEdit — é o do `setClearButtonEnabled`, e esse fica.
    botoes_ao_lado = [
        botao
        for botao in campo.findChildren(QToolButton)
        if not isinstance(botao.parent(), QLineEdit)
    ]

    assert botoes_ao_lado == []
    assert not hasattr(campo, "limpar_clicado")


def test_o_campo_de_pesquisa_ficou_mais_largo(_app) -> None:
    from app.ui.widgets.barra_pesquisa import CampoPesquisa

    campo = CampoPesquisa()

    assert campo._input.maximumWidth() == 420
    assert campo._input.isClearButtonEnabled() is True


def test_o_x_do_campo_continua_a_limpar_e_a_filtrar(_app) -> None:
    from app.ui.widgets.barra_pesquisa import CampoPesquisa

    campo = CampoPesquisa()
    vistos: list[str] = []
    campo.pesquisa_mudou.connect(vistos.append)

    campo.definir_texto("1449")
    campo.limpar()

    # A lista volta a ser filtrada com o texto vazio: é isto que o X faz.
    assert vistos == ["1449", ""]


def test_ninguem_ficou_agarrado_ao_sinal_do_pincel() -> None:
    """Se sobrasse um `limpar_clicado`, a página rebentava ao abrir."""
    from pathlib import Path

    raiz = Path(inspect.getfile(processo_corresponde)).parents[1]
    sobras = [
        str(caminho)
        for caminho in (raiz / "ui").rglob("*.py")
        if "limpar_clicado" in caminho.read_text(encoding="utf-8")
    ]

    assert sobras == []


def test_as_paginas_com_filtros_ganharam_um_botao_com_nome() -> None:
    """A ação de repor TODOS os filtros não se perdeu com o pincel."""
    from app.ui.dialogs.ocorrencias_obra_dialog import OcorrenciasObraDialog
    from app.ui.pages.ocorrencias_page import OcorrenciasPage
    from app.ui.pages.orcamentos_page import OrcamentosPage
    from app.ui.pages.ponto_situacao_page import PontoSituacaoPage
    from app.ui.pages.producao_page import ProducaoPage

    for classe in (
        ProducaoPage,
        OrcamentosPage,
        OcorrenciasPage,
        PontoSituacaoPage,
        OcorrenciasObraDialog,
    ):
        fonte = inspect.getsource(classe)
        assert "BotaoLimparFiltros()" in fonte, classe.__name__
        assert (
            "self.limpar_filtros_button.clicked.connect(self._limpar_filtros)" in fonte
        ), classe.__name__
