"""Tests for production table column configuration helpers."""

from __future__ import annotations

import json

from app.ui.helpers.colunas_producao import (
    COLUNAS_PRODUCAO,
    LARGURAS_DEFAULT_PRODUCAO,
    desserializar_config,
    serializar_config,
)


def _visiveis_default() -> list[str]:
    return [coluna.key for coluna in COLUNAS_PRODUCAO if coluna.visivel_default]


def test_desserializar_config_none_usa_defaults() -> None:
    visiveis, larguras = desserializar_config(None)

    assert visiveis == _visiveis_default()
    assert larguras == {}


def test_desserializar_config_invalido_usa_defaults() -> None:
    visiveis, larguras = desserializar_config("{nao-json")

    assert visiveis == _visiveis_default()
    assert larguras == {}


def test_serializar_e_desserializar_config_roundtrip() -> None:
    texto = serializar_config(
        ["obra", "ano", "localizacao", "desconhecida"],
        {"obra": 222, "ano": "70", "desconhecida": 999},
    )

    visiveis, larguras = desserializar_config(texto)

    assert visiveis == ["ano", "obra", "localizacao"]
    assert larguras["ano"] == 70
    assert larguras["obra"] == 222
    assert "desconhecida" not in larguras


def test_desserializar_config_ignora_colunas_desconhecidas() -> None:
    payload = {
        "visiveis": ["ano", "fantasma"],
        "larguras": {"ano": 80, "fantasma": 120},
    }

    visiveis, larguras = desserializar_config(json.dumps(payload))

    assert "fantasma" not in visiveis
    assert "fantasma" not in larguras


def test_coluna_nova_assume_visibilidade_default() -> None:
    larguras_antigas = {
        key: largura
        for key, largura in LARGURAS_DEFAULT_PRODUCAO.items()
        if key != "responsavel"
    }
    payload = {"visiveis": ["ano"], "larguras": larguras_antigas}

    visiveis, _larguras = desserializar_config(json.dumps(payload))

    assert "responsavel" in visiveis
    assert "localizacao" not in visiveis
