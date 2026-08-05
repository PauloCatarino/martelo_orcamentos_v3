"""As preferências pessoais, fora da tabela trancada pela segurança.

Descoberto na beta (2026-08-05): a Andreia, conta normal, levava

    (1142) INSERT command denied to user 'Andreia' for table 'system_settings'

ao gravar as Preferências da Preparação. A `system_settings` guarda as
credenciais do PHC/iMos e por isso está a só-leitura para quem não é admin —
mas as escolhas pessoais estavam lá dentro e ficaram reféns dessa tranca.
"""

from __future__ import annotations

from app.models.user_pref import UserPref
from app.services.user_pref_service import UTILIZADOR_SEM_SESSAO, UserPrefService


def test_grava_e_le_uma_preferencia(session) -> None:
    servico = UserPrefService(session)

    servico.guardar_valor(7, "producao_vistas", '[{"nome": "Atrasadas"}]')

    assert servico.obter_valor(7, "producao_vistas") == '[{"nome": "Atrasadas"}]'


def test_sem_nada_guardado_devolve_o_default(session) -> None:
    servico = UserPrefService(session)

    assert servico.obter_valor(7, "producao_vistas") is None
    assert servico.obter_valor(7, "producao_vistas", "[]") == "[]"


def test_cada_utilizador_tem_as_suas(session) -> None:
    servico = UserPrefService(session)

    servico.guardar_valor(7, "producao_colunas", "do sete")
    servico.guardar_valor(9, "producao_colunas", "do nove")

    assert servico.obter_valor(7, "producao_colunas") == "do sete"
    assert servico.obter_valor(9, "producao_colunas") == "do nove"


def test_gravar_outra_vez_atualiza_em_vez_de_duplicar(session) -> None:
    servico = UserPrefService(session)

    servico.guardar_valor(7, "producao_colunas", "primeira")
    servico.guardar_valor(7, "producao_colunas", "segunda")

    assert servico.obter_valor(7, "producao_colunas") == "segunda"
    registos = session.query(UserPref).filter(UserPref.user_id == 7).all()
    assert len(registos) == 1


def test_sem_sessao_vai_para_o_utilizador_zero(session) -> None:
    servico = UserPrefService(session)

    servico.guardar_valor(None, "producao_vistas", "sem sessão")

    assert servico.obter_valor(None, "producao_vistas") == "sem sessão"
    registo = session.query(UserPref).one()
    assert registo.user_id == UTILIZADOR_SEM_SESSAO


def test_id_estranho_nao_rebenta(session) -> None:
    servico = UserPrefService(session)

    servico.guardar_valor("nao é um número", "producao_vistas", "x")

    assert servico.obter_valor(None, "producao_vistas") == "x"


def test_chaves_diferentes_do_mesmo_utilizador_nao_se_pisam(session) -> None:
    servico = UserPrefService(session)

    servico.guardar_valor(7, "producao_colunas", "colunas")
    servico.guardar_valor(7, "producao_vistas", "vistas")

    assert servico.obter_valor(7, "producao_colunas") == "colunas"
    assert servico.obter_valor(7, "producao_vistas") == "vistas"


def test_chave_vazia_e_recusada(session) -> None:
    servico = UserPrefService(session)

    try:
        servico.guardar_valor(7, "  ", "x")
    except ValueError as erro:
        assert "chave" in str(erro)
    else:  # pragma: no cover - tem mesmo de recusar
        raise AssertionError("uma chave vazia devia ser recusada")
