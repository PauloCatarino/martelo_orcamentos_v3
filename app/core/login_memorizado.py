"""Memorizar o login neste PC, no Gestor de Credenciais do Windows.

Cada pessoa entra com a sua própria conta MySQL (ver ``app/db/session.py``): é o
servidor que valida a palavra-passe. Por isso "o Martelo entrar sozinho" obriga
a guardá-la algures — e fica no Gestor de Credenciais do Windows, cifrada pelo
próprio Windows e só legível pelo utilizador do Windows DESTE PC. Nunca num
ficheiro do Martelo nem na base de dados.

Vê-se e apaga-se à mão em Painel de Controlo → Gestor de Credenciais →
Credenciais do Windows → «Martelo Orcamentos V3 (<base>)».

Nada aqui pode impedir o arranque: se o Windows não deixar ler ou gravar, o
Martelo mostra o login como sempre.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

from app.config.settings import settings

_LOGGER = logging.getLogger(__name__)


class LoginMemorizado(NamedTuple):
    username: str
    password: str


def alvo() -> str:
    """Um por base: a base de ensaio e a real não se misturam no mesmo PC."""
    return f"Martelo Orcamentos V3 ({settings.DB_NAME})"


def ler() -> LoginMemorizado | None:
    """O login memorizado neste PC, ou ``None`` se não houver (ou não der)."""
    try:
        import win32cred

        credencial = win32cred.CredRead(alvo(), win32cred.CRED_TYPE_GENERIC)
    except Exception:  # noqa: BLE001 - sem memória é o caso normal
        return None

    username = str(credencial.get("UserName") or "").strip()
    blob = credencial.get("CredentialBlob") or b""
    try:
        # O Windows guarda-a em UTF-16, que é o que o pywin32 lá escreve.
        password = blob.decode("utf-16-le") if isinstance(blob, bytes) else str(blob)
    except UnicodeDecodeError:
        return None
    if not username or not password:
        return None
    return LoginMemorizado(username, password)


def gravar(username: str, password: str) -> bool:
    """Memoriza este login neste PC (substitui o que lá estiver)."""
    try:
        import win32cred

        win32cred.CredWrite(
            {
                "Type": win32cred.CRED_TYPE_GENERIC,
                "TargetName": alvo(),
                "UserName": username,
                "CredentialBlob": password,
                # Fica neste PC, para este utilizador do Windows; não viaja.
                "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
                "Comment": "Login do Martelo Orcamentos V3 memorizado neste PC",
            },
            0,
        )
    except Exception:  # noqa: BLE001 - memorizar é uma comodidade
        _LOGGER.warning("Não foi possível memorizar o login neste PC.", exc_info=True)
        return False
    return True


def esquecer() -> None:
    """Retira o login memorizado neste PC (se houver)."""
    try:
        import win32cred

        win32cred.CredDelete(alvo(), win32cred.CRED_TYPE_GENERIC, 0)
    except Exception:  # noqa: BLE001 - já não havia, ou o Windows não deixou
        pass


def e_de(username: str) -> bool:
    """Há um login memorizado neste PC e é o desta conta."""
    memorizado = ler()
    return bool(
        memorizado
        and memorizado.username.casefold() == str(username or "").strip().casefold()
    )
