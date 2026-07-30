"""Para onde vai cada coisa que o Martelo envia ao cliente.

O ``email`` do cliente vem do PHC e é um campo de contacto geral — muitas
vezes com vários endereços ou com o contacto da faturação. Quem recebe o
orçamento e quem recebe o projeto de produção raramente é a mesma pessoa, por
isso essa escolha vive em duas colunas do Martelo, configuradas no menu
Clientes. Enquanto estiverem vazias, vale o email do PHC.
"""

from __future__ import annotations

from typing import Any


def emails_envio_orcamentos(cliente: Any) -> str:
    """Destinatários do email do orçamento (vazio quando não há nenhum)."""
    return _primeiro_preenchido(cliente, "email_orcamentos")


def emails_envio_projeto_producao(cliente: Any) -> str:
    """Destinatários do email do projeto de produção."""
    return _primeiro_preenchido(cliente, "email_projeto_producao")


def _primeiro_preenchido(cliente: Any, campo: str) -> str:
    escolhido = str(getattr(cliente, campo, "") or "").strip()
    if escolhido:
        return escolhido
    return str(getattr(cliente, "email", "") or "").strip()
