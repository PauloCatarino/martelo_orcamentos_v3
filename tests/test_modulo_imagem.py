"""Tests for the module image helpers (phase 8U.4)."""

from __future__ import annotations

import os

from app.domain.modulo_imagem import (
    caminho_para_file_url,
    copiar_imagem_para_pasta,
    sanitizar_codigo,
    tooltip_imagem_html,
)


def _criar_imagem(caminho: str) -> None:
    with open(caminho, "wb") as ficheiro:
        ficheiro.write(b"fake-image-bytes")


def test_sanitizar_codigo() -> None:
    assert sanitizar_codigo("ROUP_2P") == "ROUP_2P"
    assert sanitizar_codigo("Cozinha/Base 2") == "Cozinha_Base_2"
    assert sanitizar_codigo("  ") == "modulo"
    assert sanitizar_codigo(None) == "modulo"


def test_copiar_imagem_copia_com_nome_por_codigo(tmp_path) -> None:
    origem = tmp_path / "foto_original.png"
    _criar_imagem(str(origem))
    pasta = tmp_path / "imagens_modulos"  # does not exist yet -> must be created

    resultado = copiar_imagem_para_pasta(str(origem), str(pasta), "ROUP_2P")

    assert resultado.aviso is None
    assert resultado.caminho == os.path.join(str(pasta), "ROUP_2P.png")
    assert os.path.isfile(resultado.caminho)


def test_copiar_imagem_origem_inexistente_avisa_sem_rebentar(tmp_path) -> None:
    pasta = tmp_path / "imagens"
    pasta.mkdir()

    resultado = copiar_imagem_para_pasta(
        str(tmp_path / "nao_existe.png"), str(pasta), "ROUP_2P"
    )

    # Keeps the original path and warns; does not raise.
    assert resultado.caminho == str(tmp_path / "nao_existe.png")
    assert resultado.aviso is not None
    assert "não encontrada" in resultado.aviso


def test_copiar_imagem_sem_pasta_configurada_avisa(tmp_path) -> None:
    origem = tmp_path / "foto.png"
    _criar_imagem(str(origem))

    resultado = copiar_imagem_para_pasta(str(origem), "", "ROUP_2P")

    assert resultado.caminho == str(origem)
    assert resultado.aviso is not None
    assert "não configurada" in resultado.aviso


def test_copiar_imagem_sem_origem_devolve_vazio(tmp_path) -> None:
    resultado = copiar_imagem_para_pasta(None, str(tmp_path), "ROUP_2P")
    assert resultado.caminho is None
    assert resultado.aviso is None


def test_copiar_imagem_origem_ja_no_destino_nao_duplica(tmp_path) -> None:
    pasta = tmp_path / "imagens"
    pasta.mkdir()
    destino = pasta / "ROUP_2P.png"
    _criar_imagem(str(destino))

    resultado = copiar_imagem_para_pasta(str(destino), str(pasta), "ROUP_2P")

    assert resultado.aviso is None
    assert resultado.caminho == str(destino)
    assert os.path.isfile(str(destino))


def test_caminho_para_file_url() -> None:
    assert (
        caminho_para_file_url(r"C:\imagens\roupeiro.png")
        == "file:///C:/imagens/roupeiro.png"
    )
    # UNC path keeps the host.
    assert (
        caminho_para_file_url(r"\\SERVER\share\img.png")
        == "file://SERVER/share/img.png"
    )
    assert caminho_para_file_url(None) == ""


def test_tooltip_imagem_html() -> None:
    html = tooltip_imagem_html(r"C:\imagens\roupeiro.png", largura=320)
    assert html == '<img src="file:///C:/imagens/roupeiro.png" width="320">'
    assert tooltip_imagem_html(None) == ""
