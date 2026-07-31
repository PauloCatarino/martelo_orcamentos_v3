"""Email que avisa o cliente de que a obra entrou em produção."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.domain.projeto_cliente_email import (
    ProjetoParaCliente,
    assunto_projeto_producao,
    corpo_projeto_producao,
)
from app.models.cliente import Cliente
from app.models.producao import Producao
from app.services import projeto_cliente_service as svc


def _dados(**overrides) -> ProjetoParaCliente:
    base = {
        "processo": "26.1357_01_01_JF_VIVA",
        "cliente": "MÓVEIS J.F. VIVA",
        "ref_cliente": "2512001",
        "obra": "REMODELAÇÃO T3",
        "localizacao": "LISBOA",
        "data_entrada": "31-07-2026",
        "data_entrega": "16-09-2026",
        "materias_usados": "AGL MLM LINHO CANCUN 10/16/19MM",
        "descricao_producao": "4 ROUPEIROS PORTAS ABRIR\nCLOSET U SEM PORTAS",
    }
    base.update(overrides)
    return ProjetoParaCliente(**base)


# ---- assunto e corpo ---------------------------------------------------------
def test_assunto_com_processo_ref_e_obra() -> None:
    assunto = assunto_projeto_producao(_dados())

    assert assunto == (
        "Processo: 26.1357_01_01_JF_VIVA | Ref.Cliente: 2512001 | Obra: REMODELAÇÃO T3"
    )


def test_assunto_sem_obra_nao_deixa_etiqueta_vazia() -> None:
    assunto = assunto_projeto_producao(_dados(obra="", localizacao=""))

    assert assunto == "Processo: 26.1357_01_01_JF_VIVA | Ref.Cliente: 2512001"
    assert "Obra" not in assunto


def test_corpo_tem_tudo_o_que_foi_acordado() -> None:
    corpo = corpo_projeto_producao(
        _dados(), saudacao="Bom dia", utilizador="Paulo Catarino"
    )

    assert "<p>Bom dia,</p>" in corpo
    assert "Sr. Cliente: <b>MÓVEIS J.F. VIVA</b>" in corpo
    assert "Ref. Cliente: 2512001 | Obra: REMODELAÇÃO T3 | Localização: LISBOA" in corpo
    assert "vai entrar para produção no dia <b>31-07-2026</b>" in corpo
    assert "previsão de conclusão a <b>16-09-2026</b>" in corpo
    assert "Processo: <b>26.1357_01_01_JF_VIVA</b>" in corpo
    assert "Matérias-primas usadas" in corpo
    assert "Descrição dos produtos" in corpo
    assert "Estado atual" in corpo and "Em produção" in corpo
    assert "Com os melhores cumprimentos,<br>Paulo Catarino" in corpo
    # Assinatura da IA a fechar, por pedido do Paulo.
    assert "🔨 IA Martelo" in corpo


def test_descricao_de_varias_linhas_fica_legivel_no_email() -> None:
    corpo = corpo_projeto_producao(_dados())

    assert "4 ROUPEIROS PORTAS ABRIR<br>CLOSET U SEM PORTAS" in corpo


def test_campos_em_falta_desaparecem_do_corpo() -> None:
    corpo = corpo_projeto_producao(
        _dados(obra="", localizacao="", materias_usados="")
    )

    assert "Obra:" not in corpo
    assert "Localização:" not in corpo
    assert "Matérias-primas usadas" not in corpo
    # A referência do cliente e o estado ficam sempre que existam.
    assert "Ref. Cliente: 2512001" in corpo
    assert "Em produção" in corpo


def test_sem_imagem_o_email_sai_na_mesma() -> None:
    corpo = corpo_projeto_producao(_dados(), imagem_path="")

    assert "<img" not in corpo


def test_imagem_entra_como_ficheiro_local(tmp_path: Path) -> None:
    imagem = tmp_path / "obra.png"
    imagem.write_bytes(b"")

    corpo = corpo_projeto_producao(_dados(), imagem_path=str(imagem))

    assert "<img" in corpo and imagem.name in corpo


def test_texto_do_utilizador_nao_injeta_html() -> None:
    corpo = corpo_projeto_producao(_dados(cliente="<script>alerta</script>"))

    assert "<script>" not in corpo


# ---- serviço -----------------------------------------------------------------
@pytest.fixture()
def obra(session) -> Producao:
    cliente = Cliente(
        nome="MÓVEIS J.F. VIVA",
        email="geral@jfviva.pt",
        email_projeto_producao="projetos@jfviva.pt",
    )
    session.add(cliente)
    session.flush()
    processo = Producao(
        codigo_processo="26.1357_01_01_JF_VIVA",
        ano="2026",
        num_enc_phc="1357",
        versao_obra="01",
        versao_plano="01",
        estado="Producao",
        cliente_id=cliente.id,
        nome_cliente="MÓVEIS J.F. VIVA",
        nome_cliente_simplex="JF_VIVA",
        ref_cliente="2512001",
        obra="REMODELAÇÃO T3",
        # O Martelo guarda as datas como texto dd-mm-aaaa.
        data_entrega="16-09-2026",
        materias_usados="AGL MLM LINHO CANCUN",
        descricao_producao="4 ROUPEIROS PORTAS ABRIR",
    )
    session.add(processo)
    session.commit()
    return processo


def test_preparar_usa_o_email_de_projeto_do_cliente(session, obra, monkeypatch) -> None:
    monkeypatch.setattr(svc, "_pasta_da_obra", lambda *_a, **_k: None)
    monkeypatch.setattr(svc, "_imagem_da_obra", lambda *_a, **_k: "")

    envio = svc.preparar_envio(
        session, obra.id, utilizador="Paulo", agora=datetime(2026, 7, 31, 15, 42)
    )

    # Nunca o email do PHC: esse serve para faturação e afins.
    assert envio.destino == "projetos@jfviva.pt"
    assert "Processo: 26.1357_01_01_JF_VIVA" in envio.assunto
    assert "31-07-2026" in envio.corpo_html
    assert "16-09-2026" in envio.corpo_html


def test_cliente_sem_email_avisa_mas_nao_bloqueia(session, obra, monkeypatch) -> None:
    obra_cliente = session.get(Cliente, obra.cliente_id)
    obra_cliente.email_projeto_producao = ""
    session.commit()
    monkeypatch.setattr(svc, "_pasta_da_obra", lambda *_a, **_k: None)
    monkeypatch.setattr(svc, "_imagem_da_obra", lambda *_a, **_k: "")

    envio = svc.preparar_envio(session, obra.id)

    assert envio.destino == ""
    assert any("não tem email" in aviso for aviso in envio.avisos)
    assert envio.assunto  # o email é preparado na mesma


def test_projeto_pdf_da_pasta_vai_em_anexo(session, obra, tmp_path, monkeypatch) -> None:
    (tmp_path / svc.ANEXO_PROJETO).write_bytes(b"pdf")
    monkeypatch.setattr(svc, "_pasta_da_obra", lambda *_a, **_k: tmp_path)
    monkeypatch.setattr(svc, "_imagem_da_obra", lambda *_a, **_k: "")

    envio = svc.preparar_envio(session, obra.id)

    assert envio.anexos == (str(tmp_path / svc.ANEXO_PROJETO),)
    assert not any("Não encontrei" in aviso for aviso in envio.avisos)


def test_sem_projeto_pdf_avisa_e_segue(session, obra, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(svc, "_pasta_da_obra", lambda *_a, **_k: tmp_path)
    monkeypatch.setattr(svc, "_imagem_da_obra", lambda *_a, **_k: "")

    envio = svc.preparar_envio(session, obra.id)

    assert envio.anexos == ()
    assert any(svc.ANEXO_PROJETO in aviso for aviso in envio.avisos)


def test_registo_so_acontece_no_envio(session, obra, monkeypatch) -> None:
    monkeypatch.setattr(svc, "_pasta_da_obra", lambda *_a, **_k: None)
    monkeypatch.setattr(svc, "_imagem_da_obra", lambda *_a, **_k: "")

    # Preparar não regista nada: o utilizador ainda pode cancelar.
    svc.preparar_envio(session, obra.id)
    assert obra.projeto_cliente_enviado_em is None

    svc.registar_envio(
        session,
        obra.id,
        destino="projetos@jfviva.pt",
        quando=datetime(2026, 7, 31, 15, 42),
    )

    assert obra.projeto_cliente_enviado_em == datetime(2026, 7, 31, 15, 42)
    assert obra.projeto_cliente_email == "projetos@jfviva.pt"


def test_preferencia_e_por_utilizador_e_vem_desligada(session) -> None:
    """Nem todos falam com o cliente: ninguém apanha a janela sem a pedir."""
    from app.services import producao_preparacao_service as prep

    assert prep.obter_email_projeto_ativo(session, 7) is False

    prep.guardar_email_projeto_ativo(session, 7, True)

    assert prep.obter_email_projeto_ativo(session, 7) is True
    # A escolha de um utilizador não mexe com a do outro.
    assert prep.obter_email_projeto_ativo(session, 99) is False


def test_coluna_projeto_cliente_mostra_envelope_e_data() -> None:
    from types import SimpleNamespace

    from app.ui.helpers.colunas_producao import _COLUNAS_POR_KEY

    coluna = _COLUNAS_POR_KEY["projeto_cliente"]

    assert coluna.titulo == "Projeto Cliente"
    assert coluna.valor(SimpleNamespace(projeto_cliente_enviado_em=None)) == ""
    assert (
        coluna.valor(
            SimpleNamespace(projeto_cliente_enviado_em=datetime(2026, 7, 31, 15, 42))
        )
        == "✉ 31-07-2026"
    )


def test_reenviar_avisa_e_atualiza_a_data(session, obra, monkeypatch) -> None:
    monkeypatch.setattr(svc, "_pasta_da_obra", lambda *_a, **_k: None)
    monkeypatch.setattr(svc, "_imagem_da_obra", lambda *_a, **_k: "")
    svc.registar_envio(
        session,
        obra.id,
        destino="projetos@jfviva.pt",
        quando=datetime(2026, 7, 31, 15, 42),
    )

    envio = svc.preparar_envio(session, obra.id)
    assert envio.ja_enviado is True
    assert any("já foi informado" in aviso for aviso in envio.avisos)

    svc.registar_envio(
        session,
        obra.id,
        destino="outro@jfviva.pt",
        quando=datetime(2026, 8, 5, 9, 0),
    )

    assert obra.projeto_cliente_enviado_em == datetime(2026, 8, 5, 9, 0)
    assert obra.projeto_cliente_email == "outro@jfviva.pt"
