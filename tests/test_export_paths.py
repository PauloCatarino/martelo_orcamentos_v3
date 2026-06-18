"""Testes (puros) das regras dos nomes de pasta da exportação (fase 8W.4.0)."""

from __future__ import annotations

import pytest

from app.domain.export_paths import (
    escolher_nome_pasta,
    encontrar_pasta_orcamento,
    nome_pasta_orcamento,
    renomear_pasta_orcamento,
    simplificar_cliente,
    subpasta_versao,
)


def test_simplificar_cliente_prioriza_nome_simplex():
    assert simplificar_cliente("JF VIVA", "Joao Ferreira") == "JF_VIVA"


def test_simplificar_cliente_troca_espacos_por_underscore():
    assert simplificar_cliente(None, "Maria do Carmo") == "MARIA_DO_CARMO"


def test_simplificar_cliente_fallback_quando_tudo_vazio():
    assert simplificar_cliente(None, None) == "CLIENTE"
    assert simplificar_cliente("", "  ") == "CLIENTE"


def test_subpasta_versao_dois_digitos():
    assert subpasta_versao(1) == "01"
    assert subpasta_versao(12) == "12"


def test_escolher_nome_pasta_reutiliza_existente_com_prefixo():
    existentes = ["outra_coisa", "260655_QUALQUER", "260999_X"]
    assert (
        escolher_nome_pasta(existentes, "260655", "JF VIVA", "Joao Ferreira")
        == "260655_QUALQUER"
    )


def test_escolher_nome_pasta_constroi_quando_nao_existe():
    assert (
        escolher_nome_pasta([], "260655", "JF VIVA", "Joao Ferreira")
        == "260655_JF_VIVA"
    )
    assert nome_pasta_orcamento("260655", "JF VIVA", "Joao Ferreira") == "260655_JF_VIVA"


def test_encontrar_pasta_orcamento_por_prefixo(tmp_path) -> None:
    ano = tmp_path / "2026"
    (ano / "260005_NOME_ANTIGO").mkdir(parents=True)
    (ano / "260006_OUTRO").mkdir()

    encontrada = encontrar_pasta_orcamento(ano, "260005")

    assert encontrada is not None and encontrada.name == "260005_NOME_ANTIGO"


def test_encontrar_pasta_orcamento_sem_correspondencia(tmp_path) -> None:
    assert encontrar_pasta_orcamento(tmp_path / "2026", "260005") is None


def test_renomear_pasta_orcamento_muda_o_simplex(tmp_path) -> None:
    ano = tmp_path / "2026"
    antiga = ano / "260005_NOME_ANTIGO"
    (antiga / "01").mkdir(parents=True)

    resultado = renomear_pasta_orcamento(ano, "260005", "NOME NOVO", "Nome Novo")

    assert resultado is not None
    _antiga, nova = resultado
    assert nova.name == "260005_NOME_NOVO"
    assert (nova / "01").is_dir()
    assert not antiga.exists()


def test_renomear_pasta_orcamento_nome_ja_coincide(tmp_path) -> None:
    ano = tmp_path / "2026"
    (ano / "260005_NOME_NOVO").mkdir(parents=True)

    assert renomear_pasta_orcamento(ano, "260005", "NOME_NOVO", "Nome Novo") is None


def test_renomear_pasta_orcamento_destino_existente(tmp_path) -> None:
    ano = tmp_path / "2026"
    (ano / "260005_NOME_ANTIGO").mkdir(parents=True)
    (ano / "260005_NOME_NOVO").mkdir()

    with pytest.raises(FileExistsError):
        renomear_pasta_orcamento(ano, "260005", "NOME NOVO", "Nome Novo")
