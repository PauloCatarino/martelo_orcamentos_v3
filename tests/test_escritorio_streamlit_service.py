"""Escritório do Streamlit: leituras (sem servidor — o PowerShell é simulado)."""

from __future__ import annotations

import os
import socket
import subprocess
from pathlib import Path

import pytest

from app.domain import escritorio_streamlit as regras
from app.models.producao import Producao
from app.services import escritorio_streamlit_service as svc
from app.services.phc_sql import assert_select_only
from app.services.system_setting_service import SystemSettingService


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Nenhum teste pergunta à rede pelo IP do PC do Streamlit."""
    perguntas: list[str] = []

    def nao_sei(nome, *args, **kwargs):
        perguntas.append(nome)
        raise socket.gaierror(11001, "Este anfitrião não é conhecido")

    monkeypatch.setattr(svc.socket, "getaddrinfo", nao_sei)
    return perguntas


def _windows_sabe(monkeypatch, ip: str) -> list[str]:
    perguntas: list[str] = []

    def sabe(nome, *args, **kwargs):
        perguntas.append(nome)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

    monkeypatch.setattr(svc.socket, "getaddrinfo", sabe)
    return perguntas


@pytest.fixture()
def configurado(session):
    servico = SystemSettingService(session)
    servico.guardar_valor("streamlit_sql_server", "SERVIDOR,1433")
    servico.guardar_valor("streamlit_sql_database", "Base")
    servico.guardar_valor("streamlit_sql_user", "conta")
    servico.guardar_valor("streamlit_sql_password", "segredo")
    return session


def _linhas_base() -> dict:
    return {
        "obra": [{"estado_obra": "COM_DESENHO", "desenhador_username": "pedro"}],
        "versao": [],
        "ultimo_avanco": [],
        "ce": [{"bd_ano": "2026", "bd_n_encomenda": "1497", "bd_cliente": "CRW",
                "tem_materias": 1, "bd_placas_le": True}],
        "tp": [{"bd_plano_corte": "P", "bd_status_envio": "🟢 ENVIADO", "bd_assistencia": False}],
        "utilizadores": [{"username": "pedro", "nome": "Pedro Reis", "ativo": True,
                          "is_admin": False, "local_trabalho": "Escritório - Desenho",
                          "permissoes": "[]"}],
        "locais": [{"Nome": "Escritório - Desenho", "Permissoes": '["Escritorio_Desenhos"]',
                    "Ativo": True}],
    }


def test_escrita_desligada_por_omissao(session) -> None:
    assert svc.escrita_ativa(session) is False
    SystemSettingService(session).guardar_valor(svc.KEY_STREAMLIT_ESCRITA_ATIVA, "ON")
    assert svc.escrita_ativa(session) is True


def test_ligacao_usa_tempo_curto(configurado) -> None:
    assert "Connection Timeout=8;" in svc.ligacao(configurado)


def test_ligacao_vai_pelo_ip_quando_o_windows_o_sabe(configurado, monkeypatch) -> None:
    # 28-10: «Este anfitrião não é conhecido» no SqlClient, com o nome a resolver.
    perguntas = _windows_sabe(monkeypatch, "192.168.5.210")
    texto = svc.ligacao(configurado)
    assert 'Server="192.168.5.210,1433";' in texto
    assert perguntas == ["SERVIDOR"]
    # O nome fica nas Configurações: o PC do Streamlit muda de IP.
    assert SystemSettingService(configurado).obter_valor("streamlit_sql_server", "") == "SERVIDOR,1433"


def test_ligacao_fica_com_o_nome_se_o_windows_nao_souber(configurado) -> None:
    assert 'Server="SERVIDOR,1433";' in svc.ligacao(configurado)


@pytest.mark.parametrize(
    ("servidor", "esperado"),
    [
        ("DESKTOP-PTJ4TE6,1433", "10.0.0.7,1433"),
        ("tcp:DESKTOP-PTJ4TE6,1433", "tcp:10.0.0.7,1433"),
        (r"SERVER_LE\PHC", r"10.0.0.7\PHC"),
        ("DESKTOP-PTJ4TE6", "10.0.0.7"),
    ],
)
def test_servidor_por_ip_mantem_porta_e_instancia(monkeypatch, servidor, esperado) -> None:
    _windows_sabe(monkeypatch, "10.0.0.7")
    assert svc.servidor_por_ip(servidor) == esperado


@pytest.mark.parametrize("servidor", ["192.168.5.210,1433", "localhost", r".\SQLEXPRESS", "(local)", ""])
def test_servidor_por_ip_nao_pergunta_o_que_nao_e_nome(sem_rede, servidor) -> None:
    assert svc.servidor_por_ip(servidor) == servidor
    assert sem_rede == []


def test_todas_as_consultas_sao_so_select_e_parametrizadas() -> None:
    chave = regras.chave_versao("2026", "_253", "01", "01")
    consultas = svc.consultas_do_envio(chave)
    for consulta in consultas + [svc.CONSULTA_TOKEN, svc.CONSULTA_AVANCADAS]:
        assert_select_only(consulta.sql)
        assert chave.bd_key not in consulta.sql  # o valor vai em parâmetro
    textos = " ".join(c.sql for c in consultas)
    assert "dbo.CadernoEncargos_ " in textos and "dbo.TemposProducao_ " in textos
    assert "password" not in textos.casefold()


def test_tabelas_normais_sem_underscore() -> None:
    textos = " ".join(
        c.sql for c in svc.consultas_do_envio(regras.chave_versao("2026", "1497", "02", "01"))
    )
    assert "dbo.CadernoEncargos " in textos and "CadernoEncargos_" not in textos


def test_parametros_tipados() -> None:
    parametros = svc.parametros_da_chave(regras.chave_versao("2026", "599", "05", "01"))
    assert parametros == [
        {"nome": "@ano", "tipo": "int", "valor": 2026},
        {"nome": "@numero", "tipo": "nvarchar", "tamanho": 20, "valor": "0599"},
        {"nome": "@bd_key", "tipo": "nvarchar", "tamanho": 60, "valor": "2026_0599_05_01"},
    ]


def test_avaliar_le_tudo_numa_so_ida(configurado, monkeypatch) -> None:
    chamadas = []

    def falso(script, payload, *, timeout):
        chamadas.append(payload)
        return _linhas_base()

    monkeypatch.setattr(svc, "correr_powershell", falso)
    avaliacao = svc.avaliar(
        configurado,
        regras.chave_versao("2026", "1497", "02", "01"),
        martelo_username="Pedro",
        martelo_nome="Pedro",
    )
    assert avaliacao.pronto
    assert avaliacao.utilizador == "pedro"
    assert len(chamadas) == 1
    assert [c["nome"] for c in chamadas[0]["consultas"]] == [
        "obra", "versao", "ultimo_avanco", "ce", "tp", "utilizadores", "locais",
    ]


def test_versao_que_nao_e_01_nem_vai_ao_servidor(configurado, monkeypatch) -> None:
    def rebenta(*_a, **_k):
        raise AssertionError("não devia ir ao Streamlit")

    monkeypatch.setattr(svc, "correr_powershell", rebenta)
    avaliacao = svc.avaliar(
        configurado,
        regras.chave_versao("2026", "1497", "02", "02"),
        martelo_username="Pedro",
        martelo_nome="Pedro",
    )
    assert avaliacao.motivo_recusa == "versao"


def test_powershell_desembrulha_listas_de_um(configurado, monkeypatch) -> None:
    """O PowerShell 5.1 às vezes manda uma linha sozinha sem a lista à volta."""
    linhas = _linhas_base()
    linhas["obra"] = linhas["obra"][0]
    monkeypatch.setattr(svc, "correr_powershell", lambda *a, **k: linhas)
    avaliacao = svc.avaliar(
        configurado,
        regras.chave_versao("2026", "1497", "02", "01"),
        martelo_username="Pedro",
        martelo_nome="Pedro",
    )
    assert avaliacao.pronto


def _obra(session, id_, num, estado, responsavel="Pedro") -> None:
    session.add(
        Producao(
            id=id_, codigo_processo=f"26.{num}_01_01_X", ano="2026", num_enc_phc=num,
            versao_obra="01", versao_plano="01", estado=estado, responsavel=responsavel,
            nome_cliente="X", tipo_pasta="Encomenda de Cliente",
        )
    )
    session.commit()


def test_levantar_sugestoes_so_as_minhas(configurado, monkeypatch) -> None:
    _obra(configurado, 1, "1098", "Desenho", "Pedro")
    _obra(configurado, 2, "1712", "Desenho", "Ruben")
    _obra(configurado, 3, "555", "Producao", "Pedro")
    monkeypatch.setattr(
        svc,
        "correr_powershell",
        lambda *a, **k: {
            "token": [{"max_id": 140}],
            "versoes": [
                {"bd_key": "2026_1098_01_01", "etapa": "LIBERTADA"},
                {"bd_key": "2026_1712_01_01", "etapa": "APROVISIONAMENTO"},
                {"bd_key": "2026_0555_01_01", "etapa": "APROVISIONAMENTO"},
            ],
        },
    )
    token, sugestoes = svc.levantar_sugestoes(configurado, responsavel="Pedro")
    assert token == 140
    assert [s["id"] for s in sugestoes] == [1]


def test_ler_token(configurado, monkeypatch) -> None:
    monkeypatch.setattr(svc, "correr_powershell", lambda *a, **k: {"token": {"max_id": 7}})
    assert svc.ler_token(configurado) == 7
    monkeypatch.setattr(svc, "correr_powershell", lambda *a, **k: {"token": [{"max_id": None}]})
    assert svc.ler_token(configurado) is None


@pytest.mark.parametrize(
    ("erro", "texto"),
    [
        (subprocess.TimeoutExpired("powershell", 60), "a tempo"),
        (RuntimeError("A network-related or instance-specific error occurred"), "ligar ao servidor"),
        (RuntimeError("Login failed for user 'conta'."), "recusou o utilizador"),
        (RuntimeError("Invalid object name 'dbo.Escritorio_Versoes'."), "não está instalado"),
        (RuntimeError("(provider: TCP Provider, error: 0 - Este anfitrião não é conhecido.)"),
         "ligar ao servidor"),
    ],
)
def test_explicar_erro_leitura(erro, texto) -> None:
    assert texto in svc.explicar_erro_leitura(erro)


@pytest.mark.skipif(os.name != "nt", reason="o PowerShell só existe no Windows")
def test_erro_do_powershell_chega_com_os_acentos_certos() -> None:
    # O caso de 28-10: «O servidor nÆo foi encontrado» não se reconhecia.
    script = 'throw ("O servidor n" + [char]0x00E3 + "o foi encontrado")'
    with pytest.raises(RuntimeError) as erro:
        svc.correr_powershell(script, {}, timeout=60)
    assert "não foi encontrado" in str(erro.value)
    assert "ligar ao servidor" in svc.explicar_erro_leitura(erro.value)


def test_explicar_erro_nao_mostra_o_caminho_do_script() -> None:
    texto = svc.explicar_erro_leitura(
        RuntimeError(r"C:\Users\x\AppData\Local\Temp\tmpab12.ps1 : algo correu mal")
    )
    assert ".ps1" not in texto


@pytest.mark.skipif(os.name != "nt", reason="o PowerShell só existe no Windows")
def test_script_de_leitura_e_powershell_valido(tmp_path: Path) -> None:
    caminho = tmp_path / "leitura.ps1"
    caminho.write_text(svc._PS_LEITURA, encoding="utf-8")
    resultado = subprocess.run(
        [
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "$t=$null;$e=$null;"
            f"[void][System.Management.Automation.Language.Parser]::ParseFile('{caminho}',[ref]$t,[ref]$e);"
            "$e.Count",
        ],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert resultado.stdout.strip() == "0", resultado.stdout + resultado.stderr
