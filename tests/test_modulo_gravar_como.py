"""«Gravar como…» na Biblioteca de Módulos: copiar em vez de mover.

O «Converter Âmbito» que aqui havia era o equivalente a cortar de um lado e
colar no outro: o módulo passava para Global e desaparecia da biblioteca da
pessoa. Muitas vezes o que se quer é ter o mesmo módulo nos dois sítios, cada
um a seguir o seu caminho — daí a cópia.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.domain.modulo_categorias import AMBITO_GLOBAL, AMBITO_UTILIZADOR
from app.services.def_modulo_service import (
    CriarDefModuloData,
    CriarDefModuloLinhaData,
    DefModuloService,
)


def _criar_original(session, *, ambito=AMBITO_UTILIZADOR, user_id=1):
    return DefModuloService(session).criar(
        CriarDefModuloData(
            codigo="RECORTE_L",
            nome="RECORTE PEÇAS PILAR 'L'",
            descricao="RECORTE PILAR 'L' COM 2 LATERAIS",
            ambito=ambito,
            user_id=user_id,
            categoria="ROUPEIROS",
            linhas=[
                CriarDefModuloLinhaData(ordem=1, descricao="Lateral esq"),
                CriarDefModuloLinhaData(ordem=2, descricao="Lateral drt"),
            ],
        )
    )


def _copia(codigo, ambito):
    return CriarDefModuloData(
        codigo=codigo,
        nome="RECORTE PEÇAS PILAR 'L'",
        descricao="Cópia",
        ambito=ambito,
        categoria="ROUPEIROS",
    )


def test_a_copia_leva_as_linhas_todas(session) -> None:
    original = _criar_original(session)
    servico = DefModuloService(session)

    copia = servico.duplicar(
        original.modulo.id,
        _copia("RECORTE_L_2", AMBITO_UTILIZADOR),
        acting_user_id=1,
        is_admin=False,
    )

    assert copia.modulo.codigo == "RECORTE_L_2"
    assert [linha.descricao for linha in copia.linhas] == [
        "Lateral esq",
        "Lateral drt",
    ]


def test_o_original_fica_onde_estava(session) -> None:
    """A diferença para o antigo «Converter Âmbito»."""
    original = _criar_original(session)
    servico = DefModuloService(session)

    servico.duplicar(
        original.modulo.id,
        _copia("RECORTE_L_GLOBAL", AMBITO_GLOBAL),
        acting_user_id=1,
        is_admin=True,
    )

    ainda_la = servico.obter_com_linhas(original.modulo.id)
    assert ainda_la is not None
    assert ainda_la.modulo.ambito == AMBITO_UTILIZADOR
    assert ainda_la.modulo.user_id == 1
    assert len(ainda_la.linhas) == 2


def test_qualquer_pessoa_copia_um_global_para_a_sua_biblioteca(session) -> None:
    """Era isto que o «Sem permissão» impedia."""
    global_ = _criar_original(session, ambito=AMBITO_GLOBAL, user_id=None)

    copia = DefModuloService(session).duplicar(
        global_.modulo.id,
        _copia("RECORTE_L_MEU", AMBITO_UTILIZADOR),
        acting_user_id=7,
        is_admin=False,
    )

    assert copia.modulo.ambito == AMBITO_UTILIZADOR
    assert copia.modulo.user_id == 7


def test_so_o_administrador_cria_modulos_globais(session) -> None:
    """O que é global aparece a toda a gente: não é escolha de um só."""
    original = _criar_original(session)

    with pytest.raises(ValueError, match="administrador"):
        DefModuloService(session).duplicar(
            original.modulo.id,
            _copia("RECORTE_L_GLOBAL", AMBITO_GLOBAL),
            acting_user_id=1,
            is_admin=False,
        )


def test_nao_deixa_dois_modulos_com_o_mesmo_codigo(session) -> None:
    original = _criar_original(session)

    with pytest.raises(ValueError, match="Já existe"):
        DefModuloService(session).duplicar(
            original.modulo.id,
            _copia("RECORTE_L", AMBITO_UTILIZADOR),
            acting_user_id=1,
            is_admin=False,
        )


def test_um_modulo_de_utilizador_precisa_de_dono(session) -> None:
    original = _criar_original(session)

    with pytest.raises(ValueError, match="autenticado"):
        DefModuloService(session).duplicar(
            original.modulo.id,
            _copia("RECORTE_L_2", AMBITO_UTILIZADOR),
            acting_user_id=None,
            is_admin=False,
        )


# ---- a caixa de edição -----------------------------------------------------


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _dialogo(_app, **kwargs):
    from app.ui.dialogs.editar_modulo_dialog import (
        EditarModuloDialog,
        EditarModuloDialogData,
    )

    return EditarModuloDialog(
        codigo="RECORTE_L",
        dados=EditarModuloDialogData(
            nome="RECORTE PEÇAS PILAR 'L'",
            descricao=None,
            ambito=AMBITO_UTILIZADOR,
            categoria="ROUPEIROS",
            imagem_path=None,
        ),
        **kwargs,
    )


def test_guardar_recusa_um_codigo_diferente(_app) -> None:
    """Mudar o código não renomeia o módulo — cria um novo, e isso é o outro botão."""
    guardados: list = []
    dialog = _dialogo(_app, on_save=lambda dados: guardados.append(dados) or True)
    dialog.codigo_input.setText("OUTRO_CODIGO")

    dialog._validate_and_accept()

    assert guardados == []
    assert "Gravar como" in dialog.error_label.text()


def test_gravar_como_exige_um_codigo_novo(_app) -> None:
    copiados: list = []
    dialog = _dialogo(_app, on_save_as=lambda dados: copiados.append(dados) or True)

    dialog._validate_and_save_as()

    assert copiados == []
    assert "código diferente" in dialog.error_label.text()


def test_gravar_como_com_codigo_novo_e_ambito_escolhido(_app) -> None:
    copiados: list = []
    dialog = _dialogo(_app, on_save_as=lambda dados: copiados.append(dados) or True)
    dialog.codigo_input.setText("recorte_l_2")
    dialog._selecionar(dialog.ambito_input, AMBITO_GLOBAL)

    dialog._validate_and_save_as()

    assert dialog.codigo() == "RECORTE_L_2"  # em maiúsculas, como os outros
    assert len(copiados) == 1
    assert copiados[0].ambito == AMBITO_GLOBAL


def test_sem_permissao_o_guardar_desliga_mas_o_gravar_como_fica(_app) -> None:
    dialog = _dialogo(
        _app,
        pode_guardar=False,
        motivo_sem_guardar="Este módulo é global e é o administrador que o gere.",
    )

    from PySide6.QtWidgets import QDialogButtonBox

    guardar = dialog.button_box.button(QDialogButtonBox.StandardButton.Save)
    assert guardar.isEnabled() is False
    assert dialog.save_as_button.isEnabled() is True
    assert "administrador" in dialog.aviso_label.text()
