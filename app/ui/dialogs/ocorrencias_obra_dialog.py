"""Tickets de uma obra: o que aconteceu, de quem é e em que pé está."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain import ocorrencia_tipos as tipos
from app.models.producao import Producao
from app.services import teams_service
from app.services.equipa_service import listar_membros
from app.services.producao_ocorrencias_service import (
    atualizar_ocorrencia,
    eliminar_ocorrencia,
    formatar_data,
    listar_anexos,
    listar_ocorrencias,
    mudar_estado,
    registar_envio,
    registar_ocorrencia,
)
from app.ui import tema
from app.ui.dialogs.editar_ocorrencia_dialog import EditarOcorrenciaDialog
from app.ui.dialogs.equipa_dialog import EquipaDialog
from app.ui.dialogs.escolher_pessoas_teams_dialog import EscolherPessoasTeamsDialog
from app.ui.helpers.anexos_ocorrencia import guardar_anexos, resolver_pasta_obra
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.faixa_anexos import FaixaAnexos
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


#: Fundo e texto de cada família de classificação (ver ocorrencia_tipos).
CORES_FAMILIA = {
    "erro": (tema.VERMELHO_SUAVE, tema.VERMELHO_ESCURO),
    "aviso": (tema.OCRE_SUAVE, tema.OCRE_ESCURO),
    "ok": (tema.VERDE_SUAVE, tema.VERDE_ESCURO),
    "neutro": (tema.CINZA_SUAVE, tema.CINZA_ESCURO),
}

COLUNAS = ("Nº", "Data", "Tipo", "Assunto", "Resp.", "Estado", "Fotos")


class OcorrenciasObraDialog(QDialog):
    """Read, open and hand out this obra's tickets.

    Serve para o que os clientes reportam depois da entrega, para pedidos
    adicionais e para as assistências — sem sujar os campos da obra.
    """

    def __init__(self, *, producao_id: int, codigo_processo: str, parent=None) -> None:
        super().__init__(parent)

        self._producao_id = producao_id
        self._codigo_processo = codigo_processo
        self._processo: Producao | None = None
        self._pasta_obra: str | None = None
        self._linhas: list[dict] = []
        self._membros: list = []
        self._formato_teams = teams_service.FORMATO_PADRAO

        self.setWindowTitle(f"Ocorrências — {codigo_processo}")
        self.setModal(True)
        self.resize(1080, 720)

        cabecalho = QLabel(
            "Cada linha é um ticket desta obra: o que o cliente reportou, o que "
            "faltou, o que correu mal. As fotos ficam gravadas na pasta da obra "
            "e o ticket pode ser enviado à pessoa responsável pelo Teams."
        )
        cabecalho.setWordWrap(True)
        cabecalho.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")

        self.pesquisa = CampoPesquisa(
            label="Pesquisar:", placeholder="Pesquisar no assunto ou no texto…"
        )
        self.pesquisa.pesquisa_mudou.connect(lambda _texto: self.carregar())
        self.pesquisa.limpar_clicado.connect(self._limpar_filtros)

        self.tipo_filtro = self._combo_filtro("Tipo: todos", tipos.TIPOS, "Filtrar por tipo de ticket")
        self.estado_filtro = QComboBox()
        self.estado_filtro.setToolTip(
            "Filtrar por estado. Por omissão mostra tudo — os resolvidos ficam "
            "à vista, com a cor da coluna Estado a distingui-los."
        )
        # "Todos" à cabeça: um ticket que desaparece da tabela ao ser resolvido
        # deixa de se saber que existiu.
        self.estado_filtro.addItem("Estado: todos", None)
        self.estado_filtro.addItem("Estado: por resolver", "__abertos__")
        for estado in tipos.ESTADOS:
            self.estado_filtro.addItem(estado.rotulo, estado.chave)
        self.estado_filtro.currentIndexChanged.connect(lambda _i: self.carregar())

        self.responsavel_filtro = QComboBox()
        self.responsavel_filtro.setToolTip("Filtrar por responsável")
        self.responsavel_filtro.currentIndexChanged.connect(lambda _i: self.carregar())

        filtros = QHBoxLayout()
        filtros.addWidget(self.pesquisa)
        filtros.addWidget(self.tipo_filtro)
        filtros.addWidget(self.estado_filtro)
        filtros.addWidget(self.responsavel_filtro)
        filtros.addStretch()

        self.table = QTableWidget(0, len(COLUNAS))
        self.table.setHorizontalHeaderLabels(list(COLUNAS))
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._mostrar_detalhe)
        self.table.itemDoubleClicked.connect(lambda _item: self._editar())
        cabecalho_tabela = self.table.horizontalHeader()
        cabecalho_tabela.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        cabecalho_tabela.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for coluna, largura in ((0, 48), (1, 120), (2, 160), (4, 110), (5, 100), (6, 60)):
            self.table.setColumnWidth(coluna, largura)
        # Larguras que o utilizador ajustar ficam guardadas (a coluna Assunto
        # continua a esticar sozinha, por isso não se força tudo a interativa).
        ligar_persistencia_larguras(
            self.table, "ocorrencias_obra", forcar_interativas=False
        )

        self.detalhe_titulo = QLabel("")
        self.detalhe_titulo.setStyleSheet(f"color: {tema.CASTANHO_ESCURO}; font-weight: bold;")
        self.detalhe_titulo.setWordWrap(True)

        self.detalhe_texto = QTextEdit()
        self.detalhe_texto.setReadOnly(True)
        self.detalhe_texto.setMaximumHeight(110)
        self.detalhe_texto.setToolTip("Texto completo do ticket selecionado")

        self.detalhe_anexos = FaixaAnexos(altura=96)
        self.detalhe_anexos.setAcceptDrops(False)
        self.detalhe_anexos.setToolTip("Fotos deste ticket — duplo-clique abre")

        self.detalhe_envio = QLabel("")
        self.detalhe_envio.setWordWrap(True)

        self.novo_button = QPushButton("Novo ticket")
        self.novo_button.setToolTip("Abrir um ticket novo nesta obra")
        self.novo_button.clicked.connect(self._novo)

        self.editar_button = QPushButton("Editar")
        self.editar_button.setToolTip("Corrigir o ticket selecionado e juntar fotos")
        self.editar_button.clicked.connect(self._editar)

        self.estado_button = QPushButton("Mudar estado")
        self.estado_button.setToolTip("Marcar o ticket como em curso, resolvido ou anulado")
        self.estado_button.clicked.connect(self._menu_estado)

        self.teams_button = QPushButton("Enviar para Teams")
        self.teams_button.setToolTip(
            "Abrir a conversa do responsável no Teams com o ticket já escrito. "
            "As fotos ficam copiadas para colar a seguir com Ctrl+V."
        )
        self.teams_button.clicked.connect(self._enviar_teams)

        self.eliminar_button = QPushButton("Eliminar")
        self.eliminar_button.setToolTip("Eliminar o ticket selecionado — só quem o escreveu")
        self.eliminar_button.clicked.connect(self._eliminar)

        self.equipa_button = QPushButton("Equipa…")
        self.equipa_button.setToolTip("Gerir as pessoas e os endereços de Teams")
        self.equipa_button.clicked.connect(self._abrir_equipa)

        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.clicked.connect(self.accept)

        botoes = QHBoxLayout()
        for botao in (
            self.novo_button,
            self.editar_button,
            self.estado_button,
            self.teams_button,
            self.eliminar_button,
        ):
            botoes.addWidget(botao)
        botoes.addStretch()
        botoes.addWidget(self.equipa_button)
        botoes.addWidget(self.fechar_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("ocorrenciasStatus")
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(cabecalho)
        layout.addLayout(filtros)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.detalhe_titulo)
        layout.addWidget(self.detalhe_texto)
        layout.addWidget(self.detalhe_anexos)
        layout.addWidget(self.detalhe_envio)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

        self._carregar_contexto()
        self.carregar()

    # ---- contexto --------------------------------------------------------
    def _carregar_contexto(self) -> None:
        """Load the obra and the team once — muda pouco durante o diálogo."""
        try:
            with SessionLocal() as session:
                self._processo = session.get(Producao, self._producao_id)
                if self._processo is not None:
                    self._pasta_obra = resolver_pasta_obra(session, self._processo)
                self._membros = [
                    _Membro(int(m.id), m.nome, m.email) for m in listar_membros(session)
                ]
                self._formato_teams = teams_service.formato_configurado(session)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível ler os dados da obra.")

        self.responsavel_filtro.blockSignals(True)
        self.responsavel_filtro.clear()
        self.responsavel_filtro.addItem("Responsável: todos", None)
        for membro in self._membros:
            self.responsavel_filtro.addItem(membro.nome, membro.nome)
        self.responsavel_filtro.blockSignals(False)

    # ---- dados -----------------------------------------------------------
    def carregar(self) -> None:
        """Load this obra's tickets with the filters on screen."""
        estado = self.estado_filtro.currentData()
        try:
            with SessionLocal() as session:
                ocorrencias = listar_ocorrencias(
                    session,
                    self._producao_id,
                    tipo=self.tipo_filtro.currentData(),
                    estado=None if estado == "__abertos__" else estado,
                    apenas_abertos=estado == "__abertos__",
                    responsavel=self.responsavel_filtro.currentData(),
                    texto=self.pesquisa.texto(),
                )
                self._linhas = [
                    self._instantaneo(session, ocorrencia) for ocorrencia in ocorrencias
                ]
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar os tickets.")
            return

        self._render()

    @staticmethod
    def _instantaneo(session, ocorrencia) -> dict:
        """Copy the ticket out of the session so the dialog can close it."""
        anexos = [
            {
                "id": int(anexo.id),
                "caminho": anexo.caminho,
                "nome_original": anexo.nome_original,
            }
            for anexo in listar_anexos(session, int(ocorrencia.id))
        ]
        return {
            "id": int(ocorrencia.id),
            "numero": ocorrencia.numero,
            "created_at": ocorrencia.created_at,
            "autor": ocorrencia.autor,
            "user_id": ocorrencia.user_id,
            "assunto": ocorrencia.assunto,
            "texto": ocorrencia.texto,
            "tipo": ocorrencia.tipo,
            "gravidade": ocorrencia.gravidade,
            "origem": ocorrencia.origem,
            "estado": ocorrencia.estado,
            "responsavel": ocorrencia.responsavel,
            "responsavel_membro_id": ocorrencia.responsavel_membro_id,
            "custo_estimado": ocorrencia.custo_estimado,
            "resolvido_em": ocorrencia.resolvido_em,
            "resolvido_por": ocorrencia.resolvido_por,
            "enviado_em": ocorrencia.enviado_em,
            "enviado_para": ocorrencia.enviado_para,
            "enviado_via": ocorrencia.enviado_via,
            "anexos": anexos,
        }

    def _render(self) -> None:
        self.table.setRowCount(len(self._linhas))
        for indice, linha in enumerate(self._linhas):
            numero = QTableWidgetItem(tipos.rotulo_ticket(linha["numero"]))
            numero.setData(Qt.ItemDataRole.UserRole, linha["id"])
            self.table.setItem(indice, 0, numero)
            self.table.setItem(
                indice, 1, QTableWidgetItem(formatar_data(linha["created_at"]))
            )
            self.table.setItem(
                indice,
                2,
                self._badge(
                    tipos.rotulo_tipo(linha["tipo"]), tipos.familia_tipo(linha["tipo"])
                ),
            )
            assunto = QTableWidgetItem(linha["assunto"] or linha["texto"])
            assunto.setToolTip(linha["texto"])
            self.table.setItem(indice, 3, assunto)
            self.table.setItem(indice, 4, QTableWidgetItem(linha["responsavel"] or "—"))
            self.table.setItem(
                indice,
                5,
                self._badge(
                    tipos.rotulo_estado(linha["estado"]),
                    tipos.familia_estado(linha["estado"]),
                ),
            )
            total_anexos = len(linha["anexos"])
            fotos = QTableWidgetItem(str(total_anexos) if total_anexos else "—")
            fotos.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(indice, 6, fotos)

        if self._linhas:
            self.table.selectRow(0)
            abertos = sum(1 for linha in self._linhas if tipos.esta_aberto(linha["estado"]))
            self.status_label.setText(
                f"{len(self._linhas)} ticket(s), {abertos} por resolver."
            )
        else:
            self._limpar_detalhe()
            self.status_label.setText("Sem tickets nesta obra com estes filtros.")

    @staticmethod
    def _badge(texto: str, familia: str) -> QTableWidgetItem:
        item = QTableWidgetItem(texto)
        fundo, cor = CORES_FAMILIA.get(familia, CORES_FAMILIA["neutro"])
        item.setBackground(QColor(fundo))
        item.setForeground(QColor(cor))
        return item

    # ---- detalhe ---------------------------------------------------------
    def _linha_selecionada(self) -> dict | None:
        indice = self.table.currentRow()
        if 0 <= indice < len(self._linhas):
            return self._linhas[indice]
        return None

    def _mostrar_detalhe(self) -> None:
        linha = self._linha_selecionada()
        if linha is None:
            self._limpar_detalhe()
            return

        referencia = tipos.rotulo_ticket(linha["numero"])
        partes = [
            f"{referencia} · {linha['assunto'] or '(sem assunto)'}",
            f"{tipos.rotulo_tipo(linha['tipo'])} · gravidade {tipos.rotulo_gravidade(linha['gravidade']).lower()}"
            f" · origem {tipos.rotulo_origem(linha['origem']).lower()}",
            f"{linha['autor'] or '—'} · {formatar_data(linha['created_at'])}",
        ]
        self.detalhe_titulo.setText("   |   ".join(partes))
        self.detalhe_texto.setPlainText(linha["texto"] or "")
        self.detalhe_anexos.carregar([_Anexo(**anexo) for anexo in linha["anexos"]])
        self.detalhe_envio.setText(self._texto_envio(linha))

    def _texto_envio(self, linha: dict) -> str:
        if linha["enviado_em"]:
            self.detalhe_envio.setStyleSheet(f"color: {tema.TEXTO_OK};")
            via = (linha["enviado_via"] or "").capitalize() or "chat"
            return (
                f"Enviado a {linha['enviado_para'] or '—'} no {via} — "
                f"{formatar_data(linha['enviado_em'])}"
            )
        if linha["resolvido_em"]:
            self.detalhe_envio.setStyleSheet(f"color: {tema.TEXTO_OK};")
            return (
                f"Resolvido por {linha['resolvido_por'] or '—'} em "
                f"{formatar_data(linha['resolvido_em'])}"
            )
        self.detalhe_envio.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")
        return "Ainda não foi enviado a ninguém."

    def _limpar_detalhe(self) -> None:
        self.detalhe_titulo.setText("")
        self.detalhe_texto.clear()
        self.detalhe_anexos.carregar([])
        self.detalhe_envio.setText("")

    def _limpar_filtros(self) -> None:
        self.tipo_filtro.setCurrentIndex(0)
        self.estado_filtro.setCurrentIndex(0)
        self.responsavel_filtro.setCurrentIndex(0)
        self.carregar()

    # ---- ações -----------------------------------------------------------
    def _novo(self) -> None:
        dialog = EditarOcorrenciaDialog(
            self, codigo_processo=self._codigo_processo, membros=self._membros
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        dados = dialog.dados()
        utilizador = app_session.current_user
        avisos: list[str] = []
        try:
            with SessionLocal() as session:
                ocorrencia = registar_ocorrencia(
                    session,
                    producao_id=self._producao_id,
                    user_id=getattr(utilizador, "id", None),
                    autor=getattr(utilizador, "nome", None)
                    or getattr(utilizador, "username", None),
                    **dados,
                )
                avisos = guardar_anexos(
                    session,
                    ocorrencia=ocorrencia,
                    pasta_obra=self._pasta_obra,
                    pendentes=dialog.anexos_pendentes(),
                    user_id=getattr(utilizador, "id", None),
                )
                referencia = tipos.rotulo_ticket(ocorrencia.numero)
                session.commit()
        except ValueError as erro:
            self.status_label.setText(str(erro))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível gravar o ticket.")
            return

        self.carregar()
        self.status_label.setText(
            " ".join([f"Ticket {referencia} registado.", *avisos]).strip()
        )

    def _editar(self) -> None:
        linha = self._linha_selecionada()
        if linha is None:
            self.status_label.setText("Selecione um ticket para editar.")
            return

        utilizador = app_session.current_user
        user_id = getattr(utilizador, "id", None)
        is_admin = str(getattr(utilizador, "role", "")).lower() == "admin"
        pode_editar = is_admin or (user_id is not None and linha["user_id"] == user_id)

        dialog = EditarOcorrenciaDialog(
            self,
            codigo_processo=self._codigo_processo,
            ocorrencia=_Ticket(linha),
            anexos=[_Anexo(**anexo) for anexo in linha["anexos"]],
            membros=self._membros,
            pode_editar=pode_editar,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        dados = dialog.dados()
        estado = dados.pop("estado")
        avisos: list[str] = []
        try:
            with SessionLocal() as session:
                if pode_editar:
                    atualizar_ocorrencia(
                        session, linha["id"], user_id=user_id, is_admin=is_admin, **dados
                    )
                if estado != tipos.normalizar_estado(linha["estado"]):
                    mudar_estado(
                        session,
                        linha["id"],
                        estado=estado,
                        autor=getattr(utilizador, "nome", None)
                        or getattr(utilizador, "username", None),
                    )
                avisos = guardar_anexos(
                    session,
                    ocorrencia=_Ticket(linha),
                    pasta_obra=self._pasta_obra,
                    pendentes=dialog.anexos_pendentes(),
                    removidos=dialog.anexos_removidos(),
                    user_id=user_id,
                )
                session.commit()
        except ValueError as erro:
            self.status_label.setText(str(erro))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível gravar as alterações.")
            return

        self.carregar()
        self.status_label.setText(" ".join(["Ticket atualizado.", *avisos]).strip())

    def _menu_estado(self) -> None:
        linha = self._linha_selecionada()
        if linha is None:
            self.status_label.setText("Selecione um ticket para mudar o estado.")
            return

        menu = QMenu(self)
        acoes = {menu.addAction(estado.rotulo): estado.chave for estado in tipos.ESTADOS}
        escolhida = menu.exec(self.estado_button.mapToGlobal(self.estado_button.rect().bottomLeft()))
        if escolhida is None:
            return

        utilizador = app_session.current_user
        try:
            with SessionLocal() as session:
                mudar_estado(
                    session,
                    linha["id"],
                    estado=acoes[escolhida],
                    autor=getattr(utilizador, "nome", None)
                    or getattr(utilizador, "username", None),
                )
                session.commit()
        except ValueError as erro:
            self.status_label.setText(str(erro))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível mudar o estado.")
            return

        self.carregar()
        self.status_label.setText(
            f"Ticket marcado como {tipos.rotulo_estado(acoes[escolhida]).lower()}."
        )

    def _enviar_teams(self) -> None:
        linha = self._linha_selecionada()
        if linha is None:
            self.status_label.setText("Selecione um ticket para enviar.")
            return

        if not self._membros:
            QMessageBox.information(
                self,
                "Enviar para Teams",
                "A equipa está vazia. Abra 'Equipa…' e acrescente as pessoas "
                "com o respetivo endereço de Teams.",
            )
            return

        responsavel = self._membro_do_ticket(linha)
        escolha = EscolherPessoasTeamsDialog(
            self,
            membros=self._membros,
            pre_selecionados=[responsavel.id] if responsavel is not None else [],
        )
        if escolha.exec() != QDialog.DialogCode.Accepted:
            return

        anexos = [_Anexo(**anexo) for anexo in linha["anexos"]]
        mensagem = teams_service.montar_texto_ticket(
            self._processo, _Ticket(linha), anexos
        )
        fotos = teams_service.caminhos_de_anexos(anexos)
        self._copiar_para_area_transferencia(mensagem, fotos)
        recado = " As fotos ficaram copiadas: no Teams, Ctrl+V." if fotos else ""

        if escolha.apenas_copiar():
            self.status_label.setText(f"Ticket copiado.{recado}")
            return

        destinatarios = escolha.escolhidos()
        if not destinatarios:
            self.status_label.setText(f"Ticket copiado.{recado}")
            return

        enderecos = [membro.email for membro in destinatarios]
        nomes = ", ".join(membro.nome for membro in destinatarios)
        if not teams_service.abrir_chat_teams(
            enderecos, mensagem, formato=self._formato_teams
        ):
            self.status_label.setText(
                "Não foi possível abrir o Teams. O ticket ficou copiado — cole "
                "com Ctrl+V."
            )
            return

        try:
            with SessionLocal() as session:
                registar_envio(
                    session,
                    linha["id"],
                    para=nomes,
                    via="teams",
                    quando=datetime.now(),
                )
                session.commit()
        except (ValueError, SQLAlchemyError):
            self.status_label.setText(
                "Teams aberto, mas não foi possível gravar o envio no ticket."
            )
            return

        self.carregar()
        self.status_label.setText(
            f"Teams aberto na conversa de {nomes} com o ticket escrito.{recado}"
        )

    def _copiar_para_area_transferencia(self, mensagem: str, fotos) -> None:
        """Put the text on the clipboard — e os ficheiros, se os houver.

        No Teams, um Ctrl+V a seguir anexa as fotos à mensagem. Sem fotos fica
        só o texto, que é o que serve para colar em qualquer chat.
        """
        area = QApplication.clipboard()
        if not fotos:
            area.setText(mensagem)
            return

        from PySide6.QtCore import QMimeData, QUrl

        dados = QMimeData()
        dados.setText(mensagem)
        dados.setUrls([QUrl.fromLocalFile(caminho) for caminho in fotos])
        area.setMimeData(dados)

    def _membro_do_ticket(self, linha: dict):
        """Team member of this ticket: pelo id se foi escolhido, senão pelo nome."""
        membro_id = linha.get("responsavel_membro_id")
        if membro_id is not None:
            for membro in self._membros:
                if membro.id == int(membro_id):
                    return membro

        nome = (linha.get("responsavel") or "").strip().lower()
        if not nome:
            return None
        for membro in self._membros:
            if membro.nome.strip().lower() == nome:
                return membro
        return None

    def _eliminar(self) -> None:
        linha = self._linha_selecionada()
        if linha is None:
            self.status_label.setText("Selecione um ticket para eliminar.")
            return

        referencia = tipos.rotulo_ticket(linha["numero"])
        resposta = QMessageBox.question(
            self,
            "Eliminar ticket",
            f"Eliminar o ticket {referencia} desta obra?\n\n"
            "As fotos continuam na pasta da obra.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        utilizador = app_session.current_user
        try:
            with SessionLocal() as session:
                eliminar_ocorrencia(
                    session,
                    linha["id"],
                    user_id=getattr(utilizador, "id", None),
                    is_admin=str(getattr(utilizador, "role", "")).lower() == "admin",
                )
                session.commit()
        except ValueError as erro:
            self.status_label.setText(str(erro))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível eliminar o ticket.")
            return

        self.carregar()
        self.status_label.setText(f"Ticket {referencia} eliminado.")

    def _abrir_equipa(self) -> None:
        EquipaDialog(self).exec()
        self._carregar_contexto()
        self.carregar()

    # ---- apoio -----------------------------------------------------------
    def _combo_filtro(self, primeiro: str, itens, tooltip: str) -> QComboBox:
        combo = QComboBox()
        combo.setToolTip(tooltip)
        combo.addItem(primeiro, None)
        for item in itens:
            combo.addItem(item.rotulo, item.chave)
        combo.currentIndexChanged.connect(lambda _i: self.carregar())
        return combo


class _Membro:
    """Team member copied out of the session."""

    __slots__ = ("id", "nome", "email")

    def __init__(self, identificador: int, nome: str, email: str | None) -> None:
        self.id = identificador
        self.nome = nome
        self.email = email


class _Anexo:
    """Attachment copied out of the session."""

    __slots__ = ("id", "caminho", "nome_original")

    def __init__(self, id: int, caminho: str, nome_original: str | None = None) -> None:  # noqa: A002
        self.id = id
        self.caminho = caminho
        self.nome_original = nome_original


class _Ticket:
    """Ticket copied out of the session, so the dialogs can read it freely."""

    def __init__(self, linha: dict) -> None:
        for chave, valor in linha.items():
            if chave != "anexos":
                setattr(self, chave, valor)
