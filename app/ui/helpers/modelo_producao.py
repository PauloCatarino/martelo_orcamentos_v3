"""Table model and filter/sort proxy for the production list.

Substitui o antigo ``QTableWidget`` preenchido à mão: com um modelo, a
ordenação por cabeçalho e a filtragem passam a ser incrementais e aguentam
milhares de obras sem reconstruir a tabela a cada tecla.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor

from app.domain.prazos_producao import estado_prazo
from app.services.producao_service import processo_corresponde, termos_pesquisa
from app.ui import tema
from app.ui.helpers.colunas_producao import COLUNAS_PRODUCAO
from app.ui.icones import icone


#: Colunas com conteúdo centrado.
COLUNAS_CENTRADAS = frozenset(
    {
        "criada_em",
        "ano",
        "estado",
        "enc_phc",
        "versao_obra",
        "versao_cutrite",
        "data_inicio",
        "data_entrega",
        "qt_artigos",
    }
)

#: Colunas alinhadas à direita (valores numéricos).
COLUNAS_DIREITA = frozenset({"preco"})

_MENOR_DATA = datetime.min


class ProducaoTableModel(QAbstractTableModel):
    """Expose production processes as a table, one row per process."""

    #: Valor comparável usado na ordenação (em vez do texto apresentado).
    ROLE_ORDENACAO = Qt.ItemDataRole.UserRole + 1
    #: Id da obra, para restaurar a seleção depois de filtrar/ordenar.
    ROLE_PROCESSO_ID = Qt.ItemDataRole.UserRole + 2
    #: O próprio objeto ``Producao``, usado pelo proxy ao filtrar.
    ROLE_PROCESSO = Qt.ItemDataRole.UserRole + 3

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._processos: list = []
        self._icone_pasta = icone("pasta_abrir")

    # ---- dados -----------------------------------------------------------
    def definir_processos(self, processos) -> None:
        """Replace every row in one go."""
        self.beginResetModel()
        self._processos = list(processos or [])
        self.endResetModel()

    def processo(self, row: int):
        """Return the process on one source row, or None."""
        if 0 <= row < len(self._processos):
            return self._processos[row]
        return None

    def linha_do_processo(self, processo_id) -> int:
        """Source row holding one process id, or -1."""
        for row, processo in enumerate(self._processos):
            if getattr(processo, "id", None) == processo_id:
                return row
        return -1

    # ---- QAbstractTableModel --------------------------------------------
    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802 (Qt override)
        return 0 if parent.isValid() else len(self._processos)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802 (Qt override)
        return 0 if parent.isValid() else len(COLUNAS_PRODUCAO)

    def headerData(  # noqa: N802 (Qt override)
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if orientation != Qt.Orientation.Horizontal:
            return None
        if not 0 <= section < len(COLUNAS_PRODUCAO):
            return None

        coluna = COLUNAS_PRODUCAO[section]
        if role == Qt.ItemDataRole.DisplayRole:
            return coluna.titulo
        if role == Qt.ItemDataRole.ToolTipRole and coluna.key == "criada_em":
            return "Data em que a obra foi criada nesta lista"
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        processo = self.processo(index.row())
        if processo is None:
            return None
        coluna = COLUNAS_PRODUCAO[index.column()]

        if role == self.ROLE_PROCESSO:
            return processo
        if role == self.ROLE_PROCESSO_ID:
            return getattr(processo, "id", None)
        if role == self.ROLE_ORDENACAO:
            return self._chave_ordenacao(processo, coluna)
        if role == Qt.ItemDataRole.DisplayRole:
            return coluna.valor(processo)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return self._alinhamento(coluna)
        if role == Qt.ItemDataRole.DecorationRole and coluna.key == "processo":
            return self._icone_pasta
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._dica(processo, coluna)
        if role == Qt.ItemDataRole.BackgroundRole:
            cor = self._fundo(processo, coluna)
            return QColor(cor) if cor else None
        if role == Qt.ItemDataRole.ForegroundRole:
            cor = self._texto(processo, coluna)
            return QColor(cor) if cor else None
        return None

    # ---- apresentação ----------------------------------------------------
    @staticmethod
    def _alinhamento(coluna):
        if coluna.key in COLUNAS_DIREITA:
            return int(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        if coluna.key in COLUNAS_CENTRADAS:
            return int(Qt.AlignmentFlag.AlignCenter)
        return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def _fundo(self, processo, coluna) -> str:
        if coluna.key == "estado":
            fundo, _texto = tema.cor_estado_producao(getattr(processo, "estado", None))
            return fundo
        if coluna.key == "data_entrega":
            situacao = self._prazo(processo)
            if situacao.atrasada:
                return tema.VERMELHO_SUAVE
            if situacao.tem_alerta:
                return tema.OCRE_SUAVE
        return ""

    def _texto(self, processo, coluna) -> str:
        if coluna.key == "estado":
            _fundo, texto = tema.cor_estado_producao(getattr(processo, "estado", None))
            return texto
        if coluna.key == "data_entrega":
            situacao = self._prazo(processo)
            if situacao.atrasada:
                return tema.VERMELHO_ESCURO
            if situacao.tem_alerta:
                return tema.OCRE_ESCURO
        return ""

    def _dica(self, processo, coluna) -> str:
        if coluna.key == "processo":
            return "Ver pastas do processo"
        if coluna.key == "data_entrega":
            descricao = self._prazo(processo).descricao()
            if descricao:
                return descricao
        return coluna.valor(processo)

    @staticmethod
    def _prazo(processo):
        return estado_prazo(
            getattr(processo, "data_entrega", None),
            getattr(processo, "estado", None),
        )

    # ---- ordenação -------------------------------------------------------
    @staticmethod
    def _chave_ordenacao(processo, coluna):
        """Comparable value for one cell (never the displayed text)."""
        if coluna.key == "criada_em":
            # Ordem de entrada: data de criação e, em empate, o id.
            criada = getattr(processo, "created_at", None) or _MENOR_DATA
            return (criada, getattr(processo, "id", 0) or 0)
        if coluna.key == "data_inicio":
            return _chave_data(getattr(processo, "data_inicio", None))
        if coluna.key == "data_entrega":
            return _chave_data(getattr(processo, "data_entrega", None))
        if coluna.key == "preco":
            return _chave_decimal(getattr(processo, "preco_total", None))
        if coluna.key == "qt_artigos":
            return _chave_decimal(getattr(processo, "qt_artigos", None))
        return coluna.valor(processo).lower()


class ProducaoFilterProxy(QSortFilterProxyModel):
    """Search box + filters + column sorting, on top of the table model."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._termos: list[str] = []
        self._estado: str | None = None
        self._cliente: str | None = None
        self._responsavel: str | None = None
        self._so_atrasadas = False
        self.setSortRole(ProducaoTableModel.ROLE_ORDENACAO)

    def definir_filtros(
        self,
        *,
        texto: str = "",
        estado: str | None = None,
        cliente: str | None = None,
        responsavel: str | None = None,
        so_atrasadas: bool = False,
    ) -> None:
        """Set every filter at once and re-run the filtering."""
        self._termos = termos_pesquisa(texto)
        self._estado = estado
        self._cliente = cliente
        self._responsavel = responsavel
        self._so_atrasadas = bool(so_atrasadas)
        self.invalidateFilter()

    def filterAcceptsRow(  # noqa: N802 (Qt override)
        self,
        source_row: int,
        source_parent: QModelIndex,
    ) -> bool:
        modelo = self.sourceModel()
        if modelo is None:
            return True

        processo = modelo.processo(source_row)
        if processo is None:
            return False

        return processo_corresponde(
            processo,
            termos=self._termos,
            estado=self._estado,
            cliente=self._cliente,
            responsavel=self._responsavel,
            so_atrasadas=self._so_atrasadas,
        )

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:  # noqa: N802
        """Compare the raw sort keys, tolerating mixed/missing values."""
        valor_esq = left.data(ProducaoTableModel.ROLE_ORDENACAO)
        valor_dir = right.data(ProducaoTableModel.ROLE_ORDENACAO)
        try:
            return valor_esq < valor_dir
        except TypeError:
            return str(valor_esq) < str(valor_dir)


def _chave_data(valor: object):
    """Sortable key for a ``dd-mm-aaaa`` date; empty dates go last."""
    from app.domain.datas import normalizar_data

    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor

    texto = normalizar_data(valor)
    if not texto:
        return date.max
    try:
        dia, mes, ano = (int(parte) for parte in texto.split("-"))
        return date(ano, mes, dia)
    except (TypeError, ValueError):
        return date.max


def _chave_decimal(valor: object) -> Decimal:
    """Sortable key for numbers; empty values sort last."""
    if valor is None or valor == "":
        return Decimal("-Infinity")
    try:
        return Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("-Infinity")
