"""O diálogo do email mostra o peso dos anexos e avisa antes de enviar."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _ficheiro(tmp_path: Path, nome: str, megabytes: float) -> str:
    caminho = tmp_path / nome
    caminho.write_bytes(b"0" * int(megabytes * 1024 * 1024))
    return str(caminho)


def _dialogo(anexos, *, limite: float = 18.0):
    from app.ui.dialogs.email_orcamento_dialog import EmailOrcamentoDialog

    return EmailOrcamentoDialog(anexos=anexos, tamanho_max_mb=limite)


def test_anexos_devolve_os_caminhos_e_nao_o_que_se_ve(_app, tmp_path: Path) -> None:
    # A lista mostra "nome — tamanho", mas quem envia precisa do caminho.
    caminho = _ficheiro(tmp_path, "2_Projeto_Producao.pdf", 1)
    dialogo = _dialogo([caminho])

    assert dialogo.anexos() == [caminho]
    assert "2_Projeto_Producao.pdf — 1,0 MB" in dialogo.list_anexos.item(0).text()


def test_barra_soma_todos_os_anexos(_app, tmp_path: Path) -> None:
    anexos = [_ficheiro(tmp_path, f"anexo_{i}.pdf", 3) for i in range(3)]

    dialogo = _dialogo(anexos)

    assert "3 anexos" in dialogo.lbl_tamanho.text()
    assert "9,0 MB de 18 MB" in dialogo.lbl_tamanho.text()


def test_acima_do_limite_a_barra_avisa(_app, tmp_path: Path) -> None:
    dialogo = _dialogo([_ficheiro(tmp_path, "pesado.pdf", 23)])

    assert "demasiado grande" in dialogo.lbl_tamanho.text()
    assert dialogo._resumo_anexos().excede


def test_remover_anexo_refresca_a_barra(_app, tmp_path: Path) -> None:
    dialogo = _dialogo(
        [_ficheiro(tmp_path, "pesado.pdf", 23), _ficheiro(tmp_path, "leve.pdf", 1)]
    )
    assert dialogo._resumo_anexos().excede

    dialogo.list_anexos.item(0).setSelected(True)
    dialogo._remover_anexos_selecionados()

    assert not dialogo._resumo_anexos().excede
    assert "demasiado grande" not in dialogo.lbl_tamanho.text()


def test_dentro_do_limite_envia_sem_perguntar(_app, tmp_path: Path) -> None:
    dialogo = _dialogo([_ficheiro(tmp_path, "leve.pdf", 2)])

    assert dialogo._confirmar_tamanho()


def test_limite_vem_das_definicoes(_app, tmp_path: Path) -> None:
    anexos = [_ficheiro(tmp_path, "medio.pdf", 10)]

    assert not _dialogo(anexos, limite=18)._resumo_anexos().excede
    assert _dialogo(anexos, limite=5)._resumo_anexos().excede
