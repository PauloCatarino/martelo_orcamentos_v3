"""Regras (puras) dos nomes de pasta da exportação de orçamentos (fase 8W.4.0).

Sem DB nem Qt — apenas ``str``/``pathlib`` — para ser testável sem GUI nem
base de dados. Reproduz a convenção do Martelo V2:

    base / str(ano) / f"{num_orcamento}_{SIMPLEX}" / versao2dig

onde ``SIMPLEX`` vem do ``nome_simplex`` (senão ``nome``, senão ``"CLIENTE"``)
em maiúsculas e com os espaços trocados por ``_``. Ao escolher a pasta do
orçamento reutiliza-se uma subpasta existente que já comece por
``f"{num_orcamento}_"`` (mesmo que o SIMPLEX difira), tal como no V2.
"""

from __future__ import annotations

from pathlib import Path

_CLIENTE_FALLBACK = "CLIENTE"


def simplificar_cliente(nome_simplex: str | None, nome: str | None) -> str:
    """Devolve o nome simplificado do cliente para o nome da pasta.

    Usa ``nome_simplex`` se preenchido, senão ``nome``, senão ``"CLIENTE"``;
    o resultado vem em maiúsculas e com os espaços trocados por ``_``.
    """
    bruto = (nome_simplex or "").strip() or (nome or "").strip() or _CLIENTE_FALLBACK
    return bruto.upper().replace(" ", "_")


def nome_pasta_orcamento(
    num_orcamento: str, nome_simplex: str | None, nome: str | None
) -> str:
    """Constrói o nome da pasta do orçamento: ``{num}_{SIMPLEX}``."""
    return f"{num_orcamento}_{simplificar_cliente(nome_simplex, nome)}"


def subpasta_versao(numero_versao: int) -> str:
    """Devolve o nome da subpasta da versão com 2 dígitos (1 -> ``"01"``)."""
    return f"{int(numero_versao):02d}"


def escolher_nome_pasta(
    existentes: list[str],
    num_orcamento: str,
    nome_simplex: str | None,
    nome: str | None,
) -> str:
    """Escolhe o nome da pasta do orçamento.

    Reutiliza o 1.º nome de ``existentes`` que comece por ``f"{num_orcamento}_"``
    (pasta já criada manualmente); senão constrói o nome padrão.
    """
    prefixo = f"{num_orcamento}_"
    for existente in existentes:
        if existente.startswith(prefixo):
            return existente

    return nome_pasta_orcamento(num_orcamento, nome_simplex, nome)


def encontrar_pasta_orcamento(ano_dir: Path, num_orcamento: str) -> Path | None:
    """Return the first subfolder of ``ano_dir`` starting with ``f"{num}_"``."""
    if not ano_dir.exists():
        return None

    prefixo = f"{num_orcamento}_"
    for sub in sorted(p for p in ano_dir.iterdir() if p.is_dir()):
        if sub.name.startswith(prefixo):
            return sub

    return None


def renomear_pasta_orcamento(
    ano_dir: Path, num_orcamento: str, nome_simplex: str | None, nome: str | None
) -> tuple[Path, Path] | None:
    """Rename the ``{num}_*`` budget folder to the customer's intended SIMPLEX."""
    atual = encontrar_pasta_orcamento(ano_dir, num_orcamento)
    if atual is None:
        return None

    novo_nome = nome_pasta_orcamento(num_orcamento, nome_simplex, nome)
    if atual.name == novo_nome:
        return None

    destino = ano_dir / novo_nome
    if destino.exists():
        raise FileExistsError(novo_nome)

    atual.rename(destino)
    return atual, destino
