from types import SimpleNamespace

from app.domain.valueset_modelo_pesquisa import (
    filtrar_linhas_valueset_modelo,
    linha_valueset_modelo_corresponde,
)


def _linha(**overrides):
    dados = dict(
        id=1,
        chave="FERRAGEM_TULHA",
        codigo_opcao="TULHA_60",
        nome_opcao="Tulha Gaveta 600",
        ref_materia_prima="TULHA-600",
        descricao_materia_prima="Tulha para módulo de cozinha",
        valor_texto=None,
        ref_le="TULHA-600",
        descricao_no_orcamento="Tulha Gaveta",
        unidade="UND",
        tipo_materia_prima="FERRAGEM",
        familia_materia_prima="FERRAGENS",
        prioridade=1,
        ordem=10,
        observacoes="Modelo principal",
        ativo=True,
    )
    dados.update(overrides)
    return SimpleNamespace(**dados)


def test_pesquisa_todos_os_campos_sem_distinguir_acentos() -> None:
    linha = _linha()

    assert linha_valueset_modelo_corresponde(linha, "tulha ferragens")
    assert linha_valueset_modelo_corresponde(linha, "inexistente") is False
    assert linha_valueset_modelo_corresponde(
        _linha(nome_opcao="Tulha Clássica"), "classica"
    )
    assert linha_valueset_modelo_corresponde(linha, "tulha%600", "CNC VERTICAL")
    assert linha_valueset_modelo_corresponde(linha, "cnc vertical", "CNC VERTICAL")


def test_filtrar_preserva_ordem_e_estado_pesquisavel() -> None:
    primeiro = _linha(id=1, chave="A", nome_opcao="Primeiro")
    segundo = _linha(id=2, chave="B", nome_opcao="Segundo", ativo=False)

    assert filtrar_linhas_valueset_modelo([primeiro, segundo], "") == [
        primeiro,
        segundo,
    ]
    assert filtrar_linhas_valueset_modelo([primeiro, segundo], "inativo") == [
        segundo
    ]
