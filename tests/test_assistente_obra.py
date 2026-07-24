"""Testes dos pedidos sobre uma obra (identificação + texto)."""

from __future__ import annotations

from app.domain.assistente_obra import (
    DossierObra,
    PedidoObra,
    assunto_email,
    corpo_email_html,
    identificar_pedido,
    resumo_texto,
    saudacao_por_hora,
)


def test_relatorio_da_obra_e_pedido_pdf() -> None:
    assert identificar_pedido("faz um relatório da obra 1134") == PedidoObra(
        numero="1134", modo="pdf"
    )


def test_estado_da_obra_e_pedido_texto() -> None:
    assert identificar_pedido("qual o ponto de situação da obra 1134") == PedidoObra(
        numero="1134", modo="texto"
    )


def test_email_da_obra_e_pedido_email() -> None:
    assert identificar_pedido("prepara um email do estado da obra 0800") == PedidoObra(
        numero="0800", modo="email"
    )


def test_rotulo_obra_chega_sem_gatilho() -> None:
    # «obra 1134» sozinho (rótulo antes do número) conta como pedido de obra.
    assert identificar_pedido("obra 1134") == PedidoObra(numero="1134", modo="texto")


def test_pesquisa_normal_nao_e_pedido_de_obra() -> None:
    assert identificar_pedido("obras atrasadas") is None
    assert identificar_pedido("roupeiros de correr") is None


def test_numero_isolado_sem_contexto_nao_conta() -> None:
    # Um número sem gatilho nem rótulo não é um pedido de obra.
    assert identificar_pedido("1134 e tal") is None


def test_resumo_texto_com_fases() -> None:
    dossier = DossierObra(
        codigo="26.1134_01_01_JF_VIVA",
        enc="1134",
        cliente="MÓVEIS J.F. VIVA",
        responsavel="Paulo",
        estado_local="Producao",
        data_inicio="25-06-2026",
        data_entrega="10-08-2026",
        descricao_producao="1 CLOSET 'U' COM TETOS SUTADOS",
        fases=(("Corte", 100.0, True), ("Orlagem", 60.0, False), ("CNC", 0.0, False)),
        estado_global="🔄 33.3% (1/3)",
        encontrado_streamlit=True,
    )

    texto = resumo_texto(dossier)

    assert "26.1134_01_01_JF_VIVA" in texto
    assert "MÓVEIS J.F. VIVA" in texto
    assert "Entrega prevista: 10-08-2026" in texto
    assert "Corte 100%" in texto
    assert "Orlagem 60%" in texto
    assert "🔄 33.3% (1/3)" in texto


def test_resumo_texto_sem_streamlit_avisa() -> None:
    dossier = DossierObra(codigo="26.0800_01", cliente="X", encontrado_streamlit=False)

    texto = resumo_texto(dossier)

    assert "indisponível" in texto


def test_saudacao_por_hora() -> None:
    assert saudacao_por_hora(9) == "Bom dia"
    assert saudacao_por_hora(15) == "Boa tarde"
    assert saudacao_por_hora(22) == "Boa noite"
    assert saudacao_por_hora(3) == "Boa noite"


def test_assunto_email_junta_ref_obra_localizacao() -> None:
    dossier = DossierObra(
        codigo="26.1134_01_01_JF_VIVA",
        cliente="MÓVEIS J.F. VIVA",
        ref_cliente="2507018",
        localizacao="Lisboa",
    )

    # Obra vazia não entra; Ref. e Localização entram.
    assert assunto_email(dossier) == (
        "Ponto de situação — 26.1134_01_01_JF_VIVA (MÓVEIS J.F. VIVA) "
        "| 2507018 | Lisboa"
    )


def test_corpo_email_html_saudacao_ref_e_utilizador() -> None:
    dossier = DossierObra(
        codigo="26.1134_01_01_JF_VIVA",
        cliente="MÓVEIS J.F. VIVA",
        ref_cliente="2507018",
        estado_local="Producao",
        data_entrega="10-08-2026",
        fases=(("Corte", 100.0, True),),
        encontrado_streamlit=True,
    )

    corpo = corpo_email_html(dossier, saudacao="Bom dia", utilizador="Paulo")

    assert corpo.startswith("<p>Bom dia,</p>")
    assert "font-size:14pt" in corpo  # Ref. Cliente em destaque
    assert "Ref. Cliente: 2507018" in corpo
    assert "Estado: Producao" in corpo
    assert "Com os melhores cumprimentos,<br>Paulo</p>" in corpo
