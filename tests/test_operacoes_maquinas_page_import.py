"""Import checks for the Operacoes / Maquinas page."""

from __future__ import annotations

import inspect


def test_operacoes_maquinas_page_imports() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    assert OperacoesMaquinasPage is not None


def test_operacoes_maquinas_page_registered_in_pages() -> None:
    from app.ui.pages import OperacoesMaquinasPage

    assert OperacoesMaquinasPage is not None


def test_operacoes_headers() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    assert OperacoesMaquinasPage.OPERACOES_HEADERS == [
        "Código",
        "Nome",
        "Tipo",
        "Unidade cálculo",
        "Máquina",
        "Tempo base",
        "Tempo setup",
        "Custo/hora",
        "Custo mínimo",
        "Ativo",
    ]


def test_maquinas_headers() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    assert OperacoesMaquinasPage.MAQUINAS_HEADERS == [
        "Código",
        "Nome",
        "Tipo",
        "Custo/hora STD",
        "Custo/hora SERIE",
        "€/ML STD",
        "€/ML SERIE",
        "Permite rasgos",
        "€/ML rasgo STD",
        "€/ML rasgo SERIE",
        "€/lado STD",
        "€/lado SERIE",
        "Ativo",
    ]


def test_maquinas_page_tem_botao_escaloes() -> None:
    import inspect

    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    assert hasattr(OperacoesMaquinasPage, "abrir_escaloes_maquina")
    source = inspect.getsource(OperacoesMaquinasPage.abrir_escaloes_maquina)
    assert "EscaloesAreaDialog" in source


def test_operacoes_maquinas_page_loads_on_init() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    source_names = OperacoesMaquinasPage.__init__.__code__.co_names

    assert "carregar" in source_names
    assert "QTabWidget" in source_names
    assert "QCheckBox" in source_names


def test_operacoes_maquinas_page_uses_services() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    source = inspect.getsource(OperacoesMaquinasPage.carregar)

    assert "DefOperacaoService" in source
    assert "DefMaquinaService" in source
    assert "listar_operacoes" in source
    assert "listar_maquinas" in source


def test_operacoes_maquinas_page_filters_inactive_by_default() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    init_source = inspect.getsource(OperacoesMaquinasPage.__init__)
    carregar_source = inspect.getsource(OperacoesMaquinasPage.carregar)

    assert "mostrar_inativas_check" in init_source
    assert "Mostrar inativas" in init_source
    assert "not self.mostrar_inativas_check.isChecked()" in carregar_source
    assert "if operacao.ativo" in carregar_source
    assert "if maquina.ativo" in carregar_source


def test_operacoes_maquinas_page_has_expected_methods() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    for method in ("carregar", "_preencher_operacoes", "_preencher_maquinas"):
        assert hasattr(OperacoesMaquinasPage, method)


def test_operacoes_maquinas_page_has_machine_actions() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    for method in (
        "abrir_nova_maquina",
        "abrir_editar_maquina",
        "alternar_maquina_ativa",
        "_get_selected_maquina",
    ):
        assert hasattr(OperacoesMaquinasPage, method)


def test_operacoes_maquinas_page_machine_actions_use_service_and_dialog() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    nova = inspect.getsource(OperacoesMaquinasPage.abrir_nova_maquina)
    assert "MaquinaDialog" in nova
    assert "CriarDefMaquinaData" in nova

    editar = inspect.getsource(OperacoesMaquinasPage.abrir_editar_maquina)
    assert "EditarDefMaquinaData" in editar

    toggle = inspect.getsource(OperacoesMaquinasPage.alternar_maquina_ativa)
    assert "ativar_maquina" in toggle
    assert "desativar_maquina" in toggle
    assert "QMessageBox" in toggle


def test_operacoes_maquinas_page_has_operation_actions() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    for method in (
        "abrir_nova_operacao",
        "abrir_editar_operacao",
        "alternar_operacao_ativa",
        "_get_selected_operacao",
        "_carregar_maquinas_disponiveis",
    ):
        assert hasattr(OperacoesMaquinasPage, method)


def test_operacoes_maquinas_page_operation_actions_use_service_and_dialog() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    nova = inspect.getsource(OperacoesMaquinasPage.abrir_nova_operacao)
    assert "OperacaoDialog" in nova
    assert "CriarDefOperacaoData" in nova

    editar = inspect.getsource(OperacoesMaquinasPage.abrir_editar_operacao)
    assert "EditarDefOperacaoData" in editar

    toggle = inspect.getsource(OperacoesMaquinasPage.alternar_operacao_ativa)
    assert "ativar_operacao" in toggle
    assert "desativar_operacao" in toggle
    assert "QMessageBox" in toggle
