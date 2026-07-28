"""Testes da barreira de leitura da futura integração SQL iMos."""

from __future__ import annotations

import re

import pytest

from app.services import imos_sql
from app.services.imos_sql import ImosConfig


def _cfg(**overrides) -> ImosConfig:
    cfg: ImosConfig = {
        "server": r"SERVIDOR\IMOS",
        "database": "imosdb",
        "user": "martelo_readonly",
        "password": "segredo;com;ponto",
        "trusted": False,
        "trust_server_certificate": True,
    }
    cfg.update(overrides)  # type: ignore[typeddict-item]
    return cfg


def test_connection_string_forca_application_intent_read_only() -> None:
    conn = imos_sql.build_connection_string(_cfg())

    assert "ApplicationIntent=ReadOnly" in conn
    assert "MultipleActiveResultSets=False" in conn
    assert 'Password="segredo;com;ponto"' in conn
    assert "TrustServerCertificate=True" in conn


def test_connection_string_exige_credenciais_sql() -> None:
    with pytest.raises(ValueError, match="utilizador"):
        imos_sql.build_connection_string(_cfg(user=""))
    with pytest.raises(ValueError, match="password"):
        imos_sql.build_connection_string(_cfg(password=""))


def test_connection_string_windows_nao_inclui_password() -> None:
    conn = imos_sql.build_connection_string(_cfg(trusted=True, user="", password=""))

    assert "Integrated Security=True" in conn
    assert "User ID=" not in conn
    assert "Password=" not in conn


def test_diagnostico_aceita_principal_apenas_de_leitura(monkeypatch) -> None:
    monkeypatch.setattr(
        imos_sql,
        "run_select",
        lambda _conn, _query: [
            {
                "servidor": "SQL01",
                "base_dados": "imosdb",
                "login": "martelo_readonly",
                "utilizador_base_dados": "martelo_readonly",
                "permissoes_estruturais": 0,
                "tabelas_consultaveis": 42,
                "tabelas_com_escrita": 0,
            }
        ],
    )

    result = imos_sql.diagnosticar_ligacao(_cfg())

    assert result.conta_sql_somente_leitura is True
    assert result.barreira_aplicacao_ativa is True
    assert result.tabelas_consultaveis == 42


@pytest.mark.parametrize(
    ("estruturais", "tabelas_escrita"), [(1, 0), (0, 1), (2, 7)]
)
def test_diagnostico_assinala_permissao_de_escrita_sem_executar_escrita(
    monkeypatch, estruturais: int, tabelas_escrita: int
) -> None:
    monkeypatch.setattr(
        imos_sql,
        "run_select",
        lambda _conn, _query: [
            {
                "permissoes_estruturais": estruturais,
                "tabelas_consultaveis": 10,
                "tabelas_com_escrita": tabelas_escrita,
            }
        ],
    )

    result = imos_sql.diagnosticar_ligacao(_cfg())
    assert result.conta_sql_somente_leitura is False


def test_diagnostico_aceita_ligacao_sem_tabelas_visiveis(monkeypatch) -> None:
    monkeypatch.setattr(
        imos_sql,
        "run_select",
        lambda _conn, _query: [
            {
                "permissoes_estruturais": 0,
                "tabelas_consultaveis": 0,
                "tabelas_com_escrita": 0,
            }
        ],
    )

    result = imos_sql.diagnosticar_ligacao(_cfg())
    assert result.tabelas_consultaveis == 0


def test_explicar_erro_login_remove_detalhe_tecnico() -> None:
    texto = imos_sql.explicar_erro_ligacao(
        RuntimeError("tmp123.ps1: Login failed for user 'IMOSADMIN'.")
    )
    assert "servidor SQL respondeu" in texto
    assert "password" in texto
    assert "tmp123" not in texto


def _arvore_falsa(monkeypatch, nos: list[dict]) -> list[str]:
    """Substitui o run_select por uma árvore em memória; guarda as queries."""
    queries: list[str] = []

    def _run(_conn: str, query: str) -> list[dict]:
        queries.append(query)
        # Toda a consulta da árvore passa pela mesma barreira de leitura.
        imos_sql.assert_select_only(query)

        parent = int(re.search(r"PARENT_ID = (\d+)", query).group(1))
        tipo_match = re.search(r"TYPE = (\d+)", query)
        nome_match = re.search(r"NAME = N'(.*?)'", query)
        resultado = [
            no
            for no in nos
            if no["PARENT_ID"] == parent
            and (tipo_match is None or no["TYPE"] == int(tipo_match.group(1)))
            and (nome_match is None or no["NAME"] == nome_match.group(1))
        ]
        if "TOP 1" in query:
            resultado = resultado[:1]
        return resultado

    monkeypatch.setattr(imos_sql, "run_select", _run)
    return queries


_ARVORE = [
    {"DIR_ID": 180, "NAME": "LANCA_ENCANTO", "TYPE": 1000001, "PARENT_ID": 120},
    {"DIR_ID": 6624, "NAME": "ANO_2026", "TYPE": 1000001, "PARENT_ID": 180},
    {"DIR_ID": 5383, "NAME": "ANO_2025", "TYPE": 1000001, "PARENT_ID": 180},
    {"DIR_ID": 6641, "NAME": "LINHAS_DIREITAS", "TYPE": 1000001, "PARENT_ID": 6624},
    {
        "DIR_ID": 6765,
        "NAME": "0159_01_26_LINHAS_DIREITAS",
        "TYPE": 173,
        "PARENT_ID": 6641,
    },
]


