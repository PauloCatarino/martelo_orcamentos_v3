"""Import checks for the production page."""

from __future__ import annotations

import inspect


def test_producao_page_imports_and_headers() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    assert ProducaoPage.TABLE_HEADERS == [
        "Criada em",
        "Ano",
        "Estado",
        "Responsável",
        "Processo",
        "Nº Enc PHC",
        "V. Obra",
        "V. CutRite",
        "Cliente",
        "Ref Cliente",
        "Obra",
        "Data Início",
        "Data Entrega",
        "Qt Artigos",
        "Preço",
        "Descrição Produção",
        "Localização",
        "Tipo Pasta",
    ]


def test_producao_page_init_uses_expected_widgets() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    init_source = inspect.getsource(ProducaoPage.__init__)

    assert "BarraCabecalho" in init_source
    assert "CampoPesquisa" in init_source
    assert "self.table" in init_source
    assert "Data em que a obra foi criada nesta lista" in init_source
    assert "COLUNAS_PRODUCAO" in inspect.getsource(ProducaoPage)
    # O botão "Colunas" foi substituído pelo menu do botão direito no cabeçalho.
    assert '"Colunas"' not in init_source
    assert "customContextMenuRequested.connect(self._abrir_menu_colunas)" in init_source
    assert "Clique com o botão direito para escolher as colunas visíveis" in init_source
    assert "sectionResized" in init_source
    assert '"⟳ Atualizar dados V2"' in init_source
    assert "self.atualizar_v2_button.clicked.connect(self._atualizar_dados_v2)" in init_source
    assert "self.obras_ano_label" in init_source
    assert "ligar_persistencia_larguras" not in inspect.getsource(ProducaoPage)
    assert '"Atualizar"' in init_source
    assert '"Salvar"' in init_source
    assert '"Pastas"' in init_source
    assert "Ver as pastas do processo selecionado no servidor" in init_source
    assert '"Abrir pasta"' in init_source
    assert "Abrir a pasta desta obra no explorador" in init_source
    assert '"Nova Versão"' in init_source
    assert "Criar nova versão de obra/CUT-RITE do processo selecionado" in init_source
    assert '"Lista Material_IMOS"' in init_source
    assert "self.lista_material_button" in init_source
    assert 'self.lista_material_button.setIcon(icone_ficheiro("icon_excel.ico"))' in init_source
    assert "self.lista_material_button.clicked.connect(self._lista_material_imos)" in init_source
    assert "Gerar o Excel 'Lista Material_IMOS' na pasta do processo" in init_source
    assert '"Enviar CUT-RITE"' in init_source
    assert "self.enviar_cutrite_button" in init_source
    assert 'self.enviar_cutrite_button.setIcon(icone_ficheiro("icon_cut_rite.ico"))' in init_source
    assert "self.enviar_cutrite_button.clicked.connect(self._enviar_cutrite)" in init_source
    assert "Criar o plano de corte no CUT-RITE a partir da Lista Material" in init_source
    assert '"Exportar Resumo (PDF)"' in init_source
    assert "self.exportar_resumo_pdf_button" in init_source
    assert 'self.exportar_resumo_pdf_button.setIcon(icone_ficheiro("icon_pdf_cut_rite.ico"))' in init_source
    assert "self.exportar_resumo_pdf_button.clicked.connect(self._exportar_resumo_pdf)" in init_source
    assert "Exportar para PDF o resumo do plano de corte" in init_source
    assert '"Eliminar"' in init_source
    assert "Eliminar obra: registo e/ou pasta no servidor" in init_source
    assert "cellDoubleClicked.connect(self._handle_table_double_click)" in init_source
    assert "setToolTip" in init_source
    assert "Gravar as alterações da obra selecionada" in init_source
    assert "Recarregar a lista de obras" in init_source
    assert "Converter Orçamento" in init_source
    assert "Converter um orçamento adjudicado numa obra de produção" in init_source
    assert "Novo Processo" in init_source
    assert "self.novo_processo_button" in init_source
    assert "self.novo_processo_button.clicked.connect(self._novo_processo)" in init_source
    assert "Criar uma obra a partir de uma encomenda do PHC" in init_source
    assert "SelecionarClienteDialog" not in inspect.getsource(ProducaoPage)
    assert "QCalendarWidget" in inspect.getsource(ProducaoPage)
    assert "QSplitter" in init_source
    assert 'ligar_persistencia_splitter(self.splitter, "producao")' in init_source


