"""Copia de seguranca da base de dados do Martelo V3.

PORQUE E' QUE ISTO EXISTE
-------------------------
A base vive num PC. A partir do momento em que dez pessoas gravam orcamentos
reais la' dentro, um disco que morra leva o trabalho de todos com ele. Este
script faz a copia, confirma que ela presta, guarda-a em dois sitios e deita
fora as antigas -- sozinho, todos os dias, sem ninguem se lembrar dele.

O QUE FAZ, POR ESTA ORDEM
-------------------------
  1. mysqldump da base (estrutura + dados + PROCEDIMENTOS)
  2. comprime para .sql.gz
  3. VERIFICA a copia: tem o carimbo de fim, tem as tabelas todas, abre
  4. copia para o segundo sitio (o servidor), se estiver configurado
  5. deita fora as antigas pela regra: 14 diarias, 8 semanais, 12 mensais

Se qualquer um dos passos 1-3 falhar, nao apaga nada e devolve erro.

COMO SE USA
-----------
    .venv\\Scripts\\python.exe scripts\\backup_martelo.py
    .venv\\Scripts\\python.exe scripts\\backup_martelo.py --base martelo_v3
    .venv\\Scripts\\python.exe scripts\\backup_martelo.py --copia "\\\\SERVER_LE\\...\\Backups_Martelo"
    .venv\\Scripts\\python.exe scripts\\backup_martelo.py --listar
    .venv\\Scripts\\python.exe scripts\\backup_martelo.py --testar-restauro

Para o correr todos os dias sozinho:
    powershell -ExecutionPolicy Bypass -File scripts\\instalar_backup_agendado.ps1

A PASSWORD NUNCA VAI NA LINHA DE COMANDOS. O `mysqldump` recebe-a por um
ficheiro temporario de opcoes, que e' apagado no fim -- caso contrario ficava
a` vista de qualquer pessoa que abrisse o Gestor de Tarefas.
"""

from __future__ import annotations

import argparse
import gzip
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402

