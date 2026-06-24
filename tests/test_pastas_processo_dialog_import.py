"""Import checks for the production process folders dialog."""

from __future__ import annotations

import inspect


def test_pastas_processo_dialog_usa_arvore_e_abre_pasta() -> None:
    from app.ui.dialogs.pastas_processo_dialog import PastasProcessoDialog

    source = inspect.getsource(PastasProcessoDialog)

    assert "Pastas do processo -" in source
    assert "QTreeWidget" in source
    assert "itemDoubleClicked.connect(self._abrir_pasta)" in source
    assert "Abrir no explorador" in source
    assert "Abrir a pasta selecionada no explorador" in source
    assert "itemSelectionChanged.connect(self._atualizar_botao_abrir)" in source
    assert "_caminho_item" in source
    assert "QDesktopServices.openUrl" in source
    assert '"Fechar"' in source
    assert "Sem pastas no servidor para este processo" in source