def test_producao_page_detail_editing_hooks() -> None:
    from app.ui.pages.producao_page import ProducaoPage
    import app.ui.pages.producao_page as producao_page
    import app.ui.helpers.colunas_producao as colunas_producao

    source = inspect.getsource(ProducaoPage)
    module_source = inspect.getsource(producao_page)
    helper_source = inspect.getsource(colunas_producao)

    assert hasattr(ProducaoPage, "_fill_form")
    assert hasattr(ProducaoPage, "_collect_form")
    assert hasattr(ProducaoPage, "_on_select_row")
    assert hasattr(ProducaoPage, "_save")
    assert "app_session" in source
    assert "carregar_config" in source
    assert "guardar_config" in source
    assert "SystemSettingService" in helper_source
    assert "itemSelectionChanged" in source
    assert "converter_orcamento" in source
    assert "criar_processo_externo" in source
    assert "NovoProcessoDialog" in source
    assert "listar_processos_por_encomenda" in source
    assert "responsavel=responsavel" in source
    assert "partes_nome[0]" in source
    assert '(current_user.nome or "").split()' in source
    assert "pasta_servidor = processo.pasta_servidor" in source
    assert "QMessageBox.information" in source
    assert "Pasta criada no servidor" in source
    assert "falha ao criar a pasta no servidor" in source
    assert "PastasProcessoDialog" in source
    assert "arvore_pastas_processo" in source
    assert "NovaVersaoProcessoDialog" in source
    assert "preparar_nova_versao" in source
    assert "criar_nova_versao" in source
    assert "prepare_lista_material_imos" in source
    assert "execute_lista_material_imos" in source
    assert "prepare_cutrite_import" in module_source
    assert "execute_cutrite_import" in module_source
    assert "prepare_cutrite_resumo_pdf" in module_source
    assert "execute_cutrite_resumo_pdf" in module_source
    assert "_CutRitePdfWorker" in module_source
    assert "pythoncom.CoInitialize()" in module_source
    assert "QThread" in module_source
    assert "CutRiteProgressDialog" in module_source
    assert hasattr(ProducaoPage, "_enviar_cutrite")
    assert hasattr(ProducaoPage, "_cutrite_concluido")
    assert hasattr(ProducaoPage, "_cutrite_falhou")
    assert hasattr(ProducaoPage, "_finalizar_cutrite")
    assert hasattr(ProducaoPage, "_exportar_resumo_pdf")
    assert hasattr(ProducaoPage, "_resumo_pdf_concluido")
    assert hasattr(ProducaoPage, "_resumo_pdf_falhou")
    assert hasattr(ProducaoPage, "_finalizar_resumo_pdf")
    assert "eliminar_processo_completo" in source
    assert "preview_conteudo_pasta" in source
    assert hasattr(ProducaoPage, "_eliminar_processo")
    assert hasattr(ProducaoPage, "_novo_processo")
    assert hasattr(ProducaoPage, "_tratar_encomenda_existente")
    assert hasattr(ProducaoPage, "_executar_nova_versao")
    assert hasattr(ProducaoPage, "_lista_material_imos")
    assert hasattr(ProducaoPage, "_abrir_pasta_versao_selecionada")
    assert "QApplication.setOverrideCursor" in source
    assert "QApplication.restoreOverrideCursor" in source
    assert "Lista Material IMOS" in source
    assert "Lista Material_IMOS" in source
    assert "context.output_path.exists()" in source
    assert "DATA_CONCLUSAO" in source
    assert "NOME_ENC_IMOS_IX" in source
    assert "QDesktopServices.openUrl" in source
    assert "O Excel da Lista Material da obra" in source
    assert "Pretende abrir?" in source
    assert "QUrl.fromLocalFile(str(context.output_path))" in source
    assert "Substituir?" not in inspect.getsource(ProducaoPage._lista_material_imos)
    assert "Pasta ainda não criada" in source
    assert "nome_plano_corte_input" in source
    assert "nome_enc_imos_ix_input" in source
    assert "gerar_nome_plano_cut_rite" in source
    assert "gerar_nome_enc_imos_ix" in source
    assert "codigo_processo_com_cliente" in source
    assert "_atualizar_campos_derivados" in source
    assert "_selecionar_cliente" not in source
    assert "apenas_phc=True" not in source
    assert "cliente_picker" not in source
    assert "self.cliente_input = self._readonly_line()" in source
    assert "self.cliente_simplex_input = self._readonly_line()" in source
    assert "self.num_cliente_phc_input = self._readonly_line()" in source
    assert "Cliente original do processo (fixo)" in source
    assert "_abrir_calendario_data" in source
    assert "Data Início no formato dd-mm-aaaa" in source
    assert "codigo_processo" in source
    assert "icone_ficheiro" in source
    assert '"icon_cut_rite.ico"' in source
    assert '"icon_imos_2025.ico"' in source
    assert "QStyle.StandardPixmap.SP_DirOpenIcon" in source
    assert "item.setIcon" in source
    assert "Ver pastas do processo" in source
    assert "normalizar_data" in source
    assert "imagem_path" in source
    assert "resolver_imagem_imos" in source
    assert "_mostrar_imagem_obra" in source
    assert "QStackedWidget" in source
    assert "QTreeView" in source
    assert "QFileSystemModel" in source
    assert "_abrir_item_arvore" in source
    assert "self.imagem_stack.setCurrentWidget(self.imagem_preview)" in source
    assert "self.imagem_stack.setCurrentWidget(self.arvore_pasta)" in source
    assert "Sem imagem IMOS (sem pasta da obra)" in source
    assert "QFileDialog" not in source
    assert "Escolher Imagem/PDF..." not in source
    assert "Limpar Imagem" not in source
    assert "self._imagem_path" in source
    assert "Data no formato dd-mm-aaaa" in source
    assert "Estado da obra em produção" in source
    assert "Pasta de destino no servidor" in source
    assert "Há alterações por gravar. Descartar?" in source
    assert producao_page.TIPOS_PASTA_PRODUCAO == (
        "Encomenda de Cliente",
        "Encomenda de Cliente Final",
    )