#: Sitios habituais do mysqldump no Windows, por ordem de preferencia.
MYSQLDUMP_CANDIDATOS = (
    Path(r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"),
    Path(r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe"),
    Path(r"C:\Program Files (x86)\MySQL\MySQL Server 8.0\bin\mysqldump.exe"),
    Path(r"C:\xampp\mysql\bin\mysqldump.exe"),
)

#: Quantas copias guardar de cada escalao.
DIARIAS = 14
SEMANAIS = 8
MENSAIS = 12

#: Rede de seguranca: nunca deixar a pasta com menos do que isto.
MINIMO_A_GUARDAR = 3

#: Carimbo que o mysqldump poe na ultima linha quando correu ate' ao fim.
CARIMBO_FIM = "Dump completed"

PADRAO_NOME = re.compile(
    r"^(?P<base>.+)_(?P<data>\d{4}-\d{2}-\d{2})_(?P<hora>\d{4})\.sql\.gz$"
)


# ---------------------------------------------------------------------------
# Sitios
# ---------------------------------------------------------------------------

def pasta_local_por_omissao() -> Path:
    """Pasta local das copias (a rapida e sempre disponivel)."""
    raiz = (os.getenv("LOCALAPPDATA") or "").strip()
    base = Path(raiz) if raiz else Path.home()
    return base / "Martelo Orcamentos V3" / "backups"


def encontrar_mysqldump() -> Path:
    """Devolve o mysqldump.exe, ou explica onde e' que ele devia estar."""
    do_path = shutil.which("mysqldump")
    if do_path:
        return Path(do_path)

    for candidato in MYSQLDUMP_CANDIDATOS:
        if candidato.exists():
            return candidato

    raise SystemExit(
        "[ERRO] nao encontrei o mysqldump.exe.\n"
        "       Costuma estar em C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin\\.\n"
        "       Indique-o com --mysqldump C:\\caminho\\para\\mysqldump.exe"
    )


# ---------------------------------------------------------------------------
# A copia
# ---------------------------------------------------------------------------

def credenciais_da_copia() -> tuple[str, str, bool]:
    """A conta com que a copia se liga: ``(utilizador, password, e_a_propria)``.

    Prefere a conta so' das copias (``BACKUP_DB_USER`` / ``BACKUP_DB_PASSWORD``
    no ``.env``), que le tudo e nao escreve nada -- ver
    ``deploy/mysql_conta_copias.sql``. So' se ela nao estiver configurada e' que
    usa a conta de manutencao, e nesse caso avisa: e' a conta de manutencao que
    nao consegue ler os procedimentos, e uma copia sem eles nao serve.
    """
    utilizador = (os.getenv("BACKUP_DB_USER") or "").strip()
    password = os.getenv("BACKUP_DB_PASSWORD") or ""
    if utilizador:
        return utilizador, password, True

    return settings.DB_USER, settings.DB_PASSWORD, False


def credenciais_de_manutencao() -> tuple[str, str]:
    """A conta do ``.env``, para o que precisa de ESCRITA (restaurar um teste).

    A conta das copias nao serve aqui: nao escreve nada, de proposito.
    """
    return settings.DB_USER, settings.DB_PASSWORD


def _ficheiro_de_opcoes(
    pasta: Path, credenciais: tuple[str, str] | None = None
) -> Path:
    """Ficheiro temporario com a password, para ela nao ir na linha de comandos."""
    utilizador, password = credenciais or credenciais_da_copia()[:2]
    caminho = pasta / "my.cnf"
    caminho.write_text(
        "[client]\n"
        f"user={utilizador}\n"
        f"password={password}\n"
        f"host={settings.DB_HOST}\n"
        f"port={settings.DB_PORT}\n",
        encoding="utf-8",
    )
    return caminho


#: O que dizer quando a conta nao consegue ler os procedimentos.
AVISO_SHOW_ROUTINE = """
[ERRO] a conta '{conta}' nao consegue ler os procedimentos da base.

       Isto NAO e' um pormenor: e' em `martelo_aplicar_grants` que vive o que
       da' acesso as tabelas a`s contas dos colegas. Uma copia sem ele restaura
       uma base onde ninguem consegue trabalhar -- e so' se descobre no dia em
       que for precisa.

       Porque acontece: os procedimentos foram criados pelo root, e no MySQL 8
       ver o corpo de um procedimento alheio exige o privilegio SHOW_ROUTINE.

       Como resolver (uma vez, com a conta root):

           GRANT SHOW_ROUTINE ON *.* TO '{conta}'@'localhost';
           FLUSH PRIVILEGES;

       Melhor ainda: dar as copias uma conta so' delas, que le tudo e nao
       escreve nada -- ver deploy\\mysql_conta_copias.sql.
"""


def fazer_dump(
    base: str, destino: Path, mysqldump: Path, *, procedimentos: bool = True
) -> None:
    """Corre o mysqldump da base para ``destino`` (.sql.gz)."""
    destino.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="martelo_bk_") as temporaria:
        opcoes = _ficheiro_de_opcoes(Path(temporaria))
        comando = [
            str(mysqldump),
            f"--defaults-file={opcoes}",
            # Copia coerente sem trancar a base: quem estiver a trabalhar nao da'
            # por nada.
            "--single-transaction",
            "--triggers",
            "--events",
            # Sem isto o mysqldump 8.0 exige o privilegio PROCESS, que a conta de
            # manutencao nao tem: falhava com "Access denied ... PROCESS".
            "--no-tablespaces",
            "--default-character-set=utf8mb4",
            "--hex-blob",
        ]
        if procedimentos:
            # Os PROCEDIMENTOS sao a parte que toda a gente se esquece de copiar
            # -- e' la' que vive o martelo_aplicar_grants, sem o qual as contas
            # dos colegas ficam sem acesso as tabelas.
            comando.append("--routines")
        comando.append(base)

        # Escreve direto para o .gz: a base nunca chega a existir em claro no disco.
        with gzip.open(destino, "wb") as saida:
            processo = subprocess.Popen(
                comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            assert processo.stdout is not None
            for bloco in iter(lambda: processo.stdout.read(1 << 16), b""):
                saida.write(bloco)
            _, erro = processo.communicate()

    if processo.returncode != 0:
        if destino.exists():
            destino.unlink()
        texto = (erro or b"").decode("utf-8", errors="replace").strip()
        if "SHOW CREATE PROCEDURE" in texto or "SHOW_ROUTINE" in texto:
            raise SystemExit(
                AVISO_SHOW_ROUTINE.format(conta=credenciais_da_copia()[0])
            )
        raise SystemExit(f"[ERRO] o mysqldump falhou (codigo {processo.returncode}):\n{texto}")


def verificar(
    copia: Path, tabelas_esperadas: int, *, procedimentos_esperados: int = 0
) -> tuple[int, int]:
    """Confirma que a copia presta. Devolve (tabelas, procedimentos) encontrados.

    Uma copia que nao se le nao e' copia nenhuma. Isto abre mesmo o ficheiro,
    conta as tabelas e os procedimentos, e procura o carimbo que o mysqldump so'
    escreve quando chegou ao fim -- um dump cortado a meio (disco cheio, rede a
    cair) nao o tem.
    """
    if not copia.exists() or copia.stat().st_size == 0:
        raise SystemExit(f"[ERRO] a copia ficou vazia: {copia}")

    tabelas = 0
    rotinas = 0
    ultimas: list[str] = []
    try:
        with gzip.open(copia, "rt", encoding="utf-8", errors="replace") as ficheiro:
            for linha in ficheiro:
                if linha.startswith("CREATE TABLE"):
                    tabelas += 1
                elif "PROCEDURE" in linha and "CREATE" in linha:
                    rotinas += 1
                ultimas.append(linha)
                if len(ultimas) > 5:
                    ultimas.pop(0)
    except OSError as erro:
        raise SystemExit(f"[ERRO] a copia nao abre ({erro}): {copia}")

    fim = "".join(ultimas)
    if CARIMBO_FIM not in fim:
        raise SystemExit(
            f"[ERRO] a copia esta' cortada a meio (sem '{CARIMBO_FIM}'): {copia}\n"
            "       Espaco em disco? A base caiu a meio da copia?"
        )

    if tabelas_esperadas and tabelas < tabelas_esperadas:
        raise SystemExit(
            f"[ERRO] a copia so' tem {tabelas} tabelas, e a base tem "
            f"{tabelas_esperadas}: {copia}"
        )

    if procedimentos_esperados and rotinas < procedimentos_esperados:
        raise SystemExit(
            f"[ERRO] a copia so' tem {rotinas} procedimentos, e a base tem "
            f"{procedimentos_esperados}.\n"
            "       Sem eles, a base restaurada fica sem o martelo_aplicar_grants\n"
            f"       e ninguem consegue trabalhar nela: {copia}"
        )

    return tabelas, rotinas


def contar_na_base(base: str) -> tuple[int, int]:
    """Quantas tabelas e procedimentos a base tem agora (para conferir a copia)."""
    utilizador, password, _ = credenciais_da_copia()
    try:
        import pymysql

        ligacao = pymysql.connect(
            host=settings.DB_HOST,
            port=int(settings.DB_PORT),
            user=utilizador,
            password=password,
            connect_timeout=6,
        )
        with ligacao.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                (base,),
            )
            tabelas = int(cursor.fetchone()[0])
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.routines "
                "WHERE routine_schema = %s AND routine_type = 'PROCEDURE'",
                (base,),
            )
            rotinas = int(cursor.fetchone()[0])
        ligacao.close()
        return tabelas, rotinas
    except Exception:  # noqa: BLE001 -- sem isto a copia faz-se na mesma
        return 0, 0


