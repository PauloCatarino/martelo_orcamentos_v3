"""Import checks for the production page."""

from __future__ import annotations

import inspect


def test_producao_page_imports_and_headers() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    assert ProducaoPage.TABLE_HEADERS == [
        "Ano",
        "Processo",
        "Estado",
        "Cliente",
        "Ref Cliente",
        "Obra",
        "Localização",
        "Nº Enc PHC",
        "V. Obra",
        "V. CutRite",
        "Data Início",
        "Data Entrega",
        "Responsável",
        "Tipo Pasta",
    ]


def test_producao_page_init_uses_expected_widgets() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    init_source = inspect.getsource(ProducaoPage.__init__)

    assert "BarraCabecalho" in init_source
    assert "CampoPesquisa" in init_source
    assert "self.table" in init_source
    assert "ligar_persistencia_larguras" in init_source
    assert '"Atualizar"' in init_source
    assert '"Salvar"' in init_source
    assert "setToolTip" in init_source
    assert "Gravar as alterações da obra selecionada" in init_source
    assert "Recarregar a lista de obras" in init_source
    assert "Converter Orçamento" in init_source
    assert "Converter um orçamento adjudicado numa obra de produção" in init_source
    assert "QSplitter" in init_source
    assert 'ligar_persistencia_splitter(self.splitter, "producao")' in init_source
    assert '"Novo"' not in init_source


def test_producao_page_detail_editing_hooks() -> None:
    from app.ui.pages.producao_page import ProducaoPage
    import app.ui.pages.producao_page as producao_page

    source = inspect.getsource(ProducaoPage)

    assert hasattr(ProducaoPage, "_fill_form")
    assert hasattr(ProducaoPage, "_collect_form")
    assert hasattr(ProducaoPage, "_on_select_row")
    assert hasattr(ProducaoPage, "_save")
    assert "app_session" in source
    assert "itemSelectionChanged" in source
    assert "converter_orcamento" in source
    assert "normalizar_data" in source
    assert "imagem_path" in source
    assert "QFileDialog" in source
    assert "Escolher Imagem/PDF..." in source
    assert "Limpar Imagem" in source
    assert "self._imagem_path" in source
    assert "Data no formato dd-mm-aaaa" in source
    assert "Estado da obra em produção" in source
    assert "Pasta de destino no servidor" in source
    assert "Há alterações por gravar. Descartar?" in source
    assert producao_page.TIPOS_PASTA_PRODUCAO == (
        "Encomenda de Cliente",
        "Encomenda de Cliente Final",
    )
