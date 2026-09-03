"""Raw materials catalog page."""

from __future__ import annotations

import re
import unicodedata

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.materia_prima_types import (
    MESES_PRECO_DESATUALIZADO,
    TIPO_PRECO_LIVRE,
    preco_desatualizado,
    preco_em_falta,
)
from app.domain.numeros import formatar_percentagem, normalize_percentagem_humana
from app.repositories.def_materia_prima_repository import DefMateriaPrimaResumo
from app.services.def_materia_prima_service import DefMateriaPrimaService
from app.ui import tema
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.colunas_visiveis import ligar_menu_colunas
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency, format_quantity


class MateriasPrimasPage(QWidget):
    """Page for listing imported raw materials."""

    TABLE_HEADERS = [
        "Ref LE",
        "Descrição",
        "Tipo Excel",
        "Família Excel",
        "Unidade",
        "Tipo preço",
        "Preço tabela",
        "Desc %",
        "Mrg %",
        "Desp %",
        "Preço Líquido",
        "Último preço",
        "Stock",
        "Fornecedor",
        "Ref. fornecedor",
        "Fabricante",
        "Cor",
        "Ref. PHC",
        "Link",
        "Orla 0.4",
        "Orla 1.0",
        "Comp MP",
        "Larg MP",
        "Esp MP",
        "Observações",
        "Criado por",
        "Alterado por",
        "Ativo",
    ]

    #: Colunas escondidas até alguém as pedir no botão "Colunas...".
    #: Cada utilizador guarda a sua escolha, por isso isto é só o ponto de partida.
    COLUNAS_OCULTAS_POR_DEFEITO = (
        "Tipo preço",
        "Preço tabela",
        "Desc %",
        "Mrg %",
        "Ref. fornecedor",
        "Fabricante",
        "Cor",
        "Ref. PHC",
        "Observações",
        "Criado por",
        "Alterado por",
    )

    #: Colunas que levam as cores dos avisos (preço em falta / preço antigo).
    COLUNA_PRECO_LIQUIDO = TABLE_HEADERS.index("Preço Líquido")
    COLUNA_ULTIMO_PRECO = TABLE_HEADERS.index("Último preço")

    def __init__(self) -> None:
        super().__init__()

        self._materias_primas: list[DefMateriaPrimaResumo] = []

        self.cabecalho = BarraCabecalho(
            "Mat\u00e9rias-Primas",
            [
                "Cat\u00e1logo de mat\u00e9rias-primas do Martelo: \u00e9 aqui que se inserem, "
                "alteram e descontinuam os materiais que alimentam o custeio dos "
                "or\u00e7amentos. Descontinuar n\u00e3o mexe nos or\u00e7amentos j\u00e1 feitos."
            ],
        )

        self.refresh_button = QPushButton("Atualizar Página")
        self.refresh_button.clicked.connect(self.carregar_materias_primas)
        self.refresh_button.setToolTip("Recarregar as matérias-primas importadas")

        self.novo_button = QPushButton("+ Nova matéria-prima")
        self.novo_button.clicked.connect(self.nova_materia_prima)
        self.novo_button.setToolTip("Criar uma matéria-prima nova no Martelo")

        self.editar_button = QPushButton("Editar")
        self.editar_button.clicked.connect(self.editar_materia_prima)
        self.editar_button.setToolTip(
            "Editar a matéria-prima selecionada (duplo-clique faz o mesmo)"
        )

        self.ativar_button = QPushButton("Desativar")
        self.ativar_button.clicked.connect(self.alternar_ativo)
        self.ativar_button.setToolTip(
            "Descontinuar a matéria-prima: deixa de aparecer nas escolhas de "
            "linhas novas, mas os orçamentos que já a usam ficam intactos"
        )

        self.fornecedores_button = QPushButton("Fornecedores…")
        self.fornecedores_button.clicked.connect(self.gerir_fornecedores)
        self.fornecedores_button.setToolTip(
            "Ver e preencher os contactos dos fornecedores — é daqui que sai o "
            "destinatário do pedido de preços"
        )

        self.pedir_precos_button = QPushButton("✉ Pedir preços…")
        self.pedir_precos_button.clicked.connect(self.pedir_precos)
        self.pedir_precos_button.setToolTip(
            "Juntar os preços por rever, agrupá-los por fornecedor e preparar os "
            "emails no Outlook — nada é enviado sem si"
        )

        self.ler_resposta_button = QPushButton("Ler resposta…")
        self.ler_resposta_button.clicked.connect(self.ler_resposta_fornecedor)
        self.ler_resposta_button.setToolTip(
            "Abrir o ficheiro que o fornecedor devolveu — o nosso anexo, a "
            "lista dele em Excel ou uma tabela de preços em PDF — e rever os "
            "preços antes de entrarem no catálogo"
        )

        self.exportar_button = QPushButton("Exportar Excel")
        self.exportar_button.clicked.connect(self.exportar_excel)
        self.exportar_button.setToolTip(
            "Gravar num ficheiro Excel exatamente o que está a ver — as colunas "
            "que escolheu, pela ordem em que as pôs. Para consultar ou imprimir."
        )

        self.colunas_button = QPushButton("Colunas…")
        self.colunas_button.setToolTip(
            "Escolher as colunas que quer ver. A escolha fica guardada na sua "
            "conta — cada pessoa vê a tabela à sua maneira."
        )
        self.colunas_button.clicked.connect(self._escolher_colunas)

        self.mostrar_inativos_input = QCheckBox("Mostrar não ativos")
        self.mostrar_inativos_input.setToolTip(
            "Mostrar também as matérias-primas descontinuadas, riscadas"
        )
        self.mostrar_inativos_input.stateChanged.connect(self.aplicar_pesquisa)

        self.status_label = QLabel("")
        self.status_label.setObjectName("materiasPrimasStatus")

        self.campo_pesquisa = CampoPesquisa(
            placeholder="Pesquisar mat\u00e9ria-prima\u2026 (espa\u00e7o para v\u00e1rios termos)"
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self.aplicar_pesquisa)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.campo_pesquisa)
        toolbar.addWidget(self.novo_button)
        toolbar.addWidget(self.editar_button)
        toolbar.addWidget(self.ativar_button)
        toolbar.addWidget(self.fornecedores_button)
        toolbar.addWidget(self.pedir_precos_button)
        toolbar.addWidget(self.ler_resposta_button)
        toolbar.addWidget(self.colunas_button)
        toolbar.addWidget(self.mostrar_inativos_input)
        toolbar.addStretch()
        toolbar.addWidget(self.exportar_button)
        toolbar.addWidget(self.refresh_button)

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # A ordem natural é a da descrição, que junta sozinha os equivalentes
        # (todas as "AGL MLM BRANCO ..." ficam seguidas). Clicar num cabeçalho
        # reordena por essa coluna, para quando se procura de outra maneira.
        self.table.setSortingEnabled(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
        # guardar_ordem: o utilizador arrasta os cabeçalhos para a ordem que
        # quiser e ela fica guardada na conta dele, tal como as larguras.
        self._larguras_restauradas = ligar_persistencia_larguras(
            self.table, "materias_primas", guardar_ordem=True
        )
        self._abrir_menu_colunas = ligar_menu_colunas(
            self.table, "materias_primas", self.COLUNAS_OCULTAS_POR_DEFEITO
        )
        self._larguras_seed_feito = False
        # A tabela é ordenável: clicar num cabeçalho troca as linhas de sítio.
        # Por isso o mapa é por ID da matéria-prima, e cada linha leva o seu id
        # colado à célula (UserRole). Guardar isto por NÚMERO DE LINHA dava a
        # ficha errada assim que a tabela fosse reordenada — e como o "Guardar"
        # da ficha grava no material que ela abriu, a edição ia parar ao
        # material errado.
        self._materias_por_id: dict[int, DefMateriaPrimaResumo] = {}
        # "Modo resolução" (assistente): duplo-clique aplica a matéria-prima à
        # linha do custeio e volta.
        self._resolucao_callback = None
        self.table.cellDoubleClicked.connect(self._on_duplo_clique)
        self.table.itemSelectionChanged.connect(self._atualizar_botoes)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(toolbar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar_materias_primas()

    def carregar_materias_primas(self) -> None:
        """Load raw materials into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()
        self._materias_primas = []

        try:
            with SessionLocal() as session:
                materias_primas = DefMateriaPrimaService(session).listar_materias_primas()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar as materias-primas.")
            return

        self._materias_primas = materias_primas
        self.aplicar_pesquisa()

        if not materias_primas:
            self.status_label.setText("Sem materias-primas para mostrar.")

    def aplicar_pesquisa(self, _text: str | None = None) -> None:
        """Filter the loaded raw materials according to the search text."""
        self.status_label.clear()
        search_text = self.campo_pesquisa.texto()
        mostrar_inativos = self.mostrar_inativos_input.isChecked()

        filtered = [
            materia
            for materia in self._materias_primas
            if (mostrar_inativos or materia.ativo)
            and (
                not search_text.strip()
                or materia_matches_search(materia, search_text)
            )
        ]

        self._preencher_tabela(filtered)

        if not self._materias_primas:
            self.status_label.setText("Sem materias-primas para mostrar.")
        elif search_text.strip() and not filtered:
            self.status_label.setText("Sem resultados para a pesquisa.")
        else:
            self.status_label.setText(self._texto_rodape(filtered))

    def _texto_rodape(self, visiveis: list[DefMateriaPrimaResumo]) -> str:
        """Linha do supervisor: o que está à vista e o que precisa de atenção."""
        sem_preco = sum(1 for m in self._materias_primas if m.ativo and preco_em_falta(m))
        a_rever = sum(
            1 for m in self._materias_primas if m.ativo and preco_desatualizado(m)
        )
        inativos = sum(1 for m in self._materias_primas if not m.ativo)

        partes = [f"{len(visiveis)} matérias-primas à vista"]
        if inativos and not self.mostrar_inativos_input.isChecked():
            partes.append(f"{inativos} descontinuadas escondidas")
        if a_rever:
            partes.append(f"{a_rever} preços a rever")
        if sem_preco:
            partes.append(f"{sem_preco} sem preço")

        return " · ".join(partes) + "."

    def _materia_da_linha(self, row: int) -> DefMateriaPrimaResumo | None:
        """A matéria-prima de uma linha da tabela, pelo id colado à célula.

        Nunca pelo número da linha: a tabela é ordenável e o número da linha
        muda de material assim que alguém clica num cabeçalho.
        """
        item = self.table.item(row, 0)
        if item is None:
            return None

        materia_id = item.data(Qt.ItemDataRole.UserRole)
        if materia_id is None:
            return None

        return self._materias_por_id.get(int(materia_id))

    def _materia_selecionada(self) -> DefMateriaPrimaResumo | None:
        """A matéria-prima da linha selecionada, ou None."""
        linhas = self.table.selectionModel().selectedRows()
        if not linhas:
            return None

        return self._materia_da_linha(linhas[0].row())

    def _exigir_selecao(self) -> DefMateriaPrimaResumo | None:
        """Como acima, mas a avisar quando não há nada escolhido."""
        materia = self._materia_selecionada()
        if materia is None:
            self.status_label.setText("Escolha primeiro uma matéria-prima na lista.")

        return materia

    def nova_materia_prima(self) -> None:
        """Criar uma matéria-prima de raiz."""
        self._abrir_dialogo(None)

    def editar_materia_prima(self) -> None:
        """Editar a matéria-prima selecionada."""
        materia = self._exigir_selecao()
        if materia is not None:
            self._abrir_dialogo(materia)

    def alternar_ativo(self) -> None:
        """Descontinuar (ou repor) a matéria-prima selecionada."""
        materia = self._exigir_selecao()
        if materia is None:
            return

        novo_estado = not materia.ativo
        if not novo_estado:
            usos = self._contar_utilizacoes(materia.id)
            aviso = (
                f"\n\nEsta matéria-prima está em {usos} linhas de orçamento. "
                "Esses orçamentos não mudam: cada linha guarda a cópia do preço "
                "com que foi calculada."
                if usos
                else ""
            )
            confirmacao = QMessageBox.question(
                self,
                "Desativar matéria-prima",
                f"Desativar «{materia.descricao}»?\n\n"
                "Deixa de aparecer nas escolhas de linhas novas, mas continua a "
                "existir e pode ser reposta a qualquer momento." + aviso,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirmacao != QMessageBox.StandardButton.Yes:
                return

        try:
            with SessionLocal() as session:
                DefMateriaPrimaService(session).definir_ativo(
                    materia.id, ativo=novo_estado
                )
        except SQLAlchemyError as error:
            print(f"[Materias-Primas] Erro ao mudar o estado: {error}")
            self.status_label.setText("Não foi possível mudar o estado da matéria-prima.")
            return

        self.carregar_materias_primas()
        self.status_label.setText(
            f"«{materia.descricao}» "
            + ("reposta como ativa." if novo_estado else "desativada.")
        )

    def _contar_utilizacoes(self, materia_prima_id: int) -> int:
        """Em quantas linhas de orçamento o material já foi usado."""
        try:
            with SessionLocal() as session:
                return DefMateriaPrimaService(session).contar_utilizacoes(
                    materia_prima_id
                )
        except SQLAlchemyError:
            return 0

    def _abrir_dialogo(self, materia: DefMateriaPrimaResumo | None) -> None:
        """Abrir a ficha da matéria-prima (nova ou a editar).

        A partir de uma ficha aberta, o "Gravar como…" cria uma matéria-prima
        nova com estes dados — é o mesmo gesto que existe nos outros menus.
        """
        from app.ui.dialogs.materia_prima_dialog import MateriaPrimaDialog

        historico: list = []
        utilizacoes = 0
        if materia is not None:
            try:
                with SessionLocal() as session:
                    service = DefMateriaPrimaService(session)
                    historico = service.historico_precos(materia.id)
                    utilizacoes = service.contar_utilizacoes(materia.id)
            except SQLAlchemyError as error:
                print(f"[Materias-Primas] Erro ao ler o histórico: {error}")

        dialogo = MateriaPrimaDialog(
            materia,
            parent=self,
            on_save=lambda dados: self._guardar(dados, materia),
            on_save_as=lambda dados: self._guardar(dados, None),
            historico=historico,
            utilizacoes=utilizacoes,
            ref_le_sugerida=self._proxima_ref_le,
            fornecedores=self._listar_fornecedores() or [],
        )
        dialogo.exec()

    def gerir_fornecedores(self) -> None:
        """Abrir a lista de fornecedores, para preencher contactos e emails."""
        from app.ui.dialogs.fornecedores_dialog import FornecedoresDialog

        fornecedores = self._listar_fornecedores()
        if fornecedores is None:
            return

        dialogo = FornecedoresDialog(
            fornecedores,
            parent=self,
            on_save=self._guardar_fornecedores,
            on_criar=self._criar_fornecedor,
            on_ligar_pelo_nome=self._ligar_materiais_pelo_nome,
        )
        dialogo.exec()
        # A lista mostra o nome do fornecedor, que pode ter sido corrigido.
        self.carregar_materias_primas()

    def pedir_precos(self) -> None:
        """Preparar os pedidos de atualização de preços aos fornecedores."""
        from app.ui.dialogs.pedido_precos_dialog import PedidoPrecosDialog

        pedidos = self._levantar_pedidos(MESES_PRECO_DESATUALIZADO)
        if pedidos is None:
            return

        dialogo = PedidoPrecosDialog(
            pedidos,
            parent=self,
            on_preparar=self._preparar_pedidos,
            on_meses_mudou=lambda meses: self._levantar_pedidos(meses) or [],
        )
        dialogo.exec()

    def _levantar_pedidos(self, meses: int):
        """O que há a rever, agrupado por fornecedor (None em caso de erro)."""
        from app.services.pedido_precos_service import PedidoPrecosService

        try:
            with SessionLocal() as session:
                return PedidoPrecosService(session).levantar_pedidos(meses)
        except SQLAlchemyError as error:
            print(f"[Materias-Primas] Erro ao levantar os pedidos: {error}")
            self.status_label.setText("Não foi possível reunir os preços a rever.")
            return None

    def _preparar_pedidos(self, pedidos: list) -> bool:
        """Gerar os anexos e abrir os emails no Outlook, um por fornecedor."""
        from app.core.session import app_session
        from app.services.pedido_precos_service import PedidoPrecosService

        utilizador = app_session.current_user
        remetente = getattr(utilizador, "nome", None)

        try:
            with SessionLocal() as session:
                service = PedidoPrecosService(session)
                preparados = [
                    service.preparar(pedido, remetente=remetente) for pedido in pedidos
                ]
                for preparado in preparados:
                    service.abrir_no_outlook(preparado)
        except (RuntimeError, OSError, SQLAlchemyError) as error:
            print(f"[Materias-Primas] Erro ao preparar os pedidos: {error}")
            self.status_label.setText(
                "Não foi possível preparar os emails. Verifique se o Outlook está aberto."
            )
            return False

        quantos = len(preparados)
        self.status_label.setText(
            f"{quantos} email{'s' if quantos != 1 else ''} aberto"
            f"{'s' if quantos != 1 else ''} no Outlook, por rever e enviar. "
            f"Anexos guardados em {preparados[0].anexo.parent}."
        )
        return True

    def ler_resposta_fornecedor(self) -> None:
        """Ler o ficheiro devolvido por um fornecedor e rever o que traz."""
        from PySide6.QtWidgets import QFileDialog

        from app.ui.dialogs.resposta_fornecedor_dialog import RespostaFornecedorDialog
        from app.services.pedido_precos_service import PedidoPrecosService

        try:
            with SessionLocal() as session:
                pasta = str(PedidoPrecosService(session).pasta_dos_pedidos())
        except SQLAlchemyError:
            pasta = ""

        caminho, _ = QFileDialog.getOpenFileName(
            self,
            "Resposta do fornecedor",
            pasta,
            "Resposta do fornecedor (*.xlsx *.xlsm *.pdf);;"
            "Ficheiros Excel (*.xlsx *.xlsm);;Tabela em PDF (*.pdf);;"
            "Todos os ficheiros (*)",
        )
        if not caminho:
            return

        leitura = self._ler_resposta(caminho)
        if leitura is None:
            return

        if not leitura.propostas:
            self.status_label.setText(
                "Não foi reconhecida nenhuma linha neste ficheiro. "
                + " ".join(leitura.notas)
            )
            return

        dialogo = RespostaFornecedorDialog(
            list(leitura.propostas),
            caminho=caminho,
            parent=self,
            on_aplicar=self._aplicar_resposta,
            notas=leitura.notas,
        )
        dialogo.exec()

    def _ler_resposta(self, caminho: str):
        """Ler o ficheiro do fornecedor (None em caso de erro).

        Serve tanto o anexo que mandámos como a lista do próprio fornecedor, em
        Excel ou em PDF. O que a leitura teve de adivinhar vem nas notas, para
        ser dito a quem revê.
        """
        from app.services.resposta_fornecedor_service import RespostaFornecedorService

        try:
            with SessionLocal() as session:
                return RespostaFornecedorService(session).ler_com_notas(caminho)
        except (OSError, RuntimeError, ValueError, SQLAlchemyError) as error:
            print(f"[Materias-Primas] Erro ao ler a resposta: {error}")
            self.status_label.setText(
                "Não foi possível ler o ficheiro. Confirme que é o Excel do "
                "pedido ou uma tabela de preços em PDF."
            )
            return None

    def _aplicar_resposta(self, propostas: list) -> bool:
        """Gravar no catálogo as linhas que o utilizador aprovou."""
        from app.services.resposta_fornecedor_service import RespostaFornecedorService

        try:
            with SessionLocal() as session:
                resultado = RespostaFornecedorService(session).aplicar(propostas)
        except SQLAlchemyError as error:
            print(f"[Materias-Primas] Erro ao aplicar a resposta: {error}")
            self.status_label.setText("Não foi possível aplicar os preços.")
            return False

        self.carregar_materias_primas()
        partes = [f"{resultado.atualizadas} preços atualizados"]
        if resultado.desativadas:
            partes.append(f"{resultado.desativadas} materiais desativados")
        if resultado.erros:
            partes.append(f"{len(resultado.erros)} com erro")
        self.status_label.setText(" · ".join(partes) + ".")
        return True

    def _listar_fornecedores(self):
        """Fornecedores com a contagem de materiais, ou None em caso de erro."""
        from app.services.def_fornecedor_service import DefFornecedorService

        try:
            with SessionLocal() as session:
                return DefFornecedorService(session).listar_fornecedores()
        except SQLAlchemyError as error:
            print(f"[Materias-Primas] Erro ao ler os fornecedores: {error}")
            self.status_label.setText("Não foi possível ler os fornecedores.")
            return None

    def _ligar_materiais_pelo_nome(self):
        """Repor as ligações material-fornecedor a partir do nome escrito.

        As importações antigas só traziam o nome, e houve uma altura em que isso
        apagava a ligação. Isto repõe-na sem ninguém ter de ir ao terminal.
        """
        from app.services.def_fornecedor_service import DefFornecedorService
        from scripts.reparar_ligacao_fornecedores import reparar

        try:
            with SessionLocal() as session:
                resumo = reparar(session)
                atualizados = DefFornecedorService(session).listar_fornecedores()
        except SQLAlchemyError as error:
            print(f"[Materias-Primas] Erro ao ligar os materiais: {error}")
            self.status_label.setText("Não foi possível ligar os materiais.")
            return None

        partes = [f"{resumo['ligadas']} matérias-primas ligadas"]
        if resumo["ja_ligadas"]:
            partes.append(f"{resumo['ja_ligadas']} já estavam")
        if resumo["sem_fornecedor"]:
            nomes = ", ".join(sorted(resumo["sem_fornecedor"])[:4])
            partes.append(f"sem ficha: {nomes}")

        return " · ".join(partes) + ".", atualizados

    def _guardar_fornecedores(self, alteracoes: dict) -> bool:
        """Gravar as alterações feitas na tabela de fornecedores."""
        from app.services.def_fornecedor_service import DefFornecedorService

        try:
            with SessionLocal() as session:
                service = DefFornecedorService(session)
                for fornecedor_id, dados in alteracoes.items():
                    service.editar_fornecedor(fornecedor_id, dados)
        except ValueError as error:
            self.status_label.setText(str(error))
            return False
        except SQLAlchemyError as error:
            print(f"[Materias-Primas] Erro ao gravar fornecedores: {error}")
            self.status_label.setText("Não foi possível gravar os fornecedores.")
            return False

        quantos = len(alteracoes)
        self.status_label.setText(
            f"{quantos} fornecedor{'es' if quantos != 1 else ''} atualizado"
            f"{'s' if quantos != 1 else ''}."
        )
        return True

    def _criar_fornecedor(self, nome: str):
        """Criar um fornecedor. Devolve a lista atualizada, ou None se falhou."""
        from app.services.def_fornecedor_service import (
            DefFornecedorService,
            FornecedorData,
        )

        try:
            with SessionLocal() as session:
                service = DefFornecedorService(session)
                service.criar_fornecedor(FornecedorData(nome=nome))
                return service.listar_fornecedores()
        except ValueError as error:
            self.status_label.setText(str(error))
        except SQLAlchemyError as error:
            print(f"[Materias-Primas] Erro ao criar fornecedor: {error}")
            self.status_label.setText("Não foi possível criar o fornecedor.")

        return None

    def _proxima_ref_le(self, familia: str) -> str | None:
        """Referência que uma matéria-prima nova dessa família vai receber."""
        try:
            with SessionLocal() as session:
                return DefMateriaPrimaService(session).proxima_ref_le(familia)
        except SQLAlchemyError:
            return None

    def _guardar(self, dados, materia: DefMateriaPrimaResumo | None) -> bool:
        """Gravar a ficha. Devolve False para o diálogo ficar aberto no erro."""
        from app.services.def_materia_prima_service import (
            CriarDefMateriaPrimaData,
            EditarDefMateriaPrimaData,
            ORIGEM_DADOS_V3,
        )

        campos = {
            "descricao": dados.descricao,
            "ref_le": dados.ref_le,
            "referencia_fornecedor": dados.referencia_fornecedor,
            "tipo_original_excel": dados.tipo,
            "familia_original_excel": dados.familia,
            "coresp_orla_0_4": dados.coresp_orla_0_4,
            "coresp_orla_1_0": dados.coresp_orla_1_0,
            "unidade": dados.unidade,
            "preco_tabela": dados.preco_tabela,
            "desconto": dados.desconto,
            "margem": dados.margem,
            "desperdicio_percentagem": dados.desperdicio_percentagem,
            "preco_liquido": dados.preco_liquido,
            "comprimento": dados.comprimento,
            "largura": dados.largura,
            "espessura": dados.espessura,
            "fornecedor": dados.fornecedor,
            "fornecedor_id": dados.fornecedor_id,
            "tipo_preco": dados.tipo_preco,
            "data_ultimo_preco": dados.data_ultimo_preco,
            "stock": dados.stock,
            "cor": dados.cor,
            "nome_fabricante": dados.nome_fabricante,
            "ref_phc": dados.ref_phc,
            "link": dados.link,
            "ativo": dados.ativo,
            "observacoes": dados.observacoes,
            "origem_dados": ORIGEM_DADOS_V3,
        }

        try:
            with SessionLocal() as session:
                service = DefMateriaPrimaService(session)
                if materia is None:
                    resultado = service.criar_materia_prima(
                        CriarDefMateriaPrimaData(**campos)
                    )
                    mensagem = f"«{resultado.descricao}» criada com a referência {resultado.ref_le}."
                else:
                    # A família normalizada do Martelo acompanha o registo.
                    resultado = service.editar_materia_prima(
                        materia.id,
                        EditarDefMateriaPrimaData(
                            tipo_martelo=materia.tipo_martelo,
                            familia_martelo=materia.familia_martelo,
                            **campos,
                        ),
                    )
                    mensagem = f"«{resultado.descricao}» gravada."
        except ValueError as error:
            self.status_label.setText(str(error))
            return False
        except SQLAlchemyError as error:
            print(f"[Materias-Primas] Erro ao gravar: {error}")
            self.status_label.setText("Não foi possível gravar a matéria-prima.")
            return False

        self.carregar_materias_primas()
        self.mostrar_onde_ficou(resultado.ref_le)
        self.status_label.setText(mensagem)
        return True

    def mostrar_onde_ficou(self, ref_le: str | None) -> None:
        """Levar a vista até à matéria-prima gravada, sem filtrar a lista.

        A lista é ordenada pela descrição, por isso uma matéria-prima nova
        aparece ao pé das suas equivalentes e não no fim — mas só se vê isso se
        a vista lá for. Ao contrário do ``focar_materia_prima``, que isola a
        linha para o assistente, aqui interessa precisamente a vizinhança.
        """
        if not ref_le:
            return

        alvo = ref_le.strip().upper()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and (item.text() or "").strip().upper() == alvo:
                self.table.selectRow(row)
                self.table.scrollToItem(
                    item, QAbstractItemView.ScrollHint.PositionAtCenter
                )
                self._piscar_linha(row)
                return

    def focar_materia_prima(self, ref_le: str | None) -> None:
        """Filtra pela Ref LE, seleciona e pisca a matéria-prima (assistente 3B)."""
        if not ref_le:
            return
        alvo = ref_le.strip().upper()
        # Filtrar pela Ref LE isola a matéria-prima na tabela (re-preenche já).
        self.campo_pesquisa.definir_texto(ref_le)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and (item.text() or "").strip().upper() == alvo:
                self.table.selectRow(row)
                self.table.scrollToItem(
                    item, QAbstractItemView.ScrollHint.PositionAtCenter
                )
                self._piscar_linha(row)
                return

    def _piscar_linha(self, row: int) -> None:
        """Pisca a linha (fundo ocre) durante ~1,5 s e repõe o fundo original."""
        itens = [
            self.table.item(row, col) for col in range(self.table.columnCount())
        ]
        itens = [item for item in itens if item is not None]
        fundos = [item.background() for item in itens]
        realce = QColor(tema.OCRE_SUAVE)
        for item in itens:
            item.setBackground(realce)

        def repor() -> None:
            for item, fundo in zip(itens, fundos):
                item.setBackground(fundo)

        QTimer.singleShot(1500, repor)

    def entrar_modo_resolucao(self, ao_escolher) -> None:
        """Ativa o modo resolução: duplo-clique aplica a matéria-prima (assistente 3B)."""
        self._resolucao_callback = ao_escolher
        self.status_label.setText(
            "A resolver: duplo-clique numa matéria-prima para a aplicar à linha e voltar."
        )

    def sair_modo_resolucao(self) -> None:
        self._resolucao_callback = None

    def _on_duplo_clique(self, row: int, _column: int) -> None:
        callback = self._resolucao_callback
        materia = self._materia_da_linha(row)
        if materia is None:
            return

        if callback is not None:
            self.sair_modo_resolucao()
            callback(materia)
            return

        # Fora do modo resolução, o duplo-clique abre a ficha para editar.
        self._abrir_dialogo(materia)

    def _atualizar_botoes(self) -> None:
        """O botão de estado diz o que vai fazer à linha escolhida."""
        materia = self._materia_selecionada()
        ativa = materia is None or materia.ativo
        self.ativar_button.setText("Desativar" if ativa else "Repor ativo")
        self.ativar_button.setToolTip(
            "Descontinuar a matéria-prima: deixa de aparecer nas escolhas de "
            "linhas novas, mas os orçamentos que já a usam ficam intactos"
            if ativa
            else "Voltar a pôr a matéria-prima disponível para orçamentos novos"
        )

    def _preencher_tabela(self, materias_primas: list[DefMateriaPrimaResumo]) -> None:
        """Fill the table with raw material read models."""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(materias_primas))
        self._materias_por_id = {}

        for row_index, materia in enumerate(materias_primas):
            self._materias_por_id[materia.id] = materia
            values = [
                materia.ref_le or "",
                materia.descricao,
                materia.tipo_original_excel or "",
                materia.familia_original_excel or "",
                materia.unidade or "",
                materia.tipo_preco,
                format_currency(materia.preco_tabela),
                formatar_percentagem(normalize_percentagem_humana(materia.desconto)),
                formatar_percentagem(normalize_percentagem_humana(materia.margem)),
                formatar_percentagem(
                    normalize_percentagem_humana(materia.desperdicio_percentagem)
                ),
                self._texto_preco(materia),
                self._texto_data_preco(materia),
                self._texto_stock(materia),
                materia.fornecedor or "",
                materia.referencia_fornecedor or "",
                materia.nome_fabricante or "",
                materia.cor or "",
                materia.ref_phc or "",
                materia.link or "",
                materia.coresp_orla_0_4 or "",
                materia.coresp_orla_1_0 or "",
                format_quantity(materia.comprimento),
                format_quantity(materia.largura),
                format_quantity(materia.espessura),
                materia.observacoes or "",
                materia.criado_por or "",
                materia.alterado_por or "",
                "Sim" if materia.ativo else "Não",
            ]

            riscado = not materia.ativo
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                # O id viaja com a célula. Ordenar a tabela troca as células de
                # linha, e o id vai com elas — ao contrário do número da linha.
                item.setData(Qt.ItemDataRole.UserRole, materia.id)
                item.setBackground(QColor(tema.cor_zebra(row_index)))
                if riscado:
                    # Descontinuado: risco por cima e cinzento, como o Ctrl+5 do
                    # Excel. A coluna "Ativo" fica leg\u00edvel, sem risco.
                    if column_index != len(values) - 1:
                        fonte = item.font()
                        fonte.setStrikeOut(True)
                        item.setFont(fonte)
                    item.setForeground(QColor(tema.CINZA_ESCURO))
                self.table.setItem(row_index, column_index, item)

            self._pintar_avisos(row_index, materia)

        self.table.setSortingEnabled(True)

        if (
            not self._larguras_restauradas
            and not self._larguras_seed_feito
            and materias_primas
        ):
            self.table.resizeColumnsToContents()
            self._larguras_seed_feito = True

    def exportar_excel(self) -> None:
        """Gravar num Excel o que está à vista, com as colunas do utilizador."""
        from PySide6.QtWidgets import QFileDialog

        from app.services.materias_primas_excel_export import (
            exportar_materias_primas,
            nome_do_ficheiro,
        )

        if not self.table.rowCount():
            self.status_label.setText("Não há nada para exportar.")
            return

        caminho, _filtro = QFileDialog.getSaveFileName(
            self,
            "Exportar matérias-primas",
            nome_do_ficheiro(),
            "Ficheiros Excel (*.xlsx)",
        )
        if not caminho:
            return

        colunas, linhas = self._conteudo_para_exportar()
        try:
            destino = exportar_materias_primas(colunas, linhas, caminho)
        except (OSError, RuntimeError) as error:
            print(f"[Materias-Primas] Erro ao exportar: {error}")
            self.status_label.setText(
                "Não foi possível gravar o ficheiro. Verifique se não está aberto."
            )
            return

        self.status_label.setText(
            f"{len(linhas)} matérias-primas exportadas para {destino}."
        )
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(destino.parent)))

    def _conteudo_para_exportar(self):
        """As colunas visíveis (pela ordem do utilizador) e as linhas à vista."""
        cabecalho = self.table.horizontalHeader()
        indices = [
            cabecalho.logicalIndex(posicao)
            for posicao in range(cabecalho.count())
            if not cabecalho.isSectionHidden(cabecalho.logicalIndex(posicao))
        ]
        colunas = [self.TABLE_HEADERS[indice] for indice in indices]

        linhas = []
        for row in range(self.table.rowCount()):
            valores = []
            for indice in indices:
                item = self.table.item(row, indice)
                valores.append(item.text() if item is not None else "")
            materia = self._materia_da_linha(row)
            linhas.append((valores, getattr(materia, "ativo", True)))

        return colunas, linhas

    def _escolher_colunas(self) -> None:
        """Abrir o menu das colunas (o mesmo do clique direito no cabeçalho)."""
        self._abrir_menu_colunas()

    def _texto_preco(self, materia: DefMateriaPrimaResumo) -> str:
        """Preço líquido, ou a menção de que é escrito no orçamento."""
        if materia.tipo_preco == TIPO_PRECO_LIVRE:
            return "preço livre"

        return format_currency(materia.preco_liquido)

    def _texto_data_preco(self, materia: DefMateriaPrimaResumo) -> str:
        if materia.data_ultimo_preco is None:
            return ""

        return f"{materia.data_ultimo_preco:%d-%m-%Y}"

    def _texto_stock(self, materia: DefMateriaPrimaResumo) -> str:
        if materia.stock is None:
            return ""

        return "Sim" if materia.stock else "Não"

    def _pintar_avisos(self, row_index: int, materia: DefMateriaPrimaResumo) -> None:
        """As mesmas cores do Excel: preço em falta a vermelho, preço velho a âmbar."""
        if preco_em_falta(materia):
            item = self.table.item(row_index, self.COLUNA_PRECO_LIQUIDO)
            if item is not None:
                item.setBackground(QColor(tema.VERMELHO_SUAVE))
                item.setToolTip(
                    "Sem preço: este material entra no custeio a 0,00 €. "
                    "Preencha o preço de tabela, ou marque-o como preço livre."
                )

        if preco_desatualizado(materia):
            item = self.table.item(row_index, self.COLUNA_ULTIMO_PRECO)
            if item is not None:
                item.setBackground(QColor(tema.OCRE_SUAVE))
                item.setToolTip(
                    f"Preço com mais de {MESES_PRECO_DESATUALIZADO} meses — deve ser revisto."
                )


def normalize_search_text(value: object) -> str:
    """Normalize text for accent-insensitive, case-insensitive search."""
    if value is None:
        return ""

    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def materia_matches_search(materia: DefMateriaPrimaResumo, search_text: str) -> bool:
    """Return whether a raw material matches all search tokens."""
    tokens = normalize_search_text(search_text).split()
    if not tokens:
        return True

    searchable_text = normalize_search_text(
        " ".join(
            [
                materia.ref_le or "",
                materia.descricao,
                materia.tipo_original_excel or "",
                materia.familia_original_excel or "",
                materia.unidade or "",
                materia.fornecedor or "",
            ]
        )
    )

    return all(token in searchable_text for token in tokens)
