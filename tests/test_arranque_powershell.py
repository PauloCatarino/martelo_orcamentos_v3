"""Arranque do PowerShell: caminho completo, nova tentativa e mensagem clara.

Obras 1912 e _330, 19-11-2026: o Windows recusou arrancar o PowerShell ao
Martelo instalado ([WinError 5] Acesso negado), umas vezes sim, outras não.
"""

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

import pytest

from app.services import arranque_powershell, imos_escrita, phc_sql
from app.services.arranque_powershell import (
    TENTATIVAS,
    PowerShellRecusado,
    caminho_powershell,
    arrancar_powershell,
)


def _recusa() -> PermissionError:
    """O erro que o CreateProcess dá quando o Windows recusa o arranque."""
    return PermissionError(13, "Acesso negado", None, 5)


class _Arranques:
    """``subprocess.run`` falso: recusa as primeiras ``recusas`` chamadas."""

    def __init__(self, recusas: int, stdout: str = "") -> None:
        self.recusas = recusas
        self.stdout = stdout
        self.comandos: list[list[str]] = []

    def __call__(self, comando, **_opcoes):
        self.comandos.append(list(comando))
        if len(self.comandos) <= self.recusas:
            raise _recusa()
        return subprocess.CompletedProcess(comando, 0, stdout=self.stdout, stderr="")


def test_recusa_do_windows_tem_o_winerror_5() -> None:
    erro = _recusa()
    assert isinstance(erro, PermissionError)
    assert erro.winerror == 5


def test_powershell_pelo_caminho_completo_da_pasta_do_windows(monkeypatch, tmp_path) -> None:
    exe = tmp_path / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    monkeypatch.setenv("SystemRoot", str(tmp_path))

    assert caminho_powershell() == str(exe)


def test_sem_o_exe_na_pasta_do_windows_fica_o_nome(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SystemRoot", str(tmp_path))
    assert caminho_powershell() == "powershell"
    monkeypatch.delenv("SystemRoot")
    monkeypatch.delenv("windir", raising=False)
    assert caminho_powershell() == "powershell"


def test_no_windows_deste_pc_e_o_powershell_verdadeiro() -> None:
    caminho = caminho_powershell()
    assert Path(caminho).is_absolute()
    assert Path(caminho).name.casefold() == "powershell.exe"


def test_recusado_uma_vez_tenta_outra_e_passa(monkeypatch) -> None:
    arranques = _Arranques(recusas=1, stdout="ok")
    monkeypatch.setattr(arranque_powershell.subprocess, "run", arranques)
    pausas: list[float] = []

    resultado = arrancar_powershell(["-NoProfile", "-File", "x.ps1"], dormir=pausas.append, text=True)

    assert resultado.stdout == "ok"
    assert len(arranques.comandos) == 2
    assert pausas == [1.0]
    assert arranques.comandos[0] == [caminho_powershell(), "-NoProfile", "-File", "x.ps1"]


def test_recusado_sempre_desiste_com_mensagem_do_que_fazer(monkeypatch) -> None:
    arranques = _Arranques(recusas=99)
    monkeypatch.setattr(arranque_powershell.subprocess, "run", arranques)
    pausas: list[float] = []

    with pytest.raises(PowerShellRecusado) as erro:
        arrancar_powershell(["-NoProfile"], dormir=pausas.append)

    assert len(arranques.comandos) == TENTATIVAS == 3
    assert pausas == [1.0, 2.0]
    texto = str(erro.value)
    assert "Acesso negado" in texto
    assert "Kaspersky" in texto
    assert "Martelo_Orcamentos_V3.exe" in texto
    # Continua a ser um PermissionError: quem já o apanhava, apanha.
    assert isinstance(erro.value, PermissionError)
    assert erro.value.__cause__.winerror == 5


def test_outros_erros_de_permissao_nao_se_repetem(monkeypatch) -> None:
    chamadas: list[object] = []

    def _run(comando, **_opcoes):
        chamadas.append(comando)
        raise PermissionError(13, "sem acesso ao ficheiro")

    monkeypatch.setattr(arranque_powershell.subprocess, "run", _run)

    with pytest.raises(PermissionError) as erro:
        arrancar_powershell(["-NoProfile"], dormir=lambda _s: None)

    assert not isinstance(erro.value, PowerShellRecusado)
    assert len(chamadas) == 1


def test_powershell_que_arranca_e_falha_nao_se_repete(monkeypatch) -> None:
    chamadas: list[object] = []

    def _run(comando, **_opcoes):
        chamadas.append(comando)
        return subprocess.CompletedProcess(comando, 1, stdout="", stderr="erro do SQL")

    monkeypatch.setattr(arranque_powershell.subprocess, "run", _run)

    resultado = arrancar_powershell(["-NoProfile"], dormir=lambda _s: None)

    assert resultado.returncode == 1
    assert len(chamadas) == 1


def test_select_do_imos_e_do_phc_passa_pelo_arranque(monkeypatch) -> None:
    """O que falhou na janela «Gerar listas iMOS» (obra 1912)."""
    linhas = [{"ID": 1, "NAME": "1912_01_26_LINHAS_DIREITAS"}]
    saida = base64.b64encode(json.dumps(linhas).encode("utf-8")).decode("ascii")
    arranques = _Arranques(recusas=1, stdout=saida)
    monkeypatch.setattr(arranque_powershell.subprocess, "run", arranques)
    monkeypatch.setattr(arranque_powershell.time, "sleep", lambda _s: None)

    resultado = phc_sql.run_select("Server=x;Database=y;", "SELECT ID, NAME FROM PROADMIN")

    assert resultado == linhas
    assert len(arranques.comandos) == 2
    assert arranques.comandos[-1][0] == caminho_powershell()


def test_escrita_no_imos_passa_pelo_arranque(monkeypatch) -> None:
    saida = base64.b64encode(b"[]").decode("ascii")
    arranques = _Arranques(recusas=0, stdout=saida)
    monkeypatch.setattr(arranque_powershell.subprocess, "run", arranques)

    imos_escrita.executar_payload({"conn": "", "nos": []})

    assert arranques.comandos[0][0] == caminho_powershell()
