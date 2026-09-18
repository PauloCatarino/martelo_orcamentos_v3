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
