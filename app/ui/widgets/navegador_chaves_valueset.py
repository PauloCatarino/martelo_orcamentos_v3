"""Painel de grupos e chaves ValueSet, partilhado pelas tabelas grandes.

As três tabelas de ValueSet — a do modelo, a do orçamento e a do item — têm o
mesmo problema: ~100 linhas espalhadas por ~70 chaves, em vinte e tal colunas.
Encontrar uma chave é percorrer o ecrã todo.

Este widget é a parte que se repete: a árvore de grupos → chaves à esquerda, os
chips de grupo por cima, e o filtro que daí resulta. Fica num sítio só para as
três páginas se comportarem da mesma maneira — e para uma correção valer para
todas.

**A marca ✎.** Nas tabelas do orçamento e do item o normal é importar um modelo
e depois afinar linhas à mão. Essas linhas afinadas são as mais importantes de
encontrar, e estavam escondidas numa coluna ao fundo de vinte e três. Por isso a
árvore mostra ``✎N`` em cada chave e grupo que as contenha, e há um chip que
mostra só essas. Na tabela do modelo isso não faz sentido (lá quase não há
edições locais), e por isso é opcional.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.domain.valueset_navegador_chaves import (
    MetaChave,
    agrupar_linhas,
    agrupar_linhas_contiguas,
    normalizar_chave,
    rotulo_grupo,
)
from app.ui.tema import (
    BEGE_AREIA,
    CASTANHO_ESCURO,
    OCRE_ESCURO,
)
from app.ui.widgets.estilo_tabela_orcamentos import estilo_arvore

#: Papel onde cada nó guarda ("grupo"|"chave", código).
PAPEL_NO = Qt.ItemDataRole.UserRole


class NavegadorChavesValueset(QWidget):
    """Árvore de grupos e chaves, com chips e filtro."""

    #: Emitido sempre que o filtro muda e a página tem de repintar.
    filtro_mudou = Signal()

    def __init__(self, parent=None, *, mostrar_editadas: bool = True) -> None:
        super().__init__(parent)

        self.mostrar_editadas = mostrar_editadas
        self._metas: dict[str, MetaChave] = {}
        self._grupo: str | None = None
        self._chave: str | None = None
        # O grupo veio a reboque de uma chave (e sai com ela), ou foi escolhido?
        self._grupo_implicito = False
        self._so_editadas = False
        self._grupos_fechados: set[str] = set()
        self._botoes_chips: list[QPushButton] = []

        titulo = QLabel("Navegador de chaves")
        fonte = titulo.font()
        fonte.setBold(True)
        titulo.setFont(fonte)
        titulo.setToolTip(
            "As chaves desta tabela, arrumadas pelo grupo do vocabulário. "
            "Clique numa chave para filtrar; clique outra vez para mostrar tudo."
        )

        self.arvore = QTreeWidget()
        self.arvore.setColumnCount(3 if mostrar_editadas else 2)
        self.arvore.setHeaderLabels(
            ["Chave", "✎", "Linhas"] if mostrar_editadas else ["Chave", "Linhas"]
        )
        self.arvore.setRootIsDecorated(True)
        self.arvore.setAlternatingRowColors(True)
        self.arvore.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.arvore.setStyleSheet(estilo_arvore())
        self.arvore.setToolTip(
            "Clique numa chave para filtrar a tabela por ela; clique num grupo "
            "para filtrar o grupo inteiro."
        )
        cabecalho = self.arvore.header()
        cabecalho.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for coluna in range(1, self.arvore.columnCount()):
            cabecalho.setSectionResizeMode(
                coluna, QHeaderView.ResizeMode.ResizeToContents
            )
        cabecalho.setStretchLastSection(False)
        self.arvore.itemClicked.connect(self._handle_clique)

        disposicao = QVBoxLayout()
        disposicao.setContentsMargins(0, 0, 0, 0)
        disposicao.setSpacing(5)
        disposicao.addWidget(titulo)
        disposicao.addWidget(self.arvore, stretch=1)
        self.setLayout(disposicao)

        # Os chips vivem noutro sítio do ecrã, mas o estado é este.
        self.chips_layout = QHBoxLayout()
        self.chips_layout.setSpacing(4)
        self.chips_layout.setContentsMargins(0, 0, 0, 0)
        self.chips = QWidget()
        self.chips.setLayout(self.chips_layout)

    # ----- o que a página diz ao navegador -----

    def definir_metas(self, metas: dict[str, MetaChave]) -> None:
        """O vocabulário das chaves (nome, grupo, ordem)."""
        self._metas = metas

    def atualizar(self, linhas: Sequence[Any]) -> None:
        """Redesenhar a árvore e os chips a partir das linhas pesquisadas.

        As contagens são as da pesquisa em curso, e não mudam por se estar a
        ver só um grupo — senão o número saltava ao clicar.
        """
        self._desenhar_chips(linhas)
        self._desenhar_arvore(linhas)

    # ----- o que a página pergunta ao navegador -----

    def aceita(self, linha: Any) -> bool:
        """Diz se a linha sobrevive ao grupo, à chave e ao "só editadas"."""
        if self._so_editadas and not getattr(linha, "editado_localmente", False):
            return False
        meta = self.meta_da(linha)
        if self._grupo is not None and meta.grupo != self._grupo:
            return False
        if self._chave is not None and meta.codigo != self._chave:
            return False
        return True

    def agrupar_contiguo(self, linhas: Sequence[Any]) -> list:
        """Blocos de linhas SEGUIDAS do mesmo grupo, para as faixas da tabela.

        Não reordena: as faixas seguem a ordem que a tabela já tem.
        """
        return agrupar_linhas_contiguas(linhas, self._metas)

    def meta_da(self, linha: Any) -> MetaChave:
        """O que o vocabulário sabe da chave desta linha (órfã: "Sem grupo")."""
        codigo = normalizar_chave(getattr(linha, "chave", None))
        meta = self._metas.get(codigo)
        if meta is not None:
            return meta
        return MetaChave(codigo=codigo, nome=codigo)

    @property
    def ha_filtro(self) -> bool:
        """Há grupo, chave ou "só editadas" a filtrar?"""
        return (
            self._grupo is not None
            or self._chave is not None
            or self._so_editadas
        )

    def sufixo_estado(self) -> str:
        """O que dizer na linha de estado sobre os filtros em curso."""
        partes = []
        if self._grupo is not None:
            partes.append(f"grupo: {rotulo_grupo(self._grupo)}")
        if self._chave is not None:
            partes.append(f"chave: {self._chave}")
        if self._so_editadas:
            partes.append("só as editadas localmente")
        if not partes:
            return ""
        return "  ·  " + "  ·  ".join(partes)

    def grupo_fechado(self, codigo: str) -> bool:
        """Se a faixa deste grupo está fechada na tabela."""
        return codigo in self._grupos_fechados

    def alternar_grupo_fechado(self, codigo: str) -> None:
        """Fecha/abre a faixa de um grupo e manda repintar."""
        if codigo in self._grupos_fechados:
            self._grupos_fechados.discard(codigo)
        else:
            self._grupos_fechados.add(codigo)
        self.filtro_mudou.emit()

    def limpar_filtros(self) -> None:
        """Repor grupo, chave, "só editadas" e os grupos fechados."""
        self._grupo = None
        self._grupo_implicito = False
        self._chave = None
        self._so_editadas = False
        self._grupos_fechados.clear()
        self.filtro_mudou.emit()

    # ----- interior -----

    def _desenhar_chips(self, linhas: Sequence[Any]) -> None:
        # Esvaziar o layout INTEIRO, e não só os botões: o espaçador do fim
        # também é um item, e deixá-lo lá empurrava os chips para a direita a
        # cada redesenho.
        while self.chips_layout.count():
            item = self.chips_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._botoes_chips = []

        grupos = agrupar_linhas(linhas, self._metas)
        entradas: list[tuple[str | None, str, int, str]] = [
            (None, "Todos", len(linhas), "Mostrar todas as chaves.")
        ]
        entradas.extend(
            (
                grupo.codigo,
                grupo.rotulo,
                grupo.total,
                f"Mostrar só as chaves do grupo {grupo.rotulo}.",
            )
            for grupo in grupos
        )

        for codigo, rotulo, total, dica in entradas:
            botao = QPushButton(f"{rotulo}  ({total})")
            botao.setCheckable(True)
            botao.setChecked(
                self._grupo == codigo and not (codigo is None and self._so_editadas)
            )
            botao.setToolTip(dica)
            botao.clicked.connect(
                lambda _c=False, alvo=codigo: self._escolher_grupo(alvo)
            )
            self.chips_layout.addWidget(botao)
            self._botoes_chips.append(botao)

        if self.mostrar_editadas:
            editadas = sum(
                1 for l in linhas if getattr(l, "editado_localmente", False)
            )
            botao = QPushButton(f"✎ Editadas  ({editadas})")
            botao.setCheckable(True)
            botao.setChecked(self._so_editadas)
            botao.setEnabled(editadas > 0 or self._so_editadas)
            botao.setToolTip(
                "Mostrar só as linhas que foram afinadas à mão neste orçamento, "
                "em vez das que vieram do modelo tal como estavam."
            )
            botao.setStyleSheet(
                f"QPushButton:checked {{ background: {OCRE_ESCURO}; color: white; }}"
            )
            botao.clicked.connect(lambda _c=False: self._alternar_editadas())
            self.chips_layout.addWidget(botao)
            self._botoes_chips.append(botao)

        self.chips_layout.addStretch()

    def _escolher_grupo(self, codigo: str | None) -> None:
        if codigo is None or self._grupo == codigo:
            self._grupo = None
        else:
            self._grupo = codigo
        self._grupo_implicito = False
        self._chave = None
        if codigo is None:
            self._so_editadas = False
        self.filtro_mudou.emit()

    def _alternar_editadas(self) -> None:
        self._so_editadas = not self._so_editadas
        self._chave = None
        self.filtro_mudou.emit()

    def _desenhar_arvore(self, linhas: Sequence[Any]) -> None:
        self.arvore.blockSignals(True)
        self.arvore.clear()
        for grupo in agrupar_linhas(linhas, self._metas):
            editadas_grupo = sum(
                1
                for chave in grupo.chaves
                for l in chave.linhas
                if getattr(l, "editado_localmente", False)
            )
            no_grupo = QTreeWidgetItem(
                self._colunas(grupo.rotulo, editadas_grupo, grupo.total)
            )
            fonte = no_grupo.font(0)
            fonte.setBold(True)
            no_grupo.setFont(0, fonte)
            no_grupo.setForeground(0, QBrush(QColor(CASTANHO_ESCURO)))
            no_grupo.setBackground(0, QBrush(QColor(BEGE_AREIA)))
            no_grupo.setData(0, PAPEL_NO, ("grupo", grupo.codigo))
            no_grupo.setToolTip(0, f"Filtrar pelo grupo {grupo.rotulo}.")
            self.arvore.addTopLevelItem(no_grupo)

            for chave in grupo.chaves:
                editadas = sum(
                    1
                    for l in chave.linhas
                    if getattr(l, "editado_localmente", False)
                )
                no_chave = QTreeWidgetItem(
                    self._colunas(chave.nome, editadas, chave.total)
                )
                no_chave.setData(0, PAPEL_NO, ("chave", chave.codigo))
                dica = f"{chave.codigo} — {chave.total} opção(ões)."
                if editadas:
                    dica += f" {editadas} afinada(s) à mão."
                no_chave.setToolTip(0, dica)
                if editadas and self.mostrar_editadas:
                    no_chave.setForeground(1, QBrush(QColor(OCRE_ESCURO)))
                if chave.codigo == self._chave:
                    fonte_chave = no_chave.font(0)
                    fonte_chave.setBold(True)
                    no_chave.setFont(0, fonte_chave)
                no_grupo.addChild(no_chave)

            no_grupo.setExpanded(grupo.codigo not in self._grupos_fechados)
        self.arvore.blockSignals(False)

    def _colunas(self, nome: str, editadas: int, total: int) -> list[str]:
        if not self.mostrar_editadas:
            return [nome, str(total)]
        return [nome, f"✎{editadas}" if editadas else "", str(total)]

    def _handle_clique(self, item: QTreeWidgetItem, _coluna: int) -> None:
        dados = item.data(0, PAPEL_NO)
        if not dados:
            return

        tipo, codigo = dados
        if tipo == "grupo":
            self._escolher_grupo(codigo)
            return

        if self._chave == codigo:
            self._chave = None
            # O grupo só ficou escolhido para acompanhar a chave: sai com ela,
            # senão o segundo clique deixava metade do filtro para trás.
            if self._grupo_implicito:
                self._grupo = None
                self._grupo_implicito = False
        else:
            self._chave = codigo
            pai = item.parent()
            dados_pai = pai.data(0, PAPEL_NO) if pai else None
            if dados_pai and self._grupo != dados_pai[1]:
                self._grupo = dados_pai[1]
                self._grupo_implicito = True
        self.filtro_mudou.emit()


def escrever_faixa_grupo(
    table: QTableWidget,
    row: int,
    *,
    texto: str,
    colunas: int,
    tooltip: str = "Clique para fechar ou abrir este grupo.",
) -> None:
    """Escreve na tabela uma faixa que atravessa todas as colunas.

    Só de **grupo**, e não de chave: nestas tabelas há ~70 chaves para ~100
    linhas, e uma faixa por chave quase duplicava o que está no ecrã para não
    ganhar quase nada.

    Não se usa ``setSpan``. O span do Qt junta colunas pela ordem **lógica**, e
    estas tabelas deixam o utilizador arrastar os cabeçalhos: bastava ele mover
    a primeira coluna para a faixa deixar de atravessar a tabela e passar a
    começar a meio. Em vez disso pinta-se **célula a célula**, e o texto vai na
    coluna que estiver mais à esquerda nesse momento — seja ela qual for.
    """
    cabecalho = table.horizontalHeader()
    # A coluna que está à esquerda AGORA, e não a que foi criada em primeiro.
    coluna_do_texto = cabecalho.logicalIndex(0) if cabecalho.count() else 0

    for coluna in range(colunas):
        item = QTableWidgetItem(texto if coluna == coluna_do_texto else "")
        # Faixa: não é uma linha de dados, por isso não entra na seleção — só
        # responde ao clique que a fecha e abre.
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setBackground(QBrush(QColor(BEGE_AREIA)))
        item.setForeground(QBrush(QColor(CASTANHO_ESCURO)))
        item.setToolTip(texto + chr(10) + tooltip)
        if coluna == coluna_do_texto:
            fonte = item.font()
            fonte.setBold(True)
            item.setFont(fonte)
        table.setItem(row, coluna, item)
