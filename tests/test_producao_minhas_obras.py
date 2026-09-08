from types import SimpleNamespace
from PySide6.QtWidgets import QApplication, QComboBox, QCheckBox, QLabel
from app.ui.pages import producao_page as page


def test_shortcut_selects_current_responsible_and_clears(monkeypatch):
    app=QApplication.instance() or QApplication([])
    monkeypatch.setattr(page.app_session,'current_user',SimpleNamespace(nome='Paulo Catarino',username='paulo'))
    fake=SimpleNamespace(responsavel_combo=QComboBox(),minhas_check=QCheckBox(),status_label=QLabel())
    fake.responsavel_combo.addItems(['Todos','Andreia','Paulo'])
    fake._meu_responsavel=lambda: page.ProducaoPage._meu_responsavel(fake)
    page.ProducaoPage._filtrar_minhas_obras(fake,True)
    assert fake.responsavel_combo.currentText()=='Paulo'
    page.ProducaoPage._filtrar_minhas_obras(fake,False)
    assert fake.responsavel_combo.currentText()=='Todos'
    monkeypatch.setattr(page.app_session,'current_user',SimpleNamespace(nome='Desconhecido',username='x'))
    page.ProducaoPage._filtrar_minhas_obras(fake,True)
    assert fake.responsavel_combo.currentText()=='Todos'
    assert 'Não foi encontrado' in fake.status_label.text()
