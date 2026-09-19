"""Utilizadores e Acessos: cada acesso tem de se explicar ao administrador."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from app.services.permission_service import (
    ACAO_PERMISSIONS,
    DEFAULT_USER_PERMISSIONS,
    DESCRICOES_ACESSOS,
    PERMISSAO_ASSISTENTE_ORCAMENTOS,
    PERMISSOES_EDITAVEIS,
    nasce_ligado,
)


def test_todos_os_acessos_da_grelha_tem_descricao() -> None:
    # Um acesso novo sem descrição tem de partir este teste: o admin vem cá
    # poucas vezes e já não percebia o que cada coluna liga.
    assert list(DESCRICOES_ACESSOS) == list(PERMISSOES_EDITAVEIS)
    for chave, descricao in DESCRICOES_ACESSOS.items():
        assert descricao.grupo, chave
        assert len(descricao.o_que_faz) >= 40, chave
        assert descricao.para_quem, chave
        assert descricao.titulo_curto, chave


def test_titulos_das_colunas_sao_curtos() -> None:
    for chave, descricao in DESCRICOES_ACESSOS.items():
        linhas = descricao.titulo_curto.split("\n")
        assert len(linhas) <= 2, chave
        assert all(len(linha) <= 16 for linha in linhas), chave


def test_assistente_dos_orcamentos_nasce_desligado() -> None:
    assert PERMISSAO_ASSISTENTE_ORCAMENTOS in ACAO_PERMISSIONS
    assert ACAO_PERMISSIONS[PERMISSAO_ASSISTENTE_ORCAMENTOS] == "Assistente dos Orçamentos"
    assert DEFAULT_USER_PERMISSIONS[PERMISSAO_ASSISTENTE_ORCAMENTOS] is False
    assert nasce_ligado(PERMISSAO_ASSISTENTE_ORCAMENTOS) is False
    assert nasce_ligado("menu.orcamentos") is True
    assert nasce_ligado("menu.configuracoes") is False


@pytest.fixture
def pagina(monkeypatch):
    QApplication.instance() or QApplication([])
    import app.ui.pages.user_management_page as modulo

    utilizadores = [
        SimpleNamespace(
            id=1,
            username="Andreia",
            nome="Andreia",
            email="a@example.test",
            role="user",
            departamento="Orçamentação",
            is_active=True,
            permissions=dict(DEFAULT_USER_PERMISSIONS),
        )
    ]

    class _Sessao:
        def __enter__(self):
            return None

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(modulo, "SessionLocal", lambda: _Sessao())
    monkeypatch.setattr(modulo, "list_managed_users", lambda _session: utilizadores)
    return modulo.UserManagementPage()


def test_colunas_tem_dica_e_o_quadro_explica_cada_acesso(pagina) -> None:
    fixas = len(pagina.FIXED_COLUMNS)
    for indice, chave in enumerate(PERMISSOES_EDITAVEIS):
        titulo = pagina.table.horizontalHeaderItem(fixas + indice)
        assert titulo.text() == DESCRICOES_ACESSOS[chave].titulo_curto
        assert DESCRICOES_ACESSOS[chave].o_que_faz in titulo.toolTip()
    assert pagina.descricoes.rowCount() == len(DESCRICOES_ACESSOS)
    assert pagina.descricoes.item(0, 1).text() == "Ajuda"


def test_clicar_numa_coluna_mostra_a_explicacao(pagina) -> None:
    fixas = len(pagina.FIXED_COLUMNS)
    indice = list(PERMISSOES_EDITAVEIS).index(PERMISSAO_ASSISTENTE_ORCAMENTOS)

    pagina.table.setCurrentCell(0, fixas + indice)

    linha = pagina.descricoes.currentRow()
    assert pagina.descricoes.item(linha, 1).text() == "Assistente dos Orçamentos"
    assert pagina.status_label.text().startswith("Assistente dos Orçamentos:")
