"""Testes da camada LLM do IA Martelo (prompt + validação do JSON)."""

from __future__ import annotations

from app.domain.assistente_llm import (
    construir_mensagens,
    extrair_json,
    intencao_de_json,
)


def test_extrair_json_limpa_cercas_e_texto() -> None:
    assert extrair_json('```json\n{"estado": "Producao"}\n```') == {
        "estado": "Producao"
    }
    assert extrair_json('Claro! {"cliente": "Viva"} espero ter ajudado') == {
        "cliente": "Viva"
    }
    assert extrair_json("sem json aqui") == {}
    assert extrair_json("") == {}


def test_construir_mensagens_inclui_perfil() -> None:
    system, user = construir_mensagens("obras da Viva", perfil_texto="a Viva = MÓVEIS J.F. VIVA")

    assert "JSON" in system
    assert "Vocabulário deste utilizador" in system
    assert "obras da Viva" in user


def test_intencao_recusa_tema_fora() -> None:
    intencao, recusa = intencao_de_json({"recusa": "Só ajudo nas obras."})

    assert recusa == "Só ajudo nas obras."
    assert intencao.estado is None


def test_intencao_pergunta_ambigua() -> None:
    intencao, recusa = intencao_de_json({"pergunta": "Silva é cliente ou responsável?"})

    assert recusa == ""
    assert intencao.perguntas == ("Silva é cliente ou responsável?",)


def test_intencao_valida_estado_e_nomes_reais() -> None:
    dados = {
        "estado": "na máquina",
        "cliente": "moveis j.f. viva",
        "responsavel": "Paulo",
        "so_atrasadas": True,
        "termos": "roupeiros",
    }

    intencao, _ = intencao_de_json(
        dados,
        clientes=["MÓVEIS J.F. VIVA", "Sonae"],
        responsaveis=["Paulo", "Ana"],
    )

    assert intencao.estado == "Producao"
    assert intencao.cliente == "MÓVEIS J.F. VIVA"
    assert intencao.responsavel == "Paulo"
    assert intencao.so_atrasadas is True
    assert intencao.termos == "roupeiros"


def test_intencao_descarta_valores_inventados() -> None:
    dados = {"cliente": "Cliente Que Nao Existe", "estado": "estado invalido"}

    intencao, _ = intencao_de_json(dados, clientes=["Sonae"], responsaveis=[])

    assert intencao.cliente is None
    assert intencao.estado is None
