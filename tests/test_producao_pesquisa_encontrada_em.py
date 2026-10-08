"""Produção: a linha de estado diz onde a pesquisa encontrou a obra (08-10-2026).

O Paulo procurou «consola» e apareceu a 1418, que no ecrã não tem «consola» em
lado nenhum: estava na descrição do orçamento, um campo que a pesquisa lê mas
que o detalhe da obra não mostra. Agora a linha de estado explica-o.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from sqlalchemy.exc import SQLAlchemyError

import app.ui.pages.producao_page as modulo
from app.models.producao import Producao

_app = QApplication.instance() or QApplication([])


class _SemBase:
    def __enter__(self):
        raise SQLAlchemyError("sem base nos testes")

    def __exit__(self, *_args):
        return False


class _SessaoFalsa:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _obra(proc_id: int, enc: str, **campos) -> Producao:
    return Producao(
        id=proc_id,
        codigo_processo=f"26.{enc}_01_01_JF_VIVA",
        ano="2026",
        num_enc_phc=enc,
        versao_obra="01",
        versao_plano="01",
        estado="Arquivado",
        tipo_pasta="Encomenda de Cliente",
        nome_cliente="MÓVEIS J.F. VIVA",
        nome_cliente_simplex="JF_VIVA",
        **campos,
    )


@pytest.fixture
def pagina(monkeypatch):
    obras = [
        _obra(
            1418,
            "1418",
            descricao_producao="4 ROUPEIROS PORTAS ABRIR",
            descricao_orcamento="4 roupeiros portas abrir 1 lavandaria 1 roupeiro consola 2 gavetas",
        ),
        _obra(837, "0837", descricao_producao="1 CONSOLA SUSPENSA 3 GVTS"),
    ]

    class _Servico:
        def __init__(self, _session) -> None:
            pass

        def listar_processos(self):
            return list(obras)

    monkeypatch.setattr(modulo, "SessionLocal", lambda: _SemBase())
    pagina = modulo.ProducaoPage()
    monkeypatch.setattr(modulo, "SessionLocal", lambda: _SessaoFalsa())
    monkeypatch.setattr(modulo, "ProducaoService", _Servico)
    monkeypatch.setattr(pagina, "_pedir_detalhe_obra", lambda *_a: None)
    monkeypatch.setattr(pagina, "_atualizar_botao_ocorrencias", lambda *_a: None)
    pagina.minhas_check.setChecked(False)
    pagina.responsavel_combo.setCurrentIndex(0)
    pagina.carregar_processos(selecionar_id=1418)
    _app.processEvents()
    yield pagina
    pagina._parar_thread_detalhe()
    pagina.deleteLater()


def _pesquisar(pagina, texto: str) -> None:
    pagina.campo_pesquisa.definir_texto(texto)
    pagina._render()
    _app.processEvents()


def test_campo_escondido_e_explicado_com_o_trecho(pagina) -> None:
    _pesquisar(pagina, "consola")

    assert pagina._selected_processo_id == 1418
    estado = pagina.status_label.text()
    assert estado.startswith(modulo.AVISO_ENCONTRADO_EM)
    assert "Descrição do orçamento" in estado
    assert "não aparece no ecrã" in estado
    assert "roupeiro consola 2 gavetas" in estado


def test_campo_visivel_so_diz_o_nome(pagina) -> None:
    _pesquisar(pagina, "consola")
    pagina.table.setCurrentIndex(pagina._indice_visivel_do_processo(837))
    _app.processEvents()

    assert pagina.status_label.text() == (
        f"{modulo.AVISO_ENCONTRADO_EM} Descrição produção."
    )


def test_limpar_a_pesquisa_limpa_a_explicacao(pagina) -> None:
    _pesquisar(pagina, "consola")
    _pesquisar(pagina, "")

    assert not pagina.status_label.text().startswith(modulo.AVISO_ENCONTRADO_EM)
