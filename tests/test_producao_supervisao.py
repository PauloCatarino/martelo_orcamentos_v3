"""Supervisor da mudança de estado para Produção.

Regra do Paulo: ao passar uma obra de Desenho para Produção, o Martelo confirma
a Preparação e avisa se ficou alguma coisa por fazer — com as validações que
**aquele** utilizador escolheu, porque nem todos querem as mesmas.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.producao_estados import e_producao, entra_em_producao
from app.services import producao_preparacao_service as svc
from app.services.system_setting_service import SystemSettingService


# ---- domínio: quando é que o supervisor entra --------------------------------
def test_entra_em_producao_so_na_mudanca() -> None:
    assert entra_em_producao("Desenho", "Producao") is True
    # Gravar outra vez uma obra que já está em produção não incomoda ninguém.
    assert entra_em_producao("Producao", "Producao") is False
    assert entra_em_producao("Desenho", "Finalizado") is False
    # Voltar atrás (de Finalizado para Produção) volta a ser uma entrada.
    assert entra_em_producao("Finalizado", "Producao") is True


def test_estado_producao_com_acento_e_maiusculas() -> None:
    """Obras antigas e o que vem do PHC trazem "Produção" com acento."""
    assert e_producao("Produção") is True
    assert e_producao("PRODUCAO") is True
    assert entra_em_producao("Desenho", "Produção") is True
    assert entra_em_producao("Produção", "Producao") is False
    assert e_producao(None) is False


# ---- serviço: o que o supervisor encontra ------------------------------------
@pytest.fixture()
def obra(tmp_path: Path, session) -> Path:
    """Pasta da obra vazia, com os caminhos CNC a apontar para o tmp_path."""
    settings = SystemSettingService(session)
    settings.guardar_valor(svc.KEY_PASTA_ORIGEM_CNC, str(tmp_path / "cnc"))
    settings.guardar_valor(svc.KEY_PASTA_DESTINO_CNC, str(tmp_path / "mpr"))
    pasta = tmp_path / "1319_01_01_JF_VIVA"
    pasta.mkdir()
    return pasta


def _supervisionar(session, pasta_obra, *, nome_enc="1319_01_26_JF_VIVA", user_id=7):
    return svc.supervisionar_para_producao(
        session,
        codigo_processo="26.1319_01_01_JF_VIVA",
        pasta_obra=str(pasta_obra),
        nome_enc_imos=nome_enc,
        nome_plano_cut_rite="1319_01_01_26_JF_VIVA",
        user_id=user_id,
    )


def test_pasta_vazia_devolve_pendencias(session, obra: Path) -> None:
    supervisao = _supervisionar(session, obra)

    assert supervisao.validou is True
    assert supervisao.pronta is False
    keys = {pendencia.key for pendencia in supervisao.pendencias}
    assert "conj_pdf" in keys
    assert "cnc_origem" in keys
    # A linha de resumo não é uma pendência, é o resultado delas.
    assert "obra_pronta" not in keys
    # Cada pendência traz o caminho que falta, para o aviso ser acionável.
    assert any(str(obra) in pendencia.detalhe for pendencia in supervisao.pendencias)


def test_pendencias_seguem_as_preferencias_do_utilizador(session, obra: Path) -> None:
    svc.guardar_validacoes_utilizador(session, 7, ["conj_pdf"])

    supervisao = _supervisionar(session, obra, user_id=7)

    keys = {pendencia.key for pendencia in supervisao.pendencias}
    assert "conj_pdf" in keys
    # O que este utilizador não escolheu não pode aparecer no aviso.
    assert "etiqueta_palete_pdf" not in keys
    assert "caderno_encargos" not in keys
    # As dos programas CNC são sempre obrigatórias, escolha ele o que escolher.
    assert "cnc_origem" in keys


def test_outro_utilizador_tem_outras_pendencias(session, obra: Path) -> None:
    svc.guardar_validacoes_utilizador(session, 7, ["conj_pdf"])

    do_paulo = _supervisionar(session, obra, user_id=7)
    do_outro = _supervisionar(session, obra, user_id=99)

    assert {p.key for p in do_paulo.pendencias} < {p.key for p in do_outro.pendencias}


def test_obra_toda_preparada_fica_pronta(session, obra: Path, tmp_path: Path) -> None:
    # Só as validações do CNC, para o teste não ter de criar todos os PDFs.
    svc.guardar_validacoes_utilizador(session, 7, [])
    contexto = svc.resolver_contexto(
        session,
        codigo_processo="26.1319_01_01_JF_VIVA",
        pasta_obra=str(obra),
        nome_enc_imos="1319_01_26_JF_VIVA",
        nome_plano_cut_rite="1319_01_01_26_JF_VIVA",
    )
    contexto.pasta_origem_cnc_obra.mkdir(parents=True)
    (contexto.pasta_origem_cnc_obra / "peca.mpr").write_text("programa", encoding="utf-8")
    svc.copiar_programas_para_obra(contexto)
    svc.enviar_programas_para_cnc(contexto)

    supervisao = _supervisionar(session, obra, user_id=7)

    assert supervisao.pendencias == ()
    assert supervisao.pronta is True


def test_sem_pasta_da_obra_o_supervisor_diz_porque_nao_validou(session) -> None:
    supervisao = _supervisionar(session, "")

    assert supervisao.validou is False
    assert supervisao.pronta is False
    assert "Pasta da obra" in supervisao.motivo


def test_sem_nome_enc_imos_o_supervisor_diz_porque_nao_validou(
    session, obra: Path
) -> None:
    supervisao = _supervisionar(session, obra, nome_enc="")

    assert supervisao.validou is False
    assert "Nome Enc IMOS" in supervisao.motivo
