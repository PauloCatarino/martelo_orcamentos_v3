"""Corretor ortográfico nos orçamentos, itens, emails e Produção (2026-09-16).

O Paulo pediu-o como no Word, com duas condições que estes testes guardam:
as descrições estão cheias de MAIÚSCULAS (que o Windows ignora por defeito) e
de códigos de material que nunca podem aparecer sublinhados.
"""

from __future__ import annotations

import inspect
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTextEdit

from app.domain.ortografia import palavra_em, palavras_a_verificar
from app.services import corretor_ortografico_service as svc
from app.services.corretor_ortografico_service import Corretor, definir_corretor

_app = QApplication.instance() or QApplication([])


class _VerificadorFalso:
    """Um "Windows" que só conhece as palavras da lista (em minúsculas)."""

    CONHECIDAS = {"roupeiro", "portas", "abrir", "montagem", "lisboa", "Lisboa"}

    def __init__(self) -> None:
        self.perguntas: list[str] = []

    def correta(self, palavra: str) -> bool:
        self.perguntas.append(palavra)
        # Como o do Windows: o que vem todo em maiúsculas passa sempre.
        return palavra.isupper() or palavra in self.CONHECIDAS

    def sugestoes(self, palavra: str) -> list[str]:
        return {"montajem": ["montagem", "montagens"]}.get(palavra.lower(), [])


def _corretor(dicionario=(), gravadas=None) -> Corretor:
    def gravar(chave, user_id):
        if gravadas is None:
            raise RuntimeError("sem permissão")
        gravadas.append((chave, user_id))

    corretor = Corretor(
        _VerificadorFalso(),
        carregar_dicionario=lambda: list(dicionario),
        gravar_palavra=gravar,
    )
    corretor.recarregar_dicionario(forcar=True)
    return corretor


def _textos(texto: str) -> list[str]:
    return [palavra.texto for palavra in palavras_a_verificar(texto)]


# ---- que palavras se verificam --------------------------------------------------
@pytest.mark.parametrize(
    "codigo",
    [
        "AGL_MLM_LINHO_CANCUN_19MM",
        "H3395/ST12_19mm",
        "H3395",
        "ST12",
        "H3170",
        "2x600",
        "geral@jfviva.com",
        "www.lancaencanto.pt",
        "\\\\SERVER_LE\\obras",
        "MLM",
        "AGL",
        "PUX",
        "MDF",
        "iMos",
        "CutRite",
        "de",
        "2mm",
    ],
)
def test_codigos_e_siglas_nunca_se_verificam(codigo: str) -> None:
    assert _textos(f"ROUPEIRO {codigo} PORTAS") == ["ROUPEIRO", "PORTAS"]


def test_pontuacao_a_volta_nao_faz_parte_da_palavra() -> None:
    texto = "(MONTAJEM), «roupeiro»; - portas."
    palavras = palavras_a_verificar(texto)

    assert [p.texto for p in palavras] == ["MONTAJEM", "roupeiro", "portas"]
    assert texto[palavras[0].inicio : palavras[0].fim] == "MONTAJEM"


def test_codigo_com_pontuacao_no_fim_continua_a_ser_codigo() -> None:
    assert _textos("Material: H3395/ST12_19mm, H3170.") == ["Material"]


def test_palavra_em_encontra_a_palavra_do_clique() -> None:
    texto = "ROUPEIRO MONTAJEM"
    assert palavra_em(texto, 11).texto == "MONTAJEM"
    assert palavra_em(texto, 17).texto == "MONTAJEM"  # cursor logo a seguir
    assert palavra_em("H3395 x", 2) is None


# ---- corretor -------------------------------------------------------------------
def test_maiusculas_sao_verificadas_em_minusculas() -> None:
    """O Windows aceitava MONTAJEM por vir em maiúsculas."""
    corretor = _corretor()

    assert corretor.correta("MONTAJEM") is False
    assert corretor.correta("ROUPEIRO") is True


