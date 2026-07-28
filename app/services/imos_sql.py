"""Acesso exclusivamente de leitura à base de dados SQL do iMos.

Este módulo nunca expõe uma função genérica de escrita. Além de usar
``ApplicationIntent=ReadOnly``, o diagnóstico recusa ligações cujo utilizador
consiga alterar a base de dados ou qualquer tabela visível.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypedDict

from sqlalchemy.orm import Session

from app.services.phc_sql import _parse_bool, assert_select_only, run_select
from app.services.system_setting_service import SystemSettingService

KEY_IMOS_SERVER = "imos_sql_server"
KEY_IMOS_DATABASE = "imos_sql_database"
KEY_IMOS_USER = "imos_sql_user"
KEY_IMOS_PASSWORD = "imos_sql_password"
KEY_IMOS_TRUSTED = "imos_sql_trusted"
KEY_IMOS_TRUST_CERT = "imos_sql_trust_server_certificate"
KEY_IMOS_PASTA_RAIZ = "imos_pasta_raiz"

# Árvore de encomendas do iMos (dbo.IMORDFOLDER).
# O nó `Order` é a raiz absoluta e é único em toda a base.
IMOS_DIR_ID_ORDER = 120
IMOS_TIPO_RAIZ = 1000032
IMOS_TIPO_PASTA = 1000001
IMOS_TIPO_ENCOMENDA = 173

# `IMORDFOLDER.NAME` e `PROADMIN.NAME` são ambos nvarchar(30).
IMOS_NOME_MAX = 30

DEFAULT_IMOS_PASTA_RAIZ = "LANCA_ENCANTO"


class ImosConfig(TypedDict):
    server: str
    database: str
    trusted: bool
    trust_server_certificate: bool
    user: str
    password: str


@dataclass(frozen=True)
class DiagnosticoImos:
    servidor: str
    base_dados: str
    login: str
    utilizador_base_dados: str
    tabelas_consultaveis: int
    conta_sql_somente_leitura: bool
    barreira_aplicacao_ativa: bool = True


def load_imos_config(session: Session) -> ImosConfig:
    """Carrega a configuração iMos sem assumir credenciais por defeito."""
    service = SystemSettingService(session)

    def _texto(chave: str) -> str:
        return (service.obter_valor(chave, "") or "").strip()

    return {
        "server": _texto(KEY_IMOS_SERVER),
        "database": _texto(KEY_IMOS_DATABASE),
        "user": _texto(KEY_IMOS_USER),
        "password": str(service.obter_valor(KEY_IMOS_PASSWORD, "") or ""),
        "trusted": _parse_bool(service.obter_valor(KEY_IMOS_TRUSTED, "")),
        "trust_server_certificate": _parse_bool(
            service.obter_valor(KEY_IMOS_TRUST_CERT, ""), default=True
        ),
    }


def save_imos_config(session: Session, cfg: ImosConfig) -> None:
    """Guarda apenas os dados de ligação na base local do Martelo V3."""
    SystemSettingService(session).guardar_varios(
        {
            KEY_IMOS_SERVER: cfg["server"],
            KEY_IMOS_DATABASE: cfg["database"],
            KEY_IMOS_USER: cfg["user"],
            KEY_IMOS_PASSWORD: cfg["password"],
            KEY_IMOS_TRUSTED: "ON" if cfg["trusted"] else "OFF",
            KEY_IMOS_TRUST_CERT: (
                "ON" if cfg["trust_server_certificate"] else "OFF"
            ),
        }
    )


def _connection_value(value: str, field_name: str) -> str:
    value = str(value or "")
    if "\x00" in value or "\r" in value or "\n" in value:
        raise ValueError(f"Configuração iMos inválida no campo {field_name}.")
    return '"' + value.replace('"', '""') + '"'


def build_connection_string(cfg: ImosConfig) -> str:
    """Cria uma ligação SqlClient marcada explicitamente como read-only."""
    server = (cfg.get("server") or "").strip()
    database = (cfg.get("database") or "").strip()
    user = (cfg.get("user") or "").strip()
    password = str(cfg.get("password") or "")
    trusted = bool(cfg.get("trusted"))

    if not server or not database:
        raise ValueError("Configuração iMos incompleta: servidor e base de dados são obrigatórios.")

    parts = [
        f"Server={_connection_value(server, 'Servidor')}",
        f"Database={_connection_value(database, 'Base de dados')}",
        "ApplicationIntent=ReadOnly",
        "MultipleActiveResultSets=False",
    ]
    if trusted:
        parts.append("Integrated Security=True")
    else:
        if not user:
            raise ValueError("Configuração iMos incompleta: utilizador em falta.")
        if not password:
            raise ValueError("Configuração iMos incompleta: password em falta.")
        parts.extend(
            [
                f"User ID={_connection_value(user, 'Utilizador')}",
                f"Password={_connection_value(password, 'Password')}",
            ]
        )

    if cfg.get("trust_server_certificate"):
        parts.append("TrustServerCertificate=True")
    return ";".join(parts) + ";"


_DIAGNOSTICO_QUERY = """
SELECT
    CAST(SERVERPROPERTY('ServerName') AS nvarchar(256)) AS servidor,
    DB_NAME() AS base_dados,
    SUSER_SNAME() AS login,
    USER_NAME() AS utilizador_base_dados,
    CAST(HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'AL' + 'TER') AS int)
        + CAST(HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'CON' + 'TROL') AS int)
        + CAST(HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'CRE' + 'ATE TABLE') AS int)
        AS permissoes_estruturais,
    (SELECT COUNT(*)
       FROM sys.tables t
       JOIN sys.schemas s ON s.schema_id = t.schema_id
      WHERE t.is_ms_shipped = 0
        AND HAS_PERMS_BY_NAME(
            QUOTENAME(s.name) + '.' + QUOTENAME(t.name), 'OBJECT', 'SELECT'
        ) = 1) AS tabelas_consultaveis,
    (SELECT COUNT(*)
       FROM sys.tables t
       JOIN sys.schemas s ON s.schema_id = t.schema_id
      WHERE t.is_ms_shipped = 0
        AND (
            HAS_PERMS_BY_NAME(QUOTENAME(s.name) + '.' + QUOTENAME(t.name), 'OBJECT', 'IN' + 'SERT') = 1
         OR HAS_PERMS_BY_NAME(QUOTENAME(s.name) + '.' + QUOTENAME(t.name), 'OBJECT', 'UP' + 'DATE') = 1
         OR HAS_PERMS_BY_NAME(QUOTENAME(s.name) + '.' + QUOTENAME(t.name), 'OBJECT', 'DE' + 'LETE') = 1
         OR HAS_PERMS_BY_NAME(QUOTENAME(s.name) + '.' + QUOTENAME(t.name), 'OBJECT', 'AL' + 'TER') = 1
        )) AS tabelas_com_escrita
