"""Tests for the default ValueSet models seed script."""

from __future__ import annotations

from scripts.create_default_valueset_modelos import (
    DEFAULT_VALUESET_MODELOS,
    DefaultValuesetModelosResult,
    ModeloLinhaSeed,
    ValuesetModeloSeed,
)


def _modelo_por_codigo(codigo: str) -> ValuesetModeloSeed:
    return next(modelo for modelo in DEFAULT_VALUESET_MODELOS if modelo.codigo == codigo)


def test_seed_imports() -> None:
    assert len(DEFAULT_VALUESET_MODELOS) > 0


def test_seed_contains_roupeiro_standard() -> None:
    codigos = {modelo.codigo for modelo in DEFAULT_VALUESET_MODELOS}

    assert "ROUPEIRO_STANDARD" in codigos


def test_each_model_has_codigo_and_nome() -> None:
    for modelo in DEFAULT_VALUESET_MODELOS:
        assert isinstance(modelo, ValuesetModeloSeed)
        assert modelo.codigo.strip()
        assert modelo.nome.strip()
        assert len(modelo.linhas) > 0


def test_each_line_has_chave_codigo_opcao_nome_opcao() -> None:
    for modelo in DEFAULT_VALUESET_MODELOS:
        for linha in modelo.linhas:
            assert isinstance(linha, ModeloLinhaSeed)
            assert linha.chave.strip()
            assert linha.codigo_opcao.strip()
            assert linha.nome_opcao.strip()


def test_no_empty_chaves_or_codigo_opcao() -> None:
    for modelo in DEFAULT_VALUESET_MODELOS:
        for linha in modelo.linhas:
            assert linha.chave != ""
            assert linha.codigo_opcao != ""


def test_roupeiro_contains_expected_keys() -> None:
    chaves = {linha.chave for linha in _modelo_por_codigo("ROUPEIRO_STANDARD").linhas}

    assert "MATERIAL_PORTAS" in chaves
    assert "FERRAGEM_DOBRADICA" in chaves
    assert "FERRAGEM_CORREDICA" in chaves
    assert "ACABAMENTO_FACE_SUP" in chaves


def test_no_duplicate_chave_codigo_opcao_per_model() -> None:
    for modelo in DEFAULT_VALUESET_MODELOS:
        pares = [(linha.chave, linha.codigo_opcao) for linha in modelo.linhas]
        assert len(pares) == len(set(pares))


def test_result_dataclass() -> None:
    result = DefaultValuesetModelosResult(
        modelos_criados=1,
        modelos_reutilizados=0,
        linhas_criadas=18,
        linhas_reutilizadas=0,
        linhas_atualizadas=0,
    )

    assert result.modelos_criados == 1
    assert result.linhas_criadas == 18
