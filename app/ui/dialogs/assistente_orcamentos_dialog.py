"""Janela do Assistente dos Orçamentos (resumo diário das 8h30).

Mostra só os orçamentos da própria pessoa que ficaram parados, e oferece o
passo seguinte de cada um. Nada é enviado nem mudado sem um clique: quem faz
o trabalho é o ``controlador`` (``app/ui/helpers/assistente_orcamentos.py``),
que usa a lista de Orçamentos e o email que já existem.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.domain import assistente_orcamentos as regra
from app.utils.formatters import format_eur

#: Estados que se podem escolher a partir de um orçamento enviado sem resposta.
ESTADOS_DE_RESPOSTA = ("Adjudicado", "Não Adjudicado", "Sem Interesse", "Cancelado")
ESTADO_SEM_INTERESSE = "Sem Interesse"


class ControladorAssistente(Protocol):
    def resumo(self) -> regra.ResumoDiario: ...

    def adiar(self, versao_id: int): ...

    def ver_na_lista(self, versao_id: int) -> bool: ...

    def mudar_estado(self, versao_id: int, estado: str) -> None: ...

    def email_seguimento(self, lembrete: regra.Lembrete) -> bool: ...


def _saudacao(hora: int) -> str:
    if 6 <= hora < 13:
        return "Bom dia"
    if 13 <= hora < 20:
        return "Boa tarde"
    return "Boa noite"


def frase_do_resumo(resumo: regra.ResumoDiario) -> str:
    if resumo.vazio:
        texto = "Está tudo em dia: não há orçamentos seus parados."
    else:
        partes = []
        if resumo.sem_resposta:
            partes.append(
                f"{len(resumo.sem_resposta)} orçamento(s) enviado(s) há mais de "
                f"{regra.DIAS_SEM_RESPOSTA} dias sem resposta"
            )
        if resumo.falta_orcamentar:
            partes.append(
                f"{len(resumo.falta_orcamentar)} em «Falta Orçamentar» há mais de "
                f"{regra.DIAS_FALTA_ORCAMENTAR} dias"
            )
        texto = "Hoje tem " + " e ".join(partes) + "."
    if resumo.adiados:
        texto += f" ({resumo.adiados} adiado(s) por si, voltam mais tarde.)"
    return texto


def _obra_e_ref(lembrete: regra.Lembrete) -> str:
    partes: list[str] = []
    for valor in (lembrete.obra, lembrete.ref_cliente):
        valor = (valor or "").strip()
        if valor and valor.casefold() not in {p.casefold() for p in partes}:
            partes.append(valor)
    return " | ".join(partes)


class AssistenteOrcamentosDialog(QDialog):
    def __init__(
        self,
        controlador: ControladorAssistente,
        *,
        nome: str = "",
        automatico: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.controlador = controlador
        self.setWindowTitle("Assistente dos Orçamentos")
        self.setMinimumWidth(1000)
        self.resize(1000, 600)
        self._lembretes: dict[str, list[regra.Lembrete]] = {}

        titulo = QLabel("🔨 Assistente dos Orçamentos")
        titulo.setStyleSheet("font-size: 18px; font-weight: 600;")
        primeiro_nome = (nome or "").split()[0] if (nome or "").strip() else ""
        saudacao = _saudacao(datetime.now().hour)
        self.saudacao = QLabel(f"{saudacao}{', ' + primeiro_nome if primeiro_nome else ''}.")
        self.saudacao.setStyleSheet("font-size: 14px;")
        apresentacao = QLabel(regra.APRESENTACAO)
        apresentacao.setWordWrap(True)
        apresentacao.setStyleSheet("color: #5c6570;")
        # Aberto sozinho às 8h30 tem de dizer quem é; aberto pelo botão, não.
        apresentacao.setVisible(automatico)
        self.frase = QLabel()
        self.frase.setWordWrap(True)
        self.frase.setStyleSheet("font-weight: 600;")

        self.caixa_sem_resposta, self.tabela_sem_resposta, self.mais_sem_resposta = (
            self._grupo(
                f"Enviados há mais de {regra.DIAS_SEM_RESPOSTA} dias sem resposta do cliente",
                ("Orçamento", "Cliente", "Obra", "Enviado a", "Sem resposta há", "Valor"),
            )
        )
        linha = QHBoxLayout()
        self.email_button = self._botao(
            linha,
            "Preparar email de seguimento…",
            "Abre o email já escrito a perguntar ao cliente se analisou o "
            "orçamento (como resposta ao pedido dele, se estiver na pasta). "
            "Só sai quando carregar em Enviar.",
            self._email,
        )
        self.estado_button = self._botao(
            linha,
            "Já tive resposta ▾",
            "Mudar o estado deste orçamento. «Adjudicado» abre o Editar Orçamento "
            "para escrever o nº da encomenda PHC.",
            self._menu_estado,
        )
        self._botao(
            linha,
            "Ver na lista",
            "Mostrar este orçamento na lista de Orçamentos.",
            lambda: self._ver(regra.TIPO_SEM_RESPOSTA),
        )
        self._botao(
            linha,
            f"Lembrar daqui a {regra.DIAS_ADIAR} dias",
            f"Tirar este orçamento do resumo durante {regra.DIAS_ADIAR} dias.",
            lambda: self._adiar(regra.TIPO_SEM_RESPOSTA),
        )
        linha.addStretch()
        self.caixa_sem_resposta.layout().addLayout(linha)

        self.caixa_falta, self.tabela_falta, self.mais_falta = self._grupo(
            f"Em «Falta Orçamentar» há mais de {regra.DIAS_FALTA_ORCAMENTAR} dias — "
            "ainda faz sentido orçamentar?",
            ("Orçamento", "Cliente", "Obra", "Desde", "Parado há", "Valor"),
        )
        linha = QHBoxLayout()
        self._botao(
            linha,
            "Ver na lista",
            "Mostrar este orçamento na lista de Orçamentos.",
            lambda: self._ver(regra.TIPO_FALTA_ORCAMENTAR),
        )
        self._botao(
            linha,
            "Já não vou orçamentar",
            "Passar este orçamento a «Sem Interesse» (pede confirmação).",
            self._sem_interesse,
        )
        self._botao(
            linha,
            f"Lembrar daqui a {regra.DIAS_ADIAR} dias",
            f"Tirar este orçamento do resumo durante {regra.DIAS_ADIAR} dias.",
            lambda: self._adiar(regra.TIPO_FALTA_ORCAMENTAR),
        )
        linha.addStretch()
        self.caixa_falta.layout().addLayout(linha)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #5c6570;")
        fechar = QPushButton("Fechar")
        fechar.setToolTip(
            "Fechar o assistente. Pode voltar a abri-lo no botão «Assistente» "
            "da lista de Orçamentos."
        )
        fechar.clicked.connect(self.close)
        fundo = QHBoxLayout()
        fundo.addWidget(self.status_label, 1)
        fundo.addWidget(fechar)

        layout = QVBoxLayout(self)
        layout.addWidget(titulo)
        layout.addWidget(self.saudacao)
        layout.addWidget(apresentacao)
        layout.addWidget(self.frase)
        layout.addWidget(self.caixa_sem_resposta)
        layout.addWidget(self.caixa_falta)
        layout.addStretch()
        layout.addLayout(fundo)

        self.recarregar()

    # ---- construção ------------------------------------------------------
    def _grupo(self, titulo: str, colunas: tuple[str, ...]):
        caixa = QGroupBox(titulo)
        tabela = QTableWidget(0, len(colunas))
        tabela.setHorizontalHeaderLabels(list(colunas))
        tabela.verticalHeader().setVisible(False)
        tabela.setAlternatingRowColors(True)
        tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tabela.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # Uma linha por orçamento; o texto que não cabe fica na dica.
        tabela.setWordWrap(False)
        tabela.setTextElideMode(Qt.TextElideMode.ElideRight)
        tabela.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tabela.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        tabela.setToolTip("Selecione um orçamento e escolha o que fazer nos botões de baixo.")
        mais = QLabel()
        mais.setStyleSheet("color: #5c6570;")
        caixa_layout = QVBoxLayout(caixa)
        caixa_layout.addWidget(tabela)
        caixa_layout.addWidget(mais)
        return caixa, tabela, mais

    @staticmethod
    def _botao(linha: QHBoxLayout, texto: str, dica: str, acao) -> QPushButton:
        botao = QPushButton(texto)
        botao.setToolTip(dica)
        botao.clicked.connect(acao)
        linha.addWidget(botao)
        return botao

    # ---- dados -----------------------------------------------------------
    def recarregar(self) -> None:
        resumo = self.controlador.resumo()
        self.frase.setText(frase_do_resumo(resumo))
        self._preencher(
            regra.TIPO_SEM_RESPOSTA,
            self.caixa_sem_resposta,
            self.tabela_sem_resposta,
            self.mais_sem_resposta,
            resumo.sem_resposta,
        )
        self._preencher(
            regra.TIPO_FALTA_ORCAMENTAR,
            self.caixa_falta,
            self.tabela_falta,
            self.mais_falta,
            resumo.falta_orcamentar,
        )

    def _preencher(self, tipo, caixa, tabela, mais, lembretes) -> None:
        visiveis = list(lembretes[: regra.MAX_LINHAS])
        self._lembretes[tipo] = visiveis
        caixa.setVisible(bool(lembretes))
        tabela.setRowCount(len(visiveis))
        for linha, lembrete in enumerate(visiveis):
            data = lembrete.enviado_em or lembrete.desde
            valores = (
                lembrete.codigo,
                lembrete.cliente,
                _obra_e_ref(lembrete),
                data.strftime("%d-%m-%Y"),
                regra.texto_dias(lembrete.dias),
                format_eur(lembrete.preco) if lembrete.preco is not None else "",
            )
            for coluna, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                item.setToolTip(valor)
                if coluna in (3, 4, 5):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                tabela.setItem(linha, coluna, item)
        tabela.resizeColumnsToContents()
        tabela.setColumnWidth(1, min(tabela.columnWidth(1), 280))
        tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        # A tabela tem a altura das linhas que tem: nem esconde orçamentos atrás
        # de uma barra, nem deixa um buraco em branco.
        altura = tabela.horizontalHeader().height() + 2 * tabela.frameWidth()
        altura += sum(tabela.rowHeight(linha) for linha in range(tabela.rowCount()))
        tabela.setFixedHeight(altura + 2)
        if visiveis:
            tabela.selectRow(0)
        restantes = len(lembretes) - len(visiveis)
        mais.setText(
            f"… e mais {restantes}. Trate destes primeiro; os outros aparecem a seguir."
            if restantes > 0
            else ""
        )
        mais.setVisible(restantes > 0)

    def _selecionado(self, tipo: str) -> regra.Lembrete | None:
        tabela = (
            self.tabela_sem_resposta
            if tipo == regra.TIPO_SEM_RESPOSTA
            else self.tabela_falta
        )
        linha = tabela.currentRow()
        lembretes = self._lembretes.get(tipo, [])
        if 0 <= linha < len(lembretes):
            return lembretes[linha]
        self.status_label.setText("Selecione primeiro um orçamento na tabela.")
        return None

    # ---- ações -----------------------------------------------------------
    def _email(self) -> None:
        lembrete = self._selecionado(regra.TIPO_SEM_RESPOSTA)
        if lembrete is None:
            return
        if self.controlador.email_seguimento(lembrete):
            self.status_label.setText(
                f"Email de seguimento do {lembrete.codigo} enviado. O orçamento "
                f"volta ao resumo se não houver resposta em {regra.DIAS_SEM_RESPOSTA} dias."
            )
            self.recarregar()

    def _menu_estado(self) -> None:
        lembrete = self._selecionado(regra.TIPO_SEM_RESPOSTA)
        if lembrete is None:
            return
        menu = QMenu(self)
        for estado in ESTADOS_DE_RESPOSTA:
            menu.addAction(estado)
        escolhida = menu.exec(
            self.estado_button.mapToGlobal(self.estado_button.rect().bottomLeft())
        )
        if escolhida is None:
            return
        self.controlador.mudar_estado(lembrete.versao_id, escolhida.text())
        self.status_label.setText(
            f"{lembrete.codigo}: pedido para passar a «{escolhida.text()}» — "
            "veja o resultado na lista de Orçamentos."
        )
        self.recarregar()

    def _ver(self, tipo: str) -> None:
        lembrete = self._selecionado(tipo)
        if lembrete is None:
            return
        if self.controlador.ver_na_lista(lembrete.versao_id):
            self.status_label.setText(
                f"O {lembrete.codigo} está selecionado na lista de Orçamentos."
            )
        else:
            self.status_label.setText(
                f"Não encontrei o {lembrete.codigo} na lista de Orçamentos."
            )

    def _sem_interesse(self) -> None:
        lembrete = self._selecionado(regra.TIPO_FALTA_ORCAMENTAR)
        if lembrete is None:
            return
        resposta = QMessageBox.question(
            self,
            "Assistente dos Orçamentos",
            f"Passar o orçamento {lembrete.codigo} ({lembrete.cliente}) a "
            "«Sem Interesse»?\n\nFica registado no histórico e pode voltar a "
            "mudá-lo na lista de Orçamentos.",
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        self.controlador.mudar_estado(lembrete.versao_id, ESTADO_SEM_INTERESSE)
        self.status_label.setText(f"{lembrete.codigo} passou a «Sem Interesse».")
        self.recarregar()

    def _adiar(self, tipo: str) -> None:
        lembrete = self._selecionado(tipo)
        if lembrete is None:
            return
        ate = self.controlador.adiar(lembrete.versao_id)
        quando = f" (volta a {ate.strftime('%d-%m-%Y')})" if ate else ""
        self.status_label.setText(f"{lembrete.codigo} fica de fora do resumo{quando}.")
        self.recarregar()
