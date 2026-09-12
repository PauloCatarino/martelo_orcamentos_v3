"""A página das chaves trata "mudar o código" como renomeação, não edição."""

from __future__ import annotations

import inspect


def test_editar_chave_passa_pela_renomeacao_quando_o_codigo_muda() -> None:
    from app.ui.pages.def_valueset_chaves_page import DefValuesetChavesPage

    fonte = inspect.getsource(DefValuesetChavesPage.abrir_editar_chave)

    assert "_codigo_mudou" in fonte
    assert "_renomear_chave" in fonte
    # Se o utilizador desistir do diálogo, a gravação não avança.
    assert "if resultado is None:" in fonte
    assert "return False" in fonte


def test_renomear_conta_antes_de_alterar_e_pergunta_o_alcance() -> None:
    from app.ui.pages.def_valueset_chaves_page import DefValuesetChavesPage

    fonte = inspect.getsource(DefValuesetChavesPage._renomear_chave)

    assert "contar_utilizacoes" in fonte
    assert "RenomearChaveValuesetDialog" in fonte
    assert "incluir_orcamentos=confirmacao.incluir_orcamentos" in fonte
    assert "Renomeação cancelada" in fonte


def test_codigo_mudou_ignora_espacos_e_caixa() -> None:
    from app.ui.pages.def_valueset_chaves_page import DefValuesetChavesPage

    mudou = DefValuesetChavesPage._codigo_mudou
    assert mudou("FERRAGEM_VARAO", "  ferragem varao ") is False
    assert mudou("FERRAGEM_VARAO", "FERRAGEM VARAO") is False
    assert mudou("FERRAGEM_VARAO", "FERRAGEM_VARAO_2") is True


def test_mensagem_diz_o_que_mudou_e_o_que_ficou() -> None:
    from types import SimpleNamespace

    from app.ui.pages.def_valueset_chaves_page import DefValuesetChavesPage

    so_catalogos = DefValuesetChavesPage._mensagem_renomeacao(
        SimpleNamespace(
            codigo_antigo="A", codigo_novo="B",
            catalogos_atualizados=4, orcamentos_atualizados=0,
            incluiu_orcamentos=False,
        )
    )
    assert "4 linha(s) de catálogo" in so_catalogos
    assert "orçamentos já feitos ficaram como estavam" in so_catalogos

    com_orcamentos = DefValuesetChavesPage._mensagem_renomeacao(
        SimpleNamespace(
            codigo_antigo="A", codigo_novo="B",
            catalogos_atualizados=4, orcamentos_atualizados=576,
            incluiu_orcamentos=True,
        )
    )
    assert "576 de orçamentos" in com_orcamentos


def test_dialogo_deixa_os_orcamentos_de_fora_por_omissao(qt_app=None) -> None:
    import sys

    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication(sys.argv)

    from app.services.def_valueset_chave_renomeacao_service import (
        OcorrenciaChave,
        OcorrenciasChave,
    )
    from app.ui.dialogs.renomear_chave_valueset_dialog import (
        RenomearChaveValuesetDialog,
    )

    ocorrencias = OcorrenciasChave(
        codigo="FERRAGEM_SUPORTE_VARAO",
        ocorrencias=(
            OcorrenciaChave("Linhas de modelos ValueSet", 16, False),
            OcorrenciaChave("Peças — material", 1, False),
            OcorrenciaChave("Orçamentos — ValueSet do item", 501, True),
        ),
    )
    dialog = RenomearChaveValuesetDialog(ocorrencias, "FERRAGEM_SUPORTE_LATERAL_VARAO")

    # O que faz a diferença entre corrigir e reescrever história.
    assert dialog.incluir_orcamentos is False
    assert "17" in dialog.aviso_label.text()  # só os catálogos
    assert "501" in dialog.aviso_label.text()  # e diz quantos ficam de fora

    dialog.incluir_orcamentos_check.setChecked(True)
    assert dialog.incluir_orcamentos is True
    assert "518" in dialog.aviso_label.text()


def test_dialogo_sem_orcamentos_nao_oferece_a_opcao() -> None:
    import sys

    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication(sys.argv)

    from app.services.def_valueset_chave_renomeacao_service import (
        OcorrenciaChave,
        OcorrenciasChave,
    )
    from app.ui.dialogs.renomear_chave_valueset_dialog import (
        RenomearChaveValuesetDialog,
    )

    ocorrencias = OcorrenciasChave(
        codigo="CHAVE_NOVA",
        ocorrencias=(OcorrenciaChave("Linhas de modelos ValueSet", 2, False),),
    )
    dialog = RenomearChaveValuesetDialog(ocorrencias, "CHAVE_NOVA_2")

    assert dialog.incluir_orcamentos_check.isEnabled() is False
    assert "2 linha(s) de catálogo" in dialog.aviso_label.text()
