"""Show/hide table columns per machine and per authenticated user (QSettings)."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QMenu, QTableView, QTableWidget

from app.core.session import app_session

_ORG = "Lanca Encanto"
_APP = "Martelo Orcamentos V3"


def estado_inicial_colunas(
    nomes: Sequence[str],
    guardados: Mapping[int, bool | str | int | None],
    ocultas_por_defeito: Collection[str] = (),
) -> dict[int, bool]:
    """Return column visibility by index, with saved state overriding defaults."""
    ocultas = set(ocultas_por_defeito)
    estados: dict[int, bool] = {}

    for indice, nome in enumerate(nomes):
        guardado = _para_bool(guardados.get(indice))
        if guardado is not None:
            estados[indice] = guardado
        else:
            estados[indice] = nome not in ocultas

    if estados and not any(estados.values()):
        primeiro_indice = min(estados)
        estados[primeiro_indice] = True

    return estados


def ligar_menu_colunas(
    table: QTableView | QTableWidget,
    chave: str,
    ocultas_por_defeito: Collection[str] = (),
) -> None:
    """Attach a right-click header menu to show/hide table columns."""
    header = table.horizontalHeader()
    settings = QSettings(_ORG, _APP)
    nomes = _nomes_colunas(table)

    estados = estado_inicial_colunas(
        nomes,
        _guardados(settings, chave, len(nomes)),
        ocultas_por_defeito,
    )
    _aplicar_estados(header, estados)

    def _mostrar_todas() -> None:
        for indice in range(header.count()):
            header.setSectionHidden(indice, False)
            settings.setValue(_settings_key(chave, indice), True)
        settings.sync()

    def _repor_padrao() -> None:
        settings.remove(f"colunas/{_utilizador_atual()}/{chave}")
        estados_padrao = estado_inicial_colunas(nomes, {}, ocultas_por_defeito)
        _aplicar_estados(header, estados_padrao)
        settings.sync()

    def _alternar_coluna(indice: int, visivel: bool, action) -> None:
        if not visivel and _num_colunas_visiveis(header) <= 1:
            action.setChecked(True)
            return

        header.setSectionHidden(indice, not visivel)
        settings.setValue(_settings_key(chave, indice), bool(visivel))
        settings.sync()

    def _abrir_menu(pos) -> None:
        menu = QMenu(header)
        mostrar_todas = menu.addAction("Mostrar todas")
        mostrar_todas.triggered.connect(_mostrar_todas)
        repor_padrao = menu.addAction("Repor padrão")
        repor_padrao.triggered.connect(_repor_padrao)
        menu.addSeparator()

        for indice, nome in enumerate(nomes):
            action = menu.addAction(nome)
            action.setCheckable(True)
            action.setChecked(not header.isSectionHidden(indice))
            action.triggered.connect(
                lambda checked, col=indice, act=action: _alternar_coluna(
                    col, checked, act
                )
            )

        menu.exec(header.mapToGlobal(pos))

    header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    header.customContextMenuRequested.connect(_abrir_menu)


def _nomes_colunas(table: QTableView | QTableWidget) -> list[str]:
    header = table.horizontalHeader()
    model = table.model()
    nomes: list[str] = []

    for indice in range(header.count()):
        nome = ""
        item = (
            table.horizontalHeaderItem(indice)
            if isinstance(table, QTableWidget)
            else None
        )
        if item is not None:
            nome = item.text()
        if not nome and model is not None:
            data = model.headerData(indice, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            nome = str(data) if data is not None else ""
        nomes.append(nome or f"Coluna {indice + 1}")

    return nomes


def _guardados(settings: QSettings, chave: str, count: int) -> dict[int, bool]:
    guardados: dict[int, bool] = {}
    for indice in range(count):
        key = _settings_key(chave, indice)
        if not settings.contains(key):
            continue
        valor = _para_bool(settings.value(key))
        if valor is not None:
            guardados[indice] = valor
    return guardados


def _aplicar_estados(header, estados: Mapping[int, bool]) -> None:
    for indice, visivel in estados.items():
        if 0 <= indice < header.count():
            header.setSectionHidden(indice, not visivel)


def _num_colunas_visiveis(header) -> int:
    return sum(
        1 for indice in range(header.count()) if not header.isSectionHidden(indice)
    )


def _settings_key(chave: str, indice: int) -> str:
    return f"colunas/{_utilizador_atual()}/{chave}/{indice}"


def _utilizador_atual() -> str:
    """Return the current authenticated username, or "default" without a session."""
    username = getattr(app_session.current_user, "username", None)
    return username or "default"


def _para_bool(valor) -> bool | None:
    if valor is None:
        return None
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int):
        return bool(valor)
    if isinstance(valor, str):
        normalized = valor.strip().lower()
        if normalized in {"1", "true", "yes", "sim"}:
            return True
        if normalized in {"0", "false", "no", "nao", "não"}:
            return False
    return None
