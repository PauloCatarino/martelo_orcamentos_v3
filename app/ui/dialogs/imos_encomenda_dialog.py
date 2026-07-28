"""Diálogo de criação da encomenda no iMos a partir de uma obra da Produção.

Nada é criado sem passar por aqui: o diálogo mostra o caminho que vai ser
percorrido, o nome que a encomenda vai ter (editável) e todos os valores que
vão para as colunas do iMos, incluindo o que teve de ser cortado.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.models.producao import Producao
from app.services.imos_encomenda_service import (
    PASTA_ANO_ENSAIO,
    PlanoCriacaoImos,
    executar,
    preparar,
)
from app.services.imos_escrita import (
    KEY_IMOS_ESCRITA_ATIVA,
    carregar_escrita_ativa,
    explicar_erro_escrita,
)
from app.services.imos_sql import (
    IMOS_NOME_MAX,
    IMOS_TIPO_ENCOMENDA,
    load_imos_config,
)

COR_EM_FALTA = QColor("#8a5000")
COR_AVISO = QColor("#b00020")


class ImosEncomendaDialog(QDialog):
    """Pré-visualiza e cria a encomenda do iMos para uma obra."""

    COLUNAS_CAMINHO = ["Nível", "Nome", "Estado"]
    COLUNAS_CAMPOS = ["Campo do Martelo", "Coluna iMos", "Valor que vai ser gravado", "Aviso"]

    def __init__(self, *, processo_id: int, parent=None) -> None:
        super().__init__(parent)

        self._processo_id = processo_id
        self._plano: PlanoCriacaoImos | None = None
        self._escrita_ativa = False
        self._criada = False

        self.setWindowTitle("Criar Encomenda IMOS")
        self.setModal(True)
        self.setMinimumSize(920, 640)

        self.cabecalho = QLabel(
            "O Martelo vai criar a encomenda no iMos a partir dos dados desta obra. "
            "Confirme o caminho e o nome antes de gravar — o iMos não tem "
            "desfazer, e o Martelo nunca substitui uma encomenda existente."
        )
        self.cabecalho.setWordWrap(True)

        # --- caminho -------------------------------------------------------
        self.caminho_table = QTableWidget(0, len(self.COLUNAS_CAMINHO))
        self.caminho_table.setHorizontalHeaderLabels(self.COLUNAS_CAMINHO)
        self.caminho_table.verticalHeader().setVisible(False)
        self.caminho_table.setAlternatingRowColors(True)
        self.caminho_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.caminho_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.caminho_table.setToolTip(
            "Caminho dentro do iMos, de cima para baixo. As pastas marcadas como "
            "'vai ser criada' ainda não existem e serão criadas agora."
        )
        self.caminho_table.setMaximumHeight(150)
        cabecalho_caminho = self.caminho_table.horizontalHeader()
        cabecalho_caminho.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        cabecalho_caminho.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        cabecalho_caminho.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self.ensaio_check = QCheckBox(
            f"Ensaio: criar em {PASTA_ANO_ENSAIO} em vez da pasta do ano"
        )
        self.ensaio_check.setToolTip(
            "Desvia a criação para uma pasta descartável ao lado dos ANO_XXXX, "
            "para validar o processo sem mexer no ano real. Depois de "
            f"confirmar, apague a pasta {PASTA_ANO_ENSAIO} no iX Organizer."
        )
        self.ensaio_check.toggled.connect(self._recarregar)

        grupo_caminho = QGroupBox("Onde vai ser criada")
        layout_caminho = QVBoxLayout(grupo_caminho)
        layout_caminho.addWidget(self.caminho_table)
        layout_caminho.addWidget(self.ensaio_check)

        # --- nome ----------------------------------------------------------
        self.nome_input = QLineEdit()
        self.nome_input.setMaxLength(IMOS_NOME_MAX)
        self.nome_input.setToolTip(
            "Nome da encomenda no iMos (campo NAME). O iMos só aceita "
            f"{IMOS_NOME_MAX} caracteres, por isso nomes de cliente compridos são "
            "cortados. Pode corrigir aqui antes de gravar."
        )
        self.nome_input.editingFinished.connect(self._recarregar)

        self.contador_label = QLabel("")
        self.contador_label.setToolTip(
            f"Caracteres usados no nome, de um máximo de {IMOS_NOME_MAX}."
        )
        self.nome_input.textChanged.connect(self._atualizar_contador)

        self.nome_original_label = QLabel("")
        self.nome_original_label.setWordWrap(True)

        linha_nome = QHBoxLayout()
        linha_nome.addWidget(self.nome_input, stretch=1)
        linha_nome.addWidget(self.contador_label)

        grupo_nome = QGroupBox("Nome da encomenda")
        layout_nome = QVBoxLayout(grupo_nome)
        layout_nome.addLayout(linha_nome)
        layout_nome.addWidget(self.nome_original_label)

        # --- campos --------------------------------------------------------
        self.campos_table = QTableWidget(0, len(self.COLUNAS_CAMPOS))
        self.campos_table.setHorizontalHeaderLabels(self.COLUNAS_CAMPOS)
        self.campos_table.verticalHeader().setVisible(False)
        self.campos_table.setAlternatingRowColors(True)
        self.campos_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.campos_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.campos_table.setToolTip(
            "Valores da obra já traduzidos para as colunas de dbo.PROADMIN. "
            "A coluna Aviso indica o que teve de ser cortado para caber."
        )
        cabecalho_campos = self.campos_table.horizontalHeader()
        cabecalho_campos.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        cabecalho_campos.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        cabecalho_campos.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        cabecalho_campos.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        grupo_campos = QGroupBox("O que vai ser gravado na encomenda")
        layout_campos = QVBoxLayout(grupo_campos)
        layout_campos.addWidget(self.campos_table)

        # --- avisos e botões ------------------------------------------------
        self.avisos_label = QLabel("")
        self.avisos_label.setWordWrap(True)

        self.criar_button = QPushButton("Criar no IMOS")
        self.criar_button.setToolTip(
            "Criar as pastas em falta e a encomenda no iMos, tudo na mesma "
            "operação. Se alguma parte falhar, não fica nada criado."
        )
        self.criar_button.setEnabled(False)
        self.criar_button.clicked.connect(self._criar)

        self.recarregar_button = QPushButton("Verificar de novo")
        self.recarregar_button.setToolTip(
            "Voltar a ler o iMos e recalcular o que falta criar."
        )
        self.recarregar_button.clicked.connect(self._recarregar)

        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.setToolTip("Fechar sem criar nada.")
        self.fechar_button.clicked.connect(self.reject)

        botoes = QHBoxLayout()
        botoes.addWidget(self.recarregar_button)
        botoes.addStretch()
        botoes.addWidget(self.criar_button)
        botoes.addWidget(self.fechar_button)

        # A linha do supervisor acompanha o utilizador, como nos outros menus.
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("imosEncomendaStatus")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(self.cabecalho)
        layout.addWidget(grupo_caminho)
        layout.addWidget(grupo_nome)
        layout.addWidget(grupo_campos, stretch=1)
        layout.addWidget(self.avisos_label)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

        self._recarregar(primeira_vez=True)

    # ------------------------------------------------------------------
    # Carregamento
    # ------------------------------------------------------------------

    @property
    def criada(self) -> bool:
        """Indica se a encomenda chegou a ser criada nesta sessão do diálogo."""
        return self._criada

    def _recarregar(self, *_args, primeira_vez: bool = False) -> None:
        """Refaz o plano contra o iMos; nada é escrito nesta operação.

        Aceita argumentos posicionais porque também está ligada ao ``clicked``
        de um botão, que envia o estado de seleção.
        """
        nome = None if primeira_vez else self.nome_input.text().strip()
        self.status_label.setText("A ler o iMos…")
        try:
            with SessionLocal() as session:
                processo = session.get(Producao, self._processo_id)
                if processo is None:
                    raise ValueError("Obra não encontrada.")
                cfg = load_imos_config(session)
                self._escrita_ativa = carregar_escrita_ativa(session)
                plano = preparar(
                    session,
                    cfg,
                    processo,
                    nome_encomenda=nome,
                    pasta_ano=(
                        PASTA_ANO_ENSAIO if self.ensaio_check.isChecked() else None
                    ),
                )
        except (SQLAlchemyError, ValueError, RuntimeError, OSError) as error:
            self._plano = None
            self.criar_button.setEnabled(False)
            self.status_label.setText(f"Não foi possível preparar: {error}")
            return

        self._plano = plano
        if primeira_vez:
            self.nome_input.setText(plano.nome_encomenda)
        self._render()

    def _render(self) -> None:
        plano = self._plano
        if plano is None:
            return

        self._render_caminho(plano)
        self._render_campos(plano)
        self._render_nome(plano)
        self._render_avisos(plano)
        self._atualizar_contador()

    def _render_caminho(self, plano: PlanoCriacaoImos) -> None:
        niveis = plano.caminho.niveis
        etiquetas = ["Pasta raiz", "Ano", "Cliente", "Encomenda"]
        self.caminho_table.setRowCount(len(niveis))
        for linha, nivel in enumerate(niveis):
            if nivel.existe:
                estado = f"já existe (DIR_ID {nivel.dir_id})"
            elif nivel.tipo == IMOS_TIPO_ENCOMENDA:
                estado = "vai ser criada agora"
            else:
                estado = "vai ser criada (não existe)"
            valores = [
                etiquetas[linha] if linha < len(etiquetas) else "",
                nivel.nome,
                estado,
            ]
            for coluna, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                item.setToolTip(valor)
                if not nivel.existe:
                    item.setForeground(COR_EM_FALTA)
                self.caminho_table.setItem(linha, coluna, item)

    def _render_campos(self, plano: PlanoCriacaoImos) -> None:
        # A encomenda e os dados do cliente vão para tabelas diferentes do
        # iMos, mas o utilizador só quer ver uma lista do que fica gravado.
        linhas = [(campo, "PROADMIN") for campo in plano.campos]
        linhas += [(campo, "CMSINCIDENTADRESS") for campo in plano.contacto]

        self.campos_table.setRowCount(len(linhas))
        for linha, (campo, tabela) in enumerate(linhas):
            if campo.truncado:
                aviso = f"cortado de {len(campo.valor_original)} para {campo.limite}"
            elif campo.vazio:
                aviso = "vazio na obra"
            else:
                aviso = ""
            coluna_texto = (
                campo.coluna
                if tabela == "PROADMIN"
                else f"{campo.coluna} (dados do cliente)"
            )
            valores = [campo.etiqueta, coluna_texto, campo.valor, aviso]
            for coluna, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                item.setToolTip(campo.valor_original if coluna == 2 else valor)
                if campo.truncado:
                    item.setForeground(COR_AVISO)
                self.campos_table.setItem(linha, coluna, item)

    def _render_nome(self, plano: PlanoCriacaoImos) -> None:
        if plano.nome_truncado:
            self.nome_original_label.setText(
                f"O nome completo seria '{plano.nome_sugerido}' "
                f"({len(plano.nome_sugerido)} caracteres). Foi cortado para caber "
                f"nos {IMOS_NOME_MAX} do iMos — reveja-o."
            )
            self.nome_original_label.setStyleSheet(f"color: {COR_AVISO.name()};")
        else:
            self.nome_original_label.setText("")
            self.nome_original_label.setStyleSheet("")

    def _render_avisos(self, plano: PlanoCriacaoImos) -> None:
        partes: list[str] = []
        if plano.bloqueios:
            partes.append(
                "Não é possível criar:\n"
                + "\n".join(f"• {texto}" for texto in plano.bloqueios)
            )
        if plano.avisos:
            partes.append(
                "A confirmar:\n" + "\n".join(f"• {texto}" for texto in plano.avisos)
            )
        if not self._escrita_ativa:
            partes.append(
                "A escrita no iMos está desligada. Ligue a definição "
                f"'{KEY_IMOS_ESCRITA_ATIVA}' em Configurações > Definições do "
                "sistema para poder criar."
            )

        self.avisos_label.setText("\n\n".join(partes))
        self.avisos_label.setStyleSheet(
            f"color: {COR_AVISO.name()};" if plano.bloqueios else ""
        )

        pode = plano.pode_criar and self._escrita_ativa
        self.criar_button.setEnabled(pode)
        if not self._escrita_ativa:
            self.status_label.setText("Leitura concluída. A escrita no iMos está desligada.")
        elif plano.bloqueios:
            self.status_label.setText("Leitura concluída. Resolva os pontos a vermelho.")
        elif plano.pastas_a_criar:
            self.status_label.setText(
                "Pronto a criar: "
                f"{len(plano.pastas_a_criar)} pasta(s) e a encomenda."
            )
        else:
            self.status_label.setText("Pronto a criar a encomenda.")

    def _atualizar_contador(self) -> None:
        usados = len(self.nome_input.text().strip())
        self.contador_label.setText(f"{usados}/{IMOS_NOME_MAX}")
        excedeu = usados >= IMOS_NOME_MAX
        self.contador_label.setStyleSheet(
            f"color: {COR_AVISO.name()};" if excedeu else ""
        )

    # ------------------------------------------------------------------
    # Criação
    # ------------------------------------------------------------------

    def _criar(self) -> None:
        """Recalcula o plano com o nome atual e só depois cria."""
        self._recarregar()
        plano = self._plano
        if plano is None:
            return
        if not plano.pode_criar or not self._escrita_ativa:
            QMessageBox.warning(
                self,
                "Criar Encomenda IMOS",
                "\n".join(plano.bloqueios)
                or "A escrita no iMos está desligada.",
            )
            return

        pastas = plano.pastas_a_criar
        resumo = [f"Encomenda: {plano.nome_encomenda}", f"Em: {plano.caminho.texto()}"]
        if pastas:
            resumo.append("Pastas a criar: " + ", ".join(pastas))
        confirmacao = QMessageBox.question(
            self,
            "Criar Encomenda IMOS",
            "Confirma a criação no iMos?\n\n"
            + "\n".join(resumo)
            + "\n\nO iMos não tem desfazer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmacao != QMessageBox.StandardButton.Yes:
            self.status_label.setText("Criação cancelada. Nada foi alterado no iMos.")
            return

        self.criar_button.setEnabled(False)
        self.status_label.setText("A criar no iMos…")
        try:
            with SessionLocal() as session:
                cfg = load_imos_config(session)
                criados = executar(session, cfg, plano)
        except (SQLAlchemyError, ValueError, RuntimeError, OSError) as error:
            texto = explicar_erro_escrita(error)
            self.status_label.setText(f"Falhou: {texto}")
            QMessageBox.warning(
                self,
                "Criar Encomenda IMOS",
                f"{texto}\n\nNada ficou criado: a operação foi revertida.",
            )
            self._recarregar()
            return

        self._criada = True
        detalhe = "\n".join(
            f"• {no.nome} — DIR_ID {no.dir_id}, PROADMIN {no.proadmin_id}"
            for no in criados
        )
        self.status_label.setText("Encomenda criada no iMos.")
        QMessageBox.information(
            self,
            "Criar Encomenda IMOS",
            "Criado no iMos:\n\n"
            + detalhe
            + "\n\nNo iX Organizer prima ↻ para a árvore refrescar.",
        )
        self._recarregar()

    def keyPressEvent(self, event) -> None:  # noqa: N802 (API do Qt)
        """Enter no diálogo não pode disparar a criação por engano."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.ignore()
            return
        super().keyPressEvent(event)
