"""O catálogo (máquinas e peças) é lido da base uma vez, não centenas.

Medido no orçamento 260868 do Paulo (30 itens, 2022 linhas): das ~1111
consultas por item, 284 eram a pedir outra vez a mesma máquina e a mesma peça.
Cada pedido é uma ida ao servidor, e a exportação levava um minuto e meio antes
de sequer começar a desenhar o PDF.

São definições, não dados do orçamento: não mudam a meio de um recálculo.
"""

from __future__ import annotations

import app.models  # noqa: F401  (regista os modelos em Base.metadata)
from app.models import DefMaquina, DefPeca
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)


def _contar_chamadas(servico, nome_repositorio: str) -> list[int]:
    """Substitui o get_by_id do repositório por um que conta os pedidos."""
    repositorio = getattr(servico, nome_repositorio)
    pedidos: list[int] = []
    original = repositorio.get_by_id

    def espiar(identificador):
        pedidos.append(identificador)
        return original(identificador)

    repositorio.get_by_id = espiar
    return pedidos


def test_a_mesma_maquina_so_e_lida_uma_vez(session) -> None:
    maquina = DefMaquina(codigo="CNC5", nome="CNC 5 Eixos", ativo=True)
    session.add(maquina)
    session.flush()
    servico = OrcamentoItemCusteioLinhaService(session)
    pedidos = _contar_chamadas(servico, "maquina_repository")

    primeira = servico._maquina(maquina.id)
    for _ in range(50):
        servico._maquina(maquina.id)

    assert primeira is not None
    assert primeira.codigo == "CNC5"
    assert pedidos == [maquina.id], "a base foi consultada mais do que uma vez"


def test_a_mesma_peca_so_e_lida_uma_vez(session) -> None:
    peca = DefPeca(codigo="LATERAL_2000", nome="Lateral", ativo=True)
    session.add(peca)
    session.flush()
    servico = OrcamentoItemCusteioLinhaService(session)
    pedidos = _contar_chamadas(servico, "peca_repository")

    for _ in range(30):
        servico._peca(peca.id)

    assert pedidos == [peca.id]


def test_sem_identificador_nao_ha_consulta(session) -> None:
    servico = OrcamentoItemCusteioLinhaService(session)
    pedidos_maquina = _contar_chamadas(servico, "maquina_repository")
    pedidos_peca = _contar_chamadas(servico, "peca_repository")

    assert servico._maquina(None) is None
    assert servico._peca(None) is None
    assert pedidos_maquina == []
    assert pedidos_peca == []


def test_um_id_que_nao_existe_tambem_nao_se_repete(session) -> None:
    """Guardar o "não existe" evita repetir a consulta que não devolve nada."""
    servico = OrcamentoItemCusteioLinhaService(session)
    pedidos = _contar_chamadas(servico, "maquina_repository")

    assert servico._maquina(999_999) is None
    assert servico._maquina(999_999) is None

    assert pedidos == [999_999]
