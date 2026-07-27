"""Tests for the occurrence report: data, wording and PDF."""

from __future__ import annotations

import pytest

from app.domain.assistente_obra import identificar_pedido, pedido_ocorrencias_todas
from app.domain.ocorrencia_relatorio import (
    ObraRelatorio,
    TicketRelatorio,
    contar_erros_nossos,
    contar_fotos,
    contar_por_resolver,
    contar_tickets,
    linhas_resumo,
    resumo_por_tipo,
    subtitulo_relatorio,
    titulo_relatorio,
)
from app.models import Producao
from app.services.producao_ocorrencias_service import (
    dados_para_relatorio,
    mudar_estado,
    registar_anexo,
    registar_envio,
    registar_ocorrencia,
)
from app.services.relatorio_producao_service import (
    REPORTLAB_DISPONIVEL,
    gerar_ocorrencias_pdf,
)


@pytest.fixture()
def obras(session):
    viva = Producao(
        codigo_processo="26.1134_01_01_JF_VIVA",
        ano="2026",
        num_enc_phc="1134",
        versao_obra="01",
        versao_plano="01",
        estado="Desenho",
        nome_cliente="MÓVEIS J.F. VIVA",
        ref_cliente="2504027",
    )
    antiga = Producao(
        codigo_processo="25.0900_01_01_OUTRA",
        ano="2025",
        num_enc_phc="0900",
        versao_obra="01",
        versao_plano="01",
        estado="Entregue",
        nome_cliente="Outra",
    )
    session.add_all([viva, antiga])
    session.commit()
    return viva, antiga


def _obra_exemplo(**extra) -> ObraRelatorio:
    dados = {
        "codigo": "26.1134_01_01_JF_VIVA",
        "cliente": "MÓVEIS J.F. VIVA",
        "ref_cliente": "2504027",
        "tickets": (
            TicketRelatorio(numero=1, tipo="erro_producao", estado="resolvido"),
            TicketRelatorio(numero=2, tipo="pedido_adicional", estado="aberto"),
            TicketRelatorio(numero=3, tipo="erro_producao", estado="em_curso"),
        ),
    }
    dados.update(extra)
    return ObraRelatorio(**dados)


# ---- domínio -------------------------------------------------------------
def test_a_identificacao_junta_obra_cliente_e_referencia() -> None:
    assert _obra_exemplo().identificacao == (
        "26.1134_01_01_JF_VIVA  ·  MÓVEIS J.F. VIVA  ·  Ref. 2504027"
    )


def test_obra_sem_cliente_nao_deixa_separadores_soltos() -> None:
    obra = _obra_exemplo(cliente="", ref_cliente="")

    assert obra.identificacao == "26.1134_01_01_JF_VIVA"


def test_o_resumo_por_tipo_poe_o_maior_primeiro() -> None:
    assert list(resumo_por_tipo([_obra_exemplo()])) == [
        "erro_producao",
        "pedido_adicional",
    ]


def test_contagens_do_relatorio() -> None:
    obras = [_obra_exemplo()]

    assert contar_tickets(obras) == 3
    assert contar_erros_nossos(obras) == 2  # o pedido adicional não conta
    assert contar_por_resolver(obras) == 2  # aberto + em curso
    assert contar_fotos(obras) == 0


def test_o_resumo_diz_o_que_e_erro_nosso() -> None:
    assert linhas_resumo([_obra_exemplo()]) == [
        ("Erro de produção", "2", "Sim"),
        ("Pedido adicional", "1", "—"),
    ]


def test_o_titulo_nomeia_a_obra_quando_e_so_uma() -> None:
    obras = [_obra_exemplo()]

    assert titulo_relatorio(obras, uma_obra=True) == "Ocorrências — 26.1134_01_01_JF_VIVA"
    assert titulo_relatorio(obras, uma_obra=False) == "Ocorrências"


def test_o_subtitulo_conta_tickets_por_resolver_e_erros() -> None:
    subtitulo = subtitulo_relatorio([_obra_exemplo()], ano="2026", gerado_em="27-07-2026")

    assert "3 ticket(s)" in subtitulo
    assert "2 por resolver" in subtitulo
    assert "2 classificados como erro nosso" in subtitulo
    assert "ano 2026" in subtitulo
    assert "gerado em 27-07-2026" in subtitulo


def test_relatorio_vazio_nao_rebenta() -> None:
    assert contar_tickets([]) == 0
    assert linhas_resumo([]) == []
    assert titulo_relatorio([], uma_obra=True) == "Ocorrências"


# ---- IA Martelo ----------------------------------------------------------
@pytest.mark.parametrize(
    "pergunta",
    [
        "ocorrencias da obra 1134",
        "tickets da obra 1134",
        "relatorio das ocorrencias da obra 1134",
        "problemas da obra 1134",
    ],
)
def test_a_ia_percebe_que_se_quer_a_lista_de_tickets(pergunta: str) -> None:
    pedido = identificar_pedido(pergunta)

    assert pedido is not None
    assert pedido.modo == "ocorrencias"


def test_as_ocorrencias_ganham_ao_pdf_quando_a_pergunta_tem_as_duas_palavras() -> None:
    """«relatório das ocorrências» é a lista de tickets, não o ponto de situação."""
    assert identificar_pedido("pdf das ocorrencias da obra 1134").modo == "ocorrencias"
    assert identificar_pedido("pdf da obra 1134").modo == "pdf"


@pytest.mark.parametrize(
    ("pergunta", "ano"),
    [
        ("todas as ocorrencias de 2026", "2026"),
        ("lista de ocorrencias", ""),
        ("pdf de todas as ocorrencias", ""),
        ("relatorio de ocorrencias 2025", "2025"),
    ],
)
def test_a_ia_percebe_o_pedido_de_toda_a_casa(pergunta: str, ano: str) -> None:
    assert pedido_ocorrencias_todas(pergunta) == ano


