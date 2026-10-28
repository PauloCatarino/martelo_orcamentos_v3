"""Único canal de escrita do Martelo no Escritório do Streamlit (sem servidor)."""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import uuid
from pathlib import Path

import pytest

from app.domain import escritorio_streamlit as regras
from app.domain.escritorio_streamlit import Avaliacao
from app.services import escritorio_streamlit_escrita as escrita
from app.services import escritorio_streamlit_service as leitura
from app.services.system_setting_service import SystemSettingService

CLIQUE = "7c9e6679-7425-40de-944b-e07fc1f90ae7"


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Nenhum teste pergunta à rede pelo IP do PC do Streamlit."""

    def nao_sei(*args, **kwargs):
        raise socket.gaierror(11001, "Este anfitrião não é conhecido")

    monkeypatch.setattr(leitura.socket, "getaddrinfo", nao_sei)


def _avaliacao(**kw) -> Avaliacao:
    base = {
        "chave": regras.chave_versao("2026", "599", "05", "01"),
        "resultado": regras.PRONTO,
        "mensagem": "",
        "utilizador": "pedro",
        "desenhador": "pedro",
        "ce": {"bd_ano": "2026", "bd_n_encomenda": "0599", "bd_cliente": "CRW, Lda"},
        "plano_corte": "0599_05_01_26_CRW",
    }
    base.update(kw)
    return Avaliacao(**base)


# --------------------------------------------------------------------------
# Interruptor
# --------------------------------------------------------------------------


def test_desligado_por_omissao_nao_toca_no_sql(session, monkeypatch) -> None:
    monkeypatch.setattr(
        escrita, "executar_payload", lambda _p: pytest.fail("não devia escrever")
    )
    with pytest.raises(RuntimeError, match="streamlit_escrita_ativa"):
        escrita.enviar(session, _avaliacao(), command_id=CLIQUE)


def test_ligado_escreve(session, monkeypatch) -> None:
    servico = SystemSettingService(session)
    servico.guardar_valor(leitura.KEY_STREAMLIT_ESCRITA_ATIVA, "ON")
    servico.guardar_valor("streamlit_sql_password", "segredo")
    payloads = []
    monkeypatch.setattr(
        escrita,
        "executar_payload",
        lambda p: payloads.append(p) or escrita.ResultadoEnvio(escrita.GRAVADO),
    )
    resultado = escrita.enviar(session, _avaliacao(), command_id=CLIQUE, pasta=r"\\S\obra")
    assert resultado.gravado
    detalhe = json.loads(payloads[0]["eventos"][0]["detalhe"])
    assert detalhe["via"] == "MARTELO"
    assert detalhe["pasta"] == r"\\S\obra"
    assert detalhe["versao_programa"]
    assert detalhe["posto"]


# --------------------------------------------------------------------------
# Payload
# --------------------------------------------------------------------------


def test_payload_do_caso_normal() -> None:
    payload = escrita.construir_payload("conn", _avaliacao(), command_id=CLIQUE)
    assert payload["bd_key"] == "2026_0599_05_01"
    assert payload["numero"] == "0599"
    assert payload["sufixo"] == ""
    assert payload["ensaio"] is False
    (evento,) = payload["eventos"]
    assert evento["tipo"] == "AVANCAR"
    assert evento["de"] == "DESENHO" and evento["para"] == "APROVISIONAMENTO"
    assert evento["utilizador"] == "pedro"
    assert evento["motivo"] == "Desenho concluído."
    assert evento["command_id"] == CLIQUE
    assert evento["espelho"] == (
        "Desenho → Aprovisionamento · via MARTELO · motivo: Desenho concluído."
    )
    assert payload["espelho"] == {
        "bd_key": "2026_0599_05_01",
        "bd_ano": "2026",
        "bd_n_encomenda": "0599",
        "bd_cliente": "CRW, Lda",
        "bd_plano_corte": "0599_05_01_26_CRW",
    }


def test_material_so_do_cliente_leva_o_segundo_evento() -> None:
    payload = escrita.construir_payload(
        "conn",
        _avaliacao(material_cliente="placas: Cliente · orla: Cliente"),
        command_id=CLIQUE,
    )
    avancar, libertar = payload["eventos"]
    assert libertar["tipo"] == "LIBERTAR_AUTO"
    assert libertar["utilizador"] == "sistema"
    assert libertar["command_id"] == regras.id_filho(CLIQUE, "2026_0599_05_01")
    detalhe = json.loads(libertar["detalhe"])
    assert detalhe["material"] == "placas: Cliente · orla: Cliente"
    assert detalhe["acionado_por"] == "pedro"
    # Nunca «sistema» nem «automatico» no AVANCAR.
    assert avancar["utilizador"] == "pedro"


def test_em_nome_de_e_avisos_ficam_no_detalhe() -> None:
    payload = escrita.construir_payload(
        "conn",
        _avaliacao(utilizador="admin", em_nome_de="pedro", avisos=("sem plano de corte",)),
        command_id=CLIQUE,
    )
    detalhe = json.loads(payload["eventos"][0]["detalhe"])
    assert detalhe["em_nome_de"] == "pedro"
    assert detalhe["avisos_aceites"] == ["sem plano de corte"]


def test_obra_com_underscore_usa_o_historico_gemeo() -> None:
    avaliacao = _avaliacao(chave=regras.chave_versao("2026", "_1", "01", "01"))
    payload = escrita.construir_payload("conn", avaliacao, command_id=CLIQUE)
    assert payload["bd_key"] == "2026__001_01_01"
    assert payload["sufixo"] == "_"


def test_recusa_avaliacao_que_nao_esta_pronta() -> None:
    with pytest.raises(ValueError, match="não pode avançar"):
        escrita.construir_payload(
            "conn",
            _avaliacao(resultado=regras.RECUSADO, mensagem="Falta o CE"),
            command_id=CLIQUE,
        )


def test_recusa_command_id_que_nao_e_uuid() -> None:
    with pytest.raises(ValueError, match="command_id"):
        escrita.construir_payload("conn", _avaliacao(), command_id="123")


def test_recusa_valores_maiores_que_a_coluna() -> None:
    with pytest.raises(ValueError, match="utilizador"):
        escrita.construir_payload("conn", _avaliacao(utilizador="x" * 101), command_id=CLIQUE)


def test_espelho_corta_em_vez_de_falhar() -> None:
    payload = escrita.construir_payload(
        "conn", _avaliacao(plano_corte="p" * 300), command_id=CLIQUE
    )
    assert len(payload["espelho"]["bd_plano_corte"]) == 255


def test_desenhador_pode_faltar() -> None:
    payload = escrita.construir_payload("conn", _avaliacao(desenhador=None), command_id=CLIQUE)
    assert payload["desenhador"] is None


# --------------------------------------------------------------------------
# Resposta do PowerShell
# --------------------------------------------------------------------------


@pytest.mark.parametrize("resultado", [escrita.GRAVADO, escrita.JA_REGISTADO, escrita.CONFLITO])
def test_executar_payload_le_a_resposta(monkeypatch, resultado) -> None:
    monkeypatch.setattr(
        leitura,
        "correr_powershell",
        lambda *a, **k: {"resultado": resultado, "libertada": True, "espelho": 2,
                         "espelho_erro": "", "ensaio": False},
    )
    resposta = escrita.executar_payload({})
    assert resposta.resultado == resultado
    assert resposta.libertada is True
    assert resposta.espelho == 2


def test_resposta_estranha_e_erro(monkeypatch) -> None:
    monkeypatch.setattr(leitura, "correr_powershell", lambda *a, **k: {"resultado": "?"})
    with pytest.raises(RuntimeError):
        escrita.executar_payload({})


# --------------------------------------------------------------------------
# O script: só o que tem de fazer
# --------------------------------------------------------------------------


def _instrucoes_sql() -> list[str]:
    """As instruções SQL do script, sem os comentários do PowerShell."""
    sem_comentarios = "\n".join(
        linha for linha in escrita._PS_ESCRITA.splitlines()
        if not linha.strip().startswith("#")
    )
    return re.findall(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|MERGE|EXEC|CREATE)\b",
                      sem_comentarios)


def test_script_nunca_apaga_nem_altera_tabelas() -> None:
    instrucoes = set(_instrucoes_sql())
    assert instrucoes == {"INSERT", "UPDATE"}


def test_script_so_mexe_nas_quatro_tabelas() -> None:
    alvos = set(re.findall(r"(?:INSERT INTO|UPDATE)\s+([\w.]+)", escrita._PS_ESCRITA))
    assert alvos == {"dbo.Escritorio_Versoes", "dbo.Escritorio_Eventos"}
    # A 3.ª (e 4.ª) é a do histórico, montada a partir de uma lista fechada.
    assert escrita._PS_ESCRITA.count('"INSERT INTO " + $tabelaHistorico') == 1
    assert "$tabelaHistorico = 'dbo.TemposProducaoHistorico' + $sufixo" in escrita._PS_ESCRITA
    assert "if ($sufixo -ne '' -and $sufixo -ne '_')" in escrita._PS_ESCRITA


def test_eventos_nunca_se_alteram() -> None:
    assert "UPDATE dbo.Escritorio_Eventos" not in escrita._PS_ESCRITA


def test_etapa_so_muda_com_compare_and_set() -> None:
    # Juntar as linhas partidas com «" +» para ler cada comando inteiro.
    script = re.sub(r'"\s*\+\s*"', "", escrita._PS_ESCRITA)
    comandos = re.findall(r"UPDATE dbo\.Escritorio_Versoes[^\"]+", script)
    assert len(comandos) == 2
    for comando in comandos:
        assert re.search(r"WHERE bd_key = @k AND etapa = '(DESENHO|APROVISIONAMENTO)'", comando)


def test_horas_do_servidor() -> None:
    """UTC no Escritório, hora local no histórico — nunca a hora do PC."""
    assert "SYSUTCDATETIME()" in escrita._PS_ESCRITA
    assert "GETDATE()" in escrita._PS_ESCRITA
    assert "DateTime" not in escrita._PS_ESCRITA


@pytest.mark.skipif(os.name != "nt", reason="o PowerShell só existe no Windows")
def test_script_de_escrita_e_powershell_valido(tmp_path: Path) -> None:
    caminho = tmp_path / "escrita.ps1"
    caminho.write_text(escrita._PS_ESCRITA, encoding="utf-8")
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


def test_command_id_novo_e_uuid() -> None:
    uuid.UUID(regras.novo_command_id())
