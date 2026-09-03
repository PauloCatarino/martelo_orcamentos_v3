"""Gravar a ficha tem de gravar TAMBÉM os componentes.

Apanhado pelo Paulo a 03-09-2026: escreveu os dois componentes do pé AXILO na
ficha da FER0058, gravou, e ao voltar a abrir a tabela estava vazia. A
matéria-prima gravava; os componentes não.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.materia_prima_types import PAPEL_PRINCIPAL, PAPEL_SECUNDARIO
from app.repositories.def_materia_prima_componente_repository import ComponenteDados
from app.services.def_materia_prima_componente_service import (
    DefMateriaPrimaComponenteService,
)
from app.services.def_materia_prima_service import (
    CriarDefMateriaPrimaData,
    DefMateriaPrimaService,
)
from app.ui.pages import materias_primas_page as pagina_modulo
from app.ui.pages.materias_primas_page import MateriasPrimasPage

_app = QApplication.instance() or QApplication([])


@pytest.fixture()
def pagina(session, monkeypatch):
    """A página a falar com a base de teste em vez da base a sério."""

    class SessaoFixa:
        """Um ``SessionLocal`` que devolve sempre a mesma sessão do teste."""

        def __call__(self):
            return self

        def __enter__(self):
            return session

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(pagina_modulo, "SessionLocal", SessaoFixa())
    return MateriasPrimasPage()


@pytest.fixture()
def fer0058(session):
    return DefMateriaPrimaService(session).criar_materia_prima(
        CriarDefMateriaPrimaData(
            descricao="PE NIVELADOR AXILO H55-75 + BASE",
            familia_original_excel="FERRAGENS",
            tipo_original_excel="PES",
            unidade="UND",
            preco_tabela=Decimal("0.83"),
        )
    )


def _dados_da_ficha(materia):
    """O que o diálogo devolve para esta matéria-prima, sem lhe mexer."""
    from app.ui.dialogs.materia_prima_dialog import MateriaPrimaDialogData

    return MateriaPrimaDialogData(
        descricao=materia.descricao,
        ref_le=materia.ref_le,
        familia="FERRAGENS",
        tipo="PES",
        unidade="UND",
        tipo_preco=materia.tipo_preco,
        preco_tabela=materia.preco_tabela,
        desconto=None,
        margem=None,
        preco_liquido=materia.preco_liquido,
        desperdicio_percentagem=None,
        data_ultimo_preco=None,
        comprimento=None,
        largura=None,
        espessura=None,
        coresp_orla_0_4=None,
        coresp_orla_1_0=None,
        cor=None,
        fornecedor=None,
        fornecedor_id=None,
        nome_fabricante=None,
        referencia_fornecedor=None,
        ref_phc=None,
        nome_imos=None,
        link=None,
        imagem_ficheiro=None,
        stock=False,
        ativo=True,
        observacoes=None,
    )


PE_ALTO = ComponenteDados(
    papel=PAPEL_SECUNDARIO,
    descricao="PE NIVELADOR AXILO 80MM",
    quantidade=Decimal("1"),
    nome_imos="PE_AXILO_H72_92_63776352",
    ref_phc="FF01295",
    ref_fornecedor="637.76.352",
)
BASE = ComponenteDados(
    papel=PAPEL_SECUNDARIO,
    descricao="BASE APRAFUSAR P/ PE AXILO",
    quantidade=Decimal("1"),
    nome_imos="PE_BASE_AXILO_63776333_4f",
    ref_phc="FF01177",
    ref_fornecedor="637.76.333",
)


def test_gravar_a_ficha_grava_os_componentes(pagina, fer0058, session) -> None:
    gravou = pagina._guardar(_dados_da_ficha(fer0058), fer0058, [PE_ALTO, BASE])

    assert gravou is True, pagina.status_label.text()
    guardados = DefMateriaPrimaComponenteService(session).listar(fer0058.id)
    assert [c.descricao for c in guardados] == [
        "PE NIVELADOR AXILO 80MM",
        "BASE APRAFUSAR P/ PE AXILO",
    ]
    assert [c.nome_imos for c in guardados] == [
        "PE_AXILO_H72_92_63776352",
        "PE_BASE_AXILO_63776333_4f",
    ]
    assert [c.ordem for c in guardados] == [1, 2]


def test_a_pagina_le_de_volta_o_que_gravou(pagina, fer0058) -> None:
    pagina._guardar(_dados_da_ficha(fer0058), fer0058, [PE_ALTO, BASE])

    lidos = pagina._listar_componentes(fer0058.id)

    assert len(lidos) == 2
    assert lidos[0].ref_phc == "FF01295"


def test_gravar_sem_componentes_nenhuns_limpa_a_lista(pagina, fer0058, session) -> None:
    pagina._guardar(_dados_da_ficha(fer0058), fer0058, [PE_ALTO, BASE])

    pagina._guardar(_dados_da_ficha(fer0058), fer0058, [])

    assert DefMateriaPrimaComponenteService(session).listar(fer0058.id) == []


def test_uma_lista_invalida_nao_fecha_a_ficha_e_diz_porque(pagina, fer0058) -> None:
    sem_referencia = ComponenteDados(descricao="uma peça sem referência nenhuma")

    gravou = pagina._guardar(_dados_da_ficha(fer0058), fer0058, [sem_referencia])

    assert gravou is False
    assert "referência" in pagina.status_label.text()


def test_colisao_de_principais_e_recusada_ao_gravar_a_ficha(
    pagina, fer0058, session
) -> None:
    outro = DefMateriaPrimaService(session).criar_materia_prima(
        CriarDefMateriaPrimaData(
            descricao="OUTRO PE", familia_original_excel="FERRAGENS", unidade="UND"
        )
    )
    principal = ComponenteDados(
        papel=PAPEL_PRINCIPAL,
        descricao="Pé AXILO H72→H92",
        nome_imos="PE_AXILO_H72_92_63776352",
    )
    pagina._guardar(_dados_da_ficha(fer0058), fer0058, [principal])

    gravou = pagina._guardar(_dados_da_ficha(outro), outro, [principal])

    assert gravou is False
    assert fer0058.ref_le in pagina.status_label.text()
