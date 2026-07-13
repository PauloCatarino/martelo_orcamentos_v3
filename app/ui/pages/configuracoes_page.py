"""Technical settings page."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.barra_cabecalho import BarraCabecalho


class ConfiguracoesPage(QWidget):
    """Technical administration shortcuts page."""

    TECHNICAL_AREAS = [
        "Defini\u00e7\u00f5es de Pe\u00e7as",
        "Caminhos do Sistema",
        "Liga\u00e7\u00e3o iMos (leitura)",
        "Opera\u00e7\u00f5es / M\u00e1quinas",
        "Chaves ValueSet",
        "Modelos ValueSet",
        "Margens por Defeito",
        "Regras de Quantidade",
        "Biblioteca de Módulos",
        "Auditoria do Catálogo",
    ]

    TOOLTIP_DESCRICOES = {
        "Defini\u00e7\u00f5es de Pe\u00e7as": (
            "Criar e manter a biblioteca de pe\u00e7as reutiliz\u00e1veis, incluindo "
            "dimens\u00f5es, orlas, materiais, associados e opera\u00e7\u00f5es."
        ),
        "Caminhos do Sistema": (
            "Configurar as pastas e ficheiros externos usados pelo Martelo, "
            "incluindo imagens, exporta\u00e7\u00f5es e integra\u00e7\u00f5es."
        ),
        "Liga\u00e7\u00e3o iMos (leitura)": (
            "Configurar e testar o acesso SQL ao iMos. O Martelo bloqueia qualquer "
            "comando que n\u00e3o seja uma consulta de leitura."
        ),
        "Opera\u00e7\u00f5es / M\u00e1quinas": (
            "Gerir opera\u00e7\u00f5es de produ\u00e7\u00e3o, m\u00e1quinas, tempos, setups e "
            "tarifas que transformam trabalho em custo."
        ),
        "Chaves ValueSet": (
            "Definir os tipos de escolha usados nas pe\u00e7as, como materiais, "
            "ferragens, acabamentos e sistemas de uni\u00e3o."
        ),
        "Modelos ValueSet": (
            "Criar conjuntos reutiliz\u00e1veis de op\u00e7\u00f5es e respetivas regras, "
            "materiais e opera\u00e7\u00f5es."
        ),
        "Margens por Defeito": (
            "Definir as margens iniciais dos novos or\u00e7amentos: Standard, por "
            "cliente e por utilizador. Podem ser ajustadas em cada or\u00e7amento."
        ),
        "Regras de Quantidade": (
            "Gerir express\u00f5es que calculam quantidades de componentes a partir "
            "das dimens\u00f5es e quantidade da pe\u00e7a principal."
        ),
        "Biblioteca de M\u00f3dulos": (
            "Consultar e manter m\u00f3dulos reutiliz\u00e1veis criados no custeio, "
            "prontos para inserir noutros itens."
        ),
        "Auditoria do Cat\u00e1logo": (
            "Validar pe\u00e7as, associados, opera\u00e7\u00f5es, tarifas, ValueSets e "
            "m\u00f3dulos, explicando o impacto das falhas no custo final."
        ),
    }

    def __init__(
        self,
        on_open_def_pecas: Callable[[], None] | None = None,
        on_open_materias_primas: Callable[[], None] | None = None,
        on_open_caminhos_sistema: Callable[[], None] | None = None,
        on_open_imos_ligacao: Callable[[], None] | None = None,
        on_open_operacoes_maquinas: Callable[[], None] | None = None,
        on_open_valueset_chaves: Callable[[], None] | None = None,
        on_open_valueset_modelos: Callable[[], None] | None = None,
        on_open_margens_padrao: Callable[[], None] | None = None,
        on_open_regras_quantidade: Callable[[], None] | None = None,
        on_open_biblioteca_modulos: Callable[[], None] | None = None,
        on_open_catalogo_auditoria: Callable[[], None] | None = None,
        on_open_user_management: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()

        self.on_open_def_pecas = on_open_def_pecas
        self.on_open_materias_primas = on_open_materias_primas
        self.on_open_caminhos_sistema = on_open_caminhos_sistema
        self.on_open_imos_ligacao = on_open_imos_ligacao
        self.on_open_operacoes_maquinas = on_open_operacoes_maquinas
        self.on_open_valueset_chaves = on_open_valueset_chaves
        self.on_open_valueset_modelos = on_open_valueset_modelos
        self.on_open_margens_padrao = on_open_margens_padrao
        self.on_open_regras_quantidade = on_open_regras_quantidade
        self.on_open_biblioteca_modulos = on_open_biblioteca_modulos
        self.on_open_catalogo_auditoria = on_open_catalogo_auditoria
        self.on_open_user_management = on_open_user_management

        self.cabecalho = BarraCabecalho(
            "Configura\u00e7\u00f5es",
            [
                "\u00c1rea de administra\u00e7\u00e3o t\u00e9cnica do Martelo Or\u00e7amentos V3. "
                "Aqui ser\u00e3o configuradas pe\u00e7as, materiais, ferragens, opera\u00e7\u00f5es, "
                "regras de custeio e outras tabelas de apoio."
            ],
        )

        self.status_label = QLabel("")
        self.status_label.setObjectName("configuracoesStatus")

        self.def_pecas_button = QPushButton("Defini\u00e7\u00f5es de Pe\u00e7as")
        self.def_pecas_button.clicked.connect(self._open_def_pecas)

        self.caminhos_sistema_button = QPushButton("Caminhos do Sistema")
        self.caminhos_sistema_button.clicked.connect(self._open_caminhos_sistema)

        self.imos_ligacao_button = QPushButton("Liga\u00e7\u00e3o iMos (leitura)")
        self.imos_ligacao_button.clicked.connect(self._open_imos_ligacao)

        self.operacoes_maquinas_button = QPushButton("Opera\u00e7\u00f5es / M\u00e1quinas")
        self.operacoes_maquinas_button.clicked.connect(self._open_operacoes_maquinas)

        self.valueset_chaves_button = QPushButton("Chaves ValueSet")
        self.valueset_chaves_button.clicked.connect(self._open_valueset_chaves)

        self.valueset_modelos_button = QPushButton("Modelos ValueSet")
        self.valueset_modelos_button.clicked.connect(self._open_valueset_modelos)

        self.margens_padrao_button = QPushButton("Margens por Defeito")
        self.margens_padrao_button.setToolTip(
            "Margens iniciais dos novos orçamentos (Standard, por cliente e "
            "por utilizador). Dentro de cada orçamento o utilizador altera "
            "livremente."
        )
        self.margens_padrao_button.clicked.connect(self._open_margens_padrao)

        self.regras_quantidade_button = QPushButton("Regras de Quantidade")
        self.regras_quantidade_button.setToolTip(
            "Regras (expressões) que calculam a quantidade de ferragens a partir "
            "das dimensões da peça principal (COMP/LARG/ESP/QT_PAI)."
        )
        self.regras_quantidade_button.clicked.connect(self._open_regras_quantidade)

        self.biblioteca_modulos_button = QPushButton("Biblioteca de Módulos")
        self.biblioteca_modulos_button.setToolTip(
            "Gerir os módulos reutilizáveis guardados no custeio (roupeiros, "
            "cozinhas, móveis...): pesquisar, editar o cabeçalho, eliminar e ver "
            "as linhas. Os módulos criam-se no custeio e importam-se nos itens."
        )
        self.biblioteca_modulos_button.clicked.connect(self._open_biblioteca_modulos)

        self.catalogo_auditoria_button = QPushButton("Auditoria do Catálogo")
        self.catalogo_auditoria_button.setToolTip(
            "Detetar incoerências em peças, associados, operações, regras, "
            "ValueSets e módulos, sem alterar dados."
        )
        self.catalogo_auditoria_button.clicked.connect(
            self._open_catalogo_auditoria
        )

        self.user_management_button = QPushButton("Utilizadores e Acessos")
        self.user_management_button.setToolTip(
            "Criar utilizadores e personalizar os menus disponíveis em cada conta."
        )
        self.user_management_button.clicked.connect(self._open_user_management)
        self.user_management_button.setVisible(self.on_open_user_management is not None)
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addSpacing(8)
        painel = QGroupBox("\u00c1reas de configura\u00e7\u00e3o")
        painel.setObjectName("configuracoesPainel")
        grelha = QGridLayout(painel)
        grelha.setSpacing(12)
        botoes = [
            self.def_pecas_button,
            self.caminhos_sistema_button,
            self.imos_ligacao_button,
            self.operacoes_maquinas_button,
            self.valueset_chaves_button,
            self.valueset_modelos_button,
            self.margens_padrao_button,
            self.regras_quantidade_button,
            self.biblioteca_modulos_button,
            self.catalogo_auditoria_button,
        ]
        if self.on_open_user_management is not None:
            botoes.append(self.user_management_button)
        for indice, botao in enumerate(botoes):
            botao.setMinimumHeight(48)
            botao.setToolTip(self.TOOLTIP_DESCRICOES.get(botao.text(), botao.toolTip()))
            grelha.addWidget(botao, indice // 3, indice % 3)
        layout.addWidget(painel)
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.setLayout(layout)

    def _open_def_pecas(self) -> None:
        """Open the piece definitions page through the optional callback."""
        if self.on_open_def_pecas is not None:
            self.on_open_def_pecas()

    def _open_caminhos_sistema(self) -> None:
        """Open the system paths page through the optional callback."""
        if self.on_open_caminhos_sistema is not None:
            self.on_open_caminhos_sistema()

    def _open_imos_ligacao(self) -> None:
        if self.on_open_imos_ligacao is not None:
            self.on_open_imos_ligacao()

    def _open_operacoes_maquinas(self) -> None:
        """Open the operations / machines page through the optional callback."""
        if self.on_open_operacoes_maquinas is not None:
            self.on_open_operacoes_maquinas()

    def _open_valueset_chaves(self) -> None:
        """Open the ValueSet keys page through the optional callback."""
        if self.on_open_valueset_chaves is not None:
            self.on_open_valueset_chaves()

    def _open_valueset_modelos(self) -> None:
        """Open the ValueSet models page through the optional callback."""
        if self.on_open_valueset_modelos is not None:
            self.on_open_valueset_modelos()

    def _open_margens_padrao(self) -> None:
        """Open the default margins page through the optional callback."""
        if self.on_open_margens_padrao is not None:
            self.on_open_margens_padrao()

    def _open_regras_quantidade(self) -> None:
        """Open the quantity rules page through the optional callback."""
        if self.on_open_regras_quantidade is not None:
            self.on_open_regras_quantidade()

    def _open_biblioteca_modulos(self) -> None:
        """Open the module library page through the optional callback."""
        if self.on_open_biblioteca_modulos is not None:
            self.on_open_biblioteca_modulos()

    def _open_catalogo_auditoria(self) -> None:
        """Open the read-only catalog audit page."""
        if self.on_open_catalogo_auditoria is not None:
            self.on_open_catalogo_auditoria()
    def _open_user_management(self) -> None:
        """Open account and access administration for the administrator."""
        if self.on_open_user_management is not None:
            self.on_open_user_management()
