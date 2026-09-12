"""O navegador de chaves partilhado pelas três tabelas de ValueSet.

A regra que mais interessa aqui é a marca ✎: nas tabelas do orçamento e do item
o normal é importar um modelo e depois afinar linhas à mão, e são essas as mais
difíceis de encontrar em ~100 linhas × 23 colunas.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from app.domain.valueset_navegador_chaves import metas_por_codigo


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


VOCABULARIO = [
    SimpleNamespace(codigo="MATERIAL_COSTAS", nome="Costas", grupo="MATERIAIS", ordem=1),
    SimpleNamespace(codigo="MATERIAL_PORTAS", nome="Portas", grupo="MATERIAIS", ordem=2),
    SimpleNamespace(codigo="FERRAGEM_VARAO", nome="Varão", grupo="FERRAGENS", ordem=1),
]


def _linha(id, chave, *, editada=False, ativo=True):
    return SimpleNamespace(
        id=id, chave=chave, editado_localmente=editada, ativo=ativo, ordem=id
    )


LINHAS = [
    _linha(1, "MATERIAL_COSTAS", editada=True),
    _linha(2, "MATERIAL_PORTAS"),
    _linha(3, "FERRAGEM_VARAO"),
    _linha(4, "FERRAGEM_VARAO", editada=True),
    _linha(5, "CHAVE_ORFA"),
]


@pytest.fixture()
def navegador(_app):
    from app.ui.widgets.navegador_chaves_valueset import NavegadorChavesValueset

    nav = NavegadorChavesValueset(mostrar_editadas=True)
    nav.definir_metas(metas_por_codigo(VOCABULARIO))
    nav.atualizar(LINHAS)
    return nav


def _no_da_chave(nav, codigo):
    raiz = nav.arvore.invisibleRootItem()
    for i in range(raiz.childCount()):
        grupo = raiz.child(i)
        for j in range(grupo.childCount()):
            no = grupo.child(j)
            if no.data(0, _papel()) == ("chave", codigo):
                return no
    raise AssertionError(f"chave {codigo} nao esta' no navegador")


def _papel():
    from app.ui.widgets.navegador_chaves_valueset import PAPEL_NO

    return PAPEL_NO


def _visiveis(nav, linhas=LINHAS):
    return [l.id for l in linhas if nav.aceita(l)]


def test_sem_filtro_aceita_tudo(navegador) -> None:
    assert _visiveis(navegador) == [1, 2, 3, 4, 5]
    assert navegador.ha_filtro is False


def test_chave_orfa_aparece_em_sem_grupo(navegador) -> None:
    """É a chave partida que deixa o custeio sem material, em silêncio."""
    raiz = navegador.arvore.invisibleRootItem()
    ultimo = raiz.child(raiz.childCount() - 1)

    assert ultimo.text(0) == "Sem grupo"
    assert ultimo.child(0).data(0, _papel()) == ("chave", "CHAVE_ORFA")


def test_a_arvore_conta_as_editadas_por_chave_e_por_grupo(navegador) -> None:
    raiz = navegador.arvore.invisibleRootItem()
    materiais = raiz.child(0)

    assert materiais.text(0) == "Materiais"
    assert materiais.text(1) == "✎1"  # a coluna do meio é a das editadas
    assert materiais.text(2) == "2"
    # A chave sem edições não mostra número nenhum.
    portas = _no_da_chave(navegador, "MATERIAL_PORTAS")
    assert portas.text(1) == ""


def test_clicar_numa_chave_filtra_e_o_segundo_clique_mostra_tudo(navegador) -> None:
    navegador._handle_clique(_no_da_chave(navegador, "FERRAGEM_VARAO"), 0)

    assert _visiveis(navegador) == [3, 4]
    assert "chave: FERRAGEM_VARAO" in navegador.sufixo_estado()

    navegador._handle_clique(_no_da_chave(navegador, "FERRAGEM_VARAO"), 0)

    # O grupo sai com a chave: ele só tinha entrado a reboque dela.
    assert _visiveis(navegador) == [1, 2, 3, 4, 5]
    assert navegador.sufixo_estado() == ""


def test_chip_das_editadas_mostra_so_as_afinadas_a_mao(navegador) -> None:
    navegador._alternar_editadas()

    assert _visiveis(navegador) == [1, 4]
    assert "só as editadas" in navegador.sufixo_estado()

    navegador._alternar_editadas()
    assert _visiveis(navegador) == [1, 2, 3, 4, 5]


def test_o_chip_das_editadas_conta_certo(navegador) -> None:
    textos = [b.text() for b in navegador._botoes_chips]

    assert "✎ Editadas  (2)" in textos
    assert "Todos  (5)" in textos
    assert "Materiais  (2)" in textos


def test_chip_de_grupo_filtra_o_grupo_inteiro(navegador) -> None:
    navegador._escolher_grupo("MATERIAIS")

    assert _visiveis(navegador) == [1, 2]

    navegador._escolher_grupo("MATERIAIS")
    assert _visiveis(navegador) == [1, 2, 3, 4, 5]


def test_limpar_filtros_repoe_tudo(navegador) -> None:
    navegador._escolher_grupo("FERRAGENS")
    navegador._alternar_editadas()
    navegador.alternar_grupo_fechado("FERRAGENS")

    navegador.limpar_filtros()

    assert _visiveis(navegador) == [1, 2, 3, 4, 5]
    assert navegador.ha_filtro is False
    assert navegador.grupo_fechado("FERRAGENS") is False


def test_grupos_fechados_guardam_se_para_as_faixas(navegador) -> None:
    assert navegador.grupo_fechado("MATERIAIS") is False

    navegador.alternar_grupo_fechado("MATERIAIS")
    assert navegador.grupo_fechado("MATERIAIS") is True

    navegador.alternar_grupo_fechado("MATERIAIS")
    assert navegador.grupo_fechado("MATERIAIS") is False


def test_sem_a_coluna_das_editadas_quando_nao_faz_sentido(_app) -> None:
    """Na tabela do modelo quase não há edições locais: a coluna não vai."""
    from app.ui.widgets.navegador_chaves_valueset import NavegadorChavesValueset

    nav = NavegadorChavesValueset(mostrar_editadas=False)
    nav.definir_metas(metas_por_codigo(VOCABULARIO))
    nav.atualizar(LINHAS)

    assert nav.arvore.columnCount() == 2
    assert all("Editadas" not in b.text() for b in nav._botoes_chips)


def test_agrupar_contiguo_nao_reordena(navegador) -> None:
    """As faixas seguem a ordem que a tabela tem, senão as linhas saltavam."""
    baralhadas = [LINHAS[2], LINHAS[0], LINHAS[3]]

    grupos = navegador.agrupar_contiguo(baralhadas)

    assert [g.codigo for g in grupos] == ["FERRAGENS", "MATERIAIS", "FERRAGENS"]
