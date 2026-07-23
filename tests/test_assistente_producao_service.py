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
