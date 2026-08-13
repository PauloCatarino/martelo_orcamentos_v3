"""Import checks for the budget ValueSet page."""

from __future__ import annotations

import inspect
from types import SimpleNamespace


def test_page_imports() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    assert OrcamentoValuesetPage is not None


def test_page_accepts_versao_id() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    signature = inspect.signature(OrcamentoValuesetPage)

    assert "orcamento_versao_id" in signature.parameters


def test_page_headers() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    assert OrcamentoValuesetPage.TABLE_HEADERS == [
        "Chave",
        "Opção",
        "Ref LE",
        "Descrição orçamento",
        "Unidade",
        "Preço tabela",
        "Margem %",
        "Desconto %",
        "Preço líquido",
        "Desp %",
        "Tipo",
        "Família",
        "Orla 0.4",
        "Orla 1.0",
        "Comp MP",
        "Larg MP",
        "Esp MP",
        "Prioridade",
        "Ordem",
        "Origem",
        "Editado localmente",
        "Ativo",
        "Operações",
    ]


def test_page_has_actions() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    for method in (
        "importar_modelo",
        "abrir_nova_linha",
        "abrir_editar_linha",
        "alternar_linha_ativa",
        "carregar",
        "_get_selected_linha",
        "_get_selected_linhas",
        "_handle_double_click",
    ):
        assert hasattr(OrcamentoValuesetPage, method)


def test_page_edit_uses_dialog_and_service() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    source = inspect.getsource(OrcamentoValuesetPage.abrir_editar_linha)

    assert "OrcamentoValuesetLinhaDialog" in source
    assert "editar_linha" in source
    assert "Linha ValueSet atualizada." in source


def test_page_cria_e_grava_como_opcao_local_transacional() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    init_source = inspect.getsource(OrcamentoValuesetPage.__init__)
    criar = inspect.getsource(OrcamentoValuesetPage._criar_linha_local)
    nova = inspect.getsource(OrcamentoValuesetPage.abrir_nova_linha)
    editar = inspect.getsource(OrcamentoValuesetPage.abrir_editar_linha)

    assert 'QPushButton("Nova Linha")' in init_source
    assert "CriarOrcamentoValuesetLinhaData" in criar
    assert "commit=False" in criar
    assert "copiar_operacoes_de" in criar
    assert "session.commit()" in criar
    assert 'origem_dados="EDITADO_LOCALMENTE"' in criar
    assert "editado_localmente=True" in criar
    assert "OrcamentoValuesetLinhaDialog" in nova
    assert "on_save_as=handle_save_as" in editar
    assert "prioridades_usadas" in criar


def test_criar_linha_local_orcamento_escolhe_prioridade_livre_e_copia_operacoes(
    monkeypatch,
) -> None:
    from app.ui.pages import orcamento_valueset_page as modulo

    registo = SimpleNamespace(criada=None, operacoes=None, commit=False)

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def commit(self):
            registo.commit = True

    class FakeService:
        def __init__(self, _session):
            pass

        def listar_por_chave(self, _versao_id, _chave):
            return [
                SimpleNamespace(ativo=True, prioridade=1, ordem=68),
                SimpleNamespace(ativo=True, prioridade=2, ordem=69),
            ]

        def criar_linha(self, data, *, commit=True):
            registo.criada = (data, commit)
            return SimpleNamespace(id=99, prioridade=data.prioridade)

    class FakeOperacoesService:
        def __init__(self, _session):
            pass

        def listar_operacoes_da_linha(self, linha_id):
            assert linha_id == 7
            return [SimpleNamespace(id=1)]

        def copiar_operacoes_de(self, operacoes, destino_id):
            registo.operacoes = (operacoes, destino_id)

    monkeypatch.setattr(modulo, "SessionLocal", FakeSession)
    monkeypatch.setattr(modulo, "OrcamentoValuesetLinhaService", FakeService)
    monkeypatch.setattr(
        modulo, "OrcamentoValuesetLinhaOperacaoService", FakeOperacoesService
    )
    form = SimpleNamespace(
        chave="MATERIAL_PECAS_SIMPLES",
        codigo_opcao="",
        nome_opcao="MDF local",
        prioridade=1,
        ref_materia_prima="PLC001",
        descricao_materia_prima="MDF local",
        valor_texto="MDF local",
        ref_le="PLC001",
        descricao_no_orcamento="MDF local",
        preco_tabela=None,
        margem_percentagem=None,
        desconto_percentagem=None,
        preco_liquido=None,
        unidade="M2",
        desperdicio_percentagem=None,
        tipo_materia_prima="MDF",
        familia_materia_prima="PLACAS",
        coresp_orla_0_4=None,
        coresp_orla_1_0=None,
        preco_orla_0_4_m2=None,
        preco_orla_1_0_m2=None,
        comp_mp=None,
        larg_mp=None,
        esp_mp=None,
        observacoes=None,
        ativo=True,
    )
    origem = SimpleNamespace(id=7, descricao=None, origem="MODELO")
    page = SimpleNamespace(orcamento_versao_id=20)

    result = modulo.OrcamentoValuesetPage._criar_linha_local(
        page, form, linha_origem=origem
    )

    data, commit_criar = registo.criada
    assert result.id == 99
    assert data.prioridade == 3
    assert data.ordem == 70
    assert data.origem_dados == "EDITADO_LOCALMENTE"
    assert data.origem_modelo_id is None
    assert data.editado_localmente is True
    assert commit_criar is False
    assert registo.operacoes[1] == 99
    assert registo.commit is True


