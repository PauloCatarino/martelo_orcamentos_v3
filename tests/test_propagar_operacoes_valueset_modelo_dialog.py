"""Import contracts for the model-operation propagation dialog."""

from __future__ import annotations

from pathlib import Path


SOURCE = (
    Path(__file__).parents[1]
    / "app"
    / "ui"
    / "dialogs"
    / "propagar_operacoes_valueset_modelo_dialog.py"
).read_text(encoding="utf-8")


def test_dialogo_expoe_colunas_de_ambito_estado_e_previsualizacao() -> None:
    for header in (
        "Selecionar",
        "Âmbito",
        "Proprietário",
        "Modelo",
        "Estado modelo",
        "Estado linha",
        "Substituir",
        "Adicionar",
        "Desativar",
        "Alterações previstas",
    ):
        assert f'"{header}"' in SOURCE


def test_dialogo_nao_preseleciona_e_bloqueia_destinos_sem_permissao() -> None:
    assert "Qt.CheckState.Unchecked" in SOURCE
    assert "if not destino.permitido" in SOURCE
    assert "ItemIsEnabled" in SOURCE
    assert "destino.motivo_bloqueio" in SOURCE


def test_dialogo_mostra_alteracoes_exatas_e_exige_confirmacao() -> None:
    assert "substituir" in SOURCE
    assert "adicionar" in SOURCE
    assert "desativar" in SOURCE
    assert "alteracao.descricao" in SOURCE
    assert "Selecione pelo menos um destino permitido" in SOURCE
    assert "QMessageBox.question" in SOURCE
    assert "self.selected_ids = ids" in SOURCE
