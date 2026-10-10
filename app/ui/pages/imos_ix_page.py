"""Menu IMOS IX: ferramentas do iX CAD neste PC, uma por separador.

Nasceu a 10-10-2026 com as «Traduções do iX» (o antigo
``AtualizaIMOSMsgPTG.exe``, que já não servia para o iX 2025). As próximas
funcionalidades do iMos entram aqui como separadores novos.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core import diario_bordo
from app.db.session import SessionLocal
from app.services import imos_traducoes_service as servico
from app.ui import tema
from app.ui.dialogs.imos_traducoes_dialogs import (
    AplicarTraducoesDialog,
    ReporCopiaDialog,
    estilo_ficha,
    garantir_programas_fechados,
)
from app.ui.helpers import traducoes_imos as config
from app.ui.helpers.tabela_copiavel import DICA_TABELA, tornar_copiavel
from app.ui.widgets.barra_cabecalho import BarraCabecalho

COLUNAS = ("Referência", "Texto que o iX mostra agora", "Texto da empresa (Excel)", "Estado")
COL_ESTADO = 3

_ESTADOS = {
    servico.ESTADO_CERTA: ("Já está", tema.CINZA_SUAVE, tema.CINZA_ESCURO),
    servico.ESTADO_POR_APLICAR: ("Vai mudar", tema.OCRE_SUAVE, tema.OCRE_ESCURO),
    servico.ESTADO_NAO_EXISTE: ("Não existe no iX", tema.VERMELHO_SUAVE, tema.VERMELHO_ESCURO),
}
_ORDEM_ESTADOS = {servico.ESTADO_POR_APLICAR: 0, servico.ESTADO_NAO_EXISTE: 1, servico.ESTADO_CERTA: 2}


class TraducoesIxAba(QWidget):
    """Separador «Traduções do iX»: comparar o imos.msg com o Excel e aplicar."""

    def __init__(self, *, user_id: int | None, admin: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._user_id = user_id
        self._admin = admin
        self._msg: Path | None = None
        self._lista: servico.ListaTraducoes | None = None
        self._estados: list[servico.EstadoTraducao] = []

        explica = QLabel(
            "Muda os textos em português do iX CAD (ficheiro <b>imos.msg</b>) para os "
            "nomes que a empresa usa — por exemplo o «Kommission» do iX passa a "
            "«Enc PHC:». A lista vem do Excel partilhado: quando lá acrescentar uma "
            "linha, volte aqui e aplique. <b>Antes de mexer, o Martelo faz sempre "
            "uma cópia do imos.msg</b> na mesma pasta."
        )
        explica.setWordWrap(True)
        explica.setStyleSheet(
            f"background-color: {tema.BEGE_CLARO}; border: 1px solid {tema.CINZA_CASTANHO};"
            " border-radius: 4px; padding: 8px;"
        )

        # ---- caminhos ----------------------------------------------------
        self.msg_edit = QLineEdit()
        self.msg_edit.setReadOnly(True)
        self.msg_edit.setStyleSheet(tema.ESTILO_CAMPO_BLOQUEADO)
        self.msg_edit.setToolTip(
            "O ficheiro das traduções do iX CAD deste PC. Encontra-se sozinho (o "
            "iX mais recente instalado); para escolher outro use «Procurar…»."
        )
        self.msg_procurar_button = QPushButton("Procurar…")
        self.msg_procurar_button.setToolTip(
            "Escolher outro imos.msg (só se o iX estiver instalado noutro sítio). "
            "A escolha fica só neste PC."
        )
        self.msg_procurar_button.clicked.connect(self._procurar_msg)
        self.msg_auto_button = QPushButton("Encontrar sozinho")
        self.msg_auto_button.setToolTip(
            "Esquecer o ficheiro escolhido à mão e voltar a usar o do iX CAD mais "
            "recente instalado neste PC"
        )
        self.msg_auto_button.clicked.connect(self._msg_automatico)
        self.msg_auto_button.setVisible(False)
        self.msg_pasta_button = QPushButton("Abrir pasta")
        self.msg_pasta_button.setToolTip(
            "Abrir no Explorador a pasta MSG do iX, onde ficam também as cópias"
        )
        self.msg_pasta_button.clicked.connect(self._abrir_pasta_msg)
        self.msg_nota = QLabel()
        self.msg_nota.setWordWrap(True)

        self.excel_edit = QLineEdit()
        self.excel_edit.setReadOnly(True)
        self.excel_edit.setStyleSheet(tema.ESTILO_CAMPO_BLOQUEADO)
        self.excel_edit.setToolTip(
            "O Excel das traduções (coluna B = referência, ex.: PTG;10280; coluna C "
            "= texto da empresa). É o mesmo para todos: só o administrador o muda."
        )
        self.excel_abrir_button = QPushButton("Abrir Excel")
        self.excel_abrir_button.setToolTip("Abrir o Excel para acrescentar ou corrigir traduções")
        self.excel_abrir_button.clicked.connect(self._abrir_excel)
        self.excel_procurar_button = QPushButton("Procurar…")
        self.excel_procurar_button.setToolTip(
            "Escolher outro Excel das traduções (muda para todos os PCs)"
            if admin
            else "Só o administrador muda o Excel das traduções (é o mesmo para todos)."
        )
        self.excel_procurar_button.setEnabled(admin)
        self.excel_procurar_button.clicked.connect(self._procurar_excel)

        campos = QGridLayout()
        campos.addWidget(QLabel("<b>Ficheiro do iX</b>"), 0, 0)
        campos.addWidget(self.msg_edit, 0, 1)
        campos.addWidget(self.msg_procurar_button, 0, 2)
        campos.addWidget(self.msg_pasta_button, 0, 3)
        campos.addWidget(self.msg_nota, 1, 1, 1, 2)
        campos.addWidget(self.msg_auto_button, 1, 3)
        campos.addWidget(QLabel("<b>Excel das traduções</b>"), 2, 0)
        campos.addWidget(self.excel_edit, 2, 1)
        campos.addWidget(self.excel_abrir_button, 2, 2)
        campos.addWidget(self.excel_procurar_button, 2, 3)
        campos.setColumnStretch(1, 1)

        # ---- fichas de estado ---------------------------------------------
        self.ficha_cad = QLabel()
        self.ficha_org = QLabel()
        self.ficha_excel = QLabel()
        self.ficha_certas = QLabel()
        self.ficha_por_aplicar = QLabel()
        self.ficha_nao_existe = QLabel()
        fichas = QHBoxLayout()
        for ficha in (
            self.ficha_cad,
            self.ficha_org,
            self.ficha_excel,
            self.ficha_certas,
            self.ficha_por_aplicar,
            self.ficha_nao_existe,
        ):
            fichas.addWidget(ficha)
        fichas.addStretch()

        # ---- tabela --------------------------------------------------------
        self.table = QTableWidget(0, len(COLUNAS))
        self.table.setHorizontalHeaderLabels(list(COLUNAS))
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tornar_copiavel(self.table)
        self.table.setToolTip(
            "Cada linha do Excel e o texto que o iX deste PC mostra hoje.\n\n" + DICA_TABELA
        )
        cabecalho = self.table.horizontalHeader()
        cabecalho.setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
        cabecalho.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        cabecalho.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 110)
        self.table.setColumnWidth(COL_ESTADO, 130)

        # ---- aviso + botões -------------------------------------------------
        self.aviso_check = QCheckBox(
            "Avisar ao entrar no Martelo quando este PC tiver traduções por aplicar"
        )
        self.aviso_check.setToolTip(
            "Uma vez por dia (dias úteis), se o Excel tiver linhas novas ou se o iX "
            "voltar aos textos de fábrica (reinstalado ou atualizado). O aviso só "
            "pergunta: nunca mexe no ficheiro sozinho. Fica na sua conta."
        )
        self.aviso_check.setChecked(True)
        self.aviso_check.toggled.connect(self._guardar_aviso)

        self.verificar_button = QPushButton("Verificar outra vez")
        self.verificar_button.setToolTip(
            "Voltar a ler o Excel e o imos.msg e ver se o iX CAD e o Organizer estão abertos"
        )
        self.verificar_button.clicked.connect(self.verificar)
        self.aplicar_button = QPushButton("Aplicar traduções")
        self.aplicar_button.setToolTip(
            "Faz uma cópia do imos.msg e põe-lhe os textos do Excel. Pede para "
            "fechar o iX CAD e o iX Organizer."
        )
        self.aplicar_button.clicked.connect(self.aplicar)
        self.repor_button = QPushButton("Repor uma cópia…")
        self.repor_button.setToolTip(
            "Voltar a pôr uma das cópias feitas antes (se uma tradução correr mal). "
            "Nenhuma cópia é apagada."
        )
        self.repor_button.clicked.connect(self._repor)
        botoes = QHBoxLayout()
        botoes.addWidget(self.verificar_button)
        botoes.addWidget(self.aplicar_button)
        botoes.addWidget(self.repor_button)
        botoes.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("imosTraducoesStatus")
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(explica)
        layout.addLayout(campos)
        layout.addLayout(fichas)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.aviso_check)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

        self._carregar_aviso()

    # ------------------------------------------------------------------
    def _supervisor(self, texto: str, cor: str = tema.CASTANHO_ESCURO) -> None:
        self.status_label.setText(texto)
        self.status_label.setStyleSheet(f"color: {cor};")

    def _carregar_aviso(self) -> None:
        if self._user_id is None:
            self.aviso_check.setEnabled(False)
            return
        try:
            with SessionLocal() as session:
                ligado = config.aviso_ligado(session, self._user_id)
        except Exception:  # noqa: BLE001 - sem base fica ligado
            return
        self.aviso_check.blockSignals(True)
        self.aviso_check.setChecked(ligado)
        self.aviso_check.blockSignals(False)

    def _guardar_aviso(self, ligado: bool) -> None:
        if self._user_id is None:
            return
        try:
            from app.services.user_pref_service import UserPrefService

            with SessionLocal() as session:
                UserPrefService(session).guardar_valor(
                    self._user_id, config.PREF_AVISO, "1" if ligado else "0"
                )
        except Exception as erro:  # noqa: BLE001
            self._supervisor(f"Não foi possível guardar a preferência do aviso: {erro}", tema.TEXTO_ERRO)
            return
        self._supervisor(
            "Aviso ligado: avisa ao entrar no Martelo quando houver traduções por aplicar."
            if ligado
            else "Aviso desligado: as traduções só se verificam aqui, neste menu."
        )

    def _excel(self) -> str:
        try:
            with SessionLocal() as session:
                return config.caminho_excel(session)
        except Exception:  # noqa: BLE001 - sem base, o Excel de sempre
            return servico.EXCEL_PADRAO

    def _mostrar_programas(self) -> dict[str, bool]:
        estados = servico.estado_programas()
        for ficha, nome in ((self.ficha_cad, "iX CAD"), (self.ficha_org, "iX Organizer")):
            aberto = estados.get(nome, False)
            ficha.setText(f"● {nome}: {'aberto' if aberto else 'fechado'}")
            ficha.setStyleSheet(
                estilo_ficha(tema.OCRE_SUAVE, tema.OCRE_ESCURO)
                if aberto
                else estilo_ficha(tema.VERDE_SUAVE, tema.VERDE_ESCURO)
            )
        return estados

    def verificar(self) -> None:
        """Lê o Excel e o imos.msg deste PC e mostra o que falta aplicar."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._verificar()
        finally:
            QApplication.restoreOverrideCursor()

    def _verificar(self) -> None:
        programas = self._mostrar_programas()
        self._msg, manual = config.caminho_imos_msg()
        excel = self._excel()
        self.excel_edit.setText(excel)
        if self._msg is None:
            self.msg_edit.setText("")
            self.msg_nota.setText(
                "✗ Não encontrei o iX CAD neste PC. Se estiver instalado noutro sítio, "
                "use «Procurar…»."
            )
            self.msg_nota.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
        else:
            self.msg_edit.setText(str(self._msg))
            versao = servico.versao_do_caminho(self._msg)
            self.msg_nota.setText(
                f"✓ Escolhido à mão neste PC{f' ({versao})' if versao else ''}."
                if manual
                else f"✓ Encontrado: {versao or 'iX CAD'} (o mais recente instalado neste PC)."
            )
            self.msg_nota.setStyleSheet(f"color: {tema.TEXTO_OK};")
        self.msg_pasta_button.setEnabled(self._msg is not None)
        self.msg_auto_button.setVisible(manual)

        self._lista, self._estados = None, []
        try:
            self._lista = servico.ler_excel(excel)
            if self._msg is not None:
                self._estados = servico.comparar(self._msg, self._lista)
            else:
                self._estados = [
                    servico.EstadoTraducao(t.chave, None, t.texto) for t in self._lista.traducoes
                ]
        except servico.ErroTraducoes as erro:
            self._preencher([])
            self._supervisor(str(erro).replace("\n\n", " ").replace("\n", " "), tema.TEXTO_ERRO)
            self._atualizar_botoes()
            return
        self._preencher(self._estados)
        self._atualizar_botoes()

        por_aplicar = servico.contar_por_aplicar(self._estados)
        abertos = [nome for nome, aberto in programas.items() if aberto]
        if self._msg is None:
            self._supervisor("Sem o iX CAD neste PC não há nada para aplicar.", tema.TEXTO_AVISO)
        elif por_aplicar == 0:
            self._supervisor(
                f"Tudo certo: as {len(self._estados)} traduções do Excel já estão neste PC.",
                tema.TEXTO_OK,
            )
        else:
            texto = f"{por_aplicar} tradução(ões) por aplicar neste PC."
            if abertos:
                texto += " Feche o " + " e o ".join(abertos) + " antes de aplicar."
            self._supervisor(texto, tema.TEXTO_AVISO)
        if self._lista is not None and self._lista.repetidas:
            self.status_label.setText(
                self.status_label.text()
                + " Repetidas no Excel (vale a última linha): "
                + ", ".join(self._lista.repetidas)
                + "."
            )

    def _preencher(self, estados: list[servico.EstadoTraducao]) -> None:
        # O que vai mudar fica em cima; o resto pela ordem do Excel.
        estados = sorted(estados, key=lambda e: _ORDEM_ESTADOS[e.estado])
        self.table.setRowCount(len(estados))
        contagem = {chave: 0 for chave in _ESTADOS}
        for linha, estado in enumerate(estados):
            nome, fundo, texto = _ESTADOS[estado.estado]
            contagem[estado.estado] += 1
            atual = "—" if estado.texto_atual is None else estado.texto_atual
            valores = (estado.chave, atual, estado.texto_novo, nome)
            for coluna, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                item.setToolTip(valor)
                if estado.estado != servico.ESTADO_CERTA:
                    item.setBackground(QBrush(QColor(fundo)))
                if coluna == COL_ESTADO:
                    item.setForeground(QBrush(QColor(texto)))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(linha, coluna, item)
        total = len(estados)
        self.ficha_excel.setText(f"Excel: {total} traduções")
        self.ficha_excel.setStyleSheet(estilo_ficha(tema.AZUL_SUAVE, tema.AZUL_ESCURO))
        self.ficha_certas.setText(f"{contagem[servico.ESTADO_CERTA]} já certas")
        self.ficha_certas.setStyleSheet(estilo_ficha(tema.VERDE_SUAVE, tema.VERDE_ESCURO))
        por_aplicar = contagem[servico.ESTADO_POR_APLICAR]
        self.ficha_por_aplicar.setText(f"{por_aplicar} por aplicar")
        self.ficha_por_aplicar.setStyleSheet(
            estilo_ficha(tema.OCRE_SUAVE, tema.OCRE_ESCURO)
            if por_aplicar
            else estilo_ficha(tema.CINZA_SUAVE, tema.CINZA_ESCURO)
        )
        nao_existe = contagem[servico.ESTADO_NAO_EXISTE]
        self.ficha_nao_existe.setText(f"{nao_existe} não existem no iX")
        self.ficha_nao_existe.setStyleSheet(estilo_ficha(tema.VERMELHO_SUAVE, tema.VERMELHO_ESCURO))
        self.ficha_nao_existe.setVisible(bool(nao_existe) and self._msg is not None)
        self.ficha_nao_existe.setToolTip(
            "Referências do Excel que o imos.msg deste PC não tem (escritas mal no "
            "Excel, ou de outra versão do iX). Não se aplicam."
        )

    def _atualizar_botoes(self) -> None:
        tem_ficheiro = self._msg is not None
        self.aplicar_button.setEnabled(tem_ficheiro and self._lista is not None)
        self.repor_button.setEnabled(tem_ficheiro)

    # ------------------------------------------------------------------
    def aplicar(self) -> None:
        # O Excel ou o ficheiro podem ter mudado desde a última leitura.
        self.verificar()
        if self._msg is None or self._lista is None:
            return
        if servico.contar_por_aplicar(self._estados) == 0:
            self._supervisor(
                f"Nada para aplicar: as {len(self._estados)} traduções do Excel já estão neste PC.",
                tema.TEXTO_OK,
            )
            return
        if not garantir_programas_fechados(self):
            self._supervisor("Cancelado: nada foi alterado.", tema.CASTANHO_ESCURO)
            self._mostrar_programas()
            return
        dialogo = AplicarTraducoesDialog(self._msg, self._lista, self)
        dialogo.exec()
        resultado, erro = dialogo.resultado, dialogo.erro
        self.verificar()
        if resultado is not None and resultado.alteradas:
            copia = resultado.copia.name if resultado.copia else ""
            self._supervisor(
                f"{len(resultado.alteradas)} tradução(ões) aplicada(s). Cópia de antes: "
                f"{copia}. Pode abrir o iX CAD.",
                tema.TEXTO_OK,
            )
        elif erro:
            self._supervisor(f"Não foi possível aplicar: {erro}", tema.TEXTO_ERRO)

    def _repor(self) -> None:
        if self._msg is None:
            return
        dialogo = ReporCopiaDialog(self._msg, self)
        if dialogo.exec() and dialogo.reposta is not None:
            self.verificar()
            self._supervisor(
                f"Cópia reposta: {dialogo.reposta.name}. O ficheiro que lá estava ficou guardado numa cópia nova.",
                tema.TEXTO_OK,
            )

    def _procurar_msg(self) -> None:
        inicio = str(self._msg.parent) if self._msg else str(servico.PASTA_PROGRAMAS_IMOS)
        caminho, _filtro = QFileDialog.getOpenFileName(
            self, "Escolher o imos.msg do iX", inicio, "Traduções do iX (imos.msg);;Todos (*.*)"
        )
        if not caminho:
            return
        config.guardar_caminho_neste_pc(caminho)
        diario_bordo.registar_acao("Traduções do iX: imos.msg escolhido", caminho)
        self.verificar()

    def _msg_automatico(self) -> None:
        config.guardar_caminho_neste_pc("")
        diario_bordo.registar_acao("Traduções do iX: imos.msg encontrado sozinho")
        self.verificar()

    def _procurar_excel(self) -> None:
        if not self._admin:
            return
        atual = self.excel_edit.text().strip() or servico.EXCEL_PADRAO
        caminho, _filtro = QFileDialog.getOpenFileName(
            self, "Escolher o Excel das traduções", str(Path(atual).parent), "Excel (*.xlsx *.xlsm)"
        )
        if not caminho:
            return
        try:
            from app.services.system_setting_service import SystemSettingService

            with SessionLocal() as session:
                SystemSettingService(session).guardar_valor(servico.CHAVE_EXCEL, caminho)
        except Exception as erro:  # noqa: BLE001
            QMessageBox.warning(self, "Excel das traduções", f"Não foi possível guardar:\n{erro}")
            return
        diario_bordo.registar_acao("Traduções do iX: Excel escolhido", caminho)
        self.verificar()

    def _abrir_excel(self) -> None:
        self._abrir(self.excel_edit.text().strip() or servico.EXCEL_PADRAO)

    def _abrir_pasta_msg(self) -> None:
        if self._msg is not None:
            self._abrir(str(self._msg.parent))

    def _abrir(self, caminho: str) -> None:
        try:
            os.startfile(caminho)  # noqa: S606 - ficheiro/pasta escolhidos pelo Martelo
        except OSError as erro:
            QMessageBox.warning(self, "Abrir", f"Não foi possível abrir:\n{caminho}\n\n{erro}")


class ImosIxPage(QWidget):
    """O menu IMOS IX (um separador por ferramenta)."""

    def __init__(self, *, user_id: int | None, admin: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.cabecalho = BarraCabecalho("IMOS IX", ["Ferramentas do iX CAD neste PC"])
        self.traducoes = TraducoesIxAba(user_id=user_id, admin=admin)
        self.abas = QTabWidget()
        self.abas.addTab(self.traducoes, "Traduções do iX")
        self.abas.setTabToolTip(
            0, "Pôr no iX CAD deste PC os nomes dos campos que a empresa usa (Excel das traduções)"
        )
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(self.cabecalho)
        layout.addWidget(self.abas, 1)

    def carregar(self) -> None:
        """Ao abrir o menu: ler outra vez (o Excel e o iX podem ter mudado)."""
        self.traducoes.verificar()
