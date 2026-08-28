"""Testes a` copia de seguranca -- sobretudo a` parte que APAGA.

A rotacao e' o unico sitio deste projeto onde um programa apaga ficheiros
sozinho, todas as noites, sem ninguem estar a ver. Se errar, apaga a unica
copia boa no dia em que ela e' precisa. Por isso e' a parte mais testada.
"""

from __future__ import annotations

import gzip
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "backup_martelo", RAIZ / "scripts" / "backup_martelo.py"
)
assert _spec and _spec.loader
backup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backup)


AGORA = datetime(2026, 8, 28, 3, 0)
BASE = "martelo_v3"


def _criar(pasta: Path, quando: datetime, base: str = BASE) -> Path:
    caminho = pasta / f"{base}_{quando:%Y-%m-%d_%H%M}.sql.gz"
    caminho.write_bytes(b"x")
    return caminho


def _copias_de(pasta: Path) -> set[str]:
    return {c.name for c in pasta.glob("*.sql.gz")}


# ---------------------------------------------------------------------------
# O que fica e o que sai
# ---------------------------------------------------------------------------

def test_guarda_todas_as_dos_ultimos_catorze_dias(tmp_path: Path) -> None:
    for dias in range(0, 14):
        _criar(tmp_path, AGORA - timedelta(days=dias))

    backup.limpar_antigas(tmp_path, BASE, AGORA)

    assert len(_copias_de(tmp_path)) == 14


def test_de_um_ano_de_copias_diarias_sobra_um_historico_util(tmp_path: Path) -> None:
    """365 copias diarias entram; sai uma escada de dias, semanas e meses."""
    for dias in range(0, 365):
        _criar(tmp_path, AGORA - timedelta(days=dias))

    retiradas = backup.limpar_antigas(tmp_path, BASE, AGORA)
    ficaram = sorted(_copias_de(tmp_path))

    # Muito menos ficheiros...
    assert len(ficaram) < 40
    assert len(retiradas) > 300
    # ...mas com a copia de ontem, a da semana passada e a de ha' meses.
    assert f"{BASE}_{AGORA - timedelta(days=1):%Y-%m-%d_%H%M}.sql.gz" in ficaram
    assert any(
        (AGORA - timedelta(days=40)) <= backup._data_do_nome(tmp_path / nome) <= (AGORA - timedelta(days=20))
        for nome in ficaram
    )
    assert any(
        backup._data_do_nome(tmp_path / nome) <= AGORA - timedelta(days=150)
        for nome in ficaram
    )


def test_nunca_deixa_a_pasta_com_menos_de_tres_copias(tmp_path: Path) -> None:
    """Mesmo que sejam todas velhissimas, as tres mais recentes ficam.

    Sem esta rede, uma maquina que esteve meses desligada acordava, aplicava a
    regra e ficava sem copia nenhuma.
    """
    for anos in (3, 4, 5, 6, 7):
        _criar(tmp_path, AGORA - timedelta(days=365 * anos))

    backup.limpar_antigas(tmp_path, BASE, AGORA)

    assert len(_copias_de(tmp_path)) == backup.MINIMO_A_GUARDAR


def test_com_poucas_copias_nao_mexe_em_nada(tmp_path: Path) -> None:
    for anos in (5, 6):
        _criar(tmp_path, AGORA - timedelta(days=365 * anos))

    assert backup.limpar_antigas(tmp_path, BASE, AGORA) == []
    assert len(_copias_de(tmp_path)) == 2


# ---------------------------------------------------------------------------
# No que NAO pode tocar
# ---------------------------------------------------------------------------

def test_nao_toca_em_ficheiros_que_nao_sejam_copias_suas(tmp_path: Path) -> None:
    """A pasta pode ter mais coisas la' dentro. Nenhuma e' assunto deste script."""
    for dias in range(0, 200):
        _criar(tmp_path, AGORA - timedelta(days=dias))

    intrusos = [
        tmp_path / "orcamento_importante.pdf",
        tmp_path / "notas.txt",
        tmp_path / "martelo_v3_copia_a_mao.sql.gz",
        tmp_path / "backup_antigo_2024.sql",
    ]
    for caminho in intrusos:
        caminho.write_bytes(b"nao me apagues")

    backup.limpar_antigas(tmp_path, BASE, AGORA)

    for caminho in intrusos:
        assert caminho.exists(), caminho.name


def test_nao_toca_nas_copias_de_outra_base(tmp_path: Path) -> None:
    """Copiar a producao nao pode levar as copias do desenvolvimento."""
    for dias in range(0, 200):
        _criar(tmp_path, AGORA - timedelta(days=dias), base="martelo_v3")
        _criar(tmp_path, AGORA - timedelta(days=dias), base="martelo_v3_dev")

    backup.limpar_antigas(tmp_path, "martelo_v3", AGORA)

    dev = {c for c in _copias_de(tmp_path) if c.startswith("martelo_v3_dev")}
    assert len(dev) == 200


# ---------------------------------------------------------------------------
# Uma copia estragada nunca passa por boa
# ---------------------------------------------------------------------------

