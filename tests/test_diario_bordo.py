"""Caixa negra do Martelo: o que fica registado e quanto ocupa."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from app.core import diario_bordo


@pytest.fixture()
def diario(tmp_path: Path, monkeypatch) -> Path:
    """Diário limpo em tmp_path, sem tocar no do utilizador."""
    caminho = tmp_path / "diario_martelo.log"
    monkeypatch.setenv("MARTELO_DIARIO_PATH", str(caminho))
    monkeypatch.setattr(diario_bordo, "_handler", None)
    monkeypatch.setattr(diario_bordo, "_caminho_em_uso", None)
    monkeypatch.setattr(diario_bordo, "_CONTEXTO", {"utilizador": "-", "menu": "-", "obra": "-"})

    raiz = logging.getLogger()
    handlers_antes = list(raiz.handlers)
    nivel_antes = raiz.level
    diario_bordo.configurar_diario(logging.INFO)
    yield caminho
    for handler in list(raiz.handlers):
        if handler not in handlers_antes:
            handler.close()
            raiz.removeHandler(handler)
    raiz.setLevel(nivel_antes)


def _linhas(caminho: Path) -> list[str]:
    return [linha for linha in caminho.read_text(encoding="utf-8").splitlines() if linha]


def test_cada_linha_leva_quem_onde_e_que_obra(diario: Path) -> None:
    diario_bordo.definir_utilizador("paulo")
    diario_bordo.definir_menu("producao")
    diario_bordo.definir_obra("26.1349_01_01_NEXT_LEVEL")

    diario_bordo.registar_acao("Gravou a obra", "estado=Producao")

    linha = _linhas(diario)[-1]
    assert "paulo" in linha
    assert "producao" in linha
    assert "26.1349_01_01_NEXT_LEVEL" in linha
    assert "Gravou a obra — estado=Producao" in linha


def test_avisos_e_erros_ficam_com_nivel_diferente(diario: Path) -> None:
    diario_bordo.registar_aviso("Guardar produção", "Preencha a Data Início.")
    diario_bordo.registar_erro("Exportar PDF CUT-RITE", "Não foi possível exportar.")

    texto = diario.read_text(encoding="utf-8")
    assert "WARNING" in texto and "AVISO Guardar produção" in texto
    assert "ERROR" in texto and "ERRO Exportar PDF CUT-RITE" in texto


def test_erro_dentro_de_um_except_guarda_o_traceback(diario: Path) -> None:
    try:
        raise ValueError("pasta da obra não encontrada")
    except ValueError:
        diario_bordo.registar_erro("Preparação", "falhou a validar")

    texto = diario.read_text(encoding="utf-8")
    assert "Traceback (most recent call last)" in texto
    assert "ValueError: pasta da obra não encontrada" in texto


def test_mensagens_de_varias_linhas_ficam_numa_so(diario: Path) -> None:
    """Uma linha por acontecimento — senão o ficheiro deixa de dar para filtrar."""
    diario_bordo.registar_aviso("Imprimir", "falhou\n  em duas linhas\n\n")

    assert "falhou em duas linhas" in _linhas(diario)[-1]


def test_o_que_o_martelo_ja_escreve_no_logging_tambem_entra(diario: Path) -> None:
    """Os logger.* dos serviços caem no mesmo ficheiro, com contexto."""
    diario_bordo.definir_utilizador("paulo")
    logging.getLogger("app.services.producao_preparacao_service").warning("cnc em falta")

    linha = _linhas(diario)[-1]
    assert "cnc em falta" in linha
    assert "paulo" in linha


def test_ficheiro_tem_teto_de_espaco() -> None:
    """Nunca pode crescer sem controlo no PC do utilizador."""
    assert diario_bordo.MAX_BYTES * (diario_bordo.COPIAS + 1) <= 10 * 1024 * 1024


def test_linhas_recentes_devolve_o_fim_do_ficheiro(diario: Path) -> None:
    for numero in range(50):
        diario_bordo.registar_acao(f"acao {numero}")

    recentes = diario_bordo.linhas_recentes(10)

    assert len(recentes) == 10
    assert "acao 49" in recentes[-1]


def test_diario_fica_local_e_nunca_no_servidor(monkeypatch, tmp_path: Path) -> None:
    """Escrever na rede era lento e ficava preso — ver o caso dos PDFs."""
    monkeypatch.delenv("MARTELO_DIARIO_PATH", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    caminho = diario_bordo.caminho_diario()

    assert not str(caminho).startswith("\\\\")
    assert str(caminho).startswith(str(tmp_path))


def test_limpeza_apaga_copias_antigas_e_guarda_o_mes(diario: Path, monkeypatch) -> None:
    """A cada arranque, o que tem mais de um mês desaparece sozinho."""
    import os
    import time

    diario_bordo.registar_acao("hoje")
    antiga = diario.with_name(f"{diario.name}.1")
    antiga.write_text("linhas do mês passado", encoding="utf-8")
    recente = diario.with_name(f"{diario.name}.2")
    recente.write_text("linhas de ontem", encoding="utf-8")

    agora = time.time()
    ha_60_dias = agora - 60 * 86400
    os.utime(antiga, (ha_60_dias, ha_60_dias))

    apagados = diario_bordo.limpar_registos_antigos(30, agora=agora)

    assert antiga in apagados
    assert not antiga.exists()
    # O que está dentro do mês e o ficheiro em uso ficam intocados.
    assert recente.exists()
    assert diario.exists() and "hoje" in diario.read_text(encoding="utf-8")


def test_limpeza_apaga_relatorios_esquecidos_no_temp(diario: Path, tmp_path: Path, monkeypatch) -> None:
    import os
    import time

    monkeypatch.setattr(diario_bordo.tempfile, "gettempdir", lambda: str(tmp_path))
    relatorio = tmp_path / "problema_martelo_paulo_20260101_090000.txt"
    relatorio.write_text("relatório velho", encoding="utf-8")
    outro = tmp_path / "orcamento_importante.txt"
    outro.write_text("nada a ver com o registo", encoding="utf-8")

    agora = time.time()
    velho = agora - 90 * 86400
    for ficheiro in (relatorio, outro):
        os.utime(ficheiro, (velho, velho))

    diario_bordo.limpar_registos_antigos(30, agora=agora)

    assert not relatorio.exists()
    # Só mexe no que é nosso: ficheiros de outros programas ficam quietos.
    assert outro.exists()


def test_ficheiro_log_configurado_manda_o_registo_para_la(tmp_path: Path, monkeypatch) -> None:
    """O campo "Ficheiro de log" dos Caminhos do Sistema é respeitado."""
    monkeypatch.delenv("MARTELO_DIARIO_PATH", raising=False)
    monkeypatch.setattr(diario_bordo, "_caminho_em_uso", None)
    escolhido = tmp_path / "registos" / "martelo.log"

    assert diario_bordo.caminho_diario(escolhido) == escolhido


def test_caminho_de_rede_e_ignorado(tmp_path: Path, monkeypatch) -> None:
    """Escrever o registo no servidor seria lento e prendia o ficheiro."""
    monkeypatch.delenv("MARTELO_DIARIO_PATH", raising=False)
    monkeypatch.setattr(diario_bordo, "_caminho_em_uso", None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    caminho = diario_bordo.caminho_diario(r"\\SERVER_LE\_Lanca_Encanto\logs\martelo.log")

    assert str(caminho).startswith(str(tmp_path))


def test_arranque_le_o_ficheiro_log_dos_caminhos_do_sistema() -> None:
    import inspect

    from app.config import logging_config

    fonte = inspect.getsource(logging_config)

    assert 'KEY_FICHEIRO_LOG = "ficheiro_log"' in fonte
    assert "configurar_diario(level, preferido=_ficheiro_log_configurado())" in fonte
    # Sem base de dados, o Martelo tem de arrancar na mesma.
    assert "except Exception" in fonte


def test_contexto_nunca_parte_a_linha_do_ficheiro(diario: Path) -> None:
    diario_bordo.definir_obra("1349 | com barra\ne mudança de linha")

    diario_bordo.registar_acao("teste")

    linha = _linhas(diario)[-1]
    assert linha.count("|") == 5  # data|nível|utilizador|menu|obra|mensagem
