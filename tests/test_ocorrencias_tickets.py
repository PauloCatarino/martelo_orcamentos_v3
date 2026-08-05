"""Tests for the ticket side of the obra's occurrence log."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domain import ocorrencia_tipos as tipos
from app.models import Producao, User
from app.services.producao_ocorrencias_service import (
    atualizar_ocorrencia,
    contagem_anexos,
    contar_abertas,
    eliminar_anexo,
    listar_anexos,
    listar_ocorrencias,
    listar_todas,
    mudar_estado,
    proximo_numero,
    registar_anexo,
    registar_envio,
    registar_ocorrencia,
    resumo_por_responsavel,
    resumo_por_tipo,
)
from app.ui.helpers.anexos_ocorrencia import guardar_anexos


@pytest.fixture()
def obras(session):
    viva = Producao(
        codigo_processo="26.1134_01_01_JF_VIVA",
        ano="2026",
        num_enc_phc="1134",
        versao_obra="01",
        versao_plano="01",
        estado="Desenho",
        nome_cliente="JF Viva",
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


@pytest.fixture()
def paulo(session):
    utilizador = User(
        username="paulo",
        nome="Paulo Catarino",
        email="paulo@exemplo.pt",
        password_hash="x",
        role="user",
    )
    session.add(utilizador)
    session.commit()
    return utilizador


def test_numeracao_e_por_obra_e_nao_repete(session, obras) -> None:
    viva, antiga = obras

    primeiro = registar_ocorrencia(session, producao_id=viva.id, texto="Falta prateleira")
    segundo = registar_ocorrencia(session, producao_id=viva.id, texto="Falta puxador")
    de_outra_obra = registar_ocorrencia(session, producao_id=antiga.id, texto="Risco na porta")

    assert (primeiro.numero, segundo.numero) == (1, 2)
    assert de_outra_obra.numero == 1
    assert proximo_numero(session, viva.id) == 3


def test_assunto_sai_da_primeira_linha_quando_nao_e_escrito(session, obras) -> None:
    viva, _ = obras

    ticket = registar_ocorrencia(
        session,
        producao_id=viva.id,
        texto="Falta a prateleira do quarto 2\nCombinado levar na próxima entrega.",
    )

    assert ticket.assunto == "Falta a prateleira do quarto 2"


def test_classificacao_desconhecida_cai_no_valor_seguro(session, obras) -> None:
    viva, _ = obras

    ticket = registar_ocorrencia(
        session, producao_id=viva.id, texto="Qualquer coisa", tipo="inventado"
    )

    assert ticket.tipo == "outro"
    assert ticket.estado == "aberto"
    assert ticket.gravidade == "media"


def test_filtros_da_lista_da_obra(session, obras) -> None:
    viva, _ = obras
    registar_ocorrencia(
        session,
        producao_id=viva.id,
        texto="Orla mal colada",
        tipo="erro_producao",
        responsavel="Elsa Belo",
    )
    registar_ocorrencia(
        session,
        producao_id=viva.id,
        texto="Cliente quer mais 5 suportes",
        tipo="pedido_adicional",
        responsavel="Dulce Faria",
    )

    assert len(listar_ocorrencias(session, viva.id, tipo="erro_producao")) == 1
    assert len(listar_ocorrencias(session, viva.id, responsavel="dulce")) == 1
    assert len(listar_ocorrencias(session, viva.id, texto="suportes")) == 1
    assert len(listar_ocorrencias(session, viva.id, texto="nao existe")) == 0


def test_apenas_abertos_exclui_resolvidos_e_anulados(session, obras) -> None:
    viva, _ = obras
    aberto = registar_ocorrencia(session, producao_id=viva.id, texto="Por resolver")
    fechado = registar_ocorrencia(session, producao_id=viva.id, texto="Já feito")
    mudar_estado(session, fechado.id, estado="resolvido", autor="Paulo")

    abertos = listar_ocorrencias(session, viva.id, apenas_abertos=True)

    assert [t.id for t in abertos] == [aberto.id]
    assert contar_abertas(session, viva.id) == 1


def test_resolver_guarda_quem_fechou_e_reabrir_limpa(session, obras) -> None:
    viva, _ = obras
    ticket = registar_ocorrencia(session, producao_id=viva.id, texto="Falta ferragem")

    mudar_estado(
        session,
        ticket.id,
        estado="resolvido",
        autor="Paulo Catarino",
        quando=datetime(2026, 7, 27, 15, 30),
    )
    assert ticket.resolvido_por == "Paulo Catarino"
    assert ticket.resolvido_em == datetime(2026, 7, 27, 15, 30)

    mudar_estado(session, ticket.id, estado="em_curso")
    assert ticket.resolvido_em is None
    assert ticket.resolvido_por is None


def test_so_o_autor_altera_o_ticket(session, obras, paulo) -> None:
    viva, _ = obras
    ticket = registar_ocorrencia(
        session, producao_id=viva.id, texto="Meu registo", user_id=paulo.id
    )

    with pytest.raises(ValueError):
        atualizar_ocorrencia(session, ticket.id, user_id=paulo.id + 99, texto="Alterado")

    atualizar_ocorrencia(
        session, ticket.id, user_id=paulo.id, tipo="erro_medidas", custo_estimado="12,50"
    )
    assert ticket.tipo == "erro_medidas"
    assert ticket.custo_estimado == Decimal("12.50")


def test_administrador_altera_o_de_qualquer_um(session, obras, paulo) -> None:
    viva, _ = obras
    ticket = registar_ocorrencia(
        session, producao_id=viva.id, texto="Registo do Paulo", user_id=paulo.id
    )

    atualizar_ocorrencia(
        session, ticket.id, user_id=None, is_admin=True, assunto="Corrigido"
    )

    assert ticket.assunto == "Corrigido"


def test_qualquer_pessoa_pode_fechar_o_ticket_de_outra(session, obras, paulo) -> None:
    """Quem resolve o problema raramente é quem o escreveu."""
    viva, _ = obras
    ticket = registar_ocorrencia(
        session, producao_id=viva.id, texto="Falta peça", user_id=paulo.id
    )

    mudar_estado(session, ticket.id, estado="resolvido", autor="Adriano Silva")

    assert ticket.estado == "resolvido"
    assert ticket.resolvido_por == "Adriano Silva"


def test_campo_desconhecido_no_update_e_recusado(session, obras, paulo) -> None:
    viva, _ = obras
    ticket = registar_ocorrencia(
        session, producao_id=viva.id, texto="Texto", user_id=paulo.id
    )

    with pytest.raises(ValueError, match="Campos desconhecidos"):
        atualizar_ocorrencia(session, ticket.id, user_id=paulo.id, inventado="x")


def test_envio_fica_registado_no_ticket(session, obras) -> None:
    viva, _ = obras
    ticket = registar_ocorrencia(session, producao_id=viva.id, texto="Falta peça")

    registar_envio(
        session,
        ticket.id,
        para="Adriano Silva",
        via="teams",
        quando=datetime(2026, 7, 27, 9, 5),
    )

    assert ticket.enviado_para == "Adriano Silva"
    assert ticket.enviado_via == "teams"
    assert ticket.enviado_em == datetime(2026, 7, 27, 9, 5)


def test_anexos_sao_ordenados_e_contados(session, obras) -> None:
    viva, _ = obras
    ticket = registar_ocorrencia(session, producao_id=viva.id, texto="Com fotos")

    primeiro = registar_anexo(
        session, ocorrencia_id=ticket.id, caminho="C:/obra/T0001_01.png"
    )
    segundo = registar_anexo(
        session, ocorrencia_id=ticket.id, caminho="C:/obra/T0001_02.png"
    )

    assert [a.ordem for a in (primeiro, segundo)] == [1, 2]
    assert [a.id for a in listar_anexos(session, ticket.id)] == [primeiro.id, segundo.id]
    assert contagem_anexos(session, [ticket.id]) == {ticket.id: 2}

    eliminar_anexo(session, primeiro.id)
    assert contagem_anexos(session, [ticket.id]) == {ticket.id: 1}


def test_anexo_sem_caminho_e_recusado(session, obras) -> None:
    viva, _ = obras
    ticket = registar_ocorrencia(session, producao_id=viva.id, texto="Sem foto")

    with pytest.raises(ValueError):
        registar_anexo(session, ocorrencia_id=ticket.id, caminho="   ")


def test_lista_global_junta_obra_e_ticket_e_filtra_por_ano(session, obras) -> None:
    viva, antiga = obras
    registar_ocorrencia(session, producao_id=viva.id, texto="De 2026")
    registar_ocorrencia(session, producao_id=antiga.id, texto="De 2025")

    todas = listar_todas(session)
    assert len(todas) == 2
    assert {obra.codigo_processo for obra, _ in todas} == {
        "26.1134_01_01_JF_VIVA",
        "25.0900_01_01_OUTRA",
    }

    de_2026 = listar_todas(session, ano=2026)
    assert [t.texto for _, t in de_2026] == ["De 2026"]
    # O ano da obra é texto na base de dados: aceita as duas formas.
    assert len(listar_todas(session, ano="2026")) == 1


def test_resumos_para_a_avaliacao_do_ano(session, obras) -> None:
    viva, antiga = obras
    registar_ocorrencia(
        session,
        producao_id=viva.id,
        texto="Orla mal colada",
        tipo="erro_producao",
        responsavel="Elsa Belo",
    )
    registar_ocorrencia(
        session,
        producao_id=viva.id,
        texto="Medida errada",
        tipo="erro_medidas",
        responsavel="Elsa Belo",
    )
    registar_ocorrencia(
        session,
        producao_id=antiga.id,
        texto="Pedido extra",
        tipo="pedido_adicional",
        responsavel="Dulce Faria",
    )

    assert resumo_por_tipo(session, ano=2026) == {"erro_producao": 1, "erro_medidas": 1}
    assert resumo_por_responsavel(session, ano=2026) == {"Elsa Belo": 2}
    assert resumo_por_tipo(session)["pedido_adicional"] == 1


def test_a_foto_vai_para_a_pasta_da_obra_e_fica_ligada_ao_ticket(
    session, obras, tmp_path
) -> None:
    viva, _ = obras
    ticket = registar_ocorrencia(session, producao_id=viva.id, texto="Com foto")
    origem = tmp_path / "etiqueta.jpg"
    origem.write_bytes(b"foto")

    avisos = guardar_anexos(
        session,
        ocorrencia=ticket,
        pasta_obra=str(tmp_path / "obra"),
        pendentes=[SimpleNamespace(caminho=str(origem), nome="etiqueta.jpg", imagem=None)],
    )

    assert avisos == []
    gravados = listar_anexos(session, ticket.id)
    assert len(gravados) == 1
    assert Path(gravados[0].caminho).name == "T0001_01.jpg"
    assert Path(gravados[0].caminho).parent.name == "T0001"
    assert Path(gravados[0].caminho).read_bytes() == b"foto"


def test_obra_sem_pasta_avisa_mas_nao_perde_o_ticket(session, obras, tmp_path) -> None:
    """A rede em baixo não pode impedir que o ticket fique escrito."""
    viva, _ = obras
    ticket = registar_ocorrencia(session, producao_id=viva.id, texto="Com foto")
    origem = tmp_path / "foto.png"
    origem.write_bytes(b"x")

    avisos = guardar_anexos(
        session,
        ocorrencia=ticket,
        pasta_obra=None,
        pendentes=[SimpleNamespace(caminho=str(origem), nome="foto.png", imagem=None)],
    )

    assert avisos and "pasta no servidor" in avisos[0]
    assert listar_anexos(session, ticket.id) == []
    assert ticket.texto == "Com foto"


def test_familia_do_tipo_separa_erro_nosso_de_pedido(session) -> None:
    assert tipos.e_erro_nosso("erro_producao") is True
    assert tipos.e_erro_nosso("pedido_adicional") is False
    assert tipos.e_erro_nosso("pecas_danificadas_cliente") is False


# ---- tipo "Informativo" -----------------------------------------------------
def test_tipo_informativo_existe_e_e_neutro() -> None:
    """Nem tudo o que se regista numa obra e' um problema.

    Pedido do Paulo (2026-08-05): muitas vezes o ticket serve so' para dizer
    alguma coisa a um colega pelo Teams ou para o cliente ficar a saber.
    """
    assert tipos.normalizar_tipo("informativo") == "informativo"
    assert tipos.rotulo_tipo("informativo") == "Informativo"
    # Nao pode contar como erro nosso na analise do fim do ano.
    assert tipos.familia_tipo("informativo") == "neutro"
    assert not tipos.e_erro_nosso("informativo")


def test_informativo_aparece_na_lista_de_tipos() -> None:
    rotulos = [classificacao.rotulo for classificacao in tipos.TIPOS]

    assert "Informativo" in rotulos
    # Junto dos outros neutros, antes dos erros.
    assert rotulos.index("Informativo") < rotulos.index("Erro de produção")


def test_informativo_conta_no_resumo_por_tipo(session, obras) -> None:
    viva, _ = obras
    registar_ocorrencia(
        session,
        producao_id=viva.id,
        assunto="Cliente avisado da data de montagem",
        texto="Montagem marcada para 12-08; o cliente ficou a saber.",
        tipo="informativo",
    )

    resumo = resumo_por_tipo(session)

    assert resumo.get("informativo") == 1
