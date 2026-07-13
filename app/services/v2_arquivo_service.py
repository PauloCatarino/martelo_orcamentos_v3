"""Read-only discovery and consultation adapter for the Martelo V2 archive."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import MetaData, Table, create_engine, event, inspect, select
from sqlalchemy.engine import Engine, URL


class V2ArquivoConfigError(RuntimeError):
    pass


class V2ArquivoSchemaError(RuntimeError):
    pass


@dataclass(frozen=True)
class OrcamentoV2Resumo:
    numero: str
    versao: str
    cliente: str
    ref_cliente: str
    obra: str
    descricao: str
    estado: str
    data: date | datetime | str | None
    total: Decimal | float | str | None
    utilizador: str
    tabela_origem: str


ALIASES = {
    "numero": ("num_orcamento", "numero_orcamento", "orcamento", "numero", "nr_orcamento"),
    "versao": ("versao", "numero_versao", "ver"),
    "cliente": ("cliente", "nome_cliente", "cliente_nome"),
    "ref_cliente": ("ref_cliente", "referencia_cliente", "refcli"),
    "obra": ("obra", "nome_obra"),
    "descricao": ("descricao", "descricao_orcamento", "descr", "observacoes"),
    "estado": ("estado", "status", "situacao"),
    "data": ("data", "data_orcamento", "created_at", "dt_orcamento"),
    "total": ("preco_total", "total", "valor_total", "valor"),
    "utilizador": ("utilizador", "username", "user", "criado_por"),
}


def criar_engine_v2_readonly() -> Engine:
    """Create an engine guarded against every non-read SQL statement."""
    url = os.getenv("V2_DATABASE_URL")
    if not url:
        user = os.getenv("V2_DB_USER")
        password = os.getenv("V2_DB_PASSWORD")
        if not user or not password:
            raise V2ArquivoConfigError(
                "Arquivo V2 não configurado. Defina V2_DB_USER e V2_DB_PASSWORD "
                "(utilizador MySQL apenas de leitura) ou V2_DATABASE_URL."
            )
        url = URL.create(
            "mysql+pymysql", username=user, password=password,
            host=os.getenv("V2_DB_HOST", "192.168.5.201"),
            port=int(os.getenv("V2_DB_PORT", "3306")),
            database=os.getenv("V2_DB_NAME", "orcamentos_v2"),
            query={"charset": "utf8mb4"},
        )
    engine = create_engine(url, pool_pre_ping=True, future=True)
    if engine.dialect.name == "mysql":
        event.listen(engine, "connect", _ativar_sessao_readonly)
    event.listen(engine, "before_cursor_execute", _bloquear_escrita)
    return engine


def _ativar_sessao_readonly(dbapi_connection, _connection_record) -> None:
    """Ask MySQL to reject writes at session level, independently of the UI guard."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET SESSION TRANSACTION READ ONLY")
    finally:
        cursor.close()


def _bloquear_escrita(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
    inicio = statement.lstrip().split(None, 1)[0].upper() if statement.strip() else ""
    if inicio not in {"SELECT", "SHOW", "DESCRIBE", "DESC", "EXPLAIN", "WITH", "PRAGMA"}:
        raise PermissionError(f"Arquivo V2 é apenas de leitura; comando bloqueado: {inicio or '?'}")


class V2ArquivoService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def listar_orcamentos(self, *, limite: int = 500) -> list[OrcamentoV2Resumo]:
        insp = inspect(self.engine)
        tabela_nome = self._escolher_tabela(insp.get_table_names())
        metadata = MetaData()
        tabela = Table(tabela_nome, metadata, autoload_with=self.engine)
        mapa = self._mapear_colunas(tabela)
        if "numero" not in mapa:
            raise V2ArquivoSchemaError(
                f"A tabela V2 '{tabela_nome}' não tem uma coluna reconhecida de número de orçamento."
            )
        tabelas_disponiveis = set(insp.get_table_names())
        from_clause = tabela
        colunas = [tabela]
        if "client_id" in tabela.c and "clients" in tabelas_disponiveis:
            clients = Table("clients", metadata, autoload_with=self.engine)
            if "id" in clients.c and "nome" in clients.c:
                from_clause = from_clause.outerjoin(clients, tabela.c.client_id == clients.c.id)
                colunas.append(clients.c.nome.label("__cliente_nome"))
        if "created_by" in tabela.c and "users" in tabelas_disponiveis:
            users = Table("users", metadata, autoload_with=self.engine)
            if "id" in users.c and "username" in users.c:
                from_clause = from_clause.outerjoin(users, tabela.c.created_by == users.c.id)
                colunas.append(users.c.username.label("__utilizador_nome"))
        stmt = select(*colunas).select_from(from_clause).limit(max(1, min(int(limite), 5000)))
        if "data" in mapa:
            stmt = stmt.order_by(tabela.c[mapa["data"]].desc())
        with self.engine.connect() as connection:
            rows = connection.execute(stmt).mappings().all()
        return [self._adaptar(row, mapa, tabela_nome) for row in rows]

    @staticmethod
    def _escolher_tabela(tabelas: list[str]) -> str:
        candidatas = [t for t in tabelas if "orc" in t.casefold()]
        preferidas = ("orcamentos", "orcamento", "orcamentos_cabecalho", "orcamento_cabecalho")
        por_nome = {t.casefold(): t for t in candidatas}
        for nome in preferidas:
            if nome in por_nome:
                return por_nome[nome]
        if candidatas:
            return sorted(candidatas, key=lambda t: ("item" in t.casefold(), len(t)))[0]
        raise V2ArquivoSchemaError("Não foi encontrada nenhuma tabela de orçamentos na base V2.")

    @staticmethod
    def _mapear_colunas(tabela: Table) -> dict[str, str]:
        existentes = {col.name.casefold(): col.name for col in tabela.columns}
        return {
            destino: existentes[alias]
            for destino, aliases in ALIASES.items()
            for alias in aliases
            if alias in existentes
        }

    @staticmethod
    def _adaptar(row, mapa: dict[str, str], tabela: str) -> OrcamentoV2Resumo:
        def valor(chave, default=""):
            coluna = mapa.get(chave)
            dado = row.get(coluna) if coluna else default
            return default if dado is None else dado
        return OrcamentoV2Resumo(
            numero=str(valor("numero")), versao=str(valor("versao")),
            cliente=str(row.get("__cliente_nome") or valor("cliente")),
            ref_cliente=str(valor("ref_cliente")),
            obra=str(valor("obra")), descricao=str(valor("descricao")),
            estado=str(valor("estado")), data=valor("data", None),
            total=valor("total", None),
            utilizador=str(row.get("__utilizador_nome") or valor("utilizador")),
            tabela_origem=tabela,
        )
