"""Testes do esquema visual das orlas de uma definição de peça."""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.orla_types import ORLA_FINA, ORLA_GROSSA, SEM_ORLA
from app.ui.widgets.orla_peca_preview import (
    OrlaPecaPreview,
    get_orla_visual_style,
)


_app = QApplication.instance() or QApplication([])


def test_estilos_distinguem_sem_orla_fina_e_grossa() -> None:
    sem_orla = get_orla_visual_style(SEM_ORLA)
    fina = get_orla_visual_style(ORLA_FINA)
    grossa = get_orla_visual_style(ORLA_GROSSA)

    assert sem_orla.tracejada is True
    assert fina.tracejada is False
    assert grossa.tracejada is False
    assert sem_orla.espessura < fina.espessura < grossa.espessura
    assert len({sem_orla.cor, fina.cor, grossa.cor}) == 3


def test_preview_normaliza_e_guarda_os_quatro_lados() -> None:
    preview = OrlaPecaPreview()

    preview.set_orlas(ORLA_GROSSA, SEM_ORLA, ORLA_FINA, "2")

    assert preview.orlas == (ORLA_GROSSA, SEM_ORLA, ORLA_FINA, ORLA_GROSSA)


def test_preview_mantem_visivel_o_estado_sem_orlas() -> None:
    preview = OrlaPecaPreview()
    preview.show()

    preview.set_usa_orlas(False)

    assert preview.usa_orlas is False
    assert preview.isVisible() is True


def test_preview_pode_ser_renderizado_fora_do_ecra() -> None:
    preview = OrlaPecaPreview()
    preview.resize(preview.sizeHint())
    preview.set_orlas(ORLA_GROSSA, SEM_ORLA, ORLA_GROSSA, ORLA_GROSSA)

    imagem = preview.grab().toImage()

    assert not imagem.isNull()
    assert imagem.width() == preview.width()
    assert imagem.height() == preview.height()


def test_dialogos_usam_o_mesmo_preview_reutilizavel() -> None:
    from app.ui.dialogs.editar_def_peca_dialog import EditarDefPecaDialog
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog

    for dialogo in (EditarDefPecaDialog, NovaDefPecaDialog):
        source = inspect.getsource(dialogo.__init__)
        assert "OrlaPecaPreview" in source
        assert "orla_body_layout" in source
        assert "setToolTip" in source
