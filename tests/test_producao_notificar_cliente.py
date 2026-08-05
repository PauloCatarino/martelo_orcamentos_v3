"""A opção "Notificar Cliente" no menu Funções da Produção.

Pedido do Paulo (2026-08-05): a mesma preparação de email que o Martelo propõe
ao passar a obra de Desenho para Produção, mas disponível a qualquer momento —
para reenviar, para uma obra que já lá estava, ou para quem não tem a opção
automática ligada nas Preferências da Preparação.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

from app.ui.pages.producao_page import ProducaoPage


def _pagina(processo=None):
    """Página só com o que estes métodos tocam (sem Qt nem BD)."""
    pagina = ProducaoPage.__new__(ProducaoPage)
    pagina._processo_selecionado = lambda: processo
    pagina.status_label = SimpleNamespace(
        texto="", setText=lambda t: setattr(pagina.status_label, "texto", t)
    )
    pagina.chamadas = []
    pagina._avisar_cliente_do_projeto = lambda pid, **kw: pagina.chamadas.append(
        (pid, kw)
    )
    return pagina


def test_a_opcao_esta_no_menu_funcoes() -> None:
    fonte = inspect.getsource(ProducaoPage.__init__)

    assert '"Notificar Cliente"' in fonte
    assert "self.funcoes_menu.addAction(self.notificar_cliente_action)" in fonte
    assert "self._notificar_cliente" in fonte


def test_sem_obra_selecionada_avisa_e_nao_faz_nada() -> None:
    pagina = _pagina(processo=None)

    pagina._notificar_cliente()

    assert pagina.chamadas == []
    assert "Selecione uma obra" in pagina.status_label.texto


def test_com_obra_prepara_o_email_dessa_obra() -> None:
    pagina = _pagina(processo=SimpleNamespace(id=42))

    pagina._notificar_cliente()

    assert pagina.chamadas == [(42, {"automatico": False})]


def test_pelo_menu_corre_mesmo_com_a_opcao_automatica_desligada() -> None:
    # `automatico=False` é o que salta a preferência das Preferências da
    # Preparação: um botão que se clica não pode ficar calado.
    fonte = inspect.getsource(ProducaoPage._avisar_cliente_do_projeto)

    assert "automatico: bool = True" in inspect.getsource(
        ProducaoPage._avisar_cliente_do_projeto
    )
    assert "if automatico and not obter_email_projeto_ativo" in fonte


def test_a_mudanca_de_estado_continua_a_respeitar_a_preferencia() -> None:
    # A entrada automática (gravar a obra já em Produção) não passa
    # `automatico`, por isso fica no True e continua a calar-se se a opção
    # estiver desligada.
    fonte = inspect.getsource(ProducaoPage._save)

    assert "if entrou_em_producao:" in fonte
    assert "self._avisar_cliente_do_projeto(proc_id)" in fonte
