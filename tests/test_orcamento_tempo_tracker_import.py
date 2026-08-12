from __future__ import annotations

import inspect


def test_main_window_liga_tracker_ao_orcamento_visivel() -> None:
    from app.ui.main_window import MainWindow

    init = inspect.getsource(MainWindow.__init__)
    navegar = inspect.getsource(MainWindow.show_page)
    sincronizar = inspect.getsource(MainWindow._sincronizar_tempo_orcamento)
    fechar = inspect.getsource(MainWindow.closeEvent)

    assert "OrcamentoTempoTracker" in init
    assert "tempoAtualizado.connect" in init
    assert "_sincronizar_tempo_orcamento" in navegar
    assert 'pagina == "orcamento_detail"' in sincronizar
    assert "orcamento_versao_id" in sincronizar
    assert "tracker.encerrar" in fechar


def test_tracker_exige_primeiro_plano_e_janela_nao_minimizada() -> None:
    from app.ui.orcamento_tempo_tracker import OrcamentoTempoTracker

    elegivel = inspect.getsource(OrcamentoTempoTracker._aplicacao_esta_ativa)
    assert "ApplicationActive" in elegivel
    assert "isMinimized" in elegivel

    transicao = inspect.getsource(
        OrcamentoTempoTracker._mudou_estado_aplicacao
    )
    assert "_ultima_atividade = None" in transicao


def test_tracker_grava_em_blocos_e_atividade_expira() -> None:
    from app.domain.tempo_atividade import LIMITE_INATIVIDADE_SEGUNDOS
    from app.ui.orcamento_tempo_tracker import OrcamentoTempoTracker

    assert LIMITE_INATIVIDADE_SEGUNDOS == 120
    assert OrcamentoTempoTracker.INTERVALO_GRAVACAO_SEGUNDOS == 60
