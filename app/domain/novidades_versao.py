"""As novidades de cada versão do Martelo («What's New»), ao lado dos instaladores.

Pedido do Paulo (19-11-2026): como nos programas a sério, quem instala uma versão
nova deve poder ver o que mudou — antes de instalar (no aviso) e depois (no 1.º
arranque da versão nova). As novidades são um HTML (e um PDF) por versão, escritos
à mão para os colegas, com cada secção a começar pela área (Orçamentos, Produção,
Geral), porque nem todos têm interesse em tudo.

Ficam na pasta dos instaladores, na subpasta ``Novidades``:

    <pasta dos instaladores>\\Novidades\\Novidades_Martelo_V3_1.0.33.html
    <pasta dos instaladores>\\Novidades\\Novidades_Martelo_V3_1.0.33.pdf

(as da 1.0.32 ficaram soltas na pasta dos instaladores; também se encontram.)

Módulo puro: não lê o disco nem a base de dados (isso é do serviço).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.versoes_instalador import versao_para_ordem

#: Subpasta da pasta dos instaladores onde ficam as novidades.
PASTA_NOVIDADES = "Novidades"

_PADRAO = re.compile(
    r"^Novidades_Martelo_V3_(?P<versao>\d+\.\d+\.\d+)\.(?P<ext>html|pdf)$", re.IGNORECASE
)


def nome_html(versao: str) -> str:
    """``Novidades_Martelo_V3_1.0.33.html``."""
    return f"Novidades_Martelo_V3_{versao}.html"


def nome_pdf(versao: str) -> str:
    return f"Novidades_Martelo_V3_{versao}.pdf"


@dataclass(frozen=True)
class FicheiroNovidades:
    """Um ficheiro de novidades encontrado, com a versão lida do nome."""

    nome: str
    versao: str
    extensao: str  # "html" ou "pdf"


def ler_nome(nome: str) -> FicheiroNovidades | None:
    """A versão e o tipo de um ficheiro de novidades, ou None se não for um."""
    encontrado = _PADRAO.match((nome or "").strip())
    if encontrado is None:
        return None
    return FicheiroNovidades(
        nome=nome.strip(),
        versao=encontrado.group("versao"),
        extensao=encontrado.group("ext").lower(),
    )


def versoes_com_novidades(nomes: list[str]) -> list[str]:
    """As versões que têm novidades em HTML, da mais recente para a mais antiga."""
    versoes = {f.versao for n in nomes if (f := ler_nome(n)) and f.extensao == "html"}
    return sorted(versoes, key=versao_para_ordem, reverse=True)


def versoes_por_mostrar(
    disponiveis: list[str], ultima_vista: str | None, instalada: str
) -> list[str]:
    """As novidades a mostrar no 1.º arranque depois de instalar, mais recente primeiro.

    São as versões com novidades depois da última que este PC já viu e até à
    instalada (quem salta da 1.0.32 para a 1.0.34 vê também a 1.0.33). Num PC que
    nunca viu nenhuma (a 1.ª vez que esta função existe), só a da versão instalada.
    """
    agora = versao_para_ordem(instalada)
    if agora == (0, 0, 0):
        return []
    if not ultima_vista:
        return [v for v in disponiveis if versao_para_ordem(v) == agora]
    desde = versao_para_ordem(ultima_vista)
    escolhidas = [v for v in disponiveis if desde < versao_para_ordem(v) <= agora]
    return sorted(escolhidas, key=versao_para_ordem, reverse=True)


def ha_versao_nova_instalada(ultima_vista: str | None, instalada: str) -> bool:
    """Esta versão ainda não foi vista neste PC (instalou-se uma versão nova)."""
    agora = versao_para_ordem(instalada)
    if agora == (0, 0, 0):
        return False
    return not ultima_vista or versao_para_ordem(ultima_vista) < agora
