"""Novidades de cada versão («What's New») — pedido do Paulo, 19-11-2026."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domain import novidades_versao as nv
from app.services.atualizacao_service import listar_novidades, novidades_da_versao


def test_nomes_dos_ficheiros():
    assert nv.nome_html("1.0.33") == "Novidades_Martelo_V3_1.0.33.html"
    assert nv.nome_pdf("1.0.33") == "Novidades_Martelo_V3_1.0.33.pdf"
    f = nv.ler_nome("Novidades_Martelo_V3_1.0.33.html")
    assert (f.versao, f.extensao) == ("1.0.33", "html")
    assert nv.ler_nome("Setup_Martelo_V3_1.0.33.exe") is None
    assert nv.ler_nome("Novidades_Martelo_V3_1.0.html") is None


def test_versoes_com_novidades_por_numero():
    nomes = ["Novidades_Martelo_V3_1.0.9.html", "Novidades_Martelo_V3_1.0.10.html",
             "Novidades_Martelo_V3_1.0.11.pdf", "Password_Instalador.txt"]
    # A 1.0.11 só tem PDF: não conta (o aviso abre o HTML).
    assert nv.versoes_com_novidades(nomes) == ["1.0.10", "1.0.9"]


@pytest.mark.parametrize("ultima, instalada, esperado", [
    ("1.0.32", "1.0.34", ["1.0.34", "1.0.33"]),  # saltou a 1.0.33: vê as duas
    ("1.0.33", "1.0.34", ["1.0.34"]),
    ("1.0.34", "1.0.34", []),                      # já viu
    (None, "1.0.34", ["1.0.34"]),                  # nunca viu nenhuma: só a instalada
    (None, "1.0.31", []),                          # a instalada não tem novidades
])
def test_versoes_por_mostrar(ultima, instalada, esperado):
    disponiveis = ["1.0.34", "1.0.33", "1.0.32"]
    assert nv.versoes_por_mostrar(disponiveis, ultima, instalada) == esperado


@pytest.mark.parametrize("ultima, instalada, esperado", [
    (None, "1.0.34", True), ("1.0.33", "1.0.34", True), ("1.0.34", "1.0.34", False),
    ("1.0.35", "1.0.34", False), ("1.0.33", "1.0.34-beta", False),
])
def test_ha_versao_nova_instalada(ultima, instalada, esperado):
    assert nv.ha_versao_nova_instalada(ultima, instalada) is esperado


def test_listar_novidades_subpasta_e_raiz(tmp_path):
    (tmp_path / "Novidades").mkdir()
    for nome in ("Novidades_Martelo_V3_1.0.33.html", "Novidades_Martelo_V3_1.0.33.pdf",
                 "Novidades_Martelo_V3_1.0.34.html"):
        (tmp_path / "Novidades" / nome).write_text("x")
    # As da 1.0.32 ficaram soltas na pasta dos instaladores.
    (tmp_path / "Novidades_Martelo_V3_1.0.32.html").write_text("x")
    (tmp_path / "Novidades_Martelo_V3_1.0.33.html").write_text("velha")
    lista = listar_novidades(tmp_path)
    assert [n.versao for n in lista] == ["1.0.34", "1.0.33", "1.0.32"]
    n33 = lista[1]
    assert n33.html == tmp_path / "Novidades" / "Novidades_Martelo_V3_1.0.33.html"  # a subpasta ganha
    assert n33.pdf == tmp_path / "Novidades" / "Novidades_Martelo_V3_1.0.33.pdf"
    assert lista[0].pdf is None
    assert novidades_da_versao(tmp_path, "1.0.32").html == tmp_path / "Novidades_Martelo_V3_1.0.32.html"
    assert novidades_da_versao(tmp_path, "1.0.40") is None


def test_listar_novidades_sem_pasta(tmp_path):
    assert listar_novidades(tmp_path / "nao_existe") == []


@pytest.fixture
def app_qt():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_aviso_do_primeiro_arranque(app_qt):
    from app.services.atualizacao_service import Novidades
    from app.ui.helpers.novidades_versao import NovidadesAposAtualizar

    guardadas, abertas, perguntas = [], [], []
    lista = [Novidades("1.0.34", Path("n34.html")), Novidades("1.0.33", Path("n33.html")),
             Novidades("1.0.32", Path("n32.html"))]
    aviso = NovidadesAposAtualizar(
        None, ativo=False, instalada=lambda: "1.0.34", ler_ultima=lambda: "1.0.32",
        guardar_ultima=guardadas.append, abrir=lambda _p, c: abertas.append(c) or True,
        perguntar=lambda _p, v, l: perguntas.append((v, [n.versao for n in l])) or True,
    )
    aviso._ao_ler((Path("pasta"), lista))
    assert perguntas == [("1.0.34", ["1.0.34", "1.0.33"])]
    assert abertas == [Path("n34.html"), Path("n33.html")]
    assert guardadas == ["1.0.34"]


def test_sem_novidades_no_servidor_nao_marca_como_vista(app_qt):
    from app.ui.helpers.novidades_versao import NovidadesAposAtualizar

    guardadas = []
    aviso = NovidadesAposAtualizar(
        None, ativo=False, instalada=lambda: "1.0.34", ler_ultima=lambda: "1.0.33",
        guardar_ultima=guardadas.append, perguntar=lambda *_: pytest.fail("não pergunta"),
    )
    aviso._ao_ler((Path("pasta"), []))
    assert guardadas == []  # tenta-se no próximo arranque
