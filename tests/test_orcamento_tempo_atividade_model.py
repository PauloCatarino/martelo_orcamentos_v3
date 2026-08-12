from __future__ import annotations

from app.models import OrcamentoTempoAtividade


def test_modelo_tempo_atividade_tem_chave_por_versao_e_utilizador() -> None:
    tabela = OrcamentoTempoAtividade.__table__
    assert tabela.name == "orcamento_tempo_atividade"
    assert {
        "orcamento_versao_id",
        "user_id",
        "segundos_ativos",
    } <= set(tabela.columns.keys())
    assert any(
        constraint.name == "uq_orc_tempo_versao_user"
        for constraint in tabela.constraints
    )
