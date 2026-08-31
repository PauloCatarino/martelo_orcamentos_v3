"""Ler os números de versão dos instaladores que estão na pasta do servidor.

O Martelo precisa de responder a uma pergunta simples — "a versão que tenho é a
mais recente?" — sem depender de ninguém escrever um ficheiro de controlo à
mão. A resposta está no nome dos próprios instaladores:

    Setup_Martelo_V3_1.0.8.exe  ->  1.0.8

Regras que isto tem de respeitar, e que estão todas cobertas por testes:

* comparar por NÚMERO e não por texto: a 1.0.10 é mais recente que a 1.0.9,
  mas em texto "1.0.10" < "1.0.9". Foi por aqui que muita gente se enganou;
* ignorar o instalador do Martelo **V2**, que vive na mesma pasta;
* ignorar as versões beta: quem tem o programa oficial não deve ser convidado
  a instalar uma beta por ela ter um número maior.

Módulo puro: não lê o disco nem a base de dados (isso é do serviço).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: ``Setup_Martelo_V3_1.0.8.exe``. O sufixo (``-beta``, ``-rc1``) é apanhado à
#: parte para se poder ignorar o que não é oficial.
_PADRAO = re.compile(
    r"^Setup_Martelo_V3_(?P<versao>\d+\.\d+\.\d+)(?P<sufixo>[-.][\w.]+)?\.exe$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class InstaladorDisponivel:
    """Um instalador encontrado na pasta, já com a versão lida do nome."""

    nome_ficheiro: str
    versao: str

    @property
    def ordem(self) -> tuple[int, int, int]:
        return versao_para_ordem(self.versao)


def versao_para_ordem(versao: str) -> tuple[int, int, int]:
    """"1.0.10" -> (1, 0, 10), para comparar por número e não por texto."""
    partes = (versao or "").split(".")
    if len(partes) != 3:
        return (0, 0, 0)
    try:
        maior, medio, menor = (int(parte) for parte in partes)
    except ValueError:
        return (0, 0, 0)
    return (maior, medio, menor)


def ler_versao_do_nome(nome_ficheiro: str) -> str | None:
    """A versão oficial escrita no nome do instalador, ou None.

    Devolve None para tudo o que não seja um instalador OFICIAL do V3: o
    instalador do V2, as betas e qualquer outro ficheiro que lá esteja.
    """
    encontrado = _PADRAO.match((nome_ficheiro or "").strip())
    if encontrado is None:
        return None
    if encontrado.group("sufixo"):
        return None  # beta/rc: não conta como atualização

    return encontrado.group("versao")


def escolher_mais_recente(nomes: list[str]) -> InstaladorDisponivel | None:
    """O instalador oficial mais recente de uma lista de nomes de ficheiro."""
    candidatos = [
        InstaladorDisponivel(nome_ficheiro=nome, versao=versao)
        for nome in nomes
        if (versao := ler_versao_do_nome(nome)) is not None
    ]
    if not candidatos:
        return None

    return max(candidatos, key=lambda item: item.ordem)


def ha_versao_mais_recente(instalada: str, disponivel: str) -> bool:
    """Se vale a pena convidar a atualizar."""
    return versao_para_ordem(disponivel) > versao_para_ordem(instalada)