def test_producao_page_layout_detalhe_e_menu_colunas() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    source = inspect.getsource(ProducaoPage)

    # Colunas via menu do botão direito, guardadas por utilizador.
    assert hasattr(ProducaoPage, "_abrir_menu_colunas")
    assert hasattr(ProducaoPage, "_alternar_coluna")
    assert hasattr(ProducaoPage, "_mostrar_todas_colunas")
    assert hasattr(ProducaoPage, "_repor_colunas_default")
    assert "ColunasProducaoDialog" not in source
    assert "Mostrar todas" in source
    assert "Repor colunas por defeito" in source

    # Textos em 2 linhas x 3 colunas.
    detalhe_source = inspect.getsource(ProducaoPage._criar_painel_detalhe)
    assert "row = (index // 3) * 2" in detalhe_source
    assert "col = index % 3" in detalhe_source

    # Imagem maior e campo com a pasta da obra.
    imagem_source = inspect.getsource(ProducaoPage._criar_painel_imagem)
    assert "setFixedSize(460, 330)" in imagem_source
    assert hasattr(ProducaoPage, "_criar_campo_pasta_obra")
    assert hasattr(ProducaoPage, "_copiar_caminho_pasta")
    assert hasattr(ProducaoPage, "_atualizar_campo_pasta_obra")
    assert "QApplication.clipboard().setText(caminho)" in source
    assert "caminho_versao_de_processo" in source

    # Botão temporário de sincronização com o V2.
    assert hasattr(ProducaoPage, "_atualizar_dados_v2")
    assert "comparar_v2_com_v3" in source
    assert "ProducaoV2SyncDialog" in source
    assert "aplicar_selecao" in source

    # Contador de obras do ano atual.
    contador_source = inspect.getsource(ProducaoPage._atualizar_contador_obras_ano)
    assert "QDate.currentDate().year()" in contador_source
    assert "self._combo_valor(self.responsavel_combo)" in contador_source


def test_producao_page_abre_pastas_no_duplo_clique_do_processo() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    double_click_source = inspect.getsource(ProducaoPage._handle_table_double_click)
    open_source = inspect.getsource(ProducaoPage._abrir_pastas_processo)

    assert 'COLUNAS_PRODUCAO[column].key != "processo"' in double_click_source
    assert "self._abrir_pastas_processo(processo)" in double_click_source
    assert "ano=processo.ano" in open_source
    assert "num_enc_phc=processo.num_enc_phc" in open_source
    assert "tipo_pasta=processo.tipo_pasta" in open_source
    assert "dialog.exec()" in open_source


def test_tratar_encomenda_existente_chama_nova_versao_da_mais_recente(monkeypatch) -> None:
    import app.ui.pages.producao_page as page_module
    from app.ui.pages.producao_page import ProducaoPage

    class FakeButton:
        pass

    nova_versao_button = FakeButton()
    chamadas: dict[str, object] = {}

    class FakeMessageBox:
        Icon = page_module.QMessageBox.Icon
        ButtonRole = page_module.QMessageBox.ButtonRole

        def __init__(self, parent=None):
            chamadas["parent"] = parent

        def setIcon(self, icon):
            chamadas["icon"] = icon

        def setWindowTitle(self, title):
            chamadas["title"] = title

        def setText(self, text):
            chamadas["text"] = text

        def setInformativeText(self, text):
            chamadas["informative"] = text

        def addButton(self, text, role):
            chamadas.setdefault("buttons", []).append((text, role))
            if text == "Nova Versão":
                return nova_versao_button
            return FakeButton()

        def exec(self):
            chamadas["exec"] = True

        def clickedButton(self):
            return nova_versao_button

    monkeypatch.setattr(page_module, "QMessageBox", FakeMessageBox)

    page = type("PageStub", (), {})()
    executadas: list[int] = []
    page._executar_nova_versao = lambda *, processo_id: executadas.append(processo_id)

    ProducaoPage._tratar_encomenda_existente(
        page,
        {"ano": "2026", "num_enc_phc": "1134"},
        [
            {
                "id": 1,
                "codigo": "26.1134_01_01_CLIENTE",
                "estado": "Desenho",
                "versao_obra": "01",
                "versao_plano": "01",
                "data_inicio": "25-06-2026",
                "data_entrega": "10-08-2026",
            },
            {
                "id": 2,
                "codigo": "26.1134_02_01_CLIENTE",
                "estado": "Desenho",
                "versao_obra": "02",
                "versao_plano": "01",
                "data_inicio": "25-06-2026",
                "data_entrega": "10-08-2026",
            },
        ],
    )

    assert chamadas["title"] == "Encomenda já existe"
    assert "26.1134_01_01_CLIENTE" in chamadas["informative"]
    assert "Nova Versão" in [text for text, _role in chamadas["buttons"]]
    assert executadas == [2]
