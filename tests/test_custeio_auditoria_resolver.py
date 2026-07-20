"""Fase 2C: coluna "Resolver" na página Auditoria de Custeio."""

from __future__ import annotations

import os
from decimal import Decimal
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTableWidget

from app.services.custeio_auditoria_service import CRITICO, CusteioAuditoriaItem
from app.services.custeio_supervisor import (
    ORIGEM_LINHA,
    PAGINA_MATERIAS_PRIMAS,
    chave_menu,
)
from app.ui.pages.custeio_auditoria_page import CusteioAuditoriaPage

_app = QApplication.instance() or QApplication([])


def _ocorrencia() -> CusteioAuditoriaItem:
    return CusteioAuditoriaItem(
        severidade=CRITICO, categoria="Material", codigo_teste="OBS_PRODUCAO_MATERIAL_1",
        codigo_orcamento="260002_04", cliente="INOVAÇÃO POSITIVA", utilizador="paulo",
        item="RP_01", linha="FRENTE_GAVETA", problema="Custo MP não calculado.",
        impacto_eur=None, impacto_texto="€ por determinar", acao="Completar material e preço.",
        orcamento_versao_id=1, orcamento_item_id=2, linha_id=3,
    )


def test_coluna_resolver_existe() -> None:
    assert "Resolver" in CusteioAuditoriaPage.TABLE_HEADERS


def test_botao_resolver_por_ocorrencia() -> None:
    coluna = CusteioAuditoriaPage.TABLE_HEADERS.index("Resolver")
    table = QTableWidget(1, len(CusteioAuditoriaPage.TABLE_HEADERS))
    fake = SimpleNamespace(
        table=table,
        TABLE_HEADERS=CusteioAuditoriaPage.TABLE_HEADERS,
        _abrir_resolver=lambda _it: None,
    )
    CusteioAuditoriaPage._colocar_botao_resolver(fake, 0, _ocorrencia())
    assert table.cellWidget(0, coluna) is not None


def test_navegar_resolver_interna_abre_orcamento_externa_abre_menu() -> None:
    item = _ocorrencia()
    abertos: list = []
    menus: list[str] = []
    fake = SimpleNamespace(
        on_open_orcamento=abertos.append,
        _on_navegar_menu=menus.append,
    )

    CusteioAuditoriaPage._navegar_resolver(fake, item, ORIGEM_LINHA)
    assert abertos == [item] and menus == []

    CusteioAuditoriaPage._navegar_resolver(fake, item, chave_menu(PAGINA_MATERIAS_PRIMAS))
    assert menus == [PAGINA_MATERIAS_PRIMAS]
