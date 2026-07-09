"""Tests for the shared ValueSet table styling helper."""

from __future__ import annotations

from types import SimpleNamespace

from app.ui import tema
from app.ui.widgets.estilo_tabela_valueset import (
    preparar_linhas_valueset,
    texto_ativo_valueset,
    texto_chave_valueset,
    texto_editado_valueset,
    texto_opcao_valueset,
    texto_prioridade_valueset,
)


def _linha(**kwargs):
    base = {
        "id": 1,
        "chave": "MATERIAL_CAIXOTE",
        "codigo_opcao": "OPCAO",
        "prioridade": None,
        "ordem": 1,
        "editado_localmente": False,
        "ativo": True,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_preparar_linhas_ordena_e_agrupa_por_chave_prioridade_ordem_id() -> None:
    linhas = [
        _linha(id=5, chave="MATERIAL_PORTAS", prioridade=None, ordem=1),
        _linha(id=3, chave="FERRAGEM_DOBRADICA", prioridade=None, ordem=2),
        _linha(id=2, chave="FERRAGEM_DOBRADICA", prioridade=1, ordem=9),
        _linha(id=4, chave="FERRAGEM_DOBRADICA", prioridade=None, ordem=1),
        _linha(id=1, chave="ACABAMENTO", prioridade=2, ordem=1),
    ]

    estados = preparar_linhas_valueset(linhas)

    assert [estado.linha.id for estado in estados] == [1, 2, 4, 3, 5]
    assert [estado.indice_grupo for estado in estados] == [0, 1, 1, 1, 2]
    assert [estado.primeira_do_grupo for estado in estados] == [
        True,
        True,
        False,
        False,
        True,
    ]
    assert [estado.fundo_grupo for estado in estados] == [
        tema.cor_grupo_chave(0),
        tema.cor_grupo_chave(1),
        tema.cor_grupo_chave(1),
        tema.cor_grupo_chave(1),
        tema.cor_grupo_chave(2),
    ]


def test_textos_e_marcas_para_linha_editada_prioridade_um() -> None:
    estado = preparar_linhas_valueset(
        [
            _linha(
                id=10,
                chave="FERRAGEM_PUXADOR",
                codigo_opcao="PUXADOR_TIC_TAC",
                prioridade=1,
                editado_localmente=True,
            )
        ]
    )[0]

    assert estado.prioridade_um is True
    assert estado.editado_localmente is True
    assert estado.ativo is True
    assert texto_chave_valueset(estado) == "FERRAGEM_PUXADOR"
    assert texto_opcao_valueset(estado, estado.linha.codigo_opcao) == "✎ PUXADOR_TIC_TAC"
    assert texto_prioridade_valueset(estado) == "1"
    assert texto_editado_valueset(estado) == "✎ Sim"
    assert texto_ativo_valueset(estado) == "✓"


def test_textos_e_marcas_para_linha_sem_prioridade_inativa() -> None:
    estado = preparar_linhas_valueset(
        [_linha(id=10, prioridade=None, ativo=False)]
    )[0]

    assert estado.prioridade_um is False
    assert estado.editado_localmente is False
    assert estado.ativo is False
    assert texto_prioridade_valueset(estado) == "—"
    assert texto_editado_valueset(estado) == "—"
    assert texto_ativo_valueset(estado) == "✗"


def test_chave_so_aparece_na_primeira_linha_do_grupo() -> None:
    estados = preparar_linhas_valueset(
        [
            _linha(id=1, chave="FERRAGEM_CORREDICA", ordem=1),
            _linha(id=2, chave="FERRAGEM_CORREDICA", ordem=2),
        ]
    )

    assert texto_chave_valueset(estados[0]) == "FERRAGEM_CORREDICA"
    assert texto_chave_valueset(estados[1]) == ""
