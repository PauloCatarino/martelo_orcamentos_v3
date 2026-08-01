"""Gravar como… cria uma SEGUNDA opção na mesma chave (ex.: 2.º varão)."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from app.repositories.def_valueset_modelo_linha_repository import (
    DefValuesetModeloLinhaResumo,
)


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _linha(**kwargs) -> DefValuesetModeloLinhaResumo:
    base = {
        "id": 7,
        "def_valueset_modelo_id": 10,
        "chave": "FERRAGEM_VARAO",
        "codigo_opcao": "FERRAGEM_VARAO",
        "nome_opcao": "VARAO STD",
        "padrao": False,
        "ordem": 13,
        "descricao": None,
        "materia_prima_id": None,
        "ref_materia_prima": "FER0091",
        "descricao_materia_prima": "VARAO ROUPEIRO STD",
        "valor_texto": "Varão standard",
        "origem": None,
        "ref_le": "FER0091",
        "descricao_no_orcamento": "VARAO ROUPEIRO STD",
        "preco_tabela": None,
        "margem_percentagem": None,
        "desconto_percentagem": None,
        "preco_liquido": None,
        "unidade": "ML",
        "desperdicio_percentagem": None,
        "tipo_materia_prima": "SPP",
        "familia_materia_prima": "FERRAGENS",
        "coresp_orla_0_4": None,
        "coresp_orla_1_0": None,
        "comp_mp": None,
        "larg_mp": None,
        "esp_mp": None,
        "origem_dados": "MATERIA_PRIMA",
        "editado_localmente": False,
        "ativo": True,
        "observacoes": None,
        "prioridade": 1,
    }
    base.update(kwargs)
    return DefValuesetModeloLinhaResumo(**base)


def _abrir_dialogo(monkeypatch, guardado: list):
    """Open the model-line dialog on an existing line, without a database."""
    from app.ui.dialogs import def_valueset_modelo_linha_dialog as modulo

    monkeypatch.setattr(
        modulo,
        "carregar_chaves_valueset_combo",
        lambda combo, valor_atual=None: combo.addItem("Varão", "FERRAGEM_VARAO"),
    )
    monkeypatch.setattr(
        modulo, "obter_valor_chave_combo", lambda _combo: "FERRAGEM_VARAO"
    )

    return modulo.DefValuesetModeloLinhaDialog(
        linha=_linha(),
        on_save=lambda dados: guardado.append(("guardar", dados)) or True,
        on_save_as=lambda dados: guardado.append(("gravar_como", dados)) or True,
    )


def test_gravar_como_nao_reaproveita_o_codigo_da_opcao(_app, monkeypatch) -> None:
    guardado: list = []
    dialog = _abrir_dialogo(monkeypatch, guardado)
    dialog.nome_opcao_input.setText("VARAO ROUPEIRO SILK PRETO")

    dialog._validate_and_save_as()

    acao, dados = guardado[-1]
    assert acao == "gravar_como"
    # Sem código: o serviço gera um livre a partir do nome/referências, senão
    # bateria com a opção de onde se partiu.
    assert dados.codigo_opcao == ""
    assert dados.nome_opcao == "VARAO ROUPEIRO SILK PRETO"


def test_guardar_mantem_o_codigo_da_opcao(_app, monkeypatch) -> None:
    guardado: list = []
    dialog = _abrir_dialogo(monkeypatch, guardado)

    dialog._validate_and_accept()

    acao, dados = guardado[-1]
    assert acao == "guardar"
    # A identidade técnica de uma linha que já existe não muda ao editá-la.
    assert dados.codigo_opcao == "FERRAGEM_VARAO"


def test_servico_gera_codigo_livre_para_a_segunda_opcao(monkeypatch) -> None:
    from app.services import def_valueset_modelo_linha_service as service_module

    existentes = {"FERRAGEM_VARAO"}
    criados: list = []

    class _FakeRepository:
        def __init__(self, _session):
            pass

        def get_by_modelo_chave_opcao(self, _modelo_id, _chave, codigo):
            return SimpleNamespace(id=1) if codigo in existentes else None

        def create(self, **fields):
            criados.append(fields)
            return SimpleNamespace(**fields)

    monkeypatch.setattr(service_module, "DefValuesetModeloLinhaRepository", _FakeRepository)

    session = SimpleNamespace(commit=lambda: None)
    service = service_module.DefValuesetModeloLinhaService(session)
    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="FERRAGEM_VARAO",
            codigo_opcao="",
            nome_opcao="VARAO ROUPEIRO SILK PRETO",
            ref_le="FER0092",
            prioridade=2,
        )
    )

    codigo = criados[-1]["codigo_opcao"]
    assert codigo not in existentes
    assert criados[-1]["prioridade"] == 2
