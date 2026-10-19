"""Testes (puros) das regras dos nomes de pasta da exportação (fase 8W.4.0)."""

from __future__ import annotations

import pytest

from pathlib import Path

from app.domain.export_paths import (
    escolher_nome_pasta,
    encontrar_pasta_orcamento,
    nome_pasta_orcamento,
    numero_no_nome_da_pasta,
    numero_subpasta_versao,
    proxima_versao_livre,
    renomear_pasta_orcamento,
    separar_pasta_versao,
    simplificar_cliente,
    subpasta_versao,
    versoes_nas_subpastas,
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


# --- Orçamentos antigos: versões na pasta-mãe (19-10-2026) -----------------


def test_numero_subpasta_versao_so_aceita_dois_digitos():
    assert numero_subpasta_versao("06") == 6
    assert numero_subpasta_versao("01") == 1
    assert numero_subpasta_versao("00") is None
    assert numero_subpasta_versao("PDF") is None
    assert numero_subpasta_versao("2026") is None
    assert numero_subpasta_versao("6") is None


def test_versoes_nas_subpastas_ignora_o_que_nao_e_versao():
    nomes = ["03", "01", "PDF", "02", "Copias", "05", "04"]

    assert versoes_nas_subpastas(nomes) == [1, 2, 3, 4, 5]


def test_proxima_versao_livre_e_a_seguir_a_mais_alta():
    assert proxima_versao_livre(["01", "02", "03", "04", "05"]) == 6
    # Um buraco não é aproveitado: a seguinte é sempre depois da última.
    assert proxima_versao_livre(["01", "03"]) == 4
    assert proxima_versao_livre(["PDF"]) == 1
    assert proxima_versao_livre([]) == 1


def test_separar_pasta_versao_sobe_da_pasta_da_versao_para_a_mae():
    mae = Path("//server_le/Dep._Orcamentos/2026/260186_INNERE")

    assert separar_pasta_versao(mae / "05") == (mae, 5)
    assert separar_pasta_versao(mae) == (mae, None)


def test_numero_no_nome_da_pasta():
    assert numero_no_nome_da_pasta("260446_JF_VIVA") == "260446"
    assert numero_no_nome_da_pasta("1049_COSTA & ZEFERINO") == "1049"
    assert numero_no_nome_da_pasta("OBRAS_DIVERSAS") is None
    assert numero_no_nome_da_pasta("") is None
