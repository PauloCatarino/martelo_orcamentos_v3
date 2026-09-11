from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QLabel

from app.ui.pages import orcamentos_page as page


def test_atalho_meus_orcamentos(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(page.app_session, "current_user",
                        SimpleNamespace(id=7, nome="Paulo Catarino", username="paulo"))
    fake = SimpleNamespace(utilizador_combo=QComboBox(), minhas_check=QCheckBox(),
                           status_label=QLabel(), _todos=[SimpleNamespace(utilizador_id=7, utilizador="Paulo")])
    fake.utilizador_combo.addItems(["Todos", "Andreia", "Paulo"])
    fake._meu_utilizador = lambda: page.OrcamentosPage._meu_utilizador(fake)
    page.OrcamentosPage._filtrar_meus_orcamentos(fake, True)
    assert fake.utilizador_combo.currentText() == "Paulo"
    page.OrcamentosPage._filtrar_meus_orcamentos(fake, False)
    assert fake.utilizador_combo.currentText() == "Todos"
    monkeypatch.setattr(page.app_session, "current_user", None)
    page.OrcamentosPage._filtrar_meus_orcamentos(fake, True)
    assert not fake.minhas_check.isChecked()
    assert "Não foi encontrado" in fake.status_label.text()