@pytest.mark.parametrize(
    "pergunta",
    [
        "ocorrencias da obra 1134",  # aponta a uma obra
        "obras atrasadas",           # pesquisa normal
        "estado da obra 1134",
        "",
    ],
)
def test_o_pedido_de_toda_a_casa_nao_rouba_outras_perguntas(pergunta: str) -> None:
    assert pedido_ocorrencias_todas(pergunta) is None


# ---- dados vindos da base de dados ---------------------------------------
def test_o_relatorio_de_uma_obra_le_se_do_principio_para_o_fim(session, obras) -> None:
    """Na tabela vê-se o mais recente primeiro; no relatório conta-se a história."""
    viva, _ = obras
    registar_ocorrencia(session, producao_id=viva.id, texto="Primeiro")
    registar_ocorrencia(session, producao_id=viva.id, texto="Segundo")

    relatorio = dados_para_relatorio(session, producao_id=viva.id)

    assert len(relatorio) == 1
    assert [t.referencia for t in relatorio[0].tickets] == ["T1", "T2"]
    assert relatorio[0].cliente == "MÓVEIS J.F. VIVA"
    assert relatorio[0].ref_cliente == "2504027"


def test_o_relatorio_traz_envio_resolucao_e_fotos(session, obras, tmp_path) -> None:
    from datetime import datetime

    viva, _ = obras
    ticket = registar_ocorrencia(
        session,
        producao_id=viva.id,
        texto="Falta prateleira",
        custo_estimado="12,50",
    )
    foto = tmp_path / "T0001_01.png"
    foto.write_bytes(b"x")
    registar_anexo(session, ocorrencia_id=ticket.id, caminho=str(foto))
    registar_envio(
        session, ticket.id, para="Pedro Reis", quando=datetime(2026, 7, 27, 12, 26)
    )
    mudar_estado(
        session,
        ticket.id,
        estado="resolvido",
        autor="Paulo",
        quando=datetime(2026, 7, 27, 15, 0),
    )

    linha = dados_para_relatorio(session, producao_id=viva.id)[0].tickets[0]

    assert "Pedro Reis" in linha.envio and "27-07-2026 12:26" in linha.envio
    assert "Paulo" in linha.resolucao
    assert linha.custo == "12.50 €"
    assert linha.fotos == (str(foto),)


def test_foto_que_ja_nao_esta_no_disco_nao_entra(session, obras) -> None:
    viva, _ = obras
    ticket = registar_ocorrencia(session, producao_id=viva.id, texto="Com foto perdida")
    registar_anexo(
        session, ocorrencia_id=ticket.id, caminho="Z:/pasta/que/nao/existe/foto.png"
    )

    linha = dados_para_relatorio(session, producao_id=viva.id)[0].tickets[0]

    assert linha.fotos == ()


def test_o_relatorio_de_todas_agrupa_por_obra_e_filtra_por_ano(session, obras) -> None:
    viva, antiga = obras
    registar_ocorrencia(session, producao_id=viva.id, texto="De 2026")
    registar_ocorrencia(session, producao_id=antiga.id, texto="De 2025")

    todas = dados_para_relatorio(session)
    de_2026 = dados_para_relatorio(session, ano=2026)

    assert len(todas) == 2
    assert [obra.codigo for obra in de_2026] == ["26.1134_01_01_JF_VIVA"]


def test_obra_inexistente_devolve_relatorio_vazio(session) -> None:
    assert dados_para_relatorio(session, producao_id=999999) == []


# ---- PDF -----------------------------------------------------------------
@pytest.mark.skipif(not REPORTLAB_DISPONIVEL, reason="reportlab não instalado")
def test_o_pdf_e_escrito_com_as_fotos(session, obras, tmp_path) -> None:
    viva, _ = obras
    ticket = registar_ocorrencia(
        session, producao_id=viva.id, texto="Orla mal colada", tipo="erro_producao"
    )
    foto = tmp_path / "T0001_01.png"
    foto.write_bytes(_PNG_MINIMO)
    registar_anexo(session, ocorrencia_id=ticket.id, caminho=str(foto))
    relatorio = dados_para_relatorio(session, producao_id=viva.id)

    destino = gerar_ocorrencias_pdf(
        relatorio, caminho=tmp_path / "sub" / "ocorrencias.pdf", subtitulo="teste"
    )

    assert destino.is_file()
    assert destino.stat().st_size > 0


@pytest.mark.skipif(not REPORTLAB_DISPONIVEL, reason="reportlab não instalado")
def test_o_pdf_sobrevive_a_uma_foto_que_desapareceu(tmp_path) -> None:
    """A foto é acessória: o relatório vale mesmo sem ela."""
    obra = _obra_exemplo(
        tickets=(
            TicketRelatorio(
                numero=1,
                assunto="Falta peça",
                texto="Cliente reportou",
                fotos=("Z:/nao/existe.png",),
            ),
        )
    )

    destino = gerar_ocorrencias_pdf([obra], caminho=tmp_path / "x.pdf")

    assert destino.is_file()


@pytest.mark.skipif(not REPORTLAB_DISPONIVEL, reason="reportlab não instalado")
def test_o_pdf_sem_ocorrencias_diz_que_nao_ha(tmp_path) -> None:
    destino = gerar_ocorrencias_pdf([], caminho=tmp_path / "vazio.pdf")

    assert destino.is_file()


#: PNG 1x1 válido, para o reportlab ter mesmo uma imagem que abrir.
_PNG_MINIMO = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
    "0000000c49444154789c63f8ffff3f0005fe02fe0def46b80000000049454e44ae426082"
)
