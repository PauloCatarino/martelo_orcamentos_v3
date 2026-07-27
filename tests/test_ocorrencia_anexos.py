"""Tests for where the ticket photos are written."""

from __future__ import annotations

from pathlib import Path

from app.domain.ocorrencia_anexos import (
    SUBPASTA_OCORRENCIAS,
    copiar_anexo,
    e_imagem,
    existe,
    pasta_anexos_ticket,
    preparar_pasta,
    proximo_caminho,
)


def test_a_pasta_do_ticket_fica_dentro_da_pasta_da_obra(tmp_path) -> None:
    pasta = pasta_anexos_ticket(tmp_path, 7)

    assert pasta == tmp_path / SUBPASTA_OCORRENCIAS / "T0007"


def test_sem_pasta_da_obra_nao_ha_onde_gravar() -> None:
    assert pasta_anexos_ticket(None, 7) is None
    assert pasta_anexos_ticket("   ", 7) is None


def test_obra_sem_pasta_devolve_aviso_e_nao_rebenta() -> None:
    pasta, aviso = preparar_pasta(None)

    assert pasta is None
    assert "pasta no servidor" in aviso


def test_copiar_uma_foto_cria_a_pasta_e_numera(tmp_path) -> None:
    origem = tmp_path / "foto_do_cliente.jpg"
    origem.write_bytes(b"imagem")
    destino = pasta_anexos_ticket(tmp_path / "obra", 3)

    resultado = copiar_anexo(origem, destino, 3)

    assert resultado.aviso is None
    assert Path(resultado.caminho).name == "T0003_01.jpg"
    assert Path(resultado.caminho).read_bytes() == b"imagem"
    assert resultado.nome_original == "foto_do_cliente.jpg"


def test_segunda_foto_nao_esmaga_a_primeira(tmp_path) -> None:
    destino = pasta_anexos_ticket(tmp_path / "obra", 3)
    for nome in ("a.png", "b.png"):
        origem = tmp_path / nome
        origem.write_bytes(nome.encode())
        copiar_anexo(origem, destino, 3)

    gravados = sorted(p.name for p in destino.iterdir())

    assert gravados == ["T0003_01.png", "T0003_02.png"]


def test_ficheiro_que_nao_existe_devolve_aviso(tmp_path) -> None:
    resultado = copiar_anexo(tmp_path / "nao_existe.png", tmp_path / "destino", 1)

    assert resultado.caminho is None
    assert "não encontrado" in resultado.aviso


def test_nada_escolhido_nao_e_erro(tmp_path) -> None:
    resultado = copiar_anexo(None, tmp_path, 1)

    assert (resultado.caminho, resultado.aviso) == (None, None)


def test_proximo_caminho_respeita_ficheiros_apagados_a_mao(tmp_path) -> None:
    pasta, _ = preparar_pasta(tmp_path / "T0002")
    (pasta / "T0002_01.png").write_bytes(b"x")

    seguinte = proximo_caminho(pasta, 2, ".png")

    assert seguinte.name == "T0002_02.png"


def test_reconhece_imagens_pela_extensao() -> None:
    assert e_imagem("foto.JPG") is True
    assert e_imagem("desenho.png") is True
    assert e_imagem("documento.pdf") is False
    assert e_imagem(None) is False


def test_existe_aguenta_caminho_vazio() -> None:
    assert existe(None) is False
    assert existe("") is False
