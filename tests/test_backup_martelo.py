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
# Para onde vai a segunda copia
# ---------------------------------------------------------------------------

def test_a_segunda_copia_vai_para_a_pasta_de_backups_do_servidor() -> None:
    """Desde 04-10-2026 vive junto dos outros backups da empresa."""
    assert backup.PASTA_SERVIDOR == Path(r"\\SERVER_LE\Backup\Backup_Martelo_V3")
    assert backup.ler_argumentos([]).copia == backup.PASTA_SERVIDOR


def test_a_pasta_antiga_dentro_de_base_dados_orcamento_deixou_de_ser_usada() -> None:
    assert "Base_Dados_Orcamento" not in str(backup.PASTA_SERVIDOR)


def test_sem_copia_fica_so_no_pc() -> None:
    assert backup.ler_argumentos(["--sem-copia"]).copia is None


def test_copia_pode_ir_para_outro_sitio(tmp_path: Path) -> None:
    assert backup.ler_argumentos(["--copia", str(tmp_path)]).copia == tmp_path


def test_o_instalador_da_tarefa_usa_a_mesma_pasta_do_servidor() -> None:
    """Se um mudar e o outro nao, a tarefa agendada volta a escrever no sitio velho."""
    instalador = (RAIZ / "scripts" / "instalar_backup_agendado.ps1").read_text(encoding="utf-8")
    assert f'[string]$Copia = "{backup.PASTA_SERVIDOR}"' in instalador
    assert "Base_Dados_Orcamento" not in instalador


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


# ---------------------------------------------------------------------------
# Memoria do Claude (pedida pelo Paulo a 04-10-2026)
# ---------------------------------------------------------------------------
#
# A memoria so' existe neste PC. Vai todas as noites, num .zip, para a
# subpasta Memoria_Claude dos dois sitios -- e nunca pode deitar abaixo a
# copia da base.

def _memoria(pasta: Path) -> Path:
    pasta.mkdir(parents=True)
    (pasta / "MEMORY.md").write_text("# Memory Index\n- [Regra](regra.md)\n", encoding="utf-8")
    (pasta / "regra.md").write_text("---\nname: regra\n---\nTexto com acentos: ção\n", encoding="utf-8")
    (pasta / "sub").mkdir()
    (pasta / "sub" / "outra.md").write_text("outra", encoding="utf-8")
    return pasta


def _zip_memoria(pasta: Path, quando: datetime) -> Path:
    caminho = pasta / f"memoria_claude_{quando:%Y-%m-%d_%H%M}.zip"
    caminho.write_bytes(b"x")
    return caminho


def test_a_pasta_da_memoria_e_a_do_projeto_principal() -> None:
    """O nome e' o caminho do projeto com o que nao e' letra/algarismo a '-'."""
    principal = Path(r"C:\Users\Utilizador\Documents\Martelo_Orcamentos_V3")
    esperado = (
        Path.home() / ".claude" / "projects"
        / "C--Users-Utilizador-Documents-Martelo-Orcamentos-V3" / "memory"
    )

    assert backup.pasta_memoria_por_omissao(principal) == esperado


def test_num_worktree_a_memoria_continua_a_ser_a_da_pasta_principal() -> None:
    principal = Path(r"C:\Users\Utilizador\Documents\Martelo_Orcamentos_V3")
    worktree = principal / ".claude" / "worktrees" / "algum-trabalho-1a2b3c"

    assert backup.pasta_memoria_por_omissao(worktree) == backup.pasta_memoria_por_omissao(principal)


def test_por_omissao_a_memoria_vai_e_sem_memoria_desliga(tmp_path: Path) -> None:
    assert backup.ler_argumentos([]).memoria == backup.pasta_memoria_por_omissao()
    assert backup.ler_argumentos(["--sem-memoria"]).memoria is None
    assert backup.ler_argumentos(["--memoria", str(tmp_path)]).memoria == tmp_path


def test_o_zip_leva_todos_os_ficheiros_e_confere(tmp_path: Path) -> None:
    import zipfile

    origem = _memoria(tmp_path / "memory")

    destino, quantos = backup.comprimir_memoria(origem, tmp_path / "copias", AGORA)

    assert quantos == 3
    assert destino.name == "memoria_claude_2026-08-28_0300.zip"
    with zipfile.ZipFile(destino) as entrada:
        assert set(entrada.namelist()) == {"MEMORY.md", "regra.md", "sub/outra.md"}
        assert "ção" in entrada.read("regra.md").decode("utf-8")


