"""Testes do piloto IA para roupeiros de abrir."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.domain.roupeiro_ia import (
    AnaliseRoupeiro,
    MedidaReconhecida,
    ModuloElegivel,
    PropostaComposicao,
    PropostaModulo,
    medida_para_mm,
)
from app.models import (
    DefModulo,
    IaOrcamentoAnalise,
    IaOrcamentoProposta,
    IaOrcamentoPropostaModulo,
    OrcamentoItem,
    OrcamentoItemModulo,
)
from app.services.def_modulo_service import CriarDefModuloData, DefModuloService
from app.services.ia_orcamento_service import IaOrcamentoService
from app.services.roupeiro_combinador_service import RoupeiroCombinadorService
from app.services.roupeiro_vision_service import (
    LIMITE_PDF_BYTES,
    LocalVisionProvider,
    OpenAIVisionProvider,
    interpretar_analise,
)
from app.domain.roupeiro_ia import PedidoAnaliseRoupeiro


def _modulo(
    id: int,
    preferida: str,
    *,
    minimo: str | None = None,
    maximo: str | None = None,
    posicao: str = "QUALQUER",
    caracteristicas: dict[str, Decimal] | None = None,
) -> ModuloElegivel:
    pref = Decimal(preferida)
    return ModuloElegivel(
        id=id,
        codigo=f"M{id}",
        nome=f"Módulo {id}",
        largura_min_mm=Decimal(minimo or preferida),
        largura_preferida_mm=pref,
        largura_max_mm=Decimal(maximo or preferida),
        posicao=posicao,
        caracteristicas=caracteristicas or {},
    )


def test_converte_medidas_com_virgula_decimal() -> None:
    assert medida_para_mm("62,5", "cm") == Decimal("625.000")
    assert medida_para_mm("2.4", "m") == Decimal("2400.000")
    assert medida_para_mm(800, "mm") == Decimal("800.000")


def test_resposta_invalida_e_unidade_desconhecida_sao_recusadas() -> None:
    with pytest.raises(ValueError, match="falta o campo largura"):
        interpretar_analise({"altura": {}, "profundidade": {}, "caracteristicas": {}})
    with pytest.raises(ValueError, match="Unidade"):
        medida_para_mm("12", "polegadas")


def test_interpretacao_preserva_baixa_confianca_para_confirmacao_humana() -> None:
    dados = {
        "referencia": "R1",
        "altura": {"valor": "240", "unidade": "cm", "confianca": 0.4, "texto_origem": "240"},
        "largura": {"valor": 1800, "unidade": "mm", "confianca": 0.3, "texto_origem": "1800?"},
        "profundidade": {"valor": 60, "unidade": "cm", "confianca": 0.2, "texto_origem": "60"},
        "caracteristicas": {"portas": 3},
        "restricoes": ["desenho rodado"],
        "perguntas": ["Confirmar largura"],
        "confianca": 0.3,
        "explicacao": "Leitura incerta",
    }
    analise = interpretar_analise(dados)
    assert analise.altura.valor == Decimal("2400.000")
    assert analise.largura.confianca == 0.3
    assert analise.perguntas == ("Confirmar largura",)


def test_combinador_cobre_caracteristicas_sem_repartir_largura() -> None:
    catalogo = [
        _modulo(1, "600", caracteristicas={"PORTAS": Decimal("2")}),
        _modulo(2, "800", caracteristicas={"PORTAS": Decimal("1"), "GAVETAS": Decimal("3")}),
    ]
    propostas = RoupeiroCombinadorService().propor(
        Decimal("1800"), catalogo, {"PORTAS": Decimal("4")}
    )
    assert 1 <= len(propostas) <= 3
    assert all(p.largura_total_mm == Decimal("1800") for p in propostas)
    assert all(m.largura_mm == 0 for p in propostas for m in p.modulos)
    assert [m.def_modulo_id for m in propostas[0].modulos] == [1, 1]


def test_combinador_respeita_posicao_de_remate_sem_usar_larguras() -> None:
    catalogo = [
        _modulo(1, "800", minimo="750", maximo="850"),
        _modulo(2, "100", minimo="50", maximo="150", posicao="REMATE"),
    ]
    propostas = RoupeiroCombinadorService().propor(
        Decimal("900"), catalogo, {"REMATE": Decimal("1")}, max_modulos=2
    )
    assert propostas
    for proposta in propostas:
        assert proposta.modulos[0].codigo == "M2" or proposta.modulos[-1].codigo == "M2"


def test_combinador_devolve_vazio_quando_catalogo_esta_vazio() -> None:
    assert RoupeiroCombinadorService().propor(
        Decimal("100"), []
    ) == []


def test_modulo_sem_larguras_participa_e_catalogo_pessoal_fica_isolado(session) -> None:
    service = DefModuloService(session)
    service.criar(
        CriarDefModuloData(
            codigo="PESSOAL_1",
            nome="Pessoal",
            ambito="UTILIZADOR",
            user_id=1,
            tipo_item_compativel="ROUPEIRO_ABRIR",
            caracteristicas={"PORTAS": Decimal("2")},
        )
    )
    assert len(service.listar_elegiveis_roupeiro_abrir(1)) == 1
    assert service.listar_elegiveis_roupeiro_abrir(2) == []


def test_memoria_e_propostas_ficam_privadas_por_utilizador(session, tmp_path) -> None:
    item = OrcamentoItem(
        orcamento_versao_id=1,
        ordem=1,
        tipo_item="ROUPEIRO_ABRIR",
        item="R1",
        quantidade=Decimal("1"),
    )
    session.add(item)
    session.commit()
    pdf = tmp_path / "pedido.pdf"
    pdf.write_bytes(b"%PDF-1.4 teste")
    medida = MedidaReconhecida(Decimal("1000"), "mm", 0.8, "1000")
    analise = AnaliseRoupeiro("R1", medida, medida, medida, {})
    proposta = PropostaComposicao(
        (PropostaModulo(1, "M1", "Módulo", 1, Decimal("1000")),),
        90.0,
        "teste",
        Decimal("1000"),
    )
    _analise_id, proposta_ids = IaOrcamentoService(session).registar_analise_e_propostas(
        user_id=10,
        item_id=item.id,
        documento_path=str(pdf),
        pagina=1,
        zona=None,
        fornecedor="SIMULADO",
        modelo="teste",
        analise=analise,
        propostas=[proposta],
    )
    with pytest.raises(ValueError, match="este utilizador"):
        IaOrcamentoService(session).rejeitar(proposta_ids[0], 11)
    IaOrcamentoService(session).rejeitar(proposta_ids[0], 10, "não corresponde")
    row = session.get(IaOrcamentoProposta, proposta_ids[0])
    assert row.user_id == 10
    assert row.decisao == "REJEITADA"
    assert session.scalar(select(IaOrcamentoAnalise.user_id)) == 10


def _pedido_pdf(caminho: str, respostas: str = "") -> PedidoAnaliseRoupeiro:
    return PedidoAnaliseRoupeiro(
        caminho, 1, 1, 1, None, b"png", (), (), respostas
    )


def test_openai_recusa_ficheiro_inacessivel_e_acima_do_limite(tmp_path) -> None:
    provider = OpenAIVisionProvider("modelo", api_key="teste")
    with pytest.raises(ValueError, match="não está acessível"):
        provider.analisar(_pedido_pdf(str(tmp_path / "nao-existe.pdf")))
    grande = tmp_path / "grande.pdf"
    with grande.open("wb") as stream:
        stream.seek(LIMITE_PDF_BYTES)
        stream.write(b"x")
    with pytest.raises(ValueError, match="50 MB"):
        provider.analisar(_pedido_pdf(str(grande)))


def test_openai_timeout_simulado_nao_produz_resultado(tmp_path, monkeypatch) -> None:
    pdf = tmp_path / "pedido.pdf"
    pdf.write_bytes(b"%PDF")
    provider = OpenAIVisionProvider("modelo", api_key="teste")
    monkeypatch.setattr(provider, "_post", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("timeout")))
    with pytest.raises(ValueError, match="timeout"):
        provider.analisar(_pedido_pdf(str(pdf)))


def test_openai_envia_pdf_e_recorte_com_detalhe_alto(tmp_path, monkeypatch) -> None:
    pdf = tmp_path / "pedido.pdf"
    pdf.write_bytes(b"%PDF")
    provider = OpenAIVisionProvider("gpt-5.2", api_key="teste")
    capturado = {}

    def _post(_url, payload, _headers):
        capturado.update(payload)
        return {
            "output_text": json.dumps(
                {
                    "referencia": "RP_01",
                    "altura": {"valor": None, "unidade": None, "confianca": 0, "texto_origem": None},
                    "largura": {"valor": None, "unidade": None, "confianca": 0, "texto_origem": None},
                    "profundidade": {"valor": None, "unidade": None, "confianca": 0, "texto_origem": None},
                    "caracteristicas": [],
                    "restricoes": [],
                    "perguntas": [],
                    "confianca": 0.5,
                    "explicacao": "teste",
                }
            )
        }

    monkeypatch.setattr(provider, "_post", _post)
    provider.analisar(
        _pedido_pdf(str(pdf), "As portas são de abrir e não existe remate esquerdo.")
    )

    conteudo = capturado["input"][0]["content"]
    ficheiro = next(item for item in conteudo if item["type"] == "input_file")
    imagem = next(item for item in conteudo if item["type"] == "input_image")
    texto = next(item for item in conteudo if item["type"] == "input_text")
    assert ficheiro["detail"] == "high"
    assert ficheiro["file_data"].startswith("data:application/pdf;base64,")
    assert imagem["detail"] == "high"
    assert "As portas são de abrir" in texto["text"]
    assert "informação confirmada pelo utilizador" in texto["text"]


def test_correcao_pode_remover_modulo_da_proposta(session) -> None:
    item = OrcamentoItem(
        orcamento_versao_id=1,
        ordem=1,
        tipo_item="ROUPEIRO_ABRIR",
        item="R1",
        quantidade=Decimal("1"),
    )
    modulo_1 = DefModulo(codigo="M1", nome="Módulo 1", ambito="GLOBAL", categoria="ROUPEIROS")
    modulo_2 = DefModulo(codigo="M2", nome="Módulo 2", ambito="GLOBAL", categoria="ROUPEIROS")
    session.add_all((item, modulo_1, modulo_2))
    session.flush()
    analise = IaOrcamentoAnalise(
        user_id=7,
        orcamento_item_id=item.id,
        documento_path="pedido.pdf",
        documento_hash="0" * 64,
        pagina=1,
        fornecedor="SIMULADO",
        modelo="teste",
        resultado_json="{}",
    )
    session.add(analise)
    session.flush()
    proposta = IaOrcamentoProposta(
        analise_id=analise.id,
        user_id=7,
        posicao_top3=1,
        pontuacao=90,
        proposta_original_json="{}",
    )
    session.add(proposta)
    session.flush()
    session.add_all(
        (
            IaOrcamentoPropostaModulo(
                proposta_id=proposta.id,
                def_modulo_id=modulo_1.id,
                ordem=1,
                codigo_snapshot=modulo_1.codigo,
                nome_snapshot=modulo_1.nome,
                largura_mm=Decimal("0"),
            ),
            IaOrcamentoPropostaModulo(
                proposta_id=proposta.id,
                def_modulo_id=modulo_2.id,
                ordem=2,
                codigo_snapshot=modulo_2.codigo,
                nome_snapshot=modulo_2.nome,
                largura_mm=Decimal("0"),
            ),
        )
    )
    session.commit()

    IaOrcamentoService(session).corrigir_componentes(
        proposta.id, 7, [(modulo_2.id, Decimal("0"))]
    )

    componentes = session.scalars(
        select(IaOrcamentoPropostaModulo)
        .where(IaOrcamentoPropostaModulo.proposta_id == proposta.id)
        .order_by(IaOrcamentoPropostaModulo.ordem)
    ).all()
    assert len(componentes) == 1
    assert componentes[0].def_modulo_id == modulo_2.id
    assert componentes[0].ordem == 1
    assert "modulos_removidos" in session.get(IaOrcamentoProposta, proposta.id).correcoes_json


def test_openai_mostra_detalhe_estruturado_do_erro_http() -> None:
    from io import BytesIO
    from urllib.error import HTTPError

    erro = HTTPError(
        "https://api.openai.com/v1/responses",
        400,
        "Bad Request",
        {"x-request-id": "req_teste"},
        BytesIO(
            json.dumps(
                {
                    "error": {
                        "message": "Campo inválido",
                        "type": "invalid_request_error",
                        "code": "invalid_value",
                        "param": "input",
                    }
                }
            ).encode("utf-8")
        ),
    )

    detalhe = OpenAIVisionProvider._detalhe_erro_http(erro)

    assert "Campo inválido" in detalhe
    assert "invalid_request_error" in detalhe
    assert "req_teste" in detalhe


def test_modelo_local_indisponivel_e_resposta_invalida(tmp_path, monkeypatch) -> None:
    pdf = tmp_path / "pedido.pdf"
    pdf.write_bytes(b"%PDF")
    provider = LocalVisionProvider("modelo-inexistente")
    monkeypatch.setattr(provider, "_renderizar_paginas", lambda _caminho: ["imagem"])
    monkeypatch.setattr(provider, "_post", lambda *_args, **_kwargs: {})
    with pytest.raises(ValueError, match="não devolveu conteúdo"):
        provider.analisar(_pedido_pdf(str(pdf)))
    monkeypatch.setattr(provider, "_post", lambda *_args, **_kwargs: {"message": {"content": "[]"}})
    with pytest.raises(ValueError, match="não é um objeto JSON"):
        provider.analisar(_pedido_pdf(str(pdf)))


def test_falha_intermedia_reverte_modulos_e_decisao(session) -> None:
    item = OrcamentoItem(
        orcamento_versao_id=1,
        ordem=1,
        tipo_item="ROUPEIRO_ABRIR",
        item="R1",
        quantidade=Decimal("1"),
    )
    modulo = DefModulo(codigo="M1", nome="Módulo 1", ambito="GLOBAL", categoria="ROUPEIROS")
    session.add_all((item, modulo))
    session.flush()
    analise = IaOrcamentoAnalise(
        user_id=7,
        orcamento_item_id=item.id,
        documento_path="pedido.pdf",
        documento_hash="0" * 64,
        pagina=1,
        fornecedor="SIMULADO",
        modelo="teste",
        resultado_json="{}",
    )
    session.add(analise)
    session.flush()
    proposta = IaOrcamentoProposta(
        analise_id=analise.id,
        user_id=7,
        posicao_top3=1,
        pontuacao=90,
        proposta_original_json="{}",
    )
    session.add(proposta)
    session.flush()
    session.add_all(
        (
            IaOrcamentoPropostaModulo(
                proposta_id=proposta.id,
                def_modulo_id=modulo.id,
                ordem=1,
                codigo_snapshot=modulo.codigo,
                nome_snapshot=modulo.nome,
                largura_mm=Decimal("600"),
            ),
            IaOrcamentoPropostaModulo(
                proposta_id=proposta.id,
                def_modulo_id=None,
                ordem=2,
                codigo_snapshot="REMOVIDO",
                nome_snapshot="Removido",
                largura_mm=Decimal("400"),
            ),
        )
    )
    session.commit()

    with pytest.raises(ValueError, match="já não existe"):
        IaOrcamentoService(session).confirmar(
            proposta_id=proposta.id,
            user_id=7,
            altura_mm=Decimal("2400"),
            largura_mm=Decimal("1000"),
            profundidade_mm=Decimal("600"),
        )

    assert session.scalars(select(OrcamentoItemModulo)).all() == []
    assert session.get(IaOrcamentoProposta, proposta.id).decisao == "PENDENTE"
