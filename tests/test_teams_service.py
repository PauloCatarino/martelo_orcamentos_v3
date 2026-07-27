"""Tests for handing a ticket to someone on Microsoft Teams."""

from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from app.services.teams_service import (
    MAX_MENSAGEM,
    caminhos_de_anexos,
    encurtar,
    link_chat_teams,
    montar_texto_ticket,
)


def _obra(**extra):
    dados = {
        "codigo_processo": "26.1254_01_01_LINHAS_DIREITAS",
        "nome_cliente": "Sá Machado & Filhos",
        "ref_cliente": "2504027",
    }
    dados.update(extra)
    return SimpleNamespace(**dados)


def _ticket(**extra):
    dados = {
        "numero": 3,
        "tipo": "pecas_em_falta",
        "gravidade": "media",
        "assunto": "Falta prateleira do quarto 2",
        "texto": "Cliente enviou foto da etiqueta. Voltar a produzir 1 prateleira.",
        "autor": "Paulo Catarino",
    }
    dados.update(extra)
    return SimpleNamespace(**dados)


def test_o_texto_comeca_pela_referencia_do_ticket_e_pela_obra() -> None:
    texto = montar_texto_ticket(_obra(), _ticket())

    primeira_linha = texto.splitlines()[0]
    assert primeira_linha.startswith("[T3] Peças em falta")
    assert "26.1254_01_01_LINHAS_DIREITAS" in primeira_linha


def test_o_texto_leva_cliente_assunto_e_quem_escreveu() -> None:
    texto = montar_texto_ticket(_obra(), _ticket())

    assert "Cliente: Sá Machado & Filhos" in texto
    assert "Ref.: 2504027" in texto
    assert "Assunto: Falta prateleira do quarto 2" in texto
    assert texto.rstrip().endswith("— Paulo Catarino")


def test_gravidade_alta_e_avisada_no_texto() -> None:
    normal = montar_texto_ticket(_obra(), _ticket())
    urgente = montar_texto_ticket(_obra(), _ticket(gravidade="alta"))

    assert "Gravidade: ALTA" not in normal
    assert "Gravidade: ALTA" in urgente


def test_o_texto_diz_quantas_fotos_seguem() -> None:
    anexos = [SimpleNamespace(caminho="C:/obra/T0003_01.png")]

    assert "(1 foto em anexo)" in montar_texto_ticket(_obra(), _ticket(), anexos)
    assert "(2 fotos em anexo)" in montar_texto_ticket(
        _obra(), _ticket(), anexos * 2
    )


def test_obra_sem_cliente_nao_deixa_linha_a_meio() -> None:
    texto = montar_texto_ticket(
        _obra(nome_cliente=None, ref_cliente=None), _ticket()
    )

    assert "Cliente:" not in texto
    assert "Ref.:" not in texto


def test_o_link_abre_a_conversa_com_a_mensagem_escrita() -> None:
    url = link_chat_teams("elsa.belo@lancaencanto.pt", "Bom dia")

    partes = urlparse(url)
    consulta = parse_qs(partes.query)
    assert partes.netloc == "teams.microsoft.com"
    assert partes.path == "/l/chat/0/0"
    assert consulta["users"] == ["elsa.belo@lancaencanto.pt"]
    assert consulta["message"] == ["Bom dia"]


def test_sem_endereco_nao_ha_link() -> None:
    assert link_chat_teams(None, "texto") == ""
    assert link_chat_teams("  ", "texto") == ""


def test_mensagem_com_acentos_e_quebras_sobrevive_ao_link() -> None:
    original = "Ref. 2504027\nOrla não bate certo — repetir"

    consulta = parse_qs(urlparse(link_chat_teams("a@b.pt", original)).query)

    assert consulta["message"] == [original]


def test_mensagem_enorme_e_cortada_para_o_link_aguentar() -> None:
    cortada = encurtar("x" * (MAX_MENSAGEM + 500))

    assert len(cortada) == MAX_MENSAGEM
    assert cortada.endswith("…")


def test_mensagem_curta_fica_intacta() -> None:
    assert encurtar("curta") == "curta"


def test_so_vao_as_fotos_que_ainda_estao_no_disco(tmp_path) -> None:
    existente = tmp_path / "T0003_01.png"
    existente.write_bytes(b"x")
    anexos = [
        SimpleNamespace(caminho=str(existente)),
        SimpleNamespace(caminho=str(tmp_path / "apagada.png")),
    ]

    assert caminhos_de_anexos(anexos) == [str(existente)]
