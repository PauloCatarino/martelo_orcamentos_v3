"""Crashes que matam o processo sem mensagem (Qt/Python a rebentar por baixo).

A 18-09-2026 o Martelo fechou-se sozinho três vezes no 260932_01 e o diário
não tinha nada: o Windows registou violações de acesso no python312.dll e no
shiboken6. O faulthandler escreve no próprio instante em que linha estava.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

from app.core import diario_bordo


def test_resumo_so_quando_a_sessao_acabou_num_crash() -> None:
    crash = (
        "=== arranque 2026-09-18 16:45:02 (PID 1) ===\n"
        "Windows fatal exception: access violation\n\n"
        "Current thread 0x00001 (most recent call first):\n"
        '  File "app/ui/pages/orcamento_item_custeio_page.py", line 123 in carregar\n'
    )
    resumo = diario_bordo.resumo_crash(crash)
    assert resumo is not None
    assert resumo.startswith("Windows fatal exception")
    assert "orcamento_item_custeio_page.py" in resumo

    assert diario_bordo.resumo_crash(crash + diario_bordo.MARCA_SAIDA_NORMAL) is None
    assert diario_bordo.resumo_crash("=== arranque ===\n") is None
    assert diario_bordo.resumo_crash("") is None


def test_um_crash_verdadeiro_fica_registado_e_passa_para_o_diario(tmp_path) -> None:
    """Processo à parte que rebenta a sério; o seguinte encontra o relatório."""
    diario = tmp_path / "diario_martelo.log"
    codigo = textwrap.dedent(
        f"""
        import faulthandler, sys
        sys.path.insert(0, {str(Path.cwd())!r})
        from app.core import diario_bordo
        diario_bordo._caminho_em_uso = __import__("pathlib").Path({str(diario)!r})
        diario_bordo.instalar_registo_de_crash()
        def funcao_que_rebenta():
            faulthandler._sigsegv()
        funcao_que_rebenta()
        """
    )
    resultado = subprocess.run([sys.executable, "-c", codigo], capture_output=True, timeout=60)
    assert resultado.returncode != 0  # morreu mesmo

    texto = (tmp_path / diario_bordo.NOME_CRASH).read_text(encoding="utf-8")
    assert "funcao_que_rebenta" in texto

    # Arranque seguinte (neste processo): traz o crash e guarda uma cópia.
    anterior_caminho = diario_bordo._caminho_em_uso
    anterior_ficheiro = diario_bordo._ficheiro_crash
    try:
        diario_bordo._caminho_em_uso = diario
        resumo = diario_bordo.instalar_registo_de_crash()
        assert resumo is not None and "funcao_que_rebenta" in resumo
        assert list(tmp_path.glob(diario_bordo.PADRAO_CRASH_GUARDADO))

        # Esta sessão acaba bem: o próximo arranque não inventa um crash.
        diario_bordo.marcar_saida_normal()
        assert diario_bordo.instalar_registo_de_crash() is None
    finally:
        import faulthandler

        faulthandler.disable()
        if diario_bordo._ficheiro_crash is not None:
            diario_bordo._ficheiro_crash.close()
        diario_bordo._caminho_em_uso = anterior_caminho
        diario_bordo._ficheiro_crash = anterior_ficheiro


def test_segundo_martelo_aberto_nao_inventa_crash_nem_escreve_por_cima(tmp_path) -> None:
    """Duplo clique repetido: o 1º Martelo ainda corre e o ficheiro é dele."""
    diario = tmp_path / "diario_martelo.log"
    ficheiro_do_primeiro = tmp_path / diario_bordo.NOME_CRASH
    primeiro = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"]
    )
    try:
        conteudo = f"=== arranque 2026-09-23 09:00:00 (PID {primeiro.pid}) ===\n"
        ficheiro_do_primeiro.write_text(conteudo, encoding="utf-8")
        assert diario_bordo.outro_martelo_aberto(conteudo)

        anterior_caminho = diario_bordo._caminho_em_uso
        anterior_ficheiro = diario_bordo._ficheiro_crash
        try:
            diario_bordo._caminho_em_uso = diario
            assert diario_bordo.instalar_registo_de_crash() is None
            # O ficheiro do primeiro ficou intacto; o segundo tem o seu.
            assert ficheiro_do_primeiro.read_text(encoding="utf-8") == conteudo
            assert list(tmp_path.glob("crash_martelo_pid*.log"))
        finally:
            import faulthandler

            faulthandler.disable()
            if diario_bordo._ficheiro_crash is not None:
                diario_bordo._ficheiro_crash.close()
            diario_bordo._caminho_em_uso = anterior_caminho
            diario_bordo._ficheiro_crash = anterior_ficheiro
    finally:
        primeiro.kill()
        primeiro.wait(timeout=30)

    # Depois de o primeiro fechar, o mesmo ficheiro volta a contar.
    assert not diario_bordo.outro_martelo_aberto(conteudo)


def test_resumo_ignora_avisos_do_outlook_e_mostra_o_ultimo_crash() -> None:
    """A 18-09 o ficheiro tinha 173 avisos 0x8001010e (Outlook a anexar) antes
    do crash verdadeiro; o relatório tem de mostrar o que matou o processo."""
    aviso = (
        "Windows fatal exception: code 0x8001010e\n\n"
        "Thread 0x5f70 (most recent call first):\n"
        '  File "email_orcamento_dialog.py", line 284 in _adicionar_anexos\n'
    )
    crash = (
        "Windows fatal exception: access violation\n\n"
        "Current thread 0x5f70 (most recent call first):\n"
        '  File "orcamento_item_custeio_page.py", line 2918 in _preencher_linha\n'
    )
    texto = "=== arranque ===\n" + aviso * 5 + crash

    resumo = diario_bordo.resumo_crash(texto)
    assert resumo.startswith("Windows fatal exception: access violation")
    assert "_preencher_linha" in resumo
    assert "_adicionar_anexos" not in resumo

    # Só avisos tratados e a sessão sem saída normal (ex.: morto pelo Gestor
    # de Tarefas): não se inventa um crash.
    assert diario_bordo.resumo_crash("=== arranque ===\n" + aviso * 3) is None
