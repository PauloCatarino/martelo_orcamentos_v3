"""Ordenar as linhas de um modelo ValueSet com as setas e reagrupar por chave."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import def_valueset_modelo_linha_service as service_module


def _linha(id: int, *, chave: str, ordem: int, prioridade: int | None = 1):
    return SimpleNamespace(id=id, chave=chave, ordem=ordem, prioridade=prioridade)


class _FakeRepository:
    """In-memory stand-in that keeps the lines sorted like the real query."""

    linhas: list = []
    reordenacoes: list = []

    def __init__(self, _session):
        pass

    def list_by_modelo(self, _modelo_id):
        return sorted(self.linhas, key=lambda linha: (linha.ordem, linha.chave, linha.id))

    def reordenar_linhas(self, ordered_ids):
        self.__class__.reordenacoes.append(list(ordered_ids))
        por_id = {linha.id: linha for linha in self.linhas}
        for posicao, linha_id in enumerate(ordered_ids, start=1):
            por_id[linha_id].ordem = posicao

    def proxima_ordem(self, _modelo_id):
        return max((linha.ordem for linha in self.linhas), default=0) + 1


@pytest.fixture()
def service(monkeypatch):
    monkeypatch.setattr(
        service_module, "DefValuesetModeloLinhaRepository", _FakeRepository
    )
    _FakeRepository.linhas = [
        _linha(1, chave="MATERIAL_COSTAS", ordem=1),
        _linha(2, chave="FERRAGEM_VARAO", ordem=2),
        _linha(3, chave="FERRAGEM_VARAO", ordem=3, prioridade=2),
        _linha(4, chave="ACABAMENTO_FACE_SUP", ordem=4),
    ]
    _FakeRepository.reordenacoes = []
    return service_module.DefValuesetModeloLinhaService(
        SimpleNamespace(commit=lambda: None)
    )


def _ordem_atual(service) -> list[int]:
    return [linha.id for linha in service.repository.list_by_modelo(10)]


def test_mover_para_cima_troca_com_a_linha_de_cima(service) -> None:
    assert service.mover_linha(10, 3, para_cima=True) is True

    assert _ordem_atual(service) == [1, 3, 2, 4]


def test_mover_para_baixo_troca_com_a_linha_de_baixo(service) -> None:
    assert service.mover_linha(10, 1, para_cima=False) is True

    assert _ordem_atual(service) == [2, 1, 3, 4]


def test_nos_extremos_nao_ha_movimento(service) -> None:
    assert service.mover_linha(10, 1, para_cima=True) is False
    assert service.mover_linha(10, 4, para_cima=False) is False
    assert _ordem_atual(service) == [1, 2, 3, 4]


def test_mover_renumera_de_um_a_n(service) -> None:
    # Números repetidos ou com buracos ficam limpos ao mover.
    for linha, ordem in zip(_FakeRepository.linhas, (5, 5, 9, 9)):
        linha.ordem = ordem

    service.mover_linha(10, 2, para_cima=False)

    assert sorted(linha.ordem for linha in _FakeRepository.linhas) == [1, 2, 3, 4]


def test_linha_desconhecida_nao_move(service) -> None:
    assert service.mover_linha(10, 999, para_cima=True) is False
    assert _FakeRepository.reordenacoes == []


def test_agrupar_por_chave_arruma_tudo(service) -> None:
    service.mover_linha(10, 4, para_cima=True)  # desarrumar primeiro

    total = service.agrupar_linhas_por_chave(10)

    assert total == 4
    # Alfabético por chave e, dentro da chave, a melhor prioridade primeiro.
    assert _ordem_atual(service) == [4, 2, 3, 1]


def test_linha_nova_vai_para_o_fim(service, monkeypatch) -> None:
    criados: list = []
    monkeypatch.setattr(
        _FakeRepository,
        "get_by_modelo_chave_opcao",
        lambda self, *_args: None,
        raising=False,
    )
    monkeypatch.setattr(
        _FakeRepository,
        "create",
        lambda self, **fields: criados.append(fields) or SimpleNamespace(**fields),
        raising=False,
    )

    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="FERRAGEM_PUXADOR",
            nome_opcao="PUXADOR NOVO",
            ordem=None,
        )
    )

    assert criados[-1]["ordem"] == 5  # a seguir à última (4)