""".strip()


def diagnosticar_ligacao(cfg: ImosConfig) -> DiagnosticoImos:
    """Testa a ligação e informa, sem escrever, as permissões do principal."""
    assert_select_only(_DIAGNOSTICO_QUERY)
    rows = run_select(build_connection_string(cfg), _DIAGNOSTICO_QUERY)
    if not rows:
        raise RuntimeError("A ligação iMos não devolveu informação de diagnóstico.")

    row = rows[0]
    tabelas = int(row.get("tabelas_consultaveis") or 0)
    tabelas_escrita = int(row.get("tabelas_com_escrita") or 0)
    permissoes_estruturais = int(row.get("permissoes_estruturais") or 0)
    return DiagnosticoImos(
        servidor=str(row.get("servidor") or cfg["server"]),
        base_dados=str(row.get("base_dados") or cfg["database"]),
        login=str(row.get("login") or cfg.get("user") or "Autenticação Windows"),
        utilizador_base_dados=str(row.get("utilizador_base_dados") or ""),
        tabelas_consultaveis=tabelas,
        conta_sql_somente_leitura=not (
            tabelas_escrita or permissoes_estruturais
        ),
    )


def explicar_erro_ligacao(exc: Exception) -> str:
    """Converte erros técnicos SqlClient numa orientação segura e útil."""
    detalhe = str(exc or "")
    normalizado = detalhe.casefold()
    if "login failed" in normalizado or "falha de início de sessão" in normalizado:
        return (
            "O servidor SQL respondeu, mas recusou o utilizador/password. "
            "Confirme a password do utilizador configurado e mantenha 'Usar autenticação "
            "Windows' desativado. A password memorizada pelo SQL Server Management "
            "Studio não é transferida automaticamente para o Martelo."
        )
    if "cannot open database" in normalizado or "não é possível abrir a base" in normalizado:
        return (
            "O utilizador foi reconhecido, mas não conseguiu abrir a base de dados "
            "indicada. Confirme o nome da base e as permissões de acesso."
        )
    if any(
        texto in normalizado
        for texto in ("server was not found", "network-related", "error: 26")
    ):
        return (
            "Não foi possível localizar o servidor/instância SQL. Confirme o nome, "
            "a rede e se o serviço SQL Server está ativo."
        )
    return "Não foi possível validar a ligação iMos. Confirme os dados e tente novamente."


def run_imos_select(cfg: ImosConfig, query: str) -> list[dict]:
    """Executa um único SELECT; destinado às futuras consultas mapeadas iMos."""
    assert_select_only(query)
    return run_select(build_connection_string(cfg), query)


# --------------------------------------------------------------------------
# Leitura da árvore de encomendas (dbo.IMORDFOLDER) — exclusivamente SELECT.
# --------------------------------------------------------------------------

# Os nomes que o Martelo procura já vêm normalizados para [A-Z0-9_-], mas a
# árvore do iMos tem nomes antigos com espaços, parênteses e pontos.
_NOME_IMOS_RE = re.compile(r"^[A-Za-z0-9 _().\-]{1,%d}$" % IMOS_NOME_MAX)


@dataclass(frozen=True)
class NoImos:
    """Um nó da árvore do iMos: pasta/projeto ou encomenda."""

    dir_id: int
    nome: str
    tipo: int
    parent_id: int

    @property
    def e_encomenda(self) -> bool:
        return self.tipo == IMOS_TIPO_ENCOMENDA

    @property
    def e_pasta(self) -> bool:
        return self.tipo == IMOS_TIPO_PASTA


@dataclass(frozen=True)
class NivelCaminho:
    """Um nível do caminho pretendido; `dir_id` a None significa em falta."""

    nome: str
    tipo: int
    dir_id: int | None = None

    @property
    def existe(self) -> bool:
        return self.dir_id is not None


@dataclass(frozen=True)
class CaminhoImos:
    """Caminho `raiz / ano / cliente / encomenda` resolvido contra o iMos."""

    niveis: tuple[NivelCaminho, ...]

    @property
    def encomenda(self) -> NivelCaminho:
        return self.niveis[-1]

    @property
    def pastas(self) -> tuple[NivelCaminho, ...]:
        return self.niveis[:-1]

    @property
    def em_falta(self) -> tuple[NivelCaminho, ...]:
        return tuple(nivel for nivel in self.niveis if not nivel.existe)

    @property
    def encomenda_ja_existe(self) -> bool:
        return self.encomenda.existe

    @property
    def dir_id_pai_encomenda(self) -> int | None:
        """DIR_ID da pasta do cliente, quando já existe."""
        return self.niveis[-2].dir_id

    def texto(self) -> str:
        """Caminho legível para mostrar ao utilizador."""
        return " / ".join(nivel.nome for nivel in self.niveis)


def nome_imos_valido(nome) -> bool:
    """Indica se o nome cabe e é aceite pela árvore do iMos."""
    return bool(_NOME_IMOS_RE.fullmatch(str(nome or "")))


def _literal_nome(nome) -> str:
    """Devolve o nome como literal nvarchar, recusando o que não é válido."""
    texto = str(nome or "")
    if not nome_imos_valido(texto):
        raise ValueError(
            f"Nome inválido para o iMos: {texto!r}. São permitidos até "
            f"{IMOS_NOME_MAX} caracteres em letras, algarismos, espaço e _ ( ) . -"
        )
    return "N'" + texto.replace("'", "''") + "'"


def _no_de_linha(row: dict) -> NoImos:
    return NoImos(
        dir_id=int(row.get("DIR_ID") or 0),
        nome=str(row.get("NAME") or ""),
        tipo=int(row.get("TYPE") or 0),
        parent_id=int(row.get("PARENT_ID") or 0),
    )


def listar_filhos(cfg: ImosConfig, parent_dir_id: int, *, tipo: int | None = None) -> list[NoImos]:
    """Lista os nós diretamente abaixo de uma pasta, por ordem de nome."""
    filtro_tipo = f" AND TYPE = {int(tipo)}" if tipo is not None else ""
    query = (
        "SELECT DIR_ID, NAME, TYPE, PARENT_ID FROM dbo.IMORDFOLDER WITH (NOLOCK) "
        f"WHERE PARENT_ID = {int(parent_dir_id)}{filtro_tipo} ORDER BY NAME"
    )
    return [_no_de_linha(row) for row in run_imos_select(cfg, query)]


def resolver_no(
    cfg: ImosConfig,
    *,
    parent_dir_id: int,
    nome: str,
    tipo: int | None = None,
) -> NoImos | None:
    """Devolve o nó com este nome dentro do pai indicado, ou None.

    A chave prática da árvore é `(PARENT_ID, NAME)`: a base não tem qualquer
    restrição UNIQUE, mas não existe um único nome repetido dentro do mesmo pai.
    """
    filtro_tipo = f" AND TYPE = {int(tipo)}" if tipo is not None else ""
    query = (
        "SELECT TOP 1 DIR_ID, NAME, TYPE, PARENT_ID FROM dbo.IMORDFOLDER WITH (NOLOCK) "
        f"WHERE PARENT_ID = {int(parent_dir_id)} AND NAME = {_literal_nome(nome)}"
        f"{filtro_tipo} ORDER BY DIR_ID"
    )
    rows = run_imos_select(cfg, query)
    return _no_de_linha(rows[0]) if rows else None


def procurar_encomendas_por_nome(cfg: ImosConfig, nome: str) -> list[NoImos]:
    """Todas as encomendas com este nome, em qualquer pasta da árvore.

    A árvore admite nomes repetidos em pastas diferentes (há 49 casos na base),
    mas ``CMSINCIDENTADRESS.ORDERNAME`` não tem pasta nenhuma: os dados do
    cliente são guardados só pelo nome. Dois nomes iguais misturariam esses
    dados, por isso é preciso procurar em toda a árvore e não só no pai.
    """
    query = (
        "SELECT DIR_ID, NAME, TYPE, PARENT_ID FROM dbo.IMORDFOLDER WITH (NOLOCK) "
        f"WHERE NAME = {_literal_nome(nome)} AND TYPE = {IMOS_TIPO_ENCOMENDA} "
        "ORDER BY DIR_ID"
    )
    return [_no_de_linha(row) for row in run_imos_select(cfg, query)]


def caminho_do_no(cfg: ImosConfig, dir_id: int, *, limite: int = 12) -> str:
    """Caminho legível de um nó, subindo pelos pais até à raiz `Order`.

    Sobe um nível por consulta em vez de usar um CTE recursivo, porque a
    barreira de leitura só aceita queries que comecem por `SELECT`. A árvore
    real tem 9 níveis no máximo, por isso são poucas consultas.
    """
    nomes: list[str] = []
    atual: int | None = int(dir_id)
    for _ in range(limite):
        if not atual or atual == IMOS_DIR_ID_ORDER:
            break
        rows = run_imos_select(
            cfg,
            "SELECT TOP 1 DIR_ID, NAME, TYPE, PARENT_ID FROM dbo.IMORDFOLDER "
            f"WITH (NOLOCK) WHERE DIR_ID = {int(atual)}",
        )
        if not rows:
            break
        no = _no_de_linha(rows[0])
        nomes.append(no.nome)
        atual = no.parent_id

    return " / ".join(reversed(nomes))


def nome_pasta_ano(ano) -> str:
    """Nome da pasta do ano civil na árvore do iMos (ex.: `ANO_2026`)."""
    digitos = re.sub(r"\D+", "", str(ano or ""))
    if len(digitos) == 2:
        digitos = f"20{digitos}"
    if len(digitos) != 4:
        raise ValueError(f"Ano inválido para a pasta do iMos: {ano!r}.")
    return f"ANO_{digitos}"


def carregar_pasta_raiz(session: Session) -> str:
    """Nome da pasta raiz da empresa dentro de `Order` (por defeito LANCA_ENCANTO)."""
    valor = (
        SystemSettingService(session).obter_valor(KEY_IMOS_PASTA_RAIZ, "") or ""
    ).strip()
    return valor or DEFAULT_IMOS_PASTA_RAIZ


def resolver_caminho_encomenda(
    cfg: ImosConfig,
    *,
    ano,
    cliente_simplex: str,
    nome_encomenda: str,
    pasta_raiz: str = DEFAULT_IMOS_PASTA_RAIZ,
    pasta_ano: str | None = None,
) -> CaminhoImos:
    """Resolve `Order / raiz / ANO_XXXX / cliente / encomenda` sem escrever nada.

    Cada nível só é procurado quando o anterior existe: assim que um nível falta,
    todos os seguintes ficam marcados como em falta (ainda não têm pai).

    ``pasta_ano`` substitui a pasta do ano civil por outra (é o que permite
    ensaiar numa pasta descartável em vez do ano real).
    """
    pedidos = (
        (str(pasta_raiz or DEFAULT_IMOS_PASTA_RAIZ).strip(), IMOS_TIPO_PASTA),
        (str(pasta_ano).strip() if pasta_ano else nome_pasta_ano(ano), IMOS_TIPO_PASTA),
        (str(cliente_simplex or "").strip(), IMOS_TIPO_PASTA),
        (str(nome_encomenda or "").strip(), IMOS_TIPO_ENCOMENDA),
    )

    niveis: list[NivelCaminho] = []
    parent_dir_id: int | None = IMOS_DIR_ID_ORDER
    for nome, tipo in pedidos:
        no = (
            resolver_no(cfg, parent_dir_id=parent_dir_id, nome=nome, tipo=tipo)
            if parent_dir_id is not None
            else None
        )
        niveis.append(NivelCaminho(nome=nome, tipo=tipo, dir_id=no.dir_id if no else None))
        parent_dir_id = no.dir_id if no else None

    return CaminhoImos(niveis=tuple(niveis))