# ---------------------------------------------------------------------------
# Segunda copia e limpeza
# ---------------------------------------------------------------------------

def copiar_para(copia: Path, pasta: Path) -> bool:
    """Leva a copia para o segundo sitio. Devolve se conseguiu."""
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        shutil.copy2(copia, pasta / copia.name)
        return True
    except OSError as erro:
        print(f"      AVISO: nao consegui copiar para {pasta}: {erro}")
        return False


def _data_do_nome(caminho: Path, base: str | None = None) -> datetime | None:
    """Data de uma copia, ou ``None`` se o ficheiro nao for uma copia desta base.

    Com ``base``, o nome tem de ser EXATAMENTE o desta base. Nao chega comecar
    por ela: `martelo_v3_dev_2026-08-14_0300.sql.gz` comeca por `martelo_v3_`,
    e sem esta verificacao copiar a producao deitava fora as copias do
    desenvolvimento.
    """
    encontrado = PADRAO_NOME.match(caminho.name)
    if not encontrado:
        return None
    if base is not None and encontrado.group("base") != base:
        return None
    try:
        return datetime.strptime(
            f"{encontrado.group('data')} {encontrado.group('hora')}", "%Y-%m-%d %H%M"
        )
    except ValueError:
        return None


def copias_da_base(pasta: Path, base: str) -> list[tuple[datetime, Path]]:
    """As copias desta base que estao nesta pasta, das mais recentes para tras."""
    encontradas = []
    for caminho in pasta.glob(f"{base}_*.sql.gz"):
        data = _data_do_nome(caminho, base)
        if data is not None:
            encontradas.append((data, caminho))
    encontradas.sort(key=lambda par: par[0], reverse=True)
    return encontradas


