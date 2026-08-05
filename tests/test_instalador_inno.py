"""O instalador não pode abrir a aplicação como administrador.

Ficheiro que ninguém lê e que estraga o email todo: o instalador corre elevado
(precisa disso para escrever em Program Files) e, sem a bandeira
``runasoriginaluser``, a janela aberta no fim do setup nasce como
administrador. O Outlook corre como utilizador normal e o Windows não os deixa
falar — o envio falha com "A execução no servidor falhou". Aconteceu à Andreia
a testar a beta (2026-08-05).
"""

from __future__ import annotations

from pathlib import Path

import pytest

INSTALADOR = (
    Path(__file__).resolve().parents[1] / "installer" / "Martelo_Orcamentos_V3.iss"
)


def _linhas_run() -> list[str]:
    if not INSTALADOR.is_file():
        pytest.skip("instalador não disponível nesta cópia do projeto")
    texto = INSTALADOR.read_text(encoding="utf-8", errors="replace")
    dentro = False
    linhas: list[str] = []
    for linha in texto.splitlines():
        limpa = linha.strip()
        if limpa.startswith("["):
            dentro = limpa.lower() == "[run]"
            continue
        if dentro and limpa and not limpa.startswith(";"):
            linhas.append(limpa)
    return linhas


def test_abrir_no_fim_do_setup_corre_como_utilizador_normal() -> None:
    linhas = _linhas_run()

    assert linhas, "o instalador deixou de abrir a aplicação no fim?"
    for linha in linhas:
        assert "runasoriginaluser" in linha.lower(), (
            "sem 'runasoriginaluser' a aplicação aberta no fim do instalador "
            "fica elevada e o Outlook deixa de ser alcançável:\n" + linha
        )


def test_instalador_continua_a_pedir_admin_para_instalar() -> None:
    # O contrário do de cima: INSTALAR precisa de admin (Program Files); é só
    # ABRIR que não pode. Se um dia isto mudar, a bandeira acima deixa de ser
    # necessária — e este teste avisa que se pode rever.
    if not INSTALADOR.is_file():
        pytest.skip("instalador não disponível nesta cópia do projeto")

    texto = INSTALADOR.read_text(encoding="utf-8", errors="replace")

    assert "PrivilegesRequired=admin" in texto


# ---- o que o PyInstaller nao ve' sozinho -------------------------------------
SPEC = Path(__file__).resolve().parents[1] / "Martelo_Orcamentos_V3.spec"


def test_win32timezone_vai_no_executavel() -> None:
    """Sem ele, ler o `.msg` do cliente falha SO' no executavel.

    O pywin32 importa o `win32timezone` a` mao quando le^ uma data de um
    objeto COM, e o PyInstaller nao ve' esse import. Aconteceu na beta
    0.9.5: "No module named 'win32timezone'" ao abrir o email guardado,
    enquanto na dev funcionava.
    """
    if not SPEC.is_file():
        pytest.skip("spec não disponível nesta cópia do projeto")

    assert '"win32timezone"' in SPEC.read_text(encoding="utf-8", errors="replace")
