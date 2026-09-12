"""O catalogo de materias-primas abre ja' filtrado pelo genero da linha.

Sao ~1400 materias-primas. Sem pre'-filtro, acrescentar uma ferragem a uma
chave obrigava a escolher Tipo e Familia a` mao de cada vez — e o Custeio ja'
fazia isto ha' muito, so' as tres tabelas de ValueSet e' que ficaram de fora.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from app.domain.valueset_prefiltro_materia_prima import sugerir_tipo_familia_da_chave


def _linha(chave, tipo=None, familia=None, ativo=True):
    return SimpleNamespace(
        chave=chave,
        tipo_materia_prima=tipo,
        familia_materia_prima=familia,
        ativo=ativo,
    )


LINHAS = [
    _linha("SISTEMA_CORRER_CALHA_INF", "ROUPEIROS CORRER", "FERRAGENS"),
    _linha("SISTEMA_CORRER_CALHA_INF", "ROUPEIROS CORRER", "FERRAGENS"),
    _linha("MATERIAL_COSTAS", "AGLOMERADO", "PLACAS"),
    _linha("MATERIAL_ENCHIMENTOS", "AGLOMERADO", "PLACAS"),
    _linha("MATERIAL_ENCHIMENTOS", "MDF", "PLACAS"),
    _linha("MATERIAL_ENCHIMENTOS", "MDF", "PLACAS"),
    _linha("CHAVE_SEM_SNAPSHOT", None, None),
]


def test_a_chave_diz_o_gene_ro_de_material() -> None:
    assert sugerir_tipo_familia_da_chave(LINHAS, "SISTEMA_CORRER_CALHA_INF") == (
        "ROUPEIROS CORRER",
        "FERRAGENS",
    )


def test_sem_chave_nao_ha_sugestao() -> None:
    """"Sem chave" no combo e' None: filtrar por nada seria pior que nao filtrar."""
    assert sugerir_tipo_familia_da_chave(LINHAS, None) == (None, None)
    assert sugerir_tipo_familia_da_chave(LINHAS, "   ") == (None, None)


def test_chave_nova_nao_inventa_filtro() -> None:
    assert sugerir_tipo_familia_da_chave(LINHAS, "CHAVE_QUE_NAO_EXISTE") == (None, None)


def test_linhas_sem_snapshot_nao_dao_filtro_vazio() -> None:
    assert sugerir_tipo_familia_da_chave(LINHAS, "CHAVE_SEM_SNAPSHOT") == (None, None)


def test_quando_a_chave_tem_tipos_diferentes_ganha_o_mais_usado() -> None:
    """Medido na base real: 100% das chaves tem uma familia so', mas 5% tem
    dois tipos (AGLOMERADO e MDF na mesma chave), que e' legitimo — e' para isso
    que servem varias opcoes. O mais frequente e' um palpite, nao uma imposicao.
    """
    assert sugerir_tipo_familia_da_chave(LINHAS, "MATERIAL_ENCHIMENTOS") == (
        "MDF",
        "PLACAS",
    )


def test_a_chave_compara_se_sem_ligar_a_maiusculas() -> None:
    assert sugerir_tipo_familia_da_chave(LINHAS, "material_costas") == (
        "AGLOMERADO",
        "PLACAS",
    )


def test_as_inativas_contam_a_mesma() -> None:
    """Desativar uma opcao nao muda o genero de material que a chave usa."""
    linhas = [_linha("SO_INATIVA", "FERRAGENS DIVERSAS", "FERRAGENS", ativo=False)]

    assert sugerir_tipo_familia_da_chave(linhas, "SO_INATIVA") == (
        "FERRAGENS DIVERSAS",
        "FERRAGENS",
    )


pytest.importorskip("PySide6")

DIALOGOS = [
    ("def_valueset_modelo_linha_dialog", "DefValuesetModeloLinhaDialog"),
    ("orcamento_valueset_linha_dialog", "OrcamentoValuesetLinhaDialog"),
    ("orcamento_item_valueset_linha_dialog", "OrcamentoItemValuesetLinhaDialog"),
]

PAGINAS = [
    ("def_valueset_modelo_detail_page", "DefValuesetModeloDetailPage"),
    ("orcamento_valueset_page", "OrcamentoValuesetPage"),
    ("orcamento_item_valueset_page", "OrcamentoItemValuesetPage"),
]


@pytest.mark.parametrize("modulo, classe", DIALOGOS)
def test_os_tres_dialogos_abrem_o_catalogo_ja_filtrado(modulo, classe) -> None:
    import importlib

    dialogo = getattr(importlib.import_module(f"app.ui.dialogs.{modulo}"), classe)

    assert "sugestao_filtros" in inspect.signature(dialogo).parameters

    abrir = inspect.getsource(dialogo.abrir_picker_materia_prima)
    assert "initial_tipo=tipo" in abrir
    assert "initial_familia=familia" in abrir

    sugeridos = inspect.getsource(dialogo._filtros_sugeridos)
    # A propria linha manda; a sugestao so' entra no que estiver por preencher.
    assert "self.tipo_mp_input.text()" in sugeridos
    assert "self.familia_mp_input.text()" in sugeridos
    assert "tipo or sugerido_tipo" in sugeridos
    assert "familia or sugerida_familia" in sugeridos
    assert "obter_valor_chave_combo(self.chave_input)" in sugeridos


@pytest.mark.parametrize("modulo, classe", PAGINAS)
def test_as_tres_paginas_dizem_o_que_usam_as_linhas_irmas(modulo, classe) -> None:
    import importlib

    pagina = getattr(importlib.import_module(f"app.ui.pages.{modulo}"), classe)

    sugerir = inspect.getsource(pagina._sugerir_filtros_materia_prima)
    assert "sugerir_tipo_familia_da_chave" in sugerir
    assert "self._todas_linhas" in sugerir

    # Tanto a linha nova como a edicao: e' na linha nova que mais faz falta.
    fonte = inspect.getsource(importlib.import_module(f"app.ui.pages.{modulo}"))
    assert fonte.count("sugestao_filtros=self._sugerir_filtros_materia_prima") == 2


def test_um_filtro_que_o_catalogo_ja_nao_tem_nao_abre_a_lista_vazia() -> None:
    """Snapshot de um material desativado: melhor ver tudo que ver nada."""
    from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog

    fonte = inspect.getsource(MateriaPrimaPickerDialog._definir_filtro_inicial)
    assert "if indice < 0:" in fonte
    assert "return" in fonte
    # Ja' nao se acrescenta o valor perdido ao combo.
    assert "combo.addItem" not in fonte