def escolher_a_guardar(copias: list[tuple[datetime, Path]], agora: datetime) -> set[Path]:
    """Decide quais ficam: 14 diarias, depois 1 por semana, depois 1 por mes."""
    guardar: set[Path] = set()

    # Todas as dos ultimos 14 dias.
    limite_diario = agora - timedelta(days=DIARIAS)
    for data, caminho in copias:
        if data >= limite_diario:
            guardar.add(caminho)

    # A mais recente de cada semana, nas ultimas 8 semanas.
    limite_semanal = agora - timedelta(weeks=SEMANAIS)
    por_semana: dict[tuple[int, int], tuple[datetime, Path]] = {}
    for data, caminho in copias:
        if data < limite_semanal:
            continue
        chave = data.isocalendar()[:2]
        if chave not in por_semana or data > por_semana[chave][0]:
            por_semana[chave] = (data, caminho)
    guardar.update(caminho for _, caminho in por_semana.values())

    # A mais recente de cada mes, nos ultimos 12 meses.
    limite_mensal = agora - timedelta(days=31 * MENSAIS)
    por_mes: dict[tuple[int, int], tuple[datetime, Path]] = {}
    for data, caminho in copias:
        if data < limite_mensal:
            continue
        chave = (data.year, data.month)
        if chave not in por_mes or data > por_mes[chave][0]:
            por_mes[chave] = (data, caminho)
    guardar.update(caminho for _, caminho in por_mes.values())

    return guardar


def limpar_antigas(pasta: Path, base: str, agora: datetime) -> list[Path]:
    """Deita fora as copias que ja' nao sao precisas. Devolve as que tirou.

    Duas redes de seguranca: so' mexe em ficheiros com o nome exato que este
    script gera (nunca em mais nada que esteja na pasta), e nunca deixa a pasta
    com menos de tres copias, aconteca o que acontecer.
    """
    copias = copias_da_base(pasta, base)

    if len(copias) <= MINIMO_A_GUARDAR:
        return []

    guardar = escolher_a_guardar(copias, agora)

    # Mesmo que a regra diga para tirar quase tudo, as mais recentes ficam.
    guardar.update(caminho for _, caminho in copias[:MINIMO_A_GUARDAR])

    retiradas = []
    for _, caminho in copias:
        if caminho not in guardar:
            caminho.unlink()
            retiradas.append(caminho)
    return retiradas


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def listar(pasta: Path, base: str) -> None:
    copias = copias_da_base(pasta, base)
    if not copias:
        print(f"Nao ha' copias de {base} em {pasta}")
        return

    print(f"Copias de {base} em {pasta}\n")
    total = 0
    for data, caminho in copias:
        tamanho = caminho.stat().st_size
        total += tamanho
        print(f"  {data:%Y-%m-%d %H:%M}   {tamanho/1024/1024:6.2f} MB   {caminho.name}")
    print(f"\n  {len(copias)} copias, {total/1024/1024:.1f} MB no total")
    print(f"  Mais recente: ha' {datetime.now() - copias[0][0]}")


