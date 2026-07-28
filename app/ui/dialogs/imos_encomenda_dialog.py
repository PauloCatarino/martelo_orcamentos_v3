"""Diálogo de criação da encomenda no iMos a partir de uma obra da Produção.

Nada é criado sem passar por aqui: o diálogo mostra o caminho que vai ser
percorrido, o nome que a encomenda vai ter (editável) e todos os valores que
vão para as colunas do iMos, incluindo o que teve de ser cortado.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
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

from app.core.session import app_session
from app.db.session import SessionLocal
from app.models.producao import Producao
from app.services.imos_encomenda_service import (
    COLUNAS_EDITAVEIS,
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
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras

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
        # Correções locais de TEXT_SHORT/TEXT_LONG: valem só para esta criação
        # e nunca são gravadas de volta na obra do Martelo.
        self._textos: dict[str, str] = {}
        self._a_render = False

        self.setWindowTitle("Criar Encomenda IMOS")
        self.setModal(True)
        self.setMinimumSize(960, 900)

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
        self.caminho_table.setMaximumHeight(170)
        # Larguras redimensionáveis e guardadas por utilizador, como nos
        # restantes menus.
        ligar_persistencia_larguras(self.caminho_table, "dialog_imos_encomenda_caminho")

        grupo_caminho = QGroupBox("Onde vai ser criada")
        layout_caminho = QVBoxLayout(grupo_caminho)
        layout_caminho.addWidget(self.caminho_table)

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

        # Aviso vivo do limite: o campo não deixa passar dos 30, mas o
        # utilizador tem de perceber porque é que parou de escrever.
        self.nome_limite_label = QLabel("")
        self.nome_limite_label.setWordWrap(True)

        linha_nome = QHBoxLayout()
        linha_nome.addWidget(self.nome_input, stretch=1)
        linha_nome.addWidget(self.contador_label)

        grupo_nome = QGroupBox("Nome da encomenda")
        layout_nome = QVBoxLayout(grupo_nome)
        layout_nome.addLayout(linha_nome)
        layout_nome.addWidget(self.nome_limite_label)
        layout_nome.addWidget(self.nome_original_label)

        # --- campos --------------------------------------------------------
        self.campos_table = QTableWidget(0, len(self.COLUNAS_CAMPOS))
        self.campos_table.setHorizontalHeaderLabels(self.COLUNAS_CAMPOS)
        self.campos_table.verticalHeader().setVisible(False)
        self.campos_table.setAlternatingRowColors(True)
        self.campos_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.campos_table.setToolTip(
            "Valores da obra já traduzidos para as colunas do iMos. A coluna "
            "Aviso indica o que teve de ser cortado para caber. As linhas da "
            "Descrição produção e das Matérias usados podem ser corrigidas "
            "aqui com duplo clique — a obra no Martelo não é alterada."
        )
        # A edição é permitida linha a linha; ver _render_campos.
        self.campos_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.SelectedClicked
        )
        self.campos_table.itemChanged.connect(self._campo_editado)
        ligar_persistencia_larguras(self.campos_table, "dialog_imos_encomenda_campos")

        self.editaveis_label = QLabel(
            "Duplo clique na Descrição produção ou nas Matérias usados para as "
            "corrigir só para esta encomenda. A obra no Martelo fica na mesma."
        )
        self.editaveis_label.setWordWrap(True)

        grupo_campos = QGroupBox("O que vai ser gravado na encomenda")
        layout_campos = QVBoxLayout(grupo_campos)
        layout_campos.addWidget(self.campos_table)
        layout_campos.addWidget(self.editaveis_label)

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
                    textos=self._textos,
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

        # A re-escrita da tabela dispara itemChanged; o _a_render impede que
        # isso seja confundido com uma edição do utilizador.
        self._a_render = True
        try:
            self.campos_table.setRowCount(len(linhas))
            for linha, (campo, tabela) in enumerate(linhas):
                editavel = campo.coluna in COLUNAS_EDITAVEIS
                if campo.truncado:
                    aviso = f"cortado de {len(campo.valor_original)} para {campo.limite}"
                elif campo.origem == "Editado aqui":
                    aviso = "editado aqui"
                elif campo.vazio:
                    aviso = "vazio na obra — pode escrever" if editavel else "vazio na obra"
                elif editavel:
                    aviso = "editável"
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
                    if coluna == 2 and editavel:
                        # O handler precisa de saber que coluna do iMos é esta
                        # e qual o limite dela.
                        item.setData(Qt.ItemDataRole.UserRole, campo.coluna)
                        item.setData(Qt.ItemDataRole.UserRole + 1, campo.limite)
                        dica = (
                            f"Duplo clique para corrigir (máximo {campo.limite} "
                            "caracteres). A obra no Martelo não é alterada."
                        )
                        # Num campo cortado, o valor original é a informação
                        # mais útil da dica: fica primeiro.
                        if campo.valor_original:
                            dica = f"{campo.valor_original}\n\n{dica}"
                        item.setToolTip(dica)
                    else:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.campos_table.setItem(linha, coluna, item)
        finally:
            self._a_render = False

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
        no_limite = usados >= IMOS_NOME_MAX
        self.contador_label.setStyleSheet(
            f"color: {COR_AVISO.name()};" if no_limite else ""
        )
        if no_limite:
            self.nome_limite_label.setText(
                f"Atingiu o máximo de {IMOS_NOME_MAX} caracteres que o iMos "
                "aceita no nome da encomenda — não é possível escrever mais."
            )
            self.nome_limite_label.setStyleSheet(f"color: {COR_AVISO.name()};")
        else:
            self.nome_limite_label.setText("")
            self.nome_limite_label.setStyleSheet("")

    def _campo_editado(self, item: QTableWidgetItem) -> None:
        """Guarda a correção local da Descrição produção / Matérias usados."""
        if self._a_render or item.column() != 2:
            return

        coluna = item.data(Qt.ItemDataRole.UserRole)
        if coluna not in COLUNAS_EDITAVEIS:
            return

        limite = int(item.data(Qt.ItemDataRole.UserRole + 1) or 0)
        texto = " ".join(str(item.text() or "").split())
        if len(texto) > limite:
            QMessageBox.warning(
                self,
                "Criar Encomenda IMOS",
                f"O iMos só aceita {limite} caracteres nesta coluna e escreveu "
                f"{len(texto)}. O texto foi cortado.",
            )
            texto = texto[:limite]

        self._textos[coluna] = texto
        self._recarregar()

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
                processo = session.get(Producao, self._processo_id)
                criados = executar(
                    session,
                    cfg,
                    plano,
                    processo=processo,
                    user_id=getattr(app_session.current_user, "id", None),
                )
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
