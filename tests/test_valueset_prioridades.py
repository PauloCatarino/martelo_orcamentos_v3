from types import SimpleNamespace

from app.domain.valueset_prioridades import detetar_conflito_prioridade


def _linha(id, chave, prioridade, ativo=True):
    return SimpleNamespace(id=id, chave=chave, prioridade=prioridade, ativo=ativo)


def test_deteta_repeticao_na_mesma_chave_e_sugere_primeira_livre() -> None:
    destino = _linha(3, "MATERIAL_PORTAS", 1)
    linhas = [
        _linha(1, "MATERIAL_PORTAS", 1),
        _linha(2, "MATERIAL_PORTAS", 2),
        destino,
        _linha(4, "MATERIAL_REMATES", 1),
    ]

    conflito = detetar_conflito_prioridade(destino, linhas)

    assert conflito is not None
    assert conflito.prioridade == 1
    assert conflito.sugestao == 3


def test_ignora_outra_chave_inativos_e_prioridade_vazia() -> None:
    assert detetar_conflito_prioridade(
        _linha(3, "A", 1),
        [_linha(1, "B", 1), _linha(2, "A", 1, ativo=False), _linha(3, "A", 1)],
    ) is None
    assert detetar_conflito_prioridade(
        _linha(3, "A", None), [_linha(1, "A", None), _linha(3, "A", None)]
    ) is None
