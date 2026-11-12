"""O Excel do Martelo fecha sem perguntar «Guardar alterações no Livro2?» (12-11-2026)."""
from pathlib import Path

from app.services import lista_material_excel_com as excel_com


class _Livro:
    def __init__(self, nome, fechados):
        self.nome = nome
        self.fechados = fechados

    def Close(self, gravar):
        self.fechados.append((self.nome, gravar))


class _Livros:
    def __init__(self, livros):
        self.livros = livros

    @property
    def Count(self):
        return len(self.livros)

    def Item(self, indice):
        return self.livros[indice - 1]


class _Excel:
    def __init__(self):
        self.fechados = []
        self.DisplayAlerts = True
        self.Workbooks = _Livros([_Livro("Livro1", self.fechados), _Livro("Livro2", self.fechados)])
        self.saiu = False

    def Quit(self):
        assert self.DisplayAlerts is False
        self.saiu = True


def test_fechar_excel_fecha_os_livros_sem_gravar_e_sem_perguntar():
    excel = _Excel()
    excel_com.fechar_excel(excel)
    assert excel.DisplayAlerts is False
    assert excel.fechados == [("Livro2", False), ("Livro1", False)]
    assert excel.saiu


def test_fechar_excel_aguenta_none():
    excel_com.fechar_excel(None)


def test_a_lista_material_visivel_usa_o_fechar_excel():
    raiz = Path(__file__).resolve().parents[1] / "app" / "services"
    imos = (raiz / "lista_material_imos_service.py").read_text(encoding="utf-8")
    analise = (raiz / "analise_lista_material_service.py").read_text(encoding="utf-8")
    assert "excel_com.fechar_excel(excel)" in imos
    assert "excel_com.fechar_excel(excel)" in analise
