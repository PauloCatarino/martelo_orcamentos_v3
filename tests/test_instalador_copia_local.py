r"""O instalador tem de ser copiado para o PC antes de se abrir.

Porque' e' que isto tem testes proprios: a partir de setembro de 2026 instalar
passou a exigir a conta ADMIN_<pessoa>. O UAC eleva para essa conta, que NAO
tem sessao no servidor de ficheiros -- abrir o instalador direto de
``\SERVER_LE\...`` morria com "ShellExecuteEx falhou; codigo 1385". A volta e'
copiar primeiro, com a conta normal, que tem acesso a` rede.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services import atualizacao_service as svc
from app.services.atualizacao_service import (
    InstaladorIndisponivel,
    preparar_instalador_local,
)


@pytest.fixture
def instalador(tmp_path: Path) -> Path:
    """Um ficheiro que faz de instalador, com tamanho a serio."""
    caminho = tmp_path / "servidor" / "Setup_Martelo_V3_1.0.17.exe"
    caminho.parent.mkdir(parents=True)
    caminho.write_bytes(b"x" * 4096)
    return caminho


def _fingir_rede(monkeypatch, e_rede: bool) -> None:
    monkeypatch.setattr(svc, "_e_caminho_de_rede", lambda _c: e_rede)


def test_caminho_local_e_devolvido_tal_e_qual(instalador, monkeypatch):
    """Se ja' esta' no PC, nao ha' nada a copiar."""
    _fingir_rede(monkeypatch, False)
    assert preparar_instalador_local(instalador) == instalador


def test_caminho_de_rede_e_copiado_para_o_pc(instalador, tmp_path, monkeypatch):
    _fingir_rede(monkeypatch, True)
    monkeypatch.setattr(svc.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))

    destino = preparar_instalador_local(instalador)

    assert destino != instalador
    assert destino.exists()
    assert destino.name == instalador.name
    assert destino.read_bytes() == instalador.read_bytes()
    # e o original fica intacto no servidor
    assert instalador.exists()


def test_nao_copia_outra_vez_o_que_ja_esta_inteiro(instalador, tmp_path, monkeypatch):
    """200 MB pela rede duas vezes seria mau feitio."""
    _fingir_rede(monkeypatch, True)
    monkeypatch.setattr(svc.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    primeiro = preparar_instalador_local(instalador)

    chamadas = []
    monkeypatch.setattr(svc.shutil, "copy2",
                        lambda *a, **k: chamadas.append(a))

    segundo = preparar_instalador_local(instalador)

    assert segundo == primeiro
    assert chamadas == [], "copiou de novo um ficheiro que ja' estava inteiro"


def test_copia_de_novo_se_a_copia_esta_truncada(instalador, tmp_path, monkeypatch):
    """Uma copia interrompida a meio nao pode passar por boa."""
    _fingir_rede(monkeypatch, True)
    monkeypatch.setattr(svc.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    destino = preparar_instalador_local(instalador)
    destino.write_bytes(b"x" * 10)          # ficou a meio

    preparar_instalador_local(instalador)

    assert destino.read_bytes() == instalador.read_bytes()


def test_instalador_que_nao_existe_da_erro_explicado(tmp_path, monkeypatch):
    _fingir_rede(monkeypatch, True)
    falta = tmp_path / "servidor" / "Setup_Martelo_V3_9.9.9.exe"

    with pytest.raises(InstaladorIndisponivel) as erro:
        preparar_instalador_local(falta)

    assert "nao esta' onde devia" in str(erro.value)
    assert str(falta) in str(erro.value)


def test_sem_espaco_no_disco_diz_quanto_falta(instalador, tmp_path, monkeypatch):
    _fingir_rede(monkeypatch, True)
    monkeypatch.setattr(svc.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    monkeypatch.setattr(svc.shutil, "disk_usage",
                        lambda _p: type("U", (), {"free": 0})())

    with pytest.raises(InstaladorIndisponivel) as erro:
        preparar_instalador_local(instalador)

    assert "espaco" in str(erro.value)


def test_falha_a_copiar_explica_de_onde_para_onde(instalador, tmp_path, monkeypatch):
    _fingir_rede(monkeypatch, True)
    monkeypatch.setattr(svc.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))

    def _recusa(*_a, **_k):
        raise OSError("a rede foi abaixo")

    monkeypatch.setattr(svc.shutil, "copy2", _recusa)

    with pytest.raises(InstaladorIndisponivel) as erro:
        preparar_instalador_local(instalador)

    texto = str(erro.value)
    assert str(instalador) in texto
    assert "a rede foi abaixo" in texto
