"""Responder ao pedido do cliente guardado na pasta do orçamento."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
from types import SimpleNamespace

from app.services.email_resposta_service import (
    assunto_de_resposta,
    ler_email_do_cliente,
    preparar_resposta,
    procurar_emails_do_cliente,
)


def _msg(pasta: Path, nome: str, *, idade_segundos: int = 0) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / nome
    caminho.write_bytes(b"conteudo do outlook")
    if idade_segundos:
        quando = caminho.stat().st_mtime - idade_segundos
        os.utime(caminho, (quando, quando))
    return caminho


# ---- encontrar o email ------------------------------------------------------
def test_encontra_o_msg_da_pasta(tmp_path: Path) -> None:
    _msg(tmp_path, "Pedido cotação Projeto CMM.msg")
    _msg(tmp_path, "260836_01.pdf")

    encontrados = procurar_emails_do_cliente(tmp_path)

    assert [caminho.name for caminho in encontrados] == [
        "Pedido cotação Projeto CMM.msg"
    ]


def test_mais_recente_aparece_primeiro(tmp_path: Path) -> None:
    _msg(tmp_path, "antigo.msg", idade_segundos=7200)
    _msg(tmp_path, "recente.msg")

    encontrados = procurar_emails_do_cliente(tmp_path)

    assert [caminho.name for caminho in encontrados] == ["recente.msg", "antigo.msg"]


def test_pasta_da_versao_manda_sobre_a_raiz(tmp_path: Path) -> None:
    # O pedido guardado na versão em que se está a trabalhar é o que interessa.
    raiz = tmp_path / "260836_SEIVA"
    versao = raiz / "01"
    _msg(raiz, "pedido_antigo.msg")
    _msg(versao, "pedido_desta_versao.msg")

    encontrados = procurar_emails_do_cliente(versao, raiz)

    assert [caminho.name for caminho in encontrados] == ["pedido_desta_versao.msg"]


def test_sem_msg_na_versao_procura_na_raiz(tmp_path: Path) -> None:
    raiz = tmp_path / "260836_SEIVA"
    versao = raiz / "01"
    versao.mkdir(parents=True)
    _msg(raiz, "pedido.msg")

    encontrados = procurar_emails_do_cliente(versao, raiz)

    assert [caminho.name for caminho in encontrados] == ["pedido.msg"]


def test_pasta_que_nao_existe_nao_rebenta(tmp_path: Path) -> None:
    assert procurar_emails_do_cliente(tmp_path / "nao_existe", None, "") == ()


def test_extensao_e_indiferente_a_maiusculas(tmp_path: Path) -> None:
    _msg(tmp_path, "PEDIDO.MSG")

    assert len(procurar_emails_do_cliente(tmp_path)) == 1


# ---- assunto ----------------------------------------------------------------
def test_assunto_ganha_o_re() -> None:
    assert assunto_de_resposta("Pedido cotação Projeto CMM") == (
        "RE: Pedido cotação Projeto CMM"
    )


def test_assunto_que_ja_e_resposta_nao_duplica_o_re() -> None:
    for original in ("RE: Pedido", "re: Pedido", "Fwd: Pedido", "ENC: Pedido"):
        assert assunto_de_resposta(original) == original


def test_assunto_vazio_fica_vazio() -> None:
    assert assunto_de_resposta("") == ""
    assert assunto_de_resposta(None) == ""


# ---- ler o cabeçalho --------------------------------------------------------
def _mensagem_falsa(**campos):
    base = {
        "Subject": "Pedido cotação Projeto CMM",
        "SenderEmailAddress": "geral@seiva.pt",
        "SenderName": "Ana Paula Sousa",
        "ReceivedTime": datetime(2026, 8, 4, 11, 31),
    }
    base.update(campos)
    return SimpleNamespace(**base)


def test_le_o_cabecalho_do_email(tmp_path: Path) -> None:
    caminho = _msg(tmp_path, "pedido.msg")

    lido = ler_email_do_cliente(caminho, abrir=lambda _c: _mensagem_falsa())

    assert lido is not None
    assert lido.assunto == "Pedido cotação Projeto CMM"
    assert lido.de == "geral@seiva.pt"
    assert lido.recebido_em == datetime(2026, 8, 4, 11, 31)
    assert "pedido.msg" in lido.etiqueta
    assert "geral@seiva.pt" in lido.etiqueta
    assert "04-08-2026" in lido.etiqueta


def test_sem_endereco_usa_o_nome_de_quem_enviou(tmp_path: Path) -> None:
    caminho = _msg(tmp_path, "pedido.msg")

    lido = ler_email_do_cliente(
        caminho, abrir=lambda _c: _mensagem_falsa(SenderEmailAddress="")
    )

    assert lido is not None
    assert lido.de == "Ana Paula Sousa"


def test_outlook_em_baixo_devolve_none_em_vez_de_rebentar(tmp_path: Path) -> None:
    caminho = _msg(tmp_path, "pedido.msg")

    def _falha(_caminho):
        raise RuntimeError("Outlook nao responde")

    assert ler_email_do_cliente(caminho, abrir=_falha) is None


def test_caminho_vazio_devolve_none() -> None:
    assert ler_email_do_cliente("") is None
    assert ler_email_do_cliente(None) is None


def test_preparar_resposta_sem_emails_devolve_none(tmp_path: Path) -> None:
    assert preparar_resposta(tmp_path) is None