def test_nome_proprio_em_maiusculas_nao_fica_sublinhado() -> None:
    corretor = _corretor()
    _VerificadorFalso.CONHECIDAS.discard("lisboa")
    try:
        assert corretor.correta("LISBOA") is True  # passa como "Lisboa"
    finally:
        _VerificadorFalso.CONHECIDAS.add("lisboa")


def test_sugestoes_vem_com_as_maiusculas_de_quem_escreveu() -> None:
    corretor = _corretor()

    assert corretor.sugestoes("MONTAJEM") == ["MONTAGEM", "MONTAGENS"]
    assert corretor.sugestoes("Montajem") == ["Montagem", "Montagens"]
    assert corretor.sugestoes("montajem") == ["montagem", "montagens"]


def test_dicionario_da_casa_nao_distingue_maiusculas() -> None:
    corretor = _corretor(dicionario=["Termolaminado"])

    assert corretor.correta("TERMOLAMINADO") is True
    assert corretor.correta("termolaminado") is True
    assert corretor.correta("lacagem") is False


def test_adicionar_grava_para_todos_e_aceita_logo() -> None:
    gravadas: list = []
    corretor = _corretor(gravadas=gravadas)
    assert corretor.correta("ilharga") is False

    corretor.adicionar("ILHARGA", user_id=7)

    assert gravadas == [("ilharga", 7)]
    assert corretor.correta("ilharga") is True
    assert corretor.correta("ILHARGA") is True


def test_adicionar_sem_permissao_levanta_e_nao_aceita() -> None:
    corretor = _corretor(gravadas=None)

    with pytest.raises(RuntimeError):
        corretor.adicionar("ilharga")
    assert corretor.correta("ilharga") is False


def test_sem_corretor_no_pc_nada_fica_sublinhado() -> None:
    corretor = Corretor(None, carregar_dicionario=list)

    assert corretor.disponivel is False
    assert corretor.correta("MONTAJEM") is True
    assert corretor.sugestoes("MONTAJEM") == []


def test_dicionario_indisponivel_nao_rebenta() -> None:
    def sem_tabela():
        raise RuntimeError("Table 'dicionario_palavras' doesn't exist")

    corretor = Corretor(_VerificadorFalso(), carregar_dicionario=sem_tabela)

    assert corretor.recarregar_dicionario(forcar=True) is False
    assert corretor.correta("roupeiro") is True


def test_cada_palavra_so_se_pergunta_uma_vez_ao_windows() -> None:
    corretor = _corretor()
    verificador = corretor._verificador

    for _ in range(5):
        corretor.correta("lacagem")

    assert verificador.perguntas.count("lacagem") == 1


def test_gravar_na_base_ignora_palavra_repetida(session, monkeypatch) -> None:
    from sqlalchemy.orm import Session

    from app.models.dicionario_palavra import DicionarioPalavra

    engine = session.get_bind()
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: Session(engine))

    svc._gravar_palavra_na_base("ilharga", 3)
    svc._gravar_palavra_na_base("ilharga", 4)

    linhas = session.query(DicionarioPalavra).all()
    assert [(l.palavra, l.criado_por_id) for l in linhas] == [("ilharga", 3)]
    assert svc._ler_dicionario_da_base() == ["ilharga"]


# ---- caixa de texto -----------------------------------------------------------------
@pytest.fixture
def caixa():
    from app.ui.widgets.corretor_ortografico import ligar_corretor

    gravadas: list = []
    corretor = _corretor(gravadas=gravadas)
    definir_corretor(corretor)
    edit = QTextEdit()
    ligar_corretor(edit)
    edit.resize(500, 200)
    edit.show()
    _app.processEvents()
    yield edit, gravadas
    edit.close()


def _sublinhados(edit: QTextEdit) -> list[str]:
    texto = edit.toPlainText()
    bloco = edit.document().firstBlock()
    resultado = []
    while bloco.isValid():
        for formato in bloco.layout().formats():
            inicio = bloco.position() + formato.start
            resultado.append(texto[inicio : inicio + formato.length])
        bloco = bloco.next()
    return resultado


