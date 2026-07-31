"""Relatório de problema: o que o utilizador envia quando algo corre mal."""

from __future__ import annotations

import inspect
from datetime import datetime
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.core import diario_bordo
from app.services import reporte_problema_service as svc
from app.ui.registo_avisos import _RegistoDeAvisos


@pytest.fixture(scope="module", autouse=True)
def _app():
    yield QApplication.instance() or QApplication([])


# ---- o relatório -------------------------------------------------------------
def test_relatorio_leva_contexto_descricao_e_diario() -> None:
    texto = svc.montar_relatorio(
        "exportei o PDF do CUT-RITE e não apareceu na pasta",
        versao="3.0.0",
        contexto={"utilizador": "paulo", "menu": "producao", "obra": "26.1349_01_01"},
        linhas=["2026-07-31 09:24:11 | INFO | paulo | producao | 26.1349_01_01 | Abriu o menu"],
        momento=datetime(2026, 7, 31, 9, 25, 0),
    )

    assert "2026-07-31 09:25:00" in texto
    assert "Versão: 3.0.0" in texto
    assert "Utilizador: paulo" in texto
    assert "Obra: 26.1349_01_01" in texto
    assert "exportei o PDF do CUT-RITE" in texto
    assert "Abriu o menu" in texto


def test_relatorio_sem_descricao_diz_que_esta_vazia() -> None:
    texto = svc.montar_relatorio("   ", versao="3.0.0", contexto={}, linhas=[])

    assert "(não preenchido)" in texto


def test_nome_do_relatorio_nao_estraga_o_ficheiro() -> None:
    nome = svc.nome_do_relatorio(
        {"utilizador": "paulo catarino/admin"}, momento=datetime(2026, 7, 31, 9, 25, 0)
    )

    assert nome == "problema_martelo_paulo_catarino_admin_20260731_092500.txt"


def test_gravar_relatorio_escreve_o_ficheiro(tmp_path: Path) -> None:
    destino = svc.gravar_relatorio("conteúdo", pasta=tmp_path, nome="relatorio.txt")

    assert destino.read_text(encoding="utf-8") == "conteúdo"


# ---- tudo o que o utilizador vê fica registado -------------------------------
def _mostrar(caixa: QMessageBox) -> None:
    """Mostra a caixa e fecha-a — o filtro reage ao evento de aparecer."""
    caixa.show()
    QApplication.processEvents()
    caixa.close()


def test_caixas_de_aviso_entram_no_diario(monkeypatch) -> None:
    registado: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        diario_bordo, "registar_erro", lambda t, m="", **k: registado.append(("erro", t, m))
    )
    monkeypatch.setattr(
        diario_bordo, "registar_aviso", lambda t, m="": registado.append(("aviso", t, m))
    )
    monkeypatch.setattr(
        diario_bordo, "registar_acao", lambda a, d="": registado.append(("acao", a, str(d)))
    )

    app = QApplication.instance()
    filtro = _RegistoDeAvisos()
    app.installEventFilter(filtro)
    janela = QWidget()
    try:
        _mostrar(QMessageBox(QMessageBox.Icon.Critical, "Exportar PDF", "Falhou.", parent=janela))
        _mostrar(QMessageBox(QMessageBox.Icon.Warning, "Guardar", "Preencha a data.", parent=janela))
        _mostrar(QMessageBox(QMessageBox.Icon.Information, "Preparação", "Feito.", parent=janela))
    finally:
        app.removeEventFilter(filtro)

    assert ("erro", "Exportar PDF", "Falhou.") in registado
    assert ("aviso", "Guardar", "Preencha a data.") in registado
    assert any(tipo == "acao" and "Preparação" in acao for tipo, acao, _ in registado)


def test_filtro_nunca_deixa_o_evento_por_tratar() -> None:
    """Registar não pode mudar o comportamento das janelas."""
    fonte = inspect.getsource(_RegistoDeAvisos.eventFilter)

    assert "return False" in fonte
    assert "except Exception" in fonte


# ---- ligações na aplicação ---------------------------------------------------
def test_arranque_instala_a_caixa_negra() -> None:
    from app import main

    fonte = inspect.getsource(main.main)

    assert "diario_bordo.instalar_apanhador_de_erros()" in fonte
    assert "diario_bordo.registar_arranque(VERSAO_APLICACAO)" in fonte
    # A limpeza corre sozinha a cada arranque — ninguém tem de se lembrar dela.
    assert "diario_bordo.limpar_registos_antigos()" in fonte
    assert "instalar_registo_de_avisos(qt_app)" in fonte
    assert "diario_bordo.definir_utilizador(" in fonte


def test_menu_e_obra_ficam_no_contexto() -> None:
    from app.ui.main_window import MainWindow
    from app.ui.pages.producao_page import ProducaoPage

    assert "diario_bordo.definir_menu(name)" in inspect.getsource(MainWindow.show_page)
    assert "diario_bordo.definir_obra(proc.codigo_processo)" in inspect.getsource(
        ProducaoPage._fill_form
    )
    assert "self.reportar_button" in inspect.getsource(MainWindow.__init__)
