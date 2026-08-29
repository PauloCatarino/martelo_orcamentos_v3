"""O limite do link do Teams é do URL codificado, não do texto escrito.

Um ticket com 1500 caracteres de português — com acentos e quebras de linha —
dá um URL de vários milhares de caracteres depois de codificado. O Windows
corta-o, e o que se perde é precisamente o `&message=`: o Teams abre a conversa
com a caixa **vazia** e ninguém percebe porquê.
"""

from __future__ import annotations

from urllib.parse import quote

from app.services.teams_service import MAX_URL, link_chat_teams, texto_que_cabe

EMAIL = "producao@lancaencanto.pt"


def test_mensagem_curta_vai_inteira() -> None:
    texto = "Falta os pés axilo H75."
    url = link_chat_teams(EMAIL, texto)
    assert quote(texto, safe="") in url


def test_ticket_enorme_nao_estoira_o_limite_do_windows() -> None:
    # Português a sério: acentos e mudanças de linha, que é onde a codificação
    # multiplica o tamanho.
    texto = ("Descrição da ocorrência com acentuação — çãõé.\n" * 200)
    url = link_chat_teams(EMAIL, texto)
    assert len(url) <= MAX_URL


def test_mesmo_cortado_a_conversa_abre_com_texto() -> None:
    texto = ("Peças em falta na embalagem.\n" * 300)
    url = link_chat_teams(EMAIL, texto)
    assert "&message=" in url, "sem mensagem o Teams abria a caixa vazia"
    assert "users=" in url


def test_texto_que_cabe_devolve_o_maior_pedaco() -> None:
    texto = "a" * 5000
    cabe = texto_que_cabe(texto, ja_ocupado=100, limite=200)
    # Cabe alguma coisa, e o que cabe está marcado como cortado.
    assert cabe
    assert cabe.endswith("…")
    assert 100 + len(quote(cabe, safe="")) <= 200


def test_sem_espaco_nenhum_devolve_vazio() -> None:
    assert texto_que_cabe("qualquer coisa", ja_ocupado=500, limite=100) == ""


def test_texto_vazio_continua_vazio() -> None:
    assert texto_que_cabe("", ja_ocupado=0) == ""
    assert texto_que_cabe("   ", ja_ocupado=0).strip() == ""


def test_varios_destinatarios_contam_para_o_limite() -> None:
    """Com dez pessoas o URL já começa grande — a mensagem tem de encolher."""
    emails = [f"pessoa{i}@lancaencanto.pt" for i in range(10)]
    url = link_chat_teams(emails, "texto longo. " * 500)
    assert len(url) <= MAX_URL
