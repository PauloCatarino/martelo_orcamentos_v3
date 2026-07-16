"""Lança Encanto brown/beige theme for the costing table (phase 8V.4).

Presentation only: colours, bold/italic/uppercase and the per-line-type style.
``estilo_linha_custeio`` is a pure function (no Qt) so it can be unit-tested;
the page maps the returned :class:`EstiloLinha` onto QTableWidget items.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path

from app.domain.custeio_linha_types import (
    DIVISAO_INDEPENDENTE,
    PECA_COMPOSTA,
    SEPARADOR,
)

_ICONES_DIR = Path(__file__).parent / "assets" / "icons"
_DROPDOWN_ARROW = (_ICONES_DIR / "dropdown_arrow.svg").as_posix()
_SPIN_UP_ARROW = (_ICONES_DIR / "spin_up.svg").as_posix()
_SPIN_DOWN_ARROW = (_ICONES_DIR / "spin_down.svg").as_posix()

# --- Palette (Lança Encanto) -------------------------------------------------
CASTANHO_ESCURO = "#5A3E2B"   # text / strong accent
CASTANHO_MEDIO = "#8B6F4E"    # medium brown
BEGE_AREIA = "#EFE7DA"        # sand beige (highlight background)
BEGE_CLARO = "#F7F2EA"        # light beige (alternated rows)
CINZA_CASTANHO = "#D9CFC2"    # brown-grey (separator / secondary)
TEXTO_NORMAL = "#2E2A26"      # normal text
VERDE_SUAVE = "#DCEAD8"       # success badge background
VERDE_ESCURO = "#315C35"      # success badge text
OCRE_SUAVE = "#F2DEB3"        # warning badge background
OCRE_ESCURO = "#6D4B16"       # warning badge text
AZUL_SUAVE = "#D8E7F3"        # sent badge background
AZUL_ESCURO = "#244A63"       # sent badge text
CINZA_SUAVE = "#E3E0DC"       # neutral badge background
CINZA_ESCURO = "#4A4641"      # neutral badge text
VERMELHO_SUAVE = "#E8C7C1"    # negative badge background
VERMELHO_ESCURO = "#7A231C"   # negative badge text

# Role colours derived from the palette.
DIVISAO_FUNDO = CASTANHO_MEDIO       # division block header background
DIVISAO_TEXTO = "#FFFFFF"            # light text for contrast on the division
SEPARADOR_FUNDO = CINZA_CASTANHO     # discreet separator background
ZEBRA_BASE = "#FFFFFF"               # normal rows (even)
ZEBRA_ALT = BEGE_CLARO               # normal rows (odd)

# Whole-board (Não-Stock) adjusted waste cell: a warm ochre highlight that stands
# out from the beige/white zebra, with dark-brown text (phase 8W.2.1).
PLACA_INTEIRA_FUNDO = "#E3B872"      # warm ochre highlight
PLACA_INTEIRA_TEXTO = CASTANHO_ESCURO

# Composite header: the beige highlight is applied ONLY to the structural
# columns; the remaining columns of that row keep the normal/zebra background.
COLUNAS_REALCE_COMPOSTA = (
    "Tipo linha",
    "Código",
    "Descrição livre",
    "Def. Peça",
    "Descrição",
    "Linha pai",
    "Nível",
    "QT mod",
    "QT und",
)


@dataclass(frozen=True)
class EstiloLinha:
    """Visual style of one costing row (mapped to Qt by the page)."""

    fundo: str | None = None          # row background; None -> use the zebra colour
    texto: str | None = None          # text colour
    negrito: bool = False
    italico: bool = False
    maiusculas: bool = False
    realce_estrutural: bool = False   # composite header: beige on structural cols


def cor_zebra(indice_linha: int) -> str:
    """Return the alternating (zebra) background of a normal row by index."""
    return ZEBRA_ALT if indice_linha % 2 else ZEBRA_BASE


def cor_grupo_chave(indice_grupo: int) -> str:
    """Return the background for one ValueSet-key type group."""
    return BEGE_CLARO if indice_grupo % 2 else ZEBRA_BASE


def cor_estado(estado: str | None) -> tuple[str, str]:
    """Return (background, text) colours for a budget status badge."""
    estado_norm = _normalizar_estado(estado)
    if estado_norm in {"adjudicado", "concluido"}:
        return VERDE_SUAVE, VERDE_ESCURO
    if estado_norm == "falta orcamentar":
        return OCRE_SUAVE, OCRE_ESCURO
    if estado_norm == "enviado":
        return AZUL_SUAVE, AZUL_ESCURO
    if estado_norm == "nao enviado":
        return CINZA_SUAVE, CINZA_ESCURO
    if estado_norm in {"nao adjudicado", "cancelado", "sem interesse"}:
        return VERMELHO_SUAVE, VERMELHO_ESCURO
    return ZEBRA_ALT, TEXTO_NORMAL


def cor_estado_producao(estado: str | None) -> tuple[str, str]:
    """Return (background, text) colours for a production status badge."""
    estado_norm = _normalizar_estado(estado)
    if estado_norm == "desenho":
        return "#E6F1FB", "#0C447C"
    if estado_norm == "producao":
        return "#FAEEDA", "#854F0B"
    if estado_norm == "finalizado":
        return "#EAF3DE", "#173404"
    if estado_norm == "arquivado":
        return "#F1EFE8", "#2C2C2A"
    return "", ""


def _normalizar_estado(estado: str | None) -> str:
    sem_acentos = unicodedata.normalize("NFKD", (estado or "").strip())
    return "".join(
        caractere
        for caractere in sem_acentos
        if not unicodedata.combining(caractere)
    ).lower()


def estilo_linha_custeio(tipo_linha, *, eh_filho: bool = False) -> EstiloLinha:
    """Return the style for a costing line, by type (and composite-child flag).

    - DIVISÃO: full brown background, white bold UPPERCASE text (block header);
    - PEÇA COMPOSTA: bold dark-brown text, beige highlight on structural columns;
    - SEPARADOR: discreet brown-grey background, no text;
    - composite CHILD (linha_pai set): italic, medium-brown text (zebra bg);
    - NORMAL line: normal text on the zebra background.
    """
    if tipo_linha == DIVISAO_INDEPENDENTE:
        return EstiloLinha(
            fundo=DIVISAO_FUNDO,
            texto=DIVISAO_TEXTO,
            negrito=True,
            maiusculas=True,
        )
    if tipo_linha == PECA_COMPOSTA:
        return EstiloLinha(
            texto=CASTANHO_ESCURO,
            negrito=True,
            realce_estrutural=True,
        )
    if tipo_linha == SEPARADOR:
        return EstiloLinha(fundo=SEPARADOR_FUNDO)
    if eh_filho:
        return EstiloLinha(texto=CASTANHO_MEDIO, italico=True)
    return EstiloLinha(texto=TEXTO_NORMAL)


# Estilo transversal das abas (QTabWidget/QTabBar): tab selecionado destacado a castanho.
ESTILO_ABAS = (
    f"QTabWidget::pane {{ border: 1px solid {CINZA_CASTANHO}; border-radius: 4px; top: -1px; }}\n"
    f"QTabBar::tab {{ background-color: {BEGE_CLARO}; color: {CASTANHO_ESCURO};"
    f" border: 1px solid {CINZA_CASTANHO}; border-bottom: none;"
    f" border-top-left-radius: 6px; border-top-right-radius: 6px;"
    f" padding: 6px 16px; margin-right: 2px; }}\n"
    f"QTabBar::tab:hover {{ background-color: {BEGE_AREIA}; }}\n"
    f"QTabBar::tab:selected {{ background-color: {CASTANHO_ESCURO}; color: #FFFFFF;"
    f" font-weight: bold; border: 1px solid {CASTANHO_ESCURO}; }}"
)


# Estilo da sidebar (main_window): botão da página ativa destacado a castanho.
ESTILO_SIDEBAR = (
    f"QPushButton {{ text-align: left; padding: 8px 12px; border: none;"
    f" border-radius: 4px; color: {CASTANHO_ESCURO}; background-color: transparent;"
    f" font-weight: bold; }}\n"
    f"QPushButton:hover {{ background-color: {BEGE_AREIA}; }}\n"
    f"QPushButton:checked {{ background-color: {CASTANHO_ESCURO}; color: #FFFFFF; }}"
)


# Estilo da arvore de navegacao (sidebar): item selecionado a castanho.
ESTILO_ARVORE_NAV = (
    "QTreeWidget#navTree { background-color: transparent; border: none; outline: 0; }\n"
    f"QTreeWidget#navTree::item {{ color: {CASTANHO_ESCURO}; padding: 6px 4px;"
    " border-radius: 4px; }\n"
    f"QTreeWidget#navTree::item:hover {{ background-color: {BEGE_AREIA}; }}\n"
    f"QTreeWidget#navTree::item:selected {{ background-color: {CASTANHO_ESCURO}; color: #FFFFFF; }}"
)


# Estilo comum de tabelas de configuracao.
ESTILO_TABELA_CONFIG = (
    f"QTableWidget {{ gridline-color: {CINZA_CASTANHO}; }}\n"
    "QTableWidget::item { padding: 6px 8px; }\n"
    f"QTableWidget::item:selected {{ background-color: {CASTANHO_ESCURO}; color: #FFFFFF; }}"
)


# Estilo comum de tabelas de configuracao com cabecalho castanho.
ESTILO_TABELA_CONFIG_CABECALHO = ESTILO_TABELA_CONFIG + (
    f"\nQHeaderView::section {{ background-color: {CASTANHO_ESCURO}; color: #FFFFFF;"
    " padding: 6px 8px; border: none; font-weight: bold; }"
)


# Estilo global moderado dos controlos. Páginas podem continuar a sobrepor
# regras específicas sem perder a identidade visual comum.
ESTILO_CONTROLOS = (
    f"QPushButton {{ background-color: #FFFFFF; color: {CASTANHO_ESCURO};"
    f" border: 1px solid {CINZA_CASTANHO}; border-radius: 5px;"
    " padding: 5px 11px; min-height: 18px; }\n"
    f"QPushButton:hover {{ background-color: #D8B98C; color: {CASTANHO_ESCURO};"
    f" border: 2px solid {CASTANHO_MEDIO}; font-weight: bold; }}\n"
    f"QPushButton:pressed {{ background-color: {CASTANHO_ESCURO}; color: #FFFFFF; border-color: {CASTANHO_ESCURO}; }}\n"
    "QPushButton:disabled { background-color: #F2F0EC; color: #9A958E; border-color: #DED9D1; }\n"
    f"QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{ background-color: #FFFFFF;"
    f" color: {TEXTO_NORMAL}; border: 1px solid {CINZA_CASTANHO}; border-radius: 4px;"
    " padding: 4px 7px; min-height: 18px; }\n"
    f"QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{"
    f" border: 1px solid {CASTANHO_MEDIO}; }}\n"
    f"QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right;"
    f" width: 18px; border-left: 1px solid {CINZA_CASTANHO}; }}\n"
    f"QComboBox::down-arrow {{ image: url({_DROPDOWN_ARROW}); width: 8px; height: 8px; }}\n"
    # Lista pendente do QComboBox: sem esta regra o Qt desenha o item corrente
    # com texto branco sobre cinza claro (ilegível); a seleção/hover fica
    # castanho escuro com texto branco, como nas tabelas.
    f"QComboBox QAbstractItemView {{ background-color: #FFFFFF; color: {TEXTO_NORMAL};"
    f" border: 1px solid {CINZA_CASTANHO};"
    f" selection-background-color: {CASTANHO_ESCURO}; selection-color: #FFFFFF; outline: 0; }}\n"
    "QComboBox QAbstractItemView::item { padding: 3px 7px; }\n"
    f"QComboBox QAbstractItemView::item:hover {{ background-color: {CASTANHO_ESCURO}; color: #FFFFFF; }}\n"
    f"QComboBox QAbstractItemView::item:selected {{ background-color: {CASTANHO_ESCURO}; color: #FFFFFF; }}\n"
    "QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border;"
    " subcontrol-position: top right; width: 15px; height: 10px; border: none; }\n"
    "QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border;"
    " subcontrol-position: bottom right; width: 15px; height: 10px; border: none; }\n"
    f"QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url({_SPIN_UP_ARROW});"
    " width: 8px; height: 8px; }\n"
    f"QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url({_SPIN_DOWN_ARROW});"
    " width: 8px; height: 8px; }\n"
    f"QGroupBox {{ color: {CASTANHO_ESCURO}; font-weight: bold;"
    f" border: 1px solid {CINZA_CASTANHO}; border-radius: 6px; margin-top: 8px; padding-top: 7px; }}\n"
    "QGroupBox::title { subcontrol-origin: margin; left: 9px; padding: 0 4px; }"
)

ESTILO_GLOBAL = ESTILO_ABAS + "\n" + ESTILO_CONTROLOS