def testar_restauro(copia: Path, mysqldump: Path) -> None:
    """Restaura a copia para uma base descartavel e conta o que la' ficou.

    E' o unico teste que conta: uma copia que nunca se experimentou restaurar
    e' uma copia que ainda nao se sabe se serve. Cria uma base
    ``martelo_restauro_teste``, enche-a, conta as tabelas e deixa-a la' para o
    Paulo confirmar e apagar quando quiser.
    """
    import pymysql

    nome = "martelo_restauro_teste"
    mysql = mysqldump.parent / "mysql.exe"
    if not mysql.exists():
        raise SystemExit(f"[ERRO] nao encontrei o mysql.exe ao lado de {mysqldump}")

    print(f"[1/3] criar a base de teste {nome}")
    # Restaurar cria uma base e escreve nela: a conta das copias nao serve
    # (nao escreve nada, de proposito). Aqui vai a de manutencao.
    manutencao = credenciais_de_manutencao()
    ligacao = pymysql.connect(
        host=settings.DB_HOST, port=int(settings.DB_PORT),
        user=manutencao[0], password=manutencao[1], connect_timeout=6,
    )
    with ligacao.cursor() as cursor:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{nome}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    ligacao.commit()

    print(f"[2/3] restaurar {copia.name}")
    with tempfile.TemporaryDirectory(prefix="martelo_rst_") as temporaria:
        opcoes = _ficheiro_de_opcoes(Path(temporaria), manutencao)
        with gzip.open(copia, "rb") as entrada:
            processo = subprocess.Popen(
                [str(mysql), f"--defaults-file={opcoes}", nome],
                stdin=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            assert processo.stdin is not None
            shutil.copyfileobj(entrada, processo.stdin)
            processo.stdin.close()
            _, erro = processo.communicate()

    if processo.returncode != 0:
        texto = (erro or b"").decode("utf-8", errors="replace").strip()
        raise SystemExit(f"[ERRO] o restauro falhou:\n{texto}")

    print("[3/3] conferir")
    with ligacao.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = %s AND table_type = 'BASE TABLE'", (nome,)
        )
        tabelas = int(cursor.fetchone()[0])
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = %s",
            (nome,),
        )
        procedimentos = int(cursor.fetchone()[0])
        try:
            cursor.execute(f"SELECT version_num FROM `{nome}`.alembic_version")
            migracao = cursor.fetchone()[0]
        except Exception:  # noqa: BLE001
            migracao = "?"
    ligacao.close()

    print(f"\n      OK: {tabelas} tabelas, {procedimentos} procedimentos, migracao {migracao}")
    print(f"      A base de teste `{nome}` ficou na base de dados.")
    print("      Confirme-a no Workbench e apague-a quando quiser.")


class Registo:
    """Escreve no ecra e no ficheiro ao mesmo tempo.

    A copia corre de madrugada, sozinha. Sem isto ninguem sabe se correu, e
    descobre-se no pior dia possivel que ha' seis meses que falha.
    """

    def __init__(self, caminho: Path) -> None:
        self.caminho = caminho
        self.linhas: list[str] = []

    def __call__(self, texto: str = "") -> None:
        print(texto)
        self.linhas.append(texto)

    def fechar(self, resultado: str) -> None:
        carimbo = f"{datetime.now():%Y-%m-%d %H:%M:%S}"
        try:
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            with self.caminho.open("a", encoding="utf-8") as ficheiro:
                ficheiro.write(f"\n===== {carimbo} — {resultado} =====\n")
                ficheiro.write("\n".join(self.linhas) + "\n")
        except OSError:
            pass