@pytest.mark.parametrize(
    "nome",
    ["LANCA_ENCANTO", "ANO_2026", "0159_01_26_LINHAS_DIREITAS", "ARMARIO_C2(A)", "A" * 30],
)
def test_nome_imos_valido_aceita_os_nomes_reais_da_arvore(nome: str) -> None:
    assert imos_sql.nome_imos_valido(nome) is True


@pytest.mark.parametrize("nome", ["", "A" * 31, "CLIENTE'; DROP TABLE X--", "MAU\nNOME"])
def test_nome_imos_recusa_nome_invalido_ou_grande_demais(nome: str) -> None:
    assert imos_sql.nome_imos_valido(nome) is False
    with pytest.raises(ValueError):
        imos_sql._literal_nome(nome)


@pytest.mark.parametrize(
    ("ano", "esperado"), [(2026, "ANO_2026"), ("2026", "ANO_2026"), ("26", "ANO_2026")]
)
def test_nome_pasta_ano(ano, esperado: str) -> None:
    assert imos_sql.nome_pasta_ano(ano) == esperado


def test_nome_pasta_ano_recusa_valor_sem_ano() -> None:
    with pytest.raises(ValueError):
        imos_sql.nome_pasta_ano("sem ano")


def test_resolver_no_encontra_pela_chave_pai_mais_nome(monkeypatch) -> None:
    queries = _arvore_falsa(monkeypatch, _ARVORE)

    no = imos_sql.resolver_no(
        _cfg(), parent_dir_id=120, nome="LANCA_ENCANTO", tipo=imos_sql.IMOS_TIPO_PASTA
    )

    assert no is not None
    assert no.dir_id == 180
    assert no.e_pasta is True
    assert "dbo.IMORDFOLDER" in queries[0]


def test_resolver_no_devolve_none_quando_nao_existe(monkeypatch) -> None:
    _arvore_falsa(monkeypatch, _ARVORE)

    assert (
        imos_sql.resolver_no(
            _cfg(), parent_dir_id=6624, nome="CLIENTE_NOVO", tipo=imos_sql.IMOS_TIPO_PASTA
        )
        is None
    )


def test_listar_filhos_filtra_por_tipo(monkeypatch) -> None:
    _arvore_falsa(monkeypatch, _ARVORE)

    anos = imos_sql.listar_filhos(_cfg(), 180, tipo=imos_sql.IMOS_TIPO_PASTA)

    assert [no.nome for no in anos] == ["ANO_2026", "ANO_2025"]


def test_resolver_caminho_completo_quando_tudo_existe(monkeypatch) -> None:
    _arvore_falsa(monkeypatch, _ARVORE)

    caminho = imos_sql.resolver_caminho_encomenda(
        _cfg(),
        ano=2026,
        cliente_simplex="LINHAS_DIREITAS",
        nome_encomenda="0159_01_26_LINHAS_DIREITAS",
    )

    assert caminho.em_falta == ()
    assert caminho.encomenda_ja_existe is True
    assert caminho.dir_id_pai_encomenda == 6641
    assert caminho.texto() == (
        "LANCA_ENCANTO / ANO_2026 / LINHAS_DIREITAS / 0159_01_26_LINHAS_DIREITAS"
    )


def test_resolver_caminho_marca_cliente_e_encomenda_em_falta(monkeypatch) -> None:
    _arvore_falsa(monkeypatch, _ARVORE)

    caminho = imos_sql.resolver_caminho_encomenda(
        _cfg(),
        ano=2026,
        cliente_simplex="CLIENTE_NOVO",
        nome_encomenda="1260_01_26_CLIENTE_NOVO",
    )

    assert [nivel.nome for nivel in caminho.em_falta] == [
        "CLIENTE_NOVO",
        "1260_01_26_CLIENTE_NOVO",
    ]
    assert caminho.encomenda_ja_existe is False
    assert caminho.dir_id_pai_encomenda is None


def test_resolver_caminho_para_de_procurar_abaixo_do_nivel_em_falta(monkeypatch) -> None:
    """Sem pasta do ano não há pai: os níveis seguintes nem chegam a ser consultados."""
    queries = _arvore_falsa(monkeypatch, _ARVORE)

    caminho = imos_sql.resolver_caminho_encomenda(
        _cfg(),
        ano=2030,
        cliente_simplex="LINHAS_DIREITAS",
        nome_encomenda="0159_01_30_LINHAS_DIREITAS",
    )

    assert len(caminho.em_falta) == 3
    # Só a raiz e o ano foram consultados.
    assert len(queries) == 2


def test_run_imos_select_bloqueia_escrita_antes_da_ligacao(monkeypatch) -> None:
    chamado = False

    def _run(*_args):
        nonlocal chamado
        chamado = True
        return []

    monkeypatch.setattr(imos_sql, "run_select", _run)
    with pytest.raises(RuntimeError):
        imos_sql.run_imos_select(_cfg(), "UPDATE artigo SET nome='x'")
    assert chamado is False
