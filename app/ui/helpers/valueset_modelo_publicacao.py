"""Shared UI workflow for publishing a personal ValueSet model globally."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from app.core.session import app_session
from app.db.session import SessionLocal
from app.services.def_valueset_modelo_service import (
    CriarDefValuesetModeloData,
    DefValuesetModeloService,
    SubstituirDefValuesetModeloResult,
)
from app.services.permission_service import (
    PERMISSAO_PUBLICAR_MODELO_VALUESET_GLOBAL,
    permissions_for_user,
    pode,
)
from app.ui.dialogs.substituir_valueset_modelo_dialog import (
    SubstituirValuesetModeloDialog,
)


def publicar_modelo_valueset_para_todos(
    parent: QWidget,
    original_id: int,
    dados_novos: CriarDefValuesetModeloData,
) -> SubstituirDefValuesetModeloResult | None:
    """Select, preview and explicitly replace one global model."""
    with SessionLocal() as session:
        service = DefValuesetModeloService(session)
        origem = service.resumir_conteudo_modelo(original_id)
        destinos = service.listar_destinos_globais_para_substituicao(
            excluir_modelo_id=original_id
        )
        autorizado = pode(
            permissions_for_user(session, app_session.current_user),
            PERMISSAO_PUBLICAR_MODELO_VALUESET_GLOBAL,
        )

    if not autorizado:
        raise PermissionError(
            "Não tem permissão para publicar ou substituir modelos ValueSet globais."
        )
    if not destinos:
        QMessageBox.information(
            parent,
            "Sem modelos globais",
            "Não existem modelos globais disponíveis para substituir.",
        )
        return None

    dialog = SubstituirValuesetModeloDialog(origem, destinos, parent=parent)
    if not dialog.exec() or dialog.selected_destino is None:
        return None

    destino = dialog.selected_destino
    origem_modelo = origem.modelo
    destino_modelo = destino.modelo
    confirmacao = QMessageBox.warning(
        parent,
        "Confirmar substituição integral",
        f"ORIGEM\n{origem_modelo.codigo} — {origem_modelo.nome}\n"
        f"{origem.linhas} linhas | {origem.operacoes} operações\n\n"
        f"DESTINO GLOBAL\n{destino_modelo.codigo} — {destino_modelo.nome}\n"
        f"{destino.linhas} linhas | {destino.operacoes} operações\n\n"
        f"O código global {destino_modelo.codigo} será mantido. Nome, descrição, "
        "tipo, observações, estado, materiais, linhas e operações serão "
        "substituídos.\n\nPretende continuar?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if confirmacao != QMessageBox.StandardButton.Yes:
        return None

    with SessionLocal() as session:
        return DefValuesetModeloService(session).substituir_modelo_global(
            original_id,
            destino_modelo.id,
            dados_novos,
            autorizado=autorizado,
        )
