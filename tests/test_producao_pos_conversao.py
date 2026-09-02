"""Depois de converter: filtros limpos, ficha da obra e pasta no servidor."""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

from app.ui.pages.producao_page import ProducaoPage


def _obra(**campos):
    base = {
        "codigo_processo": "26.1499_01_01_JF_VIVA",
        "nome_cliente": "MÓVEIS J.F. VIVA",
        "num_enc_phc": "1499",
        "num_orcamento": "260873",
        "versao_orc": "01",
        "ref_cliente": "2504035",
        "estado": "Desenho",
        "responsavel": "Paulo",
        "data_inicio": "02-09-2026",
        "data_entrega": "30-10-2026",
        "descricao_artigos": "1 COZINHA C/ ILHA",
    }
    base.update(campos)
    return SimpleNamespace(**base)


def test_resumo_da_obra_criada_mostra_o_essencial() -> None:
    resumo = ProducaoPage._resumo_obra_criada(_obra())

    for esperado in (
        "26.1499_01_01_JF_VIVA",
        "MÓVEIS J.F. VIVA",
        "1499",
        "260873",
        "2504035",
        "Desenho",
        "Paulo",
        "02-09-2026",
        "30-10-2026",
        "1 COZINHA C/ ILHA",
    ):
        assert esperado in resumo


def test_resumo_aguenta_campos_por_preencher() -> None:
    resumo = ProducaoPage._resumo_obra_criada(
        _obra(responsavel=None, data_inicio=None, descricao_artigos=None)
    )

    assert "Responsável: —" in resumo
    assert "Data Início: —" in resumo
    # Sem descrição, a secção nem aparece.
    assert "Descrição artigos:" not in resumo


def test_conversao_limpa_os_filtros_antes_de_mostrar_a_obra() -> None:
    fonte = inspect.getsource(ProducaoPage._converter_orcamento)

    # Sem isto, a obra acabada de criar ficava escondida por um filtro antigo.
    assert "self._limpar_filtros()" in fonte
    assert fonte.index("self._limpar_filtros()") < fonte.index(
        "self.carregar_processos(selecionar_id=processo_id)"
    )


def test_conversao_traz_do_phc_o_mesmo_que_o_novo_processo() -> None:
    fonte = inspect.getsource(ProducaoPage._converter_orcamento)

    assert "dados_encomenda_phc(" in fonte
    assert "dados_encomenda=dados_encomenda" in fonte
    assert "responsavel=responsavel" in fonte


def test_conversao_oferece_criar_a_pasta_e_mostra_a_ficha_da_obra() -> None:
    fonte = inspect.getsource(ProducaoPage._converter_orcamento)

    assert "_perguntar_criar_pasta_obra(" in fonte
    assert "_resumo_obra_criada(" in fonte
    assert "QMessageBox.information" in fonte


def test_abrir_pasta_inexistente_passa_a_oferecer_cria_la() -> None:
    fonte = inspect.getsource(ProducaoPage._abrir_pasta_versao_selecionada)

    # O aviso antigo era um beco sem saída; agora dá para criar a pasta.
    assert "_criar_pasta_da_obra_a_pedido(" in fonte
    assert 'QMessageBox.warning(self, "Abrir pasta", "Pasta ainda não criada.")' not in fonte


def test_a_pasta_so_e_criada_depois_de_o_user_dizer_que_sim() -> None:
    fonte = inspect.getsource(ProducaoPage._perguntar_criar_pasta_obra)

    assert "QMessageBox.question" in fonte
    # A criação vive noutro método, e só é chamada depois da resposta.
    assert fonte.index("QMessageBox.question") < fonte.index("_criar_pasta_da_obra(")
    # E não se pergunta nada quando a pasta já existe.
    assert "caminho_versao_de_processo_existente(" in fonte


def test_criar_pasta_guarda_o_caminho_na_obra() -> None:
    fonte = inspect.getsource(ProducaoPage._criar_pasta_da_obra)

    assert "criar_pasta_versao(destino)" in fonte
    assert "processo.pasta_servidor = str(destino)" in fonte
    assert "session.commit()" in fonte
