"""Produção: "Há alterações por gravar" (pedido do Paulo, 17-09-2026).

A pergunta era «Descartar? Yes/No»: quem carregava em Sim a pensar que estava
a gravar perdia o que tinha escrito. Passou a «Quer gravar as alterações?» com
Sim (grava), Não (descarta) e Cancelar (fica). E só pergunta quando há mesmo
alterações: o sublinhado do corretor ortográfico, por exemplo, emitia "texto
alterado" sem ninguém escrever nada.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from sqlalchemy.exc import SQLAlchemyError

import app.ui.pages.producao_page as modulo
from app.models.producao import Producao
from app.utils.formatters import format_eur, format_numero_pt

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


def _obra(proc_id: int, enc: str, notas: str = "") -> Producao:
    return Producao(
        id=proc_id,
        codigo_processo=f"26.{enc}_01_01_JF_VIVA",
        ano="2026",
        num_enc_phc=enc,
        versao_obra="01",
        versao_plano="01",
        estado="Desenho",
        tipo_pasta="Encomenda de Cliente",
        nome_cliente="MÓVEIS J.F. VIVA",
        nome_cliente_simplex="JF_VIVA",
        data_inicio="15-09-2026",
        data_entrega="30-09-2026",
        preco_total="2484.55",
        notas2=notas,
    )


@pytest.fixture
def pagina(monkeypatch):
    obras = {1572: _obra(1572, "1572"), 1582: _obra(1582, "1582")}
    gravadas: list[tuple[int, dict]] = []

    class _Servico:
        def __init__(self, _session) -> None:
            pass

        def listar_processos(self):
            return list(obras.values())

        def atualizar_processo(self, proc_id, data, *, updated_by_id):
            gravadas.append((proc_id, dict(data)))
            obras[proc_id].notas2 = data.get("notas2")

    monkeypatch.setattr(modulo, "SessionLocal", lambda: _SemBase())
    pagina = modulo.ProducaoPage()
    monkeypatch.setattr(modulo, "SessionLocal", lambda: _SessaoFalsa())
    monkeypatch.setattr(modulo, "ProducaoService", _Servico)
    monkeypatch.setattr(pagina, "_pedir_detalhe_obra", lambda *_a: None)
    monkeypatch.setattr(pagina, "_atualizar_botao_ocorrencias", lambda *_a: None)
    # Sem filtros de utilizador: as duas obras à vista.
    pagina.minhas_check.setChecked(False)
    pagina.responsavel_combo.setCurrentIndex(0)
    pagina.carregar_processos(selecionar_id=1572)
    _app.processEvents()

    respostas: list[str] = []
    perguntas: list[str] = []

    def perguntar():
        perguntas.append(pagina._selected_processo_id)
        return respostas.pop(0)

    monkeypatch.setattr(pagina, "_perguntar_gravar", perguntar)
    yield pagina, gravadas, respostas, perguntas
    pagina._parar_thread_detalhe()
    pagina.deleteLater()


def _clicar(pagina, proc_id: int) -> None:
    indice = pagina._indice_visivel_do_processo(proc_id)
    assert indice is not None
    pagina.table.setCurrentIndex(indice)
    _app.processEvents()


def test_a_obra_abre_sem_alteracoes(pagina) -> None:
    pagina, _, _, _ = pagina
    assert pagina._selected_processo_id == 1572
    assert pagina.tem_alteracoes_por_gravar() is False
    assert pagina.save_button.isEnabled() is False


def test_mudar_de_obra_sem_alteracoes_nao_pergunta(pagina) -> None:
    pagina, _, _, perguntas = pagina
    _clicar(pagina, 1582)

    assert perguntas == []
    assert pagina._selected_processo_id == 1582


def test_repintar_o_texto_nao_conta_como_alteracao(pagina) -> None:
    """O corretor repinta o texto e o Qt avisa "texto alterado"."""
    pagina, _, _, perguntas = pagina
    pagina.notas2_text.textChanged.emit()

    assert pagina.tem_alteracoes_por_gravar() is False
    assert pagina.save_button.isEnabled() is False
    _clicar(pagina, 1582)
    assert perguntas == []


def test_escrever_e_apagar_volta_a_sem_alteracoes(pagina) -> None:
    pagina, _, _, _ = pagina
    pagina.notas2_text.setPlainText("FALTA IMPRIMIR")
    assert pagina.save_button.isEnabled() is True

    pagina.notas2_text.setPlainText("")
    assert pagina.save_button.isEnabled() is False


def test_sim_grava_e_abre_a_obra_clicada(pagina) -> None:
    pagina, gravadas, respostas, perguntas = pagina
    pagina.notas2_text.setPlainText("FALTA IMPRIMIR")
    respostas.append("gravar")

    _clicar(pagina, 1582)

    assert perguntas == [1572]  # perguntou pela obra que estava a ser editada
    assert [(proc_id, data["notas2"]) for proc_id, data in gravadas] == [
        (1572, "FALTA IMPRIMIR")
    ]
    assert pagina._selected_processo_id == 1582
    assert pagina.tem_alteracoes_por_gravar() is False


def test_nao_descarta_e_abre_a_obra_clicada(pagina) -> None:
    pagina, gravadas, respostas, _ = pagina
    pagina.notas2_text.setPlainText("FALTA IMPRIMIR")
    respostas.append("descartar")

    _clicar(pagina, 1582)

    assert gravadas == []
    assert pagina._selected_processo_id == 1582
    assert pagina.notas2_text.toPlainText() == ""


def test_cancelar_fica_na_obra_com_o_texto(pagina) -> None:
    pagina, gravadas, respostas, _ = pagina
    pagina.notas2_text.setPlainText("FALTA IMPRIMIR")
    respostas.append("cancelar")

    _clicar(pagina, 1582)

    assert gravadas == []
    assert pagina._selected_processo_id == 1572
    assert pagina.notas2_text.toPlainText() == "FALTA IMPRIMIR"
    # A linha realçada volta a ser a obra do formulário.
    assert pagina._processo_na_linha_visivel(pagina.table.currentIndex().row()).id == 1572


def test_pesquisar_com_alteracoes_nao_pergunta_nem_perde_o_texto(pagina) -> None:
    pagina, gravadas, _, perguntas = pagina
    pagina.notas2_text.setPlainText("FALTA IMPRIMIR")

    pagina.campo_pesquisa.definir_texto("1582") if hasattr(
        pagina.campo_pesquisa, "definir_texto"
    ) else pagina.campo_pesquisa.setText("1582")
    pagina._render()
    _app.processEvents()

    assert perguntas == []
    assert gravadas == []
    assert pagina._selected_processo_id == 1572
    assert pagina.notas2_text.toPlainText() == "FALTA IMPRIMIR"


def test_sair_do_menu_pergunta_e_cancelar_impede(pagina) -> None:
    pagina, gravadas, respostas, perguntas = pagina
    assert pagina.pode_sair() is True  # sem alterações: sai sem perguntar
    assert perguntas == []

    pagina.notas2_text.setPlainText("FALTA IMPRIMIR")
    respostas.append("cancelar")
    assert pagina.pode_sair() is False

    respostas.append("gravar")
    assert pagina.pode_sair() is True
    assert gravadas and gravadas[-1][1]["notas2"] == "FALTA IMPRIMIR"


def test_preco_total_aparece_com_milhares(pagina) -> None:
    pagina, _, _, _ = pagina
    assert pagina.preco_total_input.text() == "2.484,55"
    # E volta a ler-se bem ao gravar.
    assert pagina._decimal_or_none("2.484,55") == pagina._decimal_or_none("2484.55")


def test_janela_principal_pergunta_a_pagina_antes_de_mudar_de_menu() -> None:
    import inspect

    from app.ui.main_window import MainWindow

    assert "pode_sair" in inspect.getsource(MainWindow.show_page)
    assert "pode_sair" in inspect.getsource(MainWindow.closeEvent)


# ---- formato dos preços -------------------------------------------------------------
@pytest.mark.parametrize(
    "valor, esperado",
    [
        ("2484.55", "2.484,55 €"),
        ("236059.86", "236.059,86 €"),
        ("1234567.8", "1.234.567,80 €"),
        ("147.68", "147,68 €"),
        ("0", "0,00 €"),
        ("-2484.5", "-2.484,50 €"),
    ],
)
def test_format_eur_separa_os_milhares_com_ponto(valor: str, esperado: str) -> None:
    assert format_eur(valor) == esperado


def test_format_eur_vazio() -> None:
    assert format_eur(None) == ""
    assert format_numero_pt("") == ""


def test_colunas_de_preco_dos_menus_usam_milhares() -> None:
    from app.models.producao import Producao
    from app.ui.helpers.colunas_producao import COLUNAS_PRODUCAO

    coluna = next(c for c in COLUNAS_PRODUCAO if c.key == "preco")
    processo = Producao(preco_total="3816.71")
    assert coluna.valor(processo) == "3.816,71 €"