def test_caixa_sublinha_so_o_que_esta_mal(caixa) -> None:
    edit, _ = caixa
    edit.setPlainText("ROUPEIRO PORTAS DE ABRIR\nMONTAJEM AGL_MLM_LINHO_CANCUN_19MM H3170")

    assert _sublinhados(edit) == ["MONTAJEM"]
    # O sublinhado é só visual: não entra no texto nem no HTML.
    assert edit.toPlainText().endswith("H3170")
    assert "wave" not in edit.toHtml() and "spellcheck" not in edit.toHtml().lower()


def _menu_na_palavra(edit: QTextEdit, palavra: str):
    posicao = edit.toPlainText().index(palavra) + 2
    cursor = edit.textCursor()
    cursor.setPosition(posicao)
    return edit._menu_corretor.construir_menu(edit.cursorRect(cursor).center())


def test_botao_direito_mostra_sugestoes_no_topo_e_troca(caixa) -> None:
    edit, _ = caixa
    edit.setPlainText("ROUPEIRO MONTAJEM INCLUIDA")

    menu = _menu_na_palavra(edit, "MONTAJEM")
    textos = [acao.text() for acao in menu.actions()]
    assert textos[:3] == ["MONTAGEM", "MONTAGENS", "Adicionar «MONTAJEM» ao dicionário"]

    menu.actions()[0].trigger()

    assert edit.toPlainText() == "ROUPEIRO MONTAGEM INCLUIDA"


def test_botao_direito_numa_palavra_certa_da_o_menu_normal(caixa) -> None:
    edit, _ = caixa
    edit.setPlainText("ROUPEIRO MONTAJEM")

    assert _menu_na_palavra(edit, "ROUPEIRO") is None


def test_adicionar_ao_dicionario_tira_o_sublinhado(caixa) -> None:
    edit, gravadas = caixa
    edit.setPlainText("Tampo termolaminado")
    assert _sublinhados(edit) == ["Tampo", "termolaminado"]

    menu = _menu_na_palavra(edit, "termolaminado")
    [acao for acao in menu.actions() if acao.text().startswith("Adicionar")][0].trigger()

    assert gravadas == [("termolaminado", None)]
    assert _sublinhados(edit) == ["Tampo"]


def test_ligar_duas_vezes_nao_duplica(caixa) -> None:
    from app.ui.widgets.corretor_ortografico import ligar_corretor

    edit, _ = caixa
    assert ligar_corretor(edit) is edit._realce_ortografico


# ---- onde está ligado -------------------------------------------------------------------
@pytest.mark.parametrize(
    "modulo, campos",
    [
        ("app.ui.dialogs.novo_orcamento_dialog", ["descricao_input", "info_1_input", "info_2_input"]),
        ("app.ui.dialogs.editar_orcamento_dialog", ["descricao_input", "info_1_input", "info_2_input"]),
        ("app.ui.dialogs.novo_item_dialog", ["descricao_input"]),
        ("app.ui.dialogs.email_orcamento_dialog", ["txt_corpo"]),
        ("app.ui.dialogs.editar_ocorrencia_dialog", ["texto_input"]),
    ],
)
def test_corretor_ligado_nas_caixas_de_texto(modulo: str, campos: list[str]) -> None:
    import importlib

    fonte = inspect.getsource(importlib.import_module(modulo))
    for campo in campos:
        assert f"ligar_corretor(self.{campo})" in fonte


def test_corretor_ligado_nas_notas_da_producao() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    assert "ligar_corretor(text_edit)" in inspect.getsource(ProducaoPage._text_edit)


# ---- Windows a sério (só corre onde houver pt-PT) --------------------------------------
def test_windows_apanha_os_erros_das_descricoes() -> None:
    verificador = svc._criar_verificador_windows()
    if verificador is None:
        pytest.skip("Este PC não tem o corretor pt-PT do Windows")
    corretor = Corretor(verificador, carregar_dicionario=list)

    assert corretor.correta("MONTAJEM") is False
    assert "MONTAGEM" in corretor.sugestoes("MONTAJEM")
    assert corretor.correta("ROUPEIRO") is True
    assert corretor.correta("dobradiças") is True
    assert "DOBRADIÇAS" in corretor.sugestoes("DOBRADICAS")
