from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from app.repositories.orcamento_repository import OrcamentoResumo
from app.services.inicio_dashboard_service import calcular_dashboard_orcamentos


def _orcamento(
    indice: int, estado: str, preco, *, manual=False, dias=0, tempo=0
):
    return OrcamentoResumo(
        orcamento_id=indice,
        orcamento_versao_id=indice,
        ano=2026,
        num_orcamento=str(indice),
        numero_versao=1,
        codigo_versao=f"260{indice:03d}_01",
        cliente_nome=f"Cliente {indice}",
        obra=f"Obra {indice}",
        descricao=None,
        localizacao=None,
        ref_cliente=None,
        estado=estado,
        preco_total=preco,
        created_at=datetime(2026, 7, 1) + timedelta(days=dias),
        tem_preco_manual=manual,
        tempo_ativo_segundos=tempo,
    )


def test_calcula_indicadores_valores_e_avisos() -> None:
    dados = calcular_dashboard_orcamentos([
        _orcamento(
            1, "Falta Orçamentar", Decimal("100"), dias=1, tempo=3600
        ),
        _orcamento(2, "Adjudicado", Decimal("250"), dias=2, tempo=1800),
        _orcamento(3, "Enviado", None, manual=True, dias=3),
    ])

    assert dados.total == 3
    assert dados.em_curso == 2
    assert dados.adjudicados == 1
    assert dados.falta_orcamentar == 1
    assert dados.enviados == 1
    assert dados.valor_em_curso == Decimal("100")
    assert dados.valor_adjudicado == Decimal("250")
    assert dados.sem_total == 1
    assert dados.com_preco_manual == 1
    assert dados.tempo_medio_segundos == 2700
    assert dados.orcamentos_com_tempo == 2
    assert dados.recentes[0].orcamento_versao_id == 3
    assert {aviso.titulo for aviso in dados.avisos} == {
        "Falta orçamentar", "Preço manual aplicado", "Total ainda não calculado"
    }


def test_dashboard_vazio() -> None:
    dados = calcular_dashboard_orcamentos([])
    assert dados.total == dados.em_curso == 0
    assert dados.recentes == ()
    assert dados.avisos == ()
    assert dados.tempo_medio_segundos == 0
    assert dados.orcamentos_com_tempo == 0
