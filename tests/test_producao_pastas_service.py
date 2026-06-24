"""Tests for production folder tree helpers."""

from __future__ import annotations

from app.services.producao_service import (
    gerar_nome_enc_imos_ix,
    gerar_nome_plano_cut_rite,
)
from app.services.producao_pastas_service import (
    PRODUCAO_BASE_PATH_DEFAULT,
    _folder_name_matches_prefix,
    _norm_enc,
    _normalizar_path_windows,
    _num_enc_norm,
    _tipo_dir,
    listar_pastas_enc_arvore,
    segmentos_pasta,
)


def test_norm_enc_formata_phc_e_cliente_final() -> None:
    assert _norm_enc("475") == "0475"
    assert _norm_enc("_5") == "_005"
    assert _num_enc_norm("1058") == "1058"
    assert _num_enc_norm("_5") == "_005"


def test_tipo_dir_distingue_cliente_final() -> None:
    assert _tipo_dir("Encomenda de Cliente Final") == "Encomenda de Cliente Final"
    assert _tipo_dir("Encomenda de Cliente") == "Encomenda de Cliente"


def test_folder_name_matches_prefix_exige_prefixo_correto() -> None:
    assert _folder_name_matches_prefix("0278_JF_VIVA", "0278") is True
    assert _folder_name_matches_prefix("1058_JF_VIVA", "1058") is True
    assert _folder_name_matches_prefix("1058", "1058") is True
    assert _folder_name_matches_prefix("10589_X", "1058") is False
    assert _folder_name_matches_prefix("0279_X", "0278") is False


def test_default_producao_base_path_usa_host_unc_correto() -> None:
    assert (
        PRODUCAO_BASE_PATH_DEFAULT
        == r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep_Producao"
    )


def test_normalizar_path_windows_colapsa_barras_e_preserva_unc() -> None:
    assert (
        _normalizar_path_windows(
            r"\\\\SERVER_LE\\_Lanca_Encanto\\LancaEncanto\\Dep_Producao"
        )
        == r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep_Producao"
    )
    assert (
        _normalizar_path_windows(
            r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep_Producao"
        )
        == r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep_Producao"
    )
    assert _normalizar_path_windows("C:/a//b") == r"C:\a\b"
    assert _normalizar_path_windows("") == ""


def test_gerar_nomes_externos_de_producao() -> None:
    assert (
        gerar_nome_plano_cut_rite(
            "2026",
            "1058",
            "01",
            "01",
            nome_cliente_simplex="JF VIVA",
        )
        == "1058_01_01_26_JF_VIVA"
    )
    assert (
        gerar_nome_enc_imos_ix(
            "2026",
            "1058",
            "01",
            nome_cliente_simplex="JF VIVA",
        )
        == "1058_01_26_JF_VIVA"
    )


def test_segmentos_pasta_para_nova_versao() -> None:
    assert segmentos_pasta(
        "1058",
        "01",
        "01",
        nome_simplex="JF_VIVA",
    ) == (
        "1058_JF_VIVA",
        "1058_01_JF_VIVA",
        "1058_01_01_JF_VIVA",
    )


def test_listar_pastas_enc_arvore_lista_niveis_do_servidor(tmp_path) -> None:
    root = tmp_path / "2026" / "Encomenda de Cliente"
    pasta_obra = root / "1058_JF_VIVA" / "1058_01_JF_VIVA"
    for plano in ("01", "02", "03"):
        (pasta_obra / f"1058_01_{plano}_JF_VIVA").mkdir(parents=True)
    (root / "10589_X").mkdir()

    root_path, arvore = listar_pastas_enc_arvore(
        object(),
        ano="2026",
        num_enc_phc="1058",
        tipo_pasta="Encomenda de Cliente",
        base_dir=tmp_path,
    )

    assert root_path == str(root)
    assert arvore == {
        "1058_JF_VIVA": {
            "1058_01_JF_VIVA": [
                "1058_01_01_JF_VIVA",
                "1058_01_02_JF_VIVA",
                "1058_01_03_JF_VIVA",
            ]
        }
    }