def test_page_uses_service_and_dialog() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    importar = inspect.getsource(OrcamentoValuesetPage.importar_modelo)
    assert "ImportarValuesetModeloDialog" in importar
    assert "_perguntar_modo_importacao_modelo" in importar
    assert "_verificar_precos_apos_importacao" in importar
    assert "importar_modelo_para_orcamento" in importar
    assert "substituir=substituir" in importar

    carregar = inspect.getsource(OrcamentoValuesetPage.carregar)
    assert "OrcamentoValuesetLinhaService" in carregar
    assert "listar_linhas_da_versao" in carregar


def test_page_import_modelo_pergunta_substituir_ou_atualizar() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    pergunta = inspect.getsource(OrcamentoValuesetPage._perguntar_modo_importacao_modelo)

    assert "Substituir tudo" in pergunta
    assert "Atualizar" in pergunta
    assert "Cancelar" in pergunta
    assert "DestructiveRole" in pergunta


def test_page_import_modelo_verifica_precos_explicitamente() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    verificar = inspect.getsource(OrcamentoValuesetPage._verificar_precos_apos_importacao)
    assert "AtualizarPrecosValuesetDialog" in verificar
    assert "detetar_divergencias_valueset" in verificar
    assert "atualizar_precos_linhas" in verificar
    assert "atualizar_modelo_origem_por_divergencias" in verificar


def test_page_formats_percentages() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    source = inspect.getsource(OrcamentoValuesetPage._preencher)

    assert "formatar_percentagem" in source
    assert "preparar_linhas_valueset" in source
    assert "aplicar_estilo_item_valueset" in source
    assert "texto_chave_valueset" in source


def test_page_valueset_visual_helper_e_menu_colunas() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    init = inspect.getsource(OrcamentoValuesetPage.__init__)

    assert "setAlternatingRowColors(False)" in init
    assert "configurar_tabela_valueset" in init
    assert '"valueset_orcamento"' in init


def test_page_has_snapshot_tools() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    for method in ("copiar_dados", "colar_dados", "limpar_dados", "_abrir_menu_contexto"):
        assert hasattr(OrcamentoValuesetPage, method)

    copiar = inspect.getsource(OrcamentoValuesetPage.copiar_dados)
    assert "copiar_snapshot_linha" in copiar
    assert "Dados da linha copiados." in copiar

    colar = inspect.getsource(OrcamentoValuesetPage.colar_dados)
    assert "aplicar_snapshot_linha" in colar
    assert "Não existem dados copiados." in colar

    limpar = inspect.getsource(OrcamentoValuesetPage.limpar_dados)
    assert "limpar_snapshot_linha" in limpar
    assert "Tem a certeza" in limpar
    assert "_get_selected_linhas" in limpar
    assert "commit=False" in limpar
    assert "Dados limpos em" in limpar


def test_page_uses_multi_selection_for_batch_actions() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    init = inspect.getsource(OrcamentoValuesetPage.__init__)
    assert "ExtendedSelection" in init

    selected = inspect.getsource(OrcamentoValuesetPage._get_selected_linhas)
    assert "selectedRows()" in selected
    assert "seen_rows" in selected

    toggle = inspect.getsource(OrcamentoValuesetPage.alternar_linha_ativa)
    assert "_get_selected_linhas" in toggle
    assert "commit=False" in toggle
    assert "Estado atualizado em" in toggle


def test_page_carrega_coluna_operacoes() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    carregar = inspect.getsource(OrcamentoValuesetPage.carregar)
    assert "OrcamentoValuesetLinhaOperacaoService" in carregar
    assert "_operacoes_por_linha" in carregar

    preencher = inspect.getsource(OrcamentoValuesetPage._preencher)
    assert "_operacoes_por_linha" in preencher


def test_page_edit_lida_com_operacoes_alteradas() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    editar = inspect.getsource(OrcamentoValuesetPage.abrir_editar_linha)
    assert "dialog.operacoes_alteradas" in editar
    assert "Operações da linha atualizadas." in editar


def test_page_copiar_colar_com_operacoes_opt_in() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    copiar = inspect.getsource(OrcamentoValuesetPage.copiar_dados)
    assert "OrcamentoValuesetLinhaOperacaoService" in copiar
    assert "_copied_operacoes" in copiar

    colar = inspect.getsource(OrcamentoValuesetPage.colar_dados)
    assert "_copied_operacoes" in colar
    assert "copiar_operacoes_de" in colar
    assert "commit=False" in colar
    assert "avisar_prioridade_repetida_apos_colagem" in colar
    assert "Colar também" in colar
    assert "Dados e operações colados" in colar


def test_page_colunas_redimensionaveis_com_seed() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    init = inspect.getsource(OrcamentoValuesetPage.__init__)
    assert "QHeaderView.ResizeMode.Interactive" in init
    assert "setStretchLastSection(False)" in init
    assert '"valueset_orcamento"' in init

    preencher = inspect.getsource(OrcamentoValuesetPage._preencher)
    assert "resizeColumnsToContents" in preencher
    assert "_larguras_iniciais_aplicadas" in preencher
