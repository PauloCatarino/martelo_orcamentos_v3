"""Dialog for the per-user costing piece library preferences."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.peca_types import COMPOSTA
from app.repositories.def_peca_repository import DefPecaResumo
from app.services.def_peca_service import DefPecaService
from app.services.def_peca_user_pref_service import DefPecaUserPrefService
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.ordem_grupos_biblioteca import (
    guardar_ordens_grupos,
    obter_ordens_grupos,
    ordenar_grupos,
)


class PreferenciasBibliotecaPecasDialog(QDialog):
    """Choose which pieces the current user sees in the costing library.

    Column 0 holds the "disponível" checkbox, column 1 the "favorito" one.
    A favorite is always available; unchecking availability clears the star.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("A Minha Biblioteca de Peças")
        self.setModal(True)
        self.setMinimumSize(560, 640)

        user = app_session.current_user
        self._user_id: int | None = getattr(user, "id", None)
        self._pecas: list[DefPecaResumo] = []
        self._alterado = False

        ajuda = QLabel(
            "Escolha as peças que aparecem na sua biblioteca do custeio e marque "
            "como favoritas as mais usadas (aparecem também no grupo Favoritos). "
            "Peças criadas no futuro só aparecem depois de as marcar aqui; "
            "“Repor” volta a mostrar todas."
        )
        ajuda.setWordWrap(True)

        username = getattr(user, "username", None) or "—"
        self.user_label = QLabel(f"Preferências do utilizador: {username}")
        self.user_label.setObjectName("preferenciasBibliotecaUser")

        self.pesquisa = CampoPesquisa(placeholder="Pesquisar peça…")
        self.pesquisa.pesquisa_mudou.connect(self._aplicar_filtro)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Peça", "Favorito"])
        self.tree.setIndentation(10)
        self.tree.setUniformRowHeights(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 400)
        self.tree.setHeaderLabels(["Peça", "Favorito", "Ordem do grupo"])
        self.tree.setColumnWidth(1, 90)
        self.tree.setColumnWidth(2, 115)
        self.tree.itemChanged.connect(self._on_item_changed)

        self.marcar_visiveis_button = QPushButton("Marcar visíveis")
        self.marcar_visiveis_button.setToolTip(
            "Marcar como disponíveis todas as peças atualmente visíveis na lista "
            "(respeita a pesquisa)."
        )
        self.marcar_visiveis_button.clicked.connect(lambda: self._marcar_visiveis(True))
        self.desmarcar_visiveis_button = QPushButton("Desmarcar visíveis")
        self.desmarcar_visiveis_button.setToolTip(
            "Desmarcar todas as peças atualmente visíveis na lista (respeita a "
            "pesquisa). Também limpa os favoritos dessas peças."
        )
        self.desmarcar_visiveis_button.clicked.connect(
            lambda: self._marcar_visiveis(False)
        )

        self.contador_label = QLabel("")
        self.contador_label.setObjectName("preferenciasBibliotecaContador")

        self.repor_button = QPushButton("Repor (mostrar todas)")
        self.repor_button.setToolTip(
            "Apaga a personalização: volta a ver todas as peças ativas, incluindo "
            "as criadas no futuro."
        )
        self.repor_button.clicked.connect(self._repor)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setToolTip(
            "Guardar a seleção de peças e favoritos deste utilizador."
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._guardar)
        self.button_box.rejected.connect(self.reject)

        selecao_layout = QHBoxLayout()
        selecao_layout.addWidget(self.marcar_visiveis_button)
        selecao_layout.addWidget(self.desmarcar_visiveis_button)
        selecao_layout.addStretch()
        selecao_layout.addWidget(self.repor_button)

        layout = QVBoxLayout()
        layout.addWidget(ajuda)
        layout.addWidget(self.user_label)
        layout.addWidget(self.pesquisa)
        layout.addWidget(self.tree, stretch=1)
        layout.addLayout(selecao_layout)
        layout.addWidget(self.contador_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self._carregar()

    @property
    def alterado(self) -> bool:
        """Whether preferences were saved (or reset) in this dialog."""
        return self._alterado

    def _carregar(self) -> None:
        """Load active pieces and the current user's preferences into the tree."""
        try:
            with SessionLocal() as session:
                self._pecas = DefPecaService(session).listar_ativas_para_biblioteca()
                prefs = DefPecaUserPrefService(session).obter_preferencias(
                    self._user_id
                )
        except SQLAlchemyError:
            self._pecas = []
            self.contador_label.setText("Não foi possível carregar as peças.")
            return

        self.tree.blockSignals(True)
        self.tree.clear()

        pecas_por_grupo: dict[str, list[DefPecaResumo]] = {}
        for peca in self._pecas:
            grupo = (peca.grupo or "").strip().upper() or "SEM GRUPO"
            pecas_por_grupo.setdefault(grupo, []).append(peca)

        self._ordens_grupos = obter_ordens_grupos(pecas_por_grupo)
        self._inputs_ordem_grupos: dict[str, QSpinBox] = {}
        for grupo in ordenar_grupos(pecas_por_grupo, self._ordens_grupos):
            parent = QTreeWidgetItem([grupo, "", ""])
            parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            self.tree.addTopLevelItem(parent)
            ordem = QSpinBox()
            ordem.setRange(1, 999)
            ordem.setValue(self._ordens_grupos[grupo])
            ordem.setToolTip("Posição deste grupo na biblioteca do custeio (1 aparece primeiro).")
            self.tree.setItemWidget(parent, 2, ordem)
            self._inputs_ordem_grupos[grupo] = ordem

            for peca in pecas_por_grupo[grupo]:
                codigo_orlas = f"{peca.orla_c1}{peca.orla_c2}{peca.orla_l1}{peca.orla_l2}"
                nome_exibido = peca.nome_biblioteca or peca.nome
                texto = f"{nome_exibido} [{codigo_orlas}]"
                if peca.tipo_peca == COMPOSTA:
                    texto += " (composta)"

                leaf = QTreeWidgetItem([texto, ""])
                leaf.setFlags(leaf.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                disponivel = prefs.peca_visivel(peca.id)
                leaf.setCheckState(
                    0,
                    Qt.CheckState.Checked if disponivel else Qt.CheckState.Unchecked,
                )
                leaf.setCheckState(
                    1,
                    Qt.CheckState.Checked
                    if peca.id in prefs.favoritas
                    else Qt.CheckState.Unchecked,
                )
                leaf.setData(0, Qt.ItemDataRole.UserRole, peca.id)
                leaf.setToolTip(
                    0,
                    "\n".join(
                        [
                            f"Código: {peca.codigo}",
                            f"Nome: {peca.nome}",
                            f"Grupo: {peca.grupo or '—'}",
                        ]
                    ),
                )
                leaf.setToolTip(1, "Favorito: atalho no grupo Favoritos da biblioteca.")
                parent.addChild(leaf)

        self.tree.expandAll()
        self.tree.blockSignals(False)
        self._atualizar_contador()

    def _folhas(self) -> list[QTreeWidgetItem]:
        """Return every leaf item (one per piece)."""
        folhas: list[QTreeWidgetItem] = []
        for indice in range(self.tree.topLevelItemCount()):
            grupo = self.tree.topLevelItem(indice)
            folhas.extend(grupo.child(i) for i in range(grupo.childCount()))
        return folhas

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """Keep favorites and availability coherent when one checkbox changes."""
        if item.data(0, Qt.ItemDataRole.UserRole) is None:
            return

        self.tree.blockSignals(True)
        if column == 1 and item.checkState(1) == Qt.CheckState.Checked:
            item.setCheckState(0, Qt.CheckState.Checked)
        if column == 0 and item.checkState(0) == Qt.CheckState.Unchecked:
            item.setCheckState(1, Qt.CheckState.Unchecked)
        self.tree.blockSignals(False)
        self._atualizar_contador()

    def _aplicar_filtro(self, *_args) -> None:
        """Hide leaves (and empty groups) that do not match the search term."""
        termo = self.pesquisa.texto().strip().lower()
        pecas_por_id = {peca.id: peca for peca in self._pecas}

        for indice in range(self.tree.topLevelItemCount()):
            grupo = self.tree.topLevelItem(indice)
            visiveis = 0
            for i in range(grupo.childCount()):
                leaf = grupo.child(i)
                peca = pecas_por_id.get(leaf.data(0, Qt.ItemDataRole.UserRole))
                corresponde = not termo or self._peca_matches(peca, leaf.text(0), termo)
                leaf.setHidden(not corresponde)
                visiveis += 1 if corresponde else 0
            grupo.setHidden(visiveis == 0)

    def _peca_matches(
        self, peca: DefPecaResumo | None, texto_folha: str, termo: str
    ) -> bool:
        """Return True when a piece matches the search term."""
        if peca is None:
            return termo in texto_folha.lower()
        campos = [
            texto_folha,
            peca.codigo,
            peca.nome,
            peca.nome_biblioteca or "",
            peca.grupo or "",
        ]
        return any(termo in (campo or "").lower() for campo in campos)

    def _marcar_visiveis(self, marcar: bool) -> None:
        """Check/uncheck every leaf currently visible under the search filter."""
        self.tree.blockSignals(True)
        for leaf in self._folhas():
            if leaf.isHidden():
                continue
            leaf.setCheckState(
                0, Qt.CheckState.Checked if marcar else Qt.CheckState.Unchecked
            )
            if not marcar:
                leaf.setCheckState(1, Qt.CheckState.Unchecked)
        self.tree.blockSignals(False)
        self._atualizar_contador()

    def _selecao_atual(self) -> tuple[set[int], set[int]]:
        """Return the checked piece ids as (selecionadas, favoritas)."""
        selecionadas: set[int] = set()
        favoritas: set[int] = set()
        for leaf in self._folhas():
            peca_id = leaf.data(0, Qt.ItemDataRole.UserRole)
            if leaf.checkState(0) == Qt.CheckState.Checked:
                selecionadas.add(int(peca_id))
            if leaf.checkState(1) == Qt.CheckState.Checked:
                favoritas.add(int(peca_id))
        return selecionadas, favoritas

    def _atualizar_contador(self) -> None:
        selecionadas, favoritas = self._selecao_atual()
        self.contador_label.setText(
            f"Disponíveis: {len(selecionadas)} de {len(self._pecas)} · "
            f"Favoritas: {len(favoritas)}"
        )

    def _guardar(self) -> None:
        """Persist the selection for the current user and close."""
        if self._user_id is None:
            QMessageBox.warning(
                self,
                "Sem sessão",
                "Não há utilizador autenticado; as preferências não podem ser guardadas.",
            )
            return

        selecionadas, favoritas = self._selecao_atual()
        if not selecionadas:
            QMessageBox.warning(
                self,
                "Seleção vazia",
                "Selecione pelo menos uma peça, ou use “Repor (mostrar "
                "todas)” para voltar a ver a biblioteca completa.",
            )
            return

        # Everything selected without favorites is the same view as the
        # default; store no rows so future pieces stay visible for this user.
        todas_sem_favoritas = (
            len(selecionadas) == len(self._pecas) and not favoritas
        )
        guardar_ordens_grupos(
            {
                grupo: input_ordem.value()
                for grupo, input_ordem in self._inputs_ordem_grupos.items()
            }
        )
        try:
            with SessionLocal() as session:
                service = DefPecaUserPrefService(session)
                if todas_sem_favoritas:
                    service.repor_preferencias(self._user_id)
                else:
                    service.guardar_preferencias(
                        self._user_id, selecionadas, favoritas
                    )
        except SQLAlchemyError:
            QMessageBox.critical(
                self,
                "Erro",
                "Não foi possível guardar as preferências da biblioteca.",
            )
            return

        self._alterado = True
        self.accept()

    def _repor(self) -> None:
        """Clear the customization after confirmation and close."""
        if self._user_id is None:
            QMessageBox.warning(
                self,
                "Sem sessão",
                "Não há utilizador autenticado; as preferências não podem ser alteradas.",
            )
            return

        confirmacao = QMessageBox.question(
            self,
            "Repor biblioteca",
            "Voltar a mostrar todas as peças ativas na sua biblioteca? A seleção "
            "personalizada e os favoritos deste utilizador são apagados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmacao != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                DefPecaUserPrefService(session).repor_preferencias(self._user_id)
        except SQLAlchemyError:
            QMessageBox.critical(
                self,
                "Erro",
                "Não foi possível repor as preferências da biblioteca.",
            )
            return

        self._alterado = True
        self.accept()
