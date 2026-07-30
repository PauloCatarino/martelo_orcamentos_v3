"""Import checks for the Clientes page."""

from __future__ import annotations


def test_clientes_page_imports() -> None:
    from app.ui.pages.clientes_page import ClientesPage

    assert ClientesPage is not None


def test_separador_phc_sem_texto_desatualizado() -> None:
    import inspect
    from app.ui.pages.clientes_page import ClientesPage

    fonte = inspect.getsource(ClientesPage._criar_tab_phc)
    assert "fase futura" not in fonte
    assert "Atualizar PHC" in fonte


def test_duplo_clique_abre_a_ficha_do_cliente() -> None:
    import inspect

    from app.ui.pages.clientes_page import ClientesPage

    fonte = inspect.getsource(ClientesPage)
    assert "ClienteDetalheDialog" in fonte
    assert "itemDoubleClicked.connect(self._abrir_ficha_phc)" in fonte
    assert "itemDoubleClicked.connect(self._abrir_ficha_temporario)" in fonte
    # A edição direta na célula foi substituída pela ficha.
    assert "EditTrigger.DoubleClicked" not in fonte


def test_realce_do_rato_ligado_nas_listas() -> None:
    import inspect

    from app.ui.pages.clientes_page import ClientesPage

    fonte = inspect.getsource(ClientesPage._nova_tabela_clientes)
    assert "RealceRatoDelegate" in fonte
    assert "setMouseTracking(True)" in fonte


def test_colunas_de_email_de_envio_existem() -> None:
    from app.ui.pages.clientes_page import ClientesPage

    cabecalhos = ClientesPage.TABLE_HEADERS
    assert "Email envio orçamentos" in cabecalhos
    assert "Email envio projeto produção" in cabecalhos
    assert cabecalhos[ClientesPage.COL_EMAIL_ORCAMENTOS] == "Email envio orçamentos"
    assert (
        cabecalhos[ClientesPage.COL_EMAIL_PROJETO] == "Email envio projeto produção"
    )
    # Todas as colunas têm largura definida (senão ficam esmagadas).
    assert set(cabecalhos) == set(ClientesPage.COLUMN_WIDTHS)


def test_email_do_orcamento_usa_a_coluna_configurada() -> None:
    import inspect

    from app.ui.pages import orcamento_relatorios_page

    fonte = inspect.getsource(orcamento_relatorios_page)
    assert "emails_envio_orcamentos(cliente)" in fonte
    assert 'destinatario=getattr(cliente, "email"' not in fonte
