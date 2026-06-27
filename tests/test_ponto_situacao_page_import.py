"""Import checks for the production dashboard page."""

from __future__ import annotations

import inspect


def test_ponto_situacao_page_imports_and_uses_charts() -> None:
    from app.ui.pages.ponto_situacao_page import PontoSituacaoPage

    source = inspect.getsource(PontoSituacaoPage)

    assert "BarraCabecalho" in source
    assert "CampoPesquisa" in source
    assert "calcular_dashboard" in source
    assert "QPieSeries" in source
    assert "QBarSeries" in source
    assert "QHorizontalBarSeries" in source
    assert "QTableWidget" in source
    assert "QPdfWriter" in source
    assert "QFileDialog" in source
    assert "_ClickableFrame" in inspect.getsource(
        __import__(
            "app.ui.pages.ponto_situacao_page",
            fromlist=["_ClickableFrame"],
        )._ClickableFrame
    )
    assert '"Atualizar"' in source
    assert '"Exportar PDF"' in source
    assert '"Obras atrasadas"' in source
    assert "ensureWidgetVisible" in source
    assert "self.utilizador_combo" in source
    assert "self.cliente_combo" in source
    assert "self.estado_combo" in source
