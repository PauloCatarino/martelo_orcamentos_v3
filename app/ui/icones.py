"""Icon helpers for UI assets."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon


def _raiz_icons() -> Path:
    """Pasta ``icons`` da raiz, resolvida tanto em dev como no .exe empacotado.

    No executável (PyInstaller) os dados são desempacotados em ``sys._MEIPASS``;
    o .spec copia a pasta para ``<_MEIPASS>/icons``. Em desenvolvimento, é a
    pasta ``icons`` na raiz do projeto (dois níveis acima deste ficheiro).
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidato = Path(base) / "icons"
        if candidato.exists():
            return candidato
    return Path(__file__).resolve().parents[2] / "icons"


_ICONES_DIR = Path(__file__).parent / "assets" / "icons"
_RAIZ_ICONS = _raiz_icons()


def icone(nome: str) -> QIcon:
    """QIcon from app/ui/assets/icons/<nome>.svg."""
    return QIcon(str(_ICONES_DIR / f"{nome}.svg"))


def icone_ficheiro(nome_ficheiro: str) -> QIcon:
    """QIcon a partir de <raiz>/icons/<nome_ficheiro> (ex.: 'icon_cleaner.ico')."""
    return QIcon(str(_RAIZ_ICONS / nome_ficheiro))


#: Que ícone leva um botão, a partir do que está escrito nele.
#:
#: O programa tem quase 400 botões e os nomes repetem-se de página para
#: página — "Novo X", "Editar X", "Atualizar", "Ativar/Desativar". Pôr o ícone
#: à mão em cada um dava trabalho e, pior, dava resultados diferentes conforme
#: quem o fizesse. Assim é o texto que decide, e a mesma ação tem sempre a
#: mesma cara em todo o lado.
#:
#: A ordem CONTA: procura-se de cima para baixo, e a primeira que encaixar no
#: princípio do texto ganha. Por isso "Abrir / Editar Peça" tem de vir antes de
#: "Abrir".
_ICONE_POR_PREFIXO: tuple[tuple[tuple[str, ...], str], ...] = (
    (("voltar", "‹ voltar"), "acao_voltar"),
    (("abrir / editar", "abrir/editar"), "orcamento_editar"),
    (("nova", "novo"), "orcamento_novo"),
    (("adicionar", "inserir", "criar"), "acao_adicionar"),
    (("editar", "alterar"), "orcamento_editar"),
    (("eliminar", "remover", "apagar"), "orcamento_eliminar"),
    (("ativar/desativar", "ativar / desativar", "desativar", "ativar"), "acao_ativar_desativar"),
    (("atualizar", "recarregar", "verificar", "sincronizar", "carregar", "ligar /"), "atualizar"),
    (("guardar", "gravar"), "acao_guardar"),
    (("importar",), "acao_importar"),
    (("exportar",), "acao_exportar"),
    (("limpar",), "acao_limpar"),
    (("pesquisar", "procurar", "selecionar mat"), "orcamento_abrir"),
    (("abrir pasta", "pasta d"), "pasta_abrir"),
    (("abrir",), "orcamento_abrir"),
)


def nome_icone_para_rotulo(rotulo: str | None) -> str | None:
    """Nome do ícone que serve este texto de botão, ou None."""
    texto = " ".join((rotulo or "").strip().lower().split())
    # Alguns rotulos comecam por um simbolo decorativo ("+ Nova...",
    # "✉ Pedir precos...", "▶ Catalogos"): o que interessa e' a palavra.
    texto = texto.lstrip("+✉▶▼◀▲«» ").strip()
    if not texto:
        return None
    for prefixos, nome in _ICONE_POR_PREFIXO:
        if any(texto.startswith(prefixo) for prefixo in prefixos):
            return nome
    return None


def decorar_botoes(*botoes) -> int:
    """Pôr em cada botão o ícone que o seu texto pede; devolve quantos levaram.

    Botões que já tenham um ícone próprio ficam como estão — quem o escolheu à
    mão sabia melhor.
    """
    postos = 0
    for botao in botoes:
        if botao is None or not hasattr(botao, "setIcon"):
            continue
        if not botao.icon().isNull():
            continue
        nome = nome_icone_para_rotulo(botao.text())
        if nome is None:
            continue
        botao.setIcon(icone(nome))
        postos += 1
    return postos


def decorar_barra(layout) -> int:
    """O mesmo, para todos os botões de um layout (a barra de ações da página)."""
    from PySide6.QtWidgets import QPushButton

    botoes = []
    for indice in range(layout.count()):
        widget = layout.itemAt(indice).widget()
        if isinstance(widget, QPushButton):
            botoes.append(widget)
    return decorar_botoes(*botoes)
