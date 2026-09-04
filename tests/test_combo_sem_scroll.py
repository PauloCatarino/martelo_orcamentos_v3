"""A roda do rato não pode mudar valores só por passar por cima do campo.

Passar o rato por cima da coluna "Mat. default" e rolar a lista trocava o
material da peça sem ninguém dar por isso — e o preço do orçamento mudava. A
mesma regra vale para os campos de número e de data.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QComboBox  # noqa: E402

from app.ui.widgets.combo_sem_scroll import (  # noqa: E402
    ComboSemScroll,
    DataSemScroll,
    SpinDuploSemScroll,
    SpinSemScroll,
)


@pytest.fixture(scope="module")
def app():
    aplicacao = QApplication.instance() or QApplication([])
    yield aplicacao


def _roda(combo: ComboSemScroll) -> QWheelEvent:
    return QWheelEvent(
        QPointF(combo.rect().center()),
        QPointF(combo.mapToGlobal(combo.rect().center())),
        QPoint(0, -120),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )


def test_roda_com_a_lista_fechada_nao_muda_a_opcao(app) -> None:
    combo = ComboSemScroll()
    combo.addItems(["Branco", "Linho Cancun", "MDF"])
    combo.setCurrentIndex(0)

    evento = _roda(combo)
    combo.wheelEvent(evento)

    assert combo.currentIndex() == 0
    # Devolvido ao pai, para a tabela por baixo rolar como o utilizador espera.
    assert evento.isAccepted() is False


def test_a_roda_nao_da_foco_ao_dropdown(app) -> None:
    combo = ComboSemScroll()

    assert combo.focusPolicy() == Qt.FocusPolicy.StrongFocus


class _ListaAberta:
    """Vista falsa: diz que a lista do dropdown está aberta."""

    @staticmethod
    def isVisible() -> bool:  # noqa: N802 (Qt naming)
        return True


def test_com_a_lista_aberta_a_roda_volta_a_funcionar(app, monkeypatch) -> None:
    combo = ComboSemScroll()
    combo.addItems(["Branco", "Linho Cancun", "MDF"])
    combo.view = lambda: _ListaAberta()

    recebidos = []
    monkeypatch.setattr(
        QComboBox, "wheelEvent", lambda self, evento: recebidos.append(evento)
    )

    combo.wheelEvent(_roda(combo))

    assert len(recebidos) == 1


def test_campo_de_numero_sem_foco_ignora_a_roda(app) -> None:
    for classe, valor in ((SpinSemScroll, 5), (SpinDuploSemScroll, 5.0)):
        campo = classe()
        campo.setRange(0, 100)
        campo.setValue(valor)

        evento = _roda(campo)
        campo.wheelEvent(evento)

        assert campo.value() == valor
        assert evento.isAccepted() is False


def test_campo_de_data_sem_foco_ignora_a_roda(app) -> None:
    campo = DataSemScroll()
    antes = campo.date()

    evento = _roda(campo)
    campo.wheelEvent(evento)

    assert campo.date() == antes
    assert evento.isAccepted() is False


def test_campo_de_numero_com_foco_volta_a_responder(app, monkeypatch) -> None:
    from PySide6.QtWidgets import QSpinBox

    campo = SpinSemScroll()
    campo.setRange(0, 100)
    campo.setValue(5)
    monkeypatch.setattr(campo, "hasFocus", lambda: True)

    recebidos = []
    monkeypatch.setattr(
        QSpinBox, "wheelEvent", lambda self, evento: recebidos.append(evento)
    )

    campo.wheelEvent(_roda(campo))

    assert len(recebidos) == 1