def test_memoria_vazia_nao_deixa_zip_nenhum(tmp_path: Path) -> None:
    origem = tmp_path / "memory"
    origem.mkdir()

    with pytest.raises(OSError, match="vazia"):
        backup.comprimir_memoria(origem, tmp_path / "copias", AGORA)

    assert not list(tmp_path.rglob("*.zip"))


def test_a_memoria_vai_para_a_subpasta_dos_dois_sitios(tmp_path: Path) -> None:
    origem = _memoria(tmp_path / "memory")
    local, servidor = tmp_path / "local", tmp_path / "servidor"
    linhas: list[str] = []

    correu_bem = backup.guardar_memoria(origem, [local, servidor], AGORA, linhas.append)

    assert correu_bem is True
    nome = "memoria_claude_2026-08-28_0300.zip"
    assert (local / backup.SUBPASTA_MEMORIA / nome).exists()
    assert (servidor / backup.SUBPASTA_MEMORIA / nome).exists()


def test_sem_memoria_e_so_aviso_nunca_erro(tmp_path: Path) -> None:
    """A copia da base e' o que importa: a memoria em falta nao a deita abaixo."""
    linhas: list[str] = []

    correu_bem = backup.guardar_memoria(
        tmp_path / "nao_existe", [tmp_path / "local"], AGORA, linhas.append
    )

    assert correu_bem is False
    assert any("AVISO" in linha for linha in linhas)


def test_servidor_inacessivel_e_so_aviso(tmp_path: Path, monkeypatch) -> None:
    origem = _memoria(tmp_path / "memory")
    monkeypatch.setattr(backup, "copiar_para", lambda copia, pasta: False)
    linhas: list[str] = []

    correu_bem = backup.guardar_memoria(
        origem, [tmp_path / "local", tmp_path / "servidor"], AGORA, linhas.append
    )

    assert correu_bem is False
    # A copia local ficou feita na mesma.
    assert list((tmp_path / "local" / backup.SUBPASTA_MEMORIA).glob("*.zip"))


def test_rotacao_da_memoria_segue_a_regra_da_base(tmp_path: Path) -> None:
    for dias in range(0, 365):
        _zip_memoria(tmp_path, AGORA - timedelta(days=dias))

    retiradas = backup.limpar_memorias_antigas(tmp_path, AGORA)

    ficaram = list(tmp_path.glob("*.zip"))
    assert len(ficaram) < 40
    assert len(retiradas) > 300
    assert (tmp_path / f"memoria_claude_{AGORA - timedelta(days=1):%Y-%m-%d_%H%M}.zip").exists()


def test_rotacao_da_memoria_nunca_deixa_menos_de_tres(tmp_path: Path) -> None:
    for anos in (3, 4, 5, 6, 7):
        _zip_memoria(tmp_path, AGORA - timedelta(days=365 * anos))

    backup.limpar_memorias_antigas(tmp_path, AGORA)

    assert len(list(tmp_path.glob("*.zip"))) == backup.MINIMO_A_GUARDAR


def test_rotacao_da_memoria_nao_toca_no_que_nao_e_seu(tmp_path: Path) -> None:
    """A copia feita a mao a 04-10 (uma pasta) e outros ficheiros ficam sempre."""
    for dias in range(0, 200):
        _zip_memoria(tmp_path, AGORA - timedelta(days=dias))
        _criar(tmp_path, AGORA - timedelta(days=dias))
    copia_a_mao = tmp_path / "memoria_2026-10-04"
    copia_a_mao.mkdir()
    (copia_a_mao / "MEMORY.md").write_text("indice", encoding="utf-8")
    intrusos = [tmp_path / "memoria_claude_feita_a_mao.zip", tmp_path / "notas.zip"]
    for caminho in intrusos:
        caminho.write_bytes(b"nao me apagues")

    backup.limpar_memorias_antigas(tmp_path, AGORA)

    assert (copia_a_mao / "MEMORY.md").exists()
    for caminho in intrusos:
        assert caminho.exists(), caminho.name
    # E as copias da base nao entram nesta rotacao.
    assert len(_copias_de(tmp_path)) == 200


def test_rotacao_da_base_nao_toca_nos_zips_da_memoria(tmp_path: Path) -> None:
    for dias in range(0, 200):
        _zip_memoria(tmp_path, AGORA - timedelta(days=dias))
        _criar(tmp_path, AGORA - timedelta(days=dias))

    backup.limpar_antigas(tmp_path, BASE, AGORA)

    assert len(list(tmp_path.glob("memoria_claude_*.zip"))) == 200
