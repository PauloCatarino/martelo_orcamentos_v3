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


def _abrir(monkeypatch, tmp_path, *, procurar=None, **extra) -> GerarListasImosDialog:
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
        **extra,
    )
    dialogo._atualizar()
    return dialogo


def _xlsx(caminho: Path) -> Path:
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("docProps/core.xml", "<cp:coreProperties xmlns:cp=\"x\"></cp:coreProperties>")
    return caminho


def test_mostra_a_ultima_gravacao_e_o_resumo_vem_desmarcado(monkeypatch, tmp_path) -> None:
    dialogo = _abrir(monkeypatch, tmp_path)

    assert dialogo.gravacao_label.text() == "22-09-2026 12:25:30"
    assert "ID 7667" in dialogo.encomenda_label.text()
    assert [dialogo.tabela.item(i, 0).text() for i in range(4)] == [l.chave for l in svc.LISTAS_IMOS]
    # O 3_Resumo_Precos vai ser descontinuado: vem desmarcado (29-09-2026).
    assert [l.chave for l in dialogo._listas_marcadas()] == [
        "2_List_Ferragens",
        "4_Etiqueta_Palete",
        "5_Custo_Obra_Ferragens",
    ]
    assert dialogo.gerar_button.isEnabled()
    assert "As listas marcadas ainda não estão na pasta da obra" in dialogo.status_label.text()


def test_o_supervisor_so_fala_das_listas_marcadas(monkeypatch, tmp_path) -> None:
    """O Resumo desatualizado não pede para ser gerado enquanto está desmarcado."""
    enc_antiga = svc.EncomendaImos(1, "X", datetime(2026, 9, 20, 9, 0))
    for chave in ("2_List_Ferragens", "3_Resumo_Precos", "4_Etiqueta_Palete", "5_Custo_Obra_Ferragens"):
        livro = _xlsx(tmp_path / f"{chave}.xlsx")
        encomenda = enc_antiga if chave == "3_Resumo_Precos" else svc.EncomendaImos(1, "X", GRAVACAO)
        svc.marcar_origem(livro, svc.texto_marca(encomenda))
    dialogo = _abrir(monkeypatch, tmp_path)

    assert "saíram da última gravação" in dialogo.status_label.text()
    dialogo.tabela.item(1, 0).setCheckState(Qt.CheckState.Checked)
    assert "3_Resumo_Precos" in dialogo.status_label.text()
    dialogo.tabela.item(1, 0).setCheckState(Qt.CheckState.Unchecked)
    assert "saíram da última gravação" in dialogo.status_label.text()


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
    assert len(dialogo._listas_marcadas()) == 4
    dialogo._marcar_todas()
    assert dialogo._listas_marcadas() == []
    assert "Marque as listas a gerar" in dialogo.status_label.text()


def test_sem_listas_marcadas_nao_gera(monkeypatch, tmp_path) -> None:
    dialogo = _abrir(monkeypatch, tmp_path)
    dialogo._marcar_todas()
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
    assert "self._importar_listas_ferragens(workbook_path)" in abrir


# ---- botão «Importar para a Lista Material» --------------------------------


def test_importar_sem_gerar_nada(monkeypatch, tmp_path) -> None:
    """Serve também para as listas geradas no iMos: não é preciso gerar primeiro."""
    chamadas: list[str] = []
    dialogo = _abrir(monkeypatch, tmp_path, importar=lambda: chamadas.append("importar") or True)

    assert dialogo.importar_button.isEnabled()
    assert not dialogo.importar_button.isHidden()
    dialogo.importar_button.click()

    assert chamadas == ["importar"]
    assert dialogo.importou
    assert dialogo.listas_geradas == 0
    assert "Listas importadas para a Lista Material" in dialogo.status_label.text()
    assert dialogo.gerar_button.isEnabled() and dialogo.fechar_button.isEnabled()


def test_importacao_falhada_diz_que_nao_ficou_feita(monkeypatch, tmp_path) -> None:
    dialogo = _abrir(monkeypatch, tmp_path, importar=lambda: False)
    dialogo.importar_button.click()

    assert not dialogo.importou
    assert "não foi concluída" in dialogo.status_label.text()


def test_sem_lista_material_o_botao_explica_porque(monkeypatch, tmp_path) -> None:
    dialogo = _abrir(monkeypatch, tmp_path, importar_indisponivel="Ainda não há Lista Material nesta obra.")

    assert not dialogo.importar_button.isEnabled()
    assert dialogo.importar_button.toolTip() == "Ainda não há Lista Material nesta obra."


def test_no_passo_3_o_botao_nao_aparece(monkeypatch, tmp_path) -> None:
    """No passo 3 importa-se ao fechar; o botão duplicava a importação."""
    dialogo = _abrir(monkeypatch, tmp_path, depois_importa=True, importar=lambda: True)
    assert dialogo.importar_button.isHidden()


def test_producao_passa_a_lista_material_a_janela() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    gerar = inspect.getsource(ProducaoPage._gerar_listas_imos)
    assert "find_lista_material_workbook(Path(pasta), nome_enc_imos=nome_enc)" in gerar
    assert "return self._importar_listas_ferragens(livro)" in gerar
    assert "importar=importar," in gerar
    assert "if not depois_importa:" in gerar
    abrir = inspect.getsource(ProducaoPage._abrir_gerar_listas_imos)
    # Já importou pela janela: não se volta a perguntar.
    assert abrir.index("if dialog.importou:") < abrir.index("QMessageBox.question(")
