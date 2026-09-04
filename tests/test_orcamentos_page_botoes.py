"""Barra de botões dos Orçamentos: ícones e um só botão para a pasta."""

from __future__ import annotations

import inspect

import pytest

pytest.importorskip("PySide6")

from app.ui.icones import icone  # noqa: E402
from app.ui.pages.orcamentos_page import OrcamentosPage  # noqa: E402


ICONES_ESPERADOS = (
    "orcamento_novo",
    "orcamento_abrir",
    "orcamento_editar",
    "orcamento_eliminar",
    "atualizar",
    "pasta_abrir",
)


@pytest.mark.parametrize("nome", ICONES_ESPERADOS)
def test_o_ficheiro_do_icone_existe_e_desenha(nome: str) -> None:
    """Um SVG em falta não dá erro nenhum: o botão fica só sem ícone."""
    assert not icone(nome).isNull(), f"ícone {nome}.svg não carregou"


def test_cada_botao_da_barra_leva_o_seu_icone() -> None:
    init = inspect.getsource(OrcamentosPage.__init__)
    for nome in ICONES_ESPERADOS:
        assert f'setIcon(icone("{nome}"))' in init, nome


def test_ha_um_so_botao_para_a_pasta_do_orcamento() -> None:
    """O «Criar Pasta» desapareceu: o «Pasta do Orçamento» já perguntava."""
    init = inspect.getsource(OrcamentosPage.__init__)

    assert "Criar Pasta do Or" not in init
    assert not hasattr(OrcamentosPage, "_criar_pasta_orcamento")
    assert hasattr(OrcamentosPage, "_abrir_pasta_orcamento")

    abrir = inspect.getsource(OrcamentosPage._abrir_pasta_orcamento)
    assert "Criar agora?" in abrir
    assert "criar=True" in abrir


def test_todos_os_botoes_da_barra_tem_dica() -> None:
    """Regra da casa: um botão sem tooltip é um botão que ninguém percebe."""
    init = inspect.getsource(OrcamentosPage.__init__)
    for botao in (
        "new_button",
        "open_button",
        "edit_button",
        "delete_button",
        "open_folder_button",
        "refresh_button",
    ):
        assert f"self.{botao}.setToolTip(" in init, botao


def test_o_rodape_separa_os_milhares_e_escreve_por_extenso() -> None:
    """«236059,86 €» lê-se mal: é fácil trocar 236 mil por 23 mil."""
    from app.utils.formatters import format_currency

    assert format_currency("236059.86") == "236059,86 €"
    assert format_currency("236059.86", milhares=True) == "236\u00a0059,86 €"

    rodape = inspect.getsource(OrcamentosPage._atualizar_rodape)
    assert "milhares=True" in rodape
    assert "euros_por_extenso" in rodape
    # Um orçamento não são "1 orçamentos".
    assert "if contagem == 1" in rodape
