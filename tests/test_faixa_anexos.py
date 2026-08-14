"""Visual attachment strip used by occurrence tickets."""

from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from app.ui.widgets.faixa_anexos import FaixaAnexos


def test_galeria_somente_leitura_mostra_foto_e_nome(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    caminho = tmp_path / "trabalho.png"
    imagem = QImage(320, 180, QImage.Format.Format_RGB32)
    imagem.fill(QColor("#8B6F4E"))
    assert imagem.save(str(caminho))
    galeria = FaixaAnexos(
        altura=176,
        tamanho_icone=QSize(190, 128),
        mostrar_nomes=True,
        somente_leitura=True,
    )

    galeria.carregar(
        [SimpleNamespace(id=7, caminho=str(caminho), nome_original="trabalho.png")]
    )

    assert galeria.count() == 1
    assert galeria.item(0).text() == "trabalho.png"
    assert not galeria.item(0).icon().isNull()
    assert not galeria.acceptDrops()
    galeria.item(0).setSelected(True)
    galeria.remover_selecionados()
    assert galeria.total() == 1
    galeria.deleteLater()
    app.processEvents()
