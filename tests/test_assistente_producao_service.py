"""Testes do serviço IA Martelo na Produção (sem BD, com dados injetados)."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.assistente_producao_service import (
    AssistenteProducaoService,
    perfil_de_entradas,
)


def _entrada(tipo: str, expressao: str, significado: str = "") -> SimpleNamespace:
    return SimpleNamespace(tipo=tipo, expressao=expressao, significado=significado)


def test_perfil_de_entradas_le_os_quadros() -> None:
    perfil = perfil_de_entradas(
        [
            _entrada("estado", "está na máquina", "Produção"),
            _entrada("cliente", "a Viva; a JF", "MÓVEIS J.F. VIVA"),
            _entrada("pessoa", "Zé", "José Martins"),
            _entrada("ambigua", "Silva", "«Silva» é o cliente ou o responsável?"),
            _entrada("material", "lacado", "leva lacagem"),  # ignorado aqui
        ]
    )

    # O quadro «estado» resolve para o estado canónico da BD (Producao).
    assert perfil.estados == {"está na máquina": "Producao"}
    assert perfil.clientes == {"a Viva": "MÓVEIS J.F. VIVA", "a JF": "MÓVEIS J.F. VIVA"}
    assert perfil.pessoas == {"Zé": "José Martins"}
    assert perfil.ambiguas == {"Silva": "«Silva» é o cliente ou o responsável?"}


def _processo(**overrides) -> SimpleNamespace:
    base = {
        "id": 1,
        "nome_cliente": "Moviflor",
        "responsavel": "Paulo",
        "estado": "Producao",
        "obra": "Roupeiros quarto",
        "descricao_producao": "3 roupeiros de correr",
        "data_entrega": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_responder_filtra_por_estado_e_descreve() -> None:
    processos = [
        _processo(id=1, estado="Producao"),
        _processo(id=2, estado="Desenho"),
    ]
    servico = AssistenteProducaoService(None)

    resposta = servico.responder("obras em produção", user_id=None, processos=processos)

    assert [p.id for p in resposta.obras] == [1]
    assert resposta.intencao.estado == "Producao"
    assert resposta.frase.startswith("Encontrei 1 obra")
    assert not resposta.precisa_perguntar


def test_responder_pergunta_quando_ambiguo() -> None:
    processos = [
        _processo(nome_cliente="Silva", responsavel="Silva"),
    ]
    servico = AssistenteProducaoService(None)

    resposta = servico.responder("obras da Silva", user_id=None, processos=processos)

    assert resposta.precisa_perguntar
    assert resposta.obras == []
    assert "cliente ou a pessoa" in resposta.frase


def test_responder_recruta_quando_palavra_desconhecida() -> None:
    processos = [_processo(obra="Cozinha", descricao_producao="móveis de cozinha")]
    servico = AssistenteProducaoService(None)

    resposta = servico.responder(
        "obras com bordaduplaxpto", user_id=None, processos=processos
    )

    assert resposta.obras == []
    assert "bordaduplaxpto" in resposta.sugestao_perfil


def test_llm_usa_filtros_validados_do_modelo() -> None:
    processos = [
        _processo(id=1, nome_cliente="Moviflor", estado="Producao"),
        _processo(id=2, nome_cliente="Sonae", estado="Desenho"),
    ]
    servico = AssistenteProducaoService(None)

    def fake_modelo(system, user):
        return '{"cliente": "moviflor", "estado": "na máquina"}'

    intencao, recusa = servico.interpretar_pergunta_llm(
        "o que temos na Moviflor a produzir",
        user_id=None,
        processos=processos,
        chamar_modelo=fake_modelo,
    )

    assert recusa == ""
    assert intencao.cliente == "Moviflor"
    assert intencao.estado == "Producao"


def test_responder_ia_pedido_de_obra_monta_dossier() -> None:
    processos = [
        _processo(id=7, num_enc_phc="1134", codigo_processo="26.1134_01_01_JF_VIVA"),
        _processo(id=8, num_enc_phc="0800"),
    ]
    servico = AssistenteProducaoService(None)

    resultado = servico.responder_ia(
        "faz um relatório da obra 1134", user_id=None, processos=processos
    )

    assert resultado.tipo == "obra"
    assert resultado.obra_id == 7
    assert resultado.modo == "pdf"
    assert "26.1134_01_01_JF_VIVA" in resultado.texto


def test_responder_ia_obra_inexistente_avisa() -> None:
    servico = AssistenteProducaoService(None)

    resultado = servico.responder_ia(
        "estado da obra 9999", user_id=None, processos=[_processo(num_enc_phc="1134")]
    )

    assert resultado.tipo == "obra"
    assert "9999" in resultado.aviso


def test_responder_ia_pergunta_normal_e_pesquisa() -> None:
    processos = [_processo(id=1, estado="Producao"), _processo(id=2, estado="Desenho")]
    servico = AssistenteProducaoService(None)

    resultado = servico.responder_ia(
        "obras atrasadas", user_id=None, processos=processos
    )

    assert resultado.tipo == "pesquisa"
    assert resultado.intencao is not None
    assert resultado.intencao.so_atrasadas is True


def test_montar_dossier_usa_fases_injetadas() -> None:
    servico = AssistenteProducaoService(None)
    processo = _processo(
        id=5, num_enc_phc="1134", responsavel="Paulo",
        versao_obra="01", versao_plano="03",
    )

    def estados_fake(_processos):
        return {5: ((("Corte", 100.0, True), ("Orlagem", 60.0, False)), "🔄 50% (1/2)", True)}

    dossier = servico.montar_dossier([processo], carregar_estados=estados_fake)

    assert dossier.encontrado_streamlit is True
    assert dossier.estado_global == "🔄 50% (1/2)"
    assert dossier.fases[0] == ("Corte", 100.0, True)
    assert len(dossier.versoes) == 1
    assert dossier.versoes[0].versao_plano == "03"


def test_montar_dossier_lista_varias_versoes_ordenadas() -> None:
    servico = AssistenteProducaoService(None)
    v1 = _processo(id=1, num_enc_phc="0800", versao_obra="01", versao_plano="01",
                   estado="Arquivado")
    v3 = _processo(id=3, num_enc_phc="0800", versao_obra="01", versao_plano="03",
                   estado="Producao")
    v2 = _processo(id=2, num_enc_phc="0800", versao_obra="01", versao_plano="02",
                   estado="Arquivado")

    # _encontrar_obras ordena; aqui simulamos a lista já ordenada.
    versoes = servico._encontrar_obras([v1, v3, v2], "800")
    dossier = servico.montar_dossier(versoes, carregar_estados=lambda _p: {})

    assert [v.versao_plano for v in dossier.versoes] == ["01", "02", "03"]
    # O cabeçalho usa a versão mais recente (plano 03, em Producao).
    assert dossier.estado_local == "Producao"


def test_llm_nao_polui_estado_com_alucinacao() -> None:
    # O modelo alucina um estado que a pergunta não pede; as regras mandam.
    processos = [_processo(id=1, responsavel="Paulo", estado="Producao")]
    servico = AssistenteProducaoService(None)

    def fake_modelo(system, user):
        return '{"estado": "Desenho", "so_atrasadas": true}'

    intencao, _ = servico.interpretar_pergunta_llm(
        "obras atrasadas do Paulo",
        user_id=None,
        processos=processos,
        chamar_modelo=fake_modelo,
    )

    # Estado fica None (as regras não o pediram); atrasadas vem das regras.
    assert intencao.estado is None
    assert intencao.responsavel == "Paulo"
    assert intencao.so_atrasadas is True


def test_llm_recusa_propaga() -> None:
    servico = AssistenteProducaoService(None)

    def fake_modelo(system, user):
        return '{"recusa": "Só ajudo nas obras."}'

    intencao, recusa = servico.interpretar_pergunta_llm(
        "conta-me uma piada", user_id=None, processos=[], chamar_modelo=fake_modelo
    )

    assert recusa == "Só ajudo nas obras."


def test_llm_cai_no_deterministico_quando_modelo_falha() -> None:
    processos = [_processo(id=1, estado="Producao"), _processo(id=2, estado="Desenho")]
    servico = AssistenteProducaoService(None)

    def modelo_partido(system, user):
        raise RuntimeError("ollama offline")

    intencao, recusa = servico.interpretar_pergunta_llm(
        "obras em produção",
        user_id=None,
        processos=processos,
        chamar_modelo=modelo_partido,
    )

    # Sem modelo, as regras determinísticas ainda percebem o estado.
    assert intencao.estado == "Producao"
    assert recusa == ""
