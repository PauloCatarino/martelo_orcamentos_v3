"""Tests for the per-user saved views of the production list."""

from __future__ import annotations

from app.ui.helpers.vistas_producao import (
    MAX_VISTAS,
    VistaProducao,
    carregar_vistas,
    CHAVE_VISTAS,
    desserializar_vistas,
    guardar_vistas,
    remover_vista,
    serializar_vistas,
    substituir_vista,
)


def test_a_chave_ja_nao_leva_o_utilizador_colado() -> None:
    # O utilizador passou a viver na sua propria coluna das `user_prefs`:
    # a chave e' so' o nome da preferencia.
    assert CHAVE_VISTAS == "producao_vistas"
    assert ":" not in CHAVE_VISTAS


def test_ida_e_volta_pela_serializacao() -> None:
    vistas = [
        VistaProducao("Atrasadas do Paulo", responsavel="Paulo", so_atrasadas=True),
        VistaProducao("Cozinhas", texto="cozinha", estado="Producao"),
    ]

    resultado = desserializar_vistas(serializar_vistas(vistas))

    assert resultado == vistas


def test_desserializar_ignora_lixo() -> None:
    assert desserializar_vistas(None) == []
    assert desserializar_vistas("") == []
    assert desserializar_vistas("{isto não é json}") == []
    assert desserializar_vistas('{"nome": "x"}') == []  # não é lista
    assert desserializar_vistas('[{"nome": "   "}]') == []  # nome vazio


def test_substituir_vista_troca_pelo_nome_sem_duplicar() -> None:
    vistas = [VistaProducao("Atrasadas", responsavel="Paulo")]

    resultado = substituir_vista(
        vistas, VistaProducao("  atrasadas  ", responsavel="Ana")
    )

    assert len(resultado) == 1
    assert resultado[0].nome == "atrasadas"
    assert resultado[0].responsavel == "Ana"


def test_substituir_vista_respeita_o_maximo() -> None:
    vistas = [VistaProducao(f"V{i}") for i in range(MAX_VISTAS)]

    resultado = substituir_vista(vistas, VistaProducao("Nova"))

    assert len(resultado) == MAX_VISTAS


def test_remover_vista_ignora_maiusculas() -> None:
    vistas = [VistaProducao("Atrasadas"), VistaProducao("Cozinhas")]

    assert [v.nome for v in remover_vista(vistas, "ATRASADAS")] == ["Cozinhas"]
    assert len(remover_vista(vistas, "não existe")) == 2


def test_guardar_e_carregar_por_utilizador(session) -> None:
    do_paulo = [VistaProducao("Minhas", responsavel="Paulo")]
    guardar_vistas(session, 1, do_paulo)
    guardar_vistas(session, 2, [VistaProducao("Da Ana", responsavel="Ana")])

    assert carregar_vistas(session, 1) == do_paulo
    assert [v.nome for v in carregar_vistas(session, 2)] == ["Da Ana"]
    assert carregar_vistas(session, 3) == []
