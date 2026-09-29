"""A janela «Gerar listas iMOS» e a opção nova no menu Funções da Produção."""

from __future__ import annotations

import inspect
import zipfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.services import imos_listas_service as svc
from app.ui.dialogs import gerar_listas_imos_dialog as dlg
from app.ui.dialogs.gerar_listas_imos_dialog import GerarListasImosDialog, texto_situacao

_app = QApplication.instance() or QApplication([])

GRAVACAO = datetime(2026, 9, 22, 12, 25, 30)


class _SessaoFalsa:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _config(tmp_path: Path) -> svc.ConfigListasImos:
    return svc.ConfigListasImos(ligacao="x", pasta_rdl=tmp_path, pasta_motor="", parametros={})


def _abrir(monkeypatch, tmp_path, *, procurar=None) -> GerarListasImosDialog:
    monkeypatch.setattr(dlg, "SessionLocal", _SessaoFalsa)
    monkeypatch.setattr(dlg, "carregar_config", lambda _s: _config(tmp_path))
    monkeypatch.setattr(
        dlg,
        "procurar_encomenda_imos",
        procurar
        or (lambda *_a, **_k: svc.EncomendaImos(proadmin_id=7667, nome="1610_01_26_JF_VIVA", ultima_gravacao=GRAVACAO)),
    )
    dialogo = GerarListasImosDialog(
        codigo_processo="26.1610_01_01",
        nome_enc="1610_01_26_JF_VIVA",
        pasta_obra=tmp_path,
    )
    dialogo._atualizar()
    return dialogo


def _xlsx(caminho: Path) -> Path:
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("docProps/core.xml", "<cp:coreProperties xmlns:cp=\"x\"></cp:coreProperties>")
    return caminho


def test_mostra_a_ultima_gravacao_e_as_quatro_listas_marcadas(monkeypatch, tmp_path) -> None:
    dialogo = _abrir(monkeypatch, tmp_path)

    assert dialogo.gravacao_label.text() == "22-09-2026 12:25:30"
    assert "ID 7667" in dialogo.encomenda_label.text()
    assert [dialogo.tabela.item(i, 0).text() for i in range(4)] == [l.chave for l in svc.LISTAS_IMOS]
    assert all(dialogo.tabela.item(i, 0).checkState() == Qt.CheckState.Checked for i in range(4))
    assert dialogo.gerar_button.isEnabled()
    assert "Ainda não há listas" in dialogo.status_label.text()


def test_lista_desatualizada_e_assinalada(monkeypatch, tmp_path) -> None:
    antiga = _xlsx(tmp_path / "2_List_Ferragens.xlsx")
    svc.marcar_origem(
        antiga,
        svc.texto_marca(svc.EncomendaImos(1, "X", datetime(2026, 9, 20, 9, 0))),
    )
    dialogo = _abrir(monkeypatch, tmp_path)

    assert dialogo.tabela.item(0, 3).text().startswith("Desatualizada")
    assert "(Martelo)" in dialogo.tabela.item(0, 2).text()
    assert "2_List_Ferragens" in dialogo.status_label.text()


def test_sem_ligacao_ao_imos_nao_deixa_gerar_e_diz_porque(monkeypatch, tmp_path) -> None:
    def falha(*_a, **_k):
        raise ValueError("Não encontrei no iMos a encomenda «X».")

    dialogo = _abrir(monkeypatch, tmp_path, procurar=falha)

    assert not dialogo.gerar_button.isEnabled()
    assert "Não encontrei no iMos" in dialogo.status_label.text()


def test_marcar_todas_alterna(monkeypatch, tmp_path) -> None:
    dialogo = _abrir(monkeypatch, tmp_path)
    dialogo._marcar_todas()
    assert dialogo._listas_marcadas() == []
    dialogo._marcar_todas()
    assert len(dialogo._listas_marcadas()) == 4


def test_sem_listas_marcadas_nao_gera(monkeypatch, tmp_path) -> None:
    dialogo = _abrir(monkeypatch, tmp_path)
    dialogo._marcar_todas()
    dialogo._gerar()
    assert dialogo._trabalho is None
    assert "Marque pelo menos uma lista" in dialogo.status_label.text()


def test_resultado_da_geracao_aparece_no_ecra(monkeypatch, tmp_path) -> None:
    dialogo = _abrir(monkeypatch, tmp_path)
    mensagens: list[str] = []
    monkeypatch.setattr(dlg.QMessageBox, "information", staticmethod(lambda *a: mensagens.append(a[2])))
    lista = svc.lista_por_chave("5_Custo_Obra_Ferragens")
    resultado = svc.ResultadoGeracao(
        encomenda=svc.EncomendaImos(7667, "1610_01_26_JF_VIVA", GRAVACAO),
        resultados=[svc.ResultadoLista(lista=lista, ok=True, segundos=1.6, anterior=tmp_path / "a.xlsx")],
    )

    dialogo._ao_terminar(resultado)

    assert dialogo.listas_geradas == 1
    assert "5_Custo_Obra_Ferragens: gerada em 2 s (a anterior ficou guardada)" in mensagens[0]
    assert "22-09-2026 12:25" in dialogo.status_label.text()


def test_textos_da_situacao() -> None:
    enc = svc.EncomendaImos(1, "X", GRAVACAO)
    lista = svc.LISTAS_IMOS[0]
    em_falta = svc.EstadoLista(lista=lista, pendente_imos=Path("x.xlsx"))
    assert "por importar" in texto_situacao(em_falta, enc)[0]
    atualizada = svc.EstadoLista(lista=lista, caminho=Path("a"), situacao=svc.SITUACAO_ATUALIZADA)
    assert texto_situacao(atualizada, enc)[0].startswith("Atualizada")


def test_opcao_no_menu_funcoes_da_producao() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    init = inspect.getsource(ProducaoPage.__init__)
    assert '"Gerar listas iMOS (ferragens)…", self' in init
    assert "self.gerar_listas_imos_action.setToolTip(" in init
    assert "self.gerar_listas_imos_action.triggered.connect(self._abrir_gerar_listas_imos)" in init
    assert "self.funcoes_menu.addAction(self.gerar_listas_imos_action)" in init
    # Depois de gerar, oferece-se a importação para a Lista Material.
    abrir = inspect.getsource(ProducaoPage._abrir_gerar_listas_imos)
    assert "find_lista_material_workbook" in abrir
    assert "self._importar_listas_ferragens(workbook_path)" in abrir
