"""Items do orçamento: setas ↑/↓ para mudar a ordem (19-10-2026).

Pedido do Paulo: selecionar um ou mais items e subi-los ou descê-los na lista
(ex.: os três roupeiros do 261057). A ordem é a da lista, do PDF e dos
relatórios; preços e totais não mudam.
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication
from sqlalchemy import select

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.domain.mover_selecao import mover_selecao
from app.domain.orcamento_estados import ESTADO_INICIAL
from app.models import Cliente, Orcamento, OrcamentoItem, OrcamentoVersao
from app.repositories.orcamento_item_repository import (
    OrcamentoItemRepository,
    OrcamentoItemResumo,
)
from app.services.orcamento_item_service import OrcamentoItemService
from app.ui.pages import orcamento_items_page as page_module


# --- Regra pura ------------------------------------------------------------


def test_subir_um_item() -> None:
    assert mover_selecao([1, 2, 3], [3], para_cima=True) == [1, 3, 2]


def test_descer_um_item() -> None:
    assert mover_selecao([1, 2, 3], [1], para_cima=False) == [2, 1, 3]


def test_varios_seguidos_andam_juntos() -> None:
    assert mover_selecao([1, 2, 3, 4], [2, 3], para_cima=True) == [2, 3, 1, 4]
    assert mover_selecao([1, 2, 3, 4], [2, 3], para_cima=False) == [1, 4, 2, 3]


def test_varios_separados_andam_cada_um_uma_posicao() -> None:
    assert mover_selecao([1, 2, 3, 4, 5], [2, 4], para_cima=True) == [2, 1, 4, 3, 5]


def test_no_topo_nao_se_mexe() -> None:
    assert mover_selecao([1, 2, 3], [1], para_cima=True) is None
    assert mover_selecao([1, 2, 3], [1, 2], para_cima=True) is None
    assert mover_selecao([1, 2, 3], [3], para_cima=False) is None


def test_encostado_ao_topo_so_o_outro_sobe() -> None:
    assert mover_selecao([1, 2, 3], [1, 3], para_cima=True) == [1, 3, 2]


def test_ids_que_nao_estao_na_lista_sao_ignorados() -> None:
    assert mover_selecao([1, 2, 3], [99], para_cima=True) is None
    assert mover_selecao([1, 2, 3], [], para_cima=True) is None


# --- Gravação na base --------------------------------------------------------


def _versao_com_items(session, ordens: list[int]) -> tuple[int, list[int]]:
    cliente = Cliente(nome="MÓVEIS J.F. VIVA", nome_simplex="JF_VIVA", is_temporary=True)
    session.add(cliente)
    session.flush()
    orcamento = Orcamento(ano=2026, num_orcamento="261057", cliente_id=cliente.id)
    session.add(orcamento)
    session.flush()
    versao = OrcamentoVersao(
        orcamento_id=orcamento.id,
        numero_versao=1,
        codigo_versao="261057_01",
        estado=ESTADO_INICIAL,
        preco_total=Decimal("2650.44"),
        preco_origem=Decimal("0"),
    )
    session.add(versao)
    session.flush()

    repositorio = OrcamentoItemRepository(session)
    ids = []
    for indice, ordem in enumerate(ordens, start=1):
        item = repositorio.create_item(
            orcamento_versao_id=versao.id,
            ordem=ordem,
            codigo=f"RP_0{indice}",
            tipo_item="OUTRO",
            item=f"RP_0{indice}",
            descricao=None,
            altura=None,
            largura=None,
            profundidade=None,
            quantidade=Decimal("1"),
            unidade="un",
            preco_unitario=Decimal("100"),
            preco_total=Decimal("100"),
        )
        ids.append(item.id)
    session.commit()
    return versao.id, ids


def _ordem_na_base(session, versao_id: int) -> list[tuple[str, int]]:
    session.expire_all()
    return [
        (item.codigo, item.ordem)
        for item in session.execute(
            select(OrcamentoItem)
            .where(OrcamentoItem.orcamento_versao_id == versao_id)
            .order_by(OrcamentoItem.ordem)
        ).scalars()
    ]


def test_subir_grava_a_ordem_nova(session) -> None:
    versao_id, (rp1, rp2, rp3) = _versao_com_items(session, [1, 2, 3])

    assert OrcamentoItemService(session).mover_items(versao_id, [rp3], para_cima=True)

    assert _ordem_na_base(session, versao_id) == [("RP_01", 1), ("RP_03", 2), ("RP_02", 3)]


def test_mover_varios_e_tapar_buracos(session) -> None:
    """Items removidos deixam buracos (1, 2, 4, 7): ao mover fica 1..N."""
    versao_id, (rp1, rp2, rp3, rp4) = _versao_com_items(session, [1, 2, 4, 7])

    assert OrcamentoItemService(session).mover_items(
        versao_id, [rp1, rp2], para_cima=False
    )

    assert _ordem_na_base(session, versao_id) == [
        ("RP_03", 1),
        ("RP_01", 2),
        ("RP_02", 3),
        ("RP_04", 4),
    ]


def test_no_fim_nao_grava_nada(session) -> None:
    versao_id, (_rp1, _rp2, rp3) = _versao_com_items(session, [1, 2, 5])

    assert not OrcamentoItemService(session).mover_items(
        versao_id, [rp3], para_cima=False
    )

    # Sem movimento, nem os buracos se mexem.
    assert _ordem_na_base(session, versao_id) == [("RP_01", 1), ("RP_02", 2), ("RP_03", 5)]


def test_reordenar_exige_todos_os_items(session) -> None:
    versao_id, (rp1, rp2, _rp3) = _versao_com_items(session, [1, 2, 3])

    with pytest.raises(ValueError):
        OrcamentoItemRepository(session).reordenar_items(versao_id, [rp2, rp1])


# --- Página dos Items --------------------------------------------------------


def _resumo(item_id: int, ordem: int) -> OrcamentoItemResumo:
    return OrcamentoItemResumo(
        id=item_id,
        orcamento_versao_id=7,
        ordem=ordem,
        codigo=f"RP_0{item_id}" if item_id > 0 else "SUP_NSTOCK",
        item=f"Item {item_id}",
        descricao=None,
        altura=None,
        largura=None,
        profundidade=None,
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=Decimal("100"),
        preco_total=Decimal("100"),
        tipo_item="OUTRO" if item_id > 0 else "SUPLEMENTO",
    )


class _FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _FakeServico:
    pedidos: list[tuple[int, list[int], bool]] = []
    ordem = [1, 2, 3]

    def __init__(self, _session) -> None:
        pass

    def mover_items(self, versao_id, item_ids, *, para_cima):
        self.__class__.pedidos.append((versao_id, list(item_ids), para_cima))
        nova = mover_selecao(self.__class__.ordem, item_ids, para_cima=para_cima)
        if nova is None:
            return False
        self.__class__.ordem = nova
        return True


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture()
def pagina(monkeypatch, _app):
    _FakeServico.pedidos = []
    _FakeServico.ordem = [1, 2, 3]

    def _carregar(self) -> None:
        items = [
            _resumo(item_id, posicao)
            for posicao, item_id in enumerate(_FakeServico.ordem, start=1)
        ]
        items.append(_resumo(-1, len(items) + 1))  # suplemento automático
        self._preencher_tabela(items)

    monkeypatch.setattr(page_module.OrcamentoItemsPage, "carregar_items", _carregar)
    monkeypatch.setattr(page_module, "SessionLocal", _FakeSession)
    monkeypatch.setattr(page_module, "OrcamentoItemService", _FakeServico)
    janela = page_module.OrcamentoItemsPage(orcamento_versao_id=7)
    yield janela
    janela.close()


def _ids_na_tabela(pagina) -> list[int]:
    return [item.id for _row, item in sorted(pagina._items_by_row.items())]


def test_setas_ficam_ao_lado_do_std_serie(pagina) -> None:
    assert pagina.subir_button.text() == "↑"
    assert pagina.descer_button.text() == "↓"
    assert "selecionados" in pagina.subir_button.toolTip()
    assert "selecionados" in pagina.descer_button.toolTip()


def test_subir_dois_items_e_continuam_selecionados(pagina) -> None:
    pagina._selecionar_items([2, 3])

    pagina.mover_items_selecionados(para_cima=True)

    assert _FakeServico.pedidos == [(7, [2, 3], True)]
    assert _ids_na_tabela(pagina) == [2, 3, 1, -1]
    assert pagina._ids_selecionados() == [2, 3]
    assert pagina.status_label.text() == "2 items movidos."


def test_no_topo_avisa_e_nao_recarrega(pagina) -> None:
    pagina._selecionar_items([1])

    pagina.mover_items_selecionados(para_cima=True)

    assert _ids_na_tabela(pagina) == [1, 2, 3, -1]
    assert pagina.status_label.text() == "A seleção já está na primeira posição."


def test_suplemento_nao_se_move(pagina) -> None:
    pagina._selecionar_items([-1])

    pagina.mover_items_selecionados(para_cima=True)

    assert _FakeServico.pedidos == []
    assert "suplementos" in pagina.status_label.text()


def test_sem_selecao_pede_para_escolher(pagina) -> None:
    # A linha «atual» fica no RP_02, mas sem seleção nada se mexe.
    pagina.table.setCurrentCell(1, 0)
    pagina.table.clearSelection()

    pagina.mover_items_selecionados(para_cima=False)

    assert _FakeServico.pedidos == []
    assert "Selecione" in pagina.status_label.text()
