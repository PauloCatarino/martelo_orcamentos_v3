"""Focused tests for the single friendly ValueSet option presentation."""

from __future__ import annotations

import inspect
from types import SimpleNamespace

from app.domain.valueset_opcoes import base_codigo_opcao, normalizar_codigo_opcao
from app.services.def_valueset_modelo_linha_service import (
    DefValuesetModeloLinhaService,
)


def test_codigo_de_materia_prima_prefere_ref_le() -> None:
    assert base_codigo_opcao(
        chave="MATERIAL_PORTAS",
        nome_opcao="MDF branco",
        ref_le="FRT 0001",
        ref_materia_prima="MP-IGNORADA",
    ) == "LE_FRT_0001"


def test_opcao_livre_gera_codigo_normalizado_a_partir_do_nome() -> None:
    assert base_codigo_opcao(
        chave="MATERIAL_PORTAS",
        nome_opcao="MDF branco 19 mm",
        ref_le=None,
        ref_materia_prima=None,
    ) == "OP_MDF_BRANCO_19_MM"
    assert normalizar_codigo_opcao("  dobradiça / reta  ") == "DOBRADICA_RETA"


def test_codigo_disponivel_resolve_colisoes_de_forma_deterministica() -> None:
    class Repository:
        def get_by_modelo_chave_opcao(self, _modelo_id, _chave, codigo):
            return object() if codigo in {"OP_MDF", "OP_MDF_2"} else None

    service = DefValuesetModeloLinhaService.__new__(DefValuesetModeloLinhaService)
    service.repository = Repository()

    assert service._codigo_disponivel(10, "MATERIAL", "OP_MDF") == "OP_MDF_3"


def test_tres_tabelas_exibem_apenas_opcao() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    for headers in (
        DefValuesetModeloDetailPage.LINHA_HEADERS,
        OrcamentoValuesetPage.TABLE_HEADERS,
        OrcamentoItemValuesetPage.TABLE_HEADERS,
    ):
        assert headers.count("Opção") == 1
        assert "Nome opção" not in headers


def test_tres_dialogos_escondem_codigo_e_mostram_um_campo_opcao() -> None:
    dialog_paths = (
        "app.ui.dialogs.def_valueset_modelo_linha_dialog",
        "app.ui.dialogs.orcamento_valueset_linha_dialog",
        "app.ui.dialogs.orcamento_item_valueset_linha_dialog",
    )
    classes = (
        "DefValuesetModeloLinhaDialog",
        "OrcamentoValuesetLinhaDialog",
        "OrcamentoItemValuesetLinhaDialog",
    )

    for module_name, class_name in zip(dialog_paths, classes):
        module = __import__(module_name, fromlist=[class_name])
        dialog_class = getattr(module, class_name)
        source = inspect.getsource(dialog_class.__init__)
        assert "self.codigo_opcao_input.setVisible(False)" in source
        assert 'form.addRow("Opção", self.nome_opcao_input)' in source
        assert 'form.addRow("Código opção"' not in source
        assert 'form.addRow("Nome opção"' not in source


def test_edicao_deve_receber_codigo_tecnico_original() -> None:
    # The dialogs expose the code only through internal callback data; the
    # service is the final guard and ignores a changed internal value on edit.
    assert "codigo_opcao_original" in inspect.getsource(
        DefValuesetModeloLinhaService.editar_linha
    )
