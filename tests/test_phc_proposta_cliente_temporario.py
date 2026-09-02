"""Proposta no PHC para um cliente TEMPORÁRIO do Martelo.

O cliente temporário não existe no PHC: a proposta vai no cliente genérico
``063`` («CONSUMIDOR FINAL») e o nome verdadeiro é escrito na janela que o PHC
abre logo a seguir ao número. Daí para a frente os passos são os mesmos.

A execução com pywinauto só corre com o PHC aberto — estes testes cobrem o
*plano* de teclas (determinístico), a escolha da proposta na base de dados e a
verificação do que ficou gravado.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.services.phc_automation_service import (
    CLIENTE_GENERICO_PHC,
    PassoTeclas,
    PassoTexto,
    construir_plano,
    formatar_num_cliente_phc,
)
from app.services.phc_propostas_service import (
    PropostaPhc,
    build_query_propostas_do_ano,
    escolher_proposta_criada,
    verificar_proposta_gravada,
)


def _textos(plano) -> list[str]:
    return [passo.texto for passo in plano if isinstance(passo, PassoTexto)]


def _teclas(plano) -> list[str]:
    return [passo.keys for passo in plano if isinstance(passo, PassoTeclas)]


# ---- o plano de teclas -----------------------------------------------------


def test_cliente_generico_e_o_063() -> None:
    assert CLIENTE_GENERICO_PHC == "063"
    # É escrito no PHC como os outros números de cliente: 4 dígitos.
    assert formatar_num_cliente_phc(CLIENTE_GENERICO_PHC) == "0063"


def test_plano_escreve_o_nome_entre_o_cliente_e_a_ref() -> None:
    plano = construir_plano(
        num_cliente_phc=CLIENTE_GENERICO_PHC,
        ref_cliente="2504035",
        designacao="Obra: 2504035",
        nome_cliente="MOVEIS TESTE LDA",
    )

    assert _textos(plano) == [
        "0063",
        "MOVEIS TESTE LDA",
        "2504035",
        "Obra: 2504035",
    ]


def test_plano_confirma_o_nome_com_enter_antes_dos_tabs() -> None:
    plano = construir_plano(
        num_cliente_phc=CLIENTE_GENERICO_PHC,
        ref_cliente="2504035",
        designacao="Obra: 2504035",
        nome_cliente="MOVEIS TESTE LDA",
    )

    # Dois ENTER: um confirma o nº de cliente, o outro fecha a janela do Nome.
    assert _teclas(plano) == ["%n", "{ENTER}", "{ENTER}", "{TAB 2}", "{TAB 8}"]


def test_plano_espera_a_janela_do_nome_abrir_e_fechar() -> None:
    from app.services.phc_automation_service import PassoEsperarPronto

    plano = construir_plano(
        num_cliente_phc=CLIENTE_GENERICO_PHC,
        ref_cliente=None,
        designacao="Obra:",
        nome_cliente="MOVEIS TESTE LDA",
    )
    descricoes = [
        passo.descricao for passo in plano if isinstance(passo, PassoEsperarPronto)
    ]

    assert "Confirmar que a janela do Nome abriu" in descricoes
    assert "Confirmar que voltou à proposta" in descricoes


def test_sem_nome_o_plano_fica_exatamente_como_estava() -> None:
    """O caminho dos clientes do PHC não pode mudar nada."""
    com_nome_vazio = construir_plano(
        num_cliente_phc="35",
        ref_cliente="2504035",
        designacao="Obra: 2504035",
        nome_cliente="",
    )
    sem_parametro = construir_plano(
        num_cliente_phc="35",
        ref_cliente="2504035",
        designacao="Obra: 2504035",
    )

    assert com_nome_vazio == sem_parametro
    assert _teclas(sem_parametro) == ["%n", "{ENTER}", "{TAB 2}", "{TAB 8}"]
    assert _textos(sem_parametro) == ["0035", "2504035", "Obra: 2504035"]


def test_nome_com_acentos_vai_escapado_para_o_send_keys() -> None:
    from app.services.phc_automation_service import _escape_literal

    plano = construir_plano(
        num_cliente_phc=CLIENTE_GENERICO_PHC,
        ref_cliente=None,
        designacao="Obra:",
        nome_cliente="MÓVEIS J.F. VIVA (LDA)",
    )
    nome = _textos(plano)[1]

    # Os parênteses são comandos do send_keys e têm de ser escapados.
    assert _escape_literal(nome) == "MÓVEIS J.F. VIVA {(}LDA{)}"


# ---- encontrar a proposta na base de dados do PHC --------------------------


def _proposta(numero, *, nome=None, ref=None):
    return PropostaPhc(
        numero=numero,
        ano=2026,
        num_cliente="63",
        ref_cliente=ref,
        data="03-09-2026",
        nome=nome,
    )


def test_a_consulta_traz_o_nome_do_destinatario() -> None:
    query = build_query_propostas_do_ano(ano=2026)

    assert "BO.NOME" in query
    assert "AS Nome" in query


def test_entre_propostas_do_generico_escolhe_a_do_nome_certo() -> None:
    """Todas ficam no cliente 63: só o nome as distingue."""
    candidatas = [
        _proposta(880, nome="OUTRO CLIENTE TEMPORARIO"),
        _proposta(881, nome="MOVEIS TESTE LDA"),
    ]

    escolhida = escolher_proposta_criada(
        candidatas, num_cliente="063", nome_cliente="MOVEIS TESTE LDA"
    )

    assert escolhida.numero == 881


def test_sem_nome_igual_ainda_devolve_a_primeira_criada() -> None:
    """O nome é preferência, não requisito: o PHC pode cortá-lo."""
    candidatas = [
        _proposta(881, nome="MOVEIS TESTE LD"),  # cortado pelo PHC
        _proposta(882, nome="MOVEIS TESTE LD"),
    ]

    escolhida = escolher_proposta_criada(
        candidatas, num_cliente="063", nome_cliente="MOVEIS TESTE LDA"
    )

    assert escolhida.numero == 881


def test_proposta_de_outro_cliente_continua_a_ser_descartada() -> None:
    candidatas = [
        PropostaPhc(
            numero=881,
            ano=2026,
            num_cliente="35",
            ref_cliente=None,
            data=None,
            nome="MOVEIS TESTE LDA",
        )
    ]

    assert (
        escolher_proposta_criada(
            candidatas, num_cliente="063", nome_cliente="MOVEIS TESTE LDA"
        )
        is None
    )


# ---- confirmar o que ficou gravado -----------------------------------------


def test_avisa_quando_o_nome_ficou_consumidor_final() -> None:
    """A janela do Nome não apareceu: a proposta fica sem se saber de quem é."""
    avisos = verificar_proposta_gravada(
        _proposta(881, nome="CONSUMIDOR FINAL", ref="2504035"),
        ["Obra: 2504035"],
        ref_cliente="2504035",
        designacao="Obra: 2504035",
        nome_cliente="MOVEIS TESTE LDA",
    )

    assert len(avisos) == 1
    assert "CONSUMIDOR FINAL" in avisos[0]
    assert "MOVEIS TESTE LDA" in avisos[0]


def test_nome_certo_nao_gera_aviso() -> None:
    avisos = verificar_proposta_gravada(
        _proposta(881, nome="MOVEIS TESTE LDA", ref="2504035"),
        ["Obra: 2504035"],
        ref_cliente="2504035",
        designacao="Obra: 2504035",
        nome_cliente="MOVEIS TESTE LDA",
    )

    assert avisos == []


def test_sem_nome_pedido_o_nome_gravado_nao_e_verificado() -> None:
    """Clientes do PHC: o nome vem do PHC e não é da nossa conta."""
    avisos = verificar_proposta_gravada(
        _proposta(881, nome="QUALQUER COISA", ref="2504035"),
        ["Obra: 2504035"],
        ref_cliente="2504035",
        designacao="Obra: 2504035",
    )

    assert avisos == []
