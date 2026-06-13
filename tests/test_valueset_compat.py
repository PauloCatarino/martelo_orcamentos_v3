"""Tests for the ValueSet 'Mat. default' compatibility rule (IMOS)."""

from __future__ import annotations

from types import SimpleNamespace

from app.domain.valueset_compat import (
    TIPO_FERRAGEM,
    TIPO_MATERIAL,
    opcoes_valueset_compativeis,
    tipo_da_chave,
)

# Key -> type map (as built from def_valueset_chaves).
_CHAVE_TIPOS = {
    "MATERIAL_FUNDOS": TIPO_MATERIAL,
    "MATERIAL_PORTAS": TIPO_MATERIAL,
    "MATERIAL_LATERAIS": TIPO_MATERIAL,
    "FERRAGEM_PE_NIVELADOR": TIPO_FERRAGEM,
    "FERRAGEM_DOBRADICA": TIPO_FERRAGEM,
    "ORLA_FINA": "ORLA",
    "ACABAMENTO_FACE_SUP": "ACABAMENTO",
}


def _opcao(chave, codigo):
    return SimpleNamespace(chave=chave, codigo_opcao=codigo)


_OPCOES = [
    _opcao("MATERIAL_FUNDOS", "MDF19"),
    _opcao("MATERIAL_PORTAS", "TERMO_BRANCO"),
    _opcao("MATERIAL_LATERAIS", "MELAMINA"),
    _opcao("FERRAGEM_PE_NIVELADOR", "PE_PLAST"),
    _opcao("FERRAGEM_PE_NIVELADOR", "PE_METAL"),
    _opcao("FERRAGEM_DOBRADICA", "BLUM"),
    _opcao("ORLA_FINA", "ORLA_BRANCA"),
]


def _chaves(opcoes):
    return [o.chave for o in opcoes]


def test_tipo_da_chave() -> None:
    assert tipo_da_chave("MATERIAL_FUNDOS", _CHAVE_TIPOS) == TIPO_MATERIAL
    assert tipo_da_chave("ferragem_pe_nivelador", _CHAVE_TIPOS) == TIPO_FERRAGEM
    assert tipo_da_chave(None, _CHAVE_TIPOS) is None
    assert tipo_da_chave("DESCONHECIDA", _CHAVE_TIPOS) is None


def test_material_linha_lista_todas_as_chaves_material() -> None:
    # A MATERIAL line (fundos) sees every MATERIAL option (cross-material).
    compat = opcoes_valueset_compativeis("MATERIAL_FUNDOS", _OPCOES, _CHAVE_TIPOS)

    assert _chaves(compat) == [
        "MATERIAL_FUNDOS",
        "MATERIAL_PORTAS",
        "MATERIAL_LATERAIS",
    ]
    # No hardware / orla options leak in.
    assert all(c.startswith("MATERIAL_") for c in _chaves(compat))


def test_ferragem_linha_lista_so_a_mesma_chave() -> None:
    # A pé-nivelador line only sees the pé options — not dobradiças.
    compat = opcoes_valueset_compativeis(
        "FERRAGEM_PE_NIVELADOR", _OPCOES, _CHAVE_TIPOS
    )

    assert _chaves(compat) == ["FERRAGEM_PE_NIVELADOR", "FERRAGEM_PE_NIVELADOR"]
    assert all(c == "FERRAGEM_PE_NIVELADOR" for c in _chaves(compat))
    assert "FERRAGEM_DOBRADICA" not in _chaves(compat)


def test_orla_e_acabamento_nao_sao_tratadas() -> None:
    assert opcoes_valueset_compativeis("ORLA_FINA", _OPCOES, _CHAVE_TIPOS) == []
    assert (
        opcoes_valueset_compativeis("ACABAMENTO_FACE_SUP", _OPCOES, _CHAVE_TIPOS) == []
    )


def test_sem_chave_ou_desconhecida_sem_opcoes() -> None:
    assert opcoes_valueset_compativeis(None, _OPCOES, _CHAVE_TIPOS) == []
    assert opcoes_valueset_compativeis("", _OPCOES, _CHAVE_TIPOS) == []
    assert opcoes_valueset_compativeis("DESCONHECIDA", _OPCOES, _CHAVE_TIPOS) == []