def _dump(pasta: Path, texto: str) -> Path:
    caminho = pasta / f"{BASE}_2026-08-28_0300.sql.gz"
    with gzip.open(caminho, "wt", encoding="utf-8") as ficheiro:
        ficheiro.write(texto)
    return caminho


def test_copia_vazia_e_recusada(tmp_path: Path) -> None:
    caminho = tmp_path / f"{BASE}_2026-08-28_0300.sql.gz"
    caminho.write_bytes(b"")

    with pytest.raises(SystemExit, match="vazia"):
        backup.verificar(caminho, 0)


def test_copia_cortada_a_meio_e_recusada(tmp_path: Path) -> None:
    """Sem o carimbo final, o dump parou a meio (disco cheio, rede a cair)."""
    caminho = _dump(tmp_path, "CREATE TABLE `orcamentos` (id INT);\n-- ficou a meio")

    with pytest.raises(SystemExit, match="cortada a meio"):
        backup.verificar(caminho, 1)


def test_copia_com_tabelas_a_menos_e_recusada(tmp_path: Path) -> None:
    caminho = _dump(
        tmp_path,
        "CREATE TABLE `orcamentos` (id INT);\n-- Dump completed on 2026-08-28\n",
    )

    with pytest.raises(SystemExit, match="tabelas"):
        backup.verificar(caminho, 59)


def test_copia_sem_procedimentos_e_recusada(tmp_path: Path) -> None:
    """E' o erro caro: a base restaura, mas ninguem consegue trabalhar nela."""
    caminho = _dump(
        tmp_path,
        "CREATE TABLE `orcamentos` (id INT);\n-- Dump completed on 2026-08-28\n",
    )

    with pytest.raises(SystemExit, match="procedimentos"):
        backup.verificar(caminho, 1, procedimentos_esperados=5)


def test_copia_completa_passa(tmp_path: Path) -> None:
    caminho = _dump(
        tmp_path,
        "CREATE TABLE `orcamentos` (id INT);\n"
        "CREATE TABLE `clientes` (id INT);\n"
        "CREATE DEFINER=`root`@`localhost` PROCEDURE `martelo_aplicar_grants`()\n"
        "-- Dump completed on 2026-08-28  3:00:01\n",
    )

    tabelas, rotinas = backup.verificar(caminho, 2, procedimentos_esperados=1)

    assert (tabelas, rotinas) == (2, 1)


# ---------------------------------------------------------------------------
# Com que conta e' que a copia se liga
# ---------------------------------------------------------------------------
#
# A copia deve usar a conta so' dela (le tudo, nao escreve nada). Se usar a de
# manutencao, o dump sai sem os procedimentos -- e uma base restaurada sem o
# martelo_aplicar_grants e' uma base onde nenhum colega consegue trabalhar.

def test_usa_a_conta_das_copias_quando_esta_configurada(monkeypatch) -> None:
    monkeypatch.setenv("BACKUP_DB_USER", "martelo_backup")
    monkeypatch.setenv("BACKUP_DB_PASSWORD", "seja-o-que-for")

    utilizador, password, propria = backup.credenciais_da_copia()

    assert (utilizador, password, propria) == ("martelo_backup", "seja-o-que-for", True)


def test_sem_conta_das_copias_recai_na_de_manutencao_e_avisa(monkeypatch) -> None:
    from app.config.settings import settings

    monkeypatch.delenv("BACKUP_DB_USER", raising=False)
    monkeypatch.delenv("BACKUP_DB_PASSWORD", raising=False)
    monkeypatch.setattr(settings, "DB_USER", "martelo_v3", raising=False)

    utilizador, _, propria = backup.credenciais_da_copia()

    # Recai, mas diz que nao e' a conta propria -- e' isso que faz sair o aviso.
    assert utilizador == "martelo_v3"
    assert propria is False


def test_restaurar_usa_sempre_a_conta_de_manutencao(monkeypatch) -> None:
    """Restaurar CRIA uma base: a conta das copias nao escreve, de proposito."""
    from app.config.settings import settings

    monkeypatch.setenv("BACKUP_DB_USER", "martelo_backup")
    monkeypatch.setattr(settings, "DB_USER", "martelo_v3", raising=False)

    assert backup.credenciais_de_manutencao()[0] == "martelo_v3"


def test_a_password_nao_vai_na_linha_de_comandos(tmp_path, monkeypatch) -> None:
    """Fica num ficheiro de opcoes: senao via-se no Gestor de Tarefas."""
    monkeypatch.setenv("BACKUP_DB_USER", "martelo_backup")
    monkeypatch.setenv("BACKUP_DB_PASSWORD", "password-secreta")

    caminho = backup._ficheiro_de_opcoes(tmp_path)
    conteudo = caminho.read_text(encoding="utf-8")

    assert "user=martelo_backup" in conteudo
    assert "password=password-secreta" in conteudo
    # E o ficheiro vive numa pasta temporaria, que desaparece no fim.
    assert caminho.parent == tmp_path