def escrever_estado(pasta: Path, texto: str) -> None:
    """Uma linha, num ficheiro, a dizer como correu a ultima copia.

    E' o sitio para onde olhar (ou apontar um alerta) sem ter de ler o registo
    todo: `ultima_copia.txt`, na pasta das copias.
    """
    try:
        (pasta / "ultima_copia.txt").write_text(
            f"{datetime.now():%Y-%m-%d %H:%M:%S}  {texto}\n", encoding="utf-8"
        )
    except OSError:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Copia de seguranca do Martelo V3")
    ap.add_argument("--base", default=settings.DB_NAME, help="base a copiar")
    ap.add_argument("--pasta", type=Path, default=None, help="pasta local das copias")
    ap.add_argument("--copia", type=Path, default=None,
                    help="segunda pasta (servidor) -- e' esta que salva de um disco morto")
    ap.add_argument("--mysqldump", type=Path, default=None)
    ap.add_argument("--listar", action="store_true", help="mostrar as copias e sair")
    ap.add_argument("--testar-restauro", action="store_true",
                    help="restaurar a copia mais recente para uma base descartavel")
    ap.add_argument("--sem-limpeza", action="store_true",
                    help="nao deitar fora nenhuma copia antiga")
    ap.add_argument("--sem-procedimentos", action="store_true",
                    help="copia SEM os procedimentos (so' para emergencia -- a base "
                         "restaurada fica sem o martelo_aplicar_grants)")
    args = ap.parse_args()

    pasta = args.pasta or pasta_local_por_omissao()
    pasta.mkdir(parents=True, exist_ok=True)

    if args.listar:
        listar(pasta, args.base)
        return 0

    mysqldump = args.mysqldump or encontrar_mysqldump()

    if args.testar_restauro:
        copias = copias_da_base(pasta, args.base)
        if not copias:
            raise SystemExit(f"[ERRO] nao ha' nenhuma copia de {args.base} em {pasta}")
        testar_restauro(copias[0][1], mysqldump)
        return 0

    agora = datetime.now()
    nome = f"{args.base}_{agora:%Y-%m-%d_%H%M}.sql.gz"
    destino = pasta / nome
    log = Registo(pasta / "backup.log")

    log(f"Martelo V3 — copia de seguranca de {args.base}")
    log(f"  {agora:%Y-%m-%d %H:%M:%S}")
    conta, _, conta_propria = credenciais_da_copia()
    log(f"  conta: {conta}" + ("" if conta_propria else "   <-- ver aviso"))
    if not conta_propria:
        log("      AVISO: nao ha' conta so' das copias configurada. Esta a usar")
        log("             a conta de MANUTENCAO, que costuma nao conseguir ler")
        log("             os procedimentos -- e uma copia sem eles nao serve.")
        log("             Ponha BACKUP_DB_USER e BACKUP_DB_PASSWORD no .env")
        log("             (a conta do deploy\\mysql_conta_copias.sql).")
    log()

    try:
        com_procedimentos = not args.sem_procedimentos
        tabelas_na_base, rotinas_na_base = contar_na_base(args.base)
        log(f"[1/4] mysqldump ({tabelas_na_base or '?'} tabelas, "
            f"{rotinas_na_base or '?'} procedimentos)")
        if not com_procedimentos:
            log("      AVISO: --sem-procedimentos. Esta copia NAO serve para")
            log("             restaurar a base a serio; e' so' para os dados.")
        fazer_dump(args.base, destino, mysqldump, procedimentos=com_procedimentos)
        megabytes = destino.stat().st_size / 1024 / 1024
        log(f"      OK -> {destino}  ({megabytes:.2f} MB)")

        log("[2/4] verificar a copia")
        tabelas, rotinas = verificar(
            destino,
            tabelas_na_base,
            procedimentos_esperados=rotinas_na_base if com_procedimentos else 0,
        )
        log(f"      OK: {tabelas} tabelas, {rotinas} procedimentos, com o carimbo de fim")

        log("[3/4] segunda copia")
        segunda = False
        if args.copia:
            segunda = copiar_para(destino, args.copia)
            if segunda:
                log(f"      OK -> {args.copia / nome}")
            else:
                log(f"      AVISO: nao consegui copiar para {args.copia}")
        else:
            log("      AVISO: sem segundo sitio (--copia).")
            log("             Uma copia que vive no mesmo disco que a base nao")
            log("             protege de nada quando e' o disco que morre.")

        log("[4/4] arrumar as antigas")
        if args.sem_limpeza:
            log("      saltado (--sem-limpeza)")
        else:
            for pasta_alvo in filter(None, (pasta, args.copia)):
                try:
                    retiradas = limpar_antigas(Path(pasta_alvo), args.base, agora)
                except OSError as erro:
                    log(f"      AVISO: nao consegui arrumar {pasta_alvo}: {erro}")
                    continue
                if retiradas:
                    log(f"      {pasta_alvo}: tirei {len(retiradas)}")
                    for caminho in retiradas:
                        log(f"        - {caminho.name}")
                else:
                    log(f"      {pasta_alvo}: nada a tirar")

    except SystemExit as erro:
        # A copia falhou. Fica escrito no registo e no ficheiro de estado, para
        # a falha nao passar despercebida ate' ao dia em que a copia e' precisa.
        log(str(erro))
        log()
        log("FALHOU.")
        log.fechar("FALHOU")
        escrever_estado(pasta, f"FALHOU a copia de {args.base} — ver backup.log")
        raise

    aviso = "" if (args.copia and segunda) else "  (SEM segunda copia)"
    log()
    log("Concluido.")
    log.fechar("OK")
    escrever_estado(pasta, f"OK — {args.base}, {megabytes:.2f} MB{aviso}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
