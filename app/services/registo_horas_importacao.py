"""Trazer o histórico da app isolada «Registo de Horas» (PHP/XAMPP) para o Martelo.

A app antiga corre no XAMPP de cada PC: a base é MariaDB local (porta e nome
em ``includes/instalacao.php``, que o instalador dela gera), com a tabela
``dias_trabalho`` — um dia por linha. Aqui só se LÊ dessa base; nada lá é
alterado nem apagado. Cada pessoa importa no seu PC, com a sua conta: as horas
ficam em nome de quem tem a sessão iniciada.

Os totais de cada dia vêm tal como estão (o histórico de 2025 foi transcrito
das folhas em papel e bate com o que foi pago); não se refazem as contas.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from app.domain import registo_horas as regra

PASTA_APP_ANTIGA = Path(r"C:\xampp\htdocs\Registro_horas")
FICHEIRO_INSTALACAO = Path("includes") / "instalacao.php"
PORTA_PADRAO = 3307
BASE_PADRAO = "horarios"


class ErroImportacao(RuntimeError):
    """Mensagem para o utilizador ler."""


@dataclass(frozen=True)
class InstalacaoAntiga:
    pasta: Path
    nome: str = ""
    porta: int = PORTA_PADRAO
    base: str = BASE_PADRAO


def _constante(texto: str, nome: str) -> str | None:
    encontrado = re.search(
        rf"const\s+{nome}\s*=\s*(?:'([^']*)'|\"([^\"]*)\"|(\d+))\s*;", texto
    )
    if not encontrado:
        return None
    return next(g for g in encontrado.groups() if g is not None)


def ler_instalacao(pasta: Path = PASTA_APP_ANTIGA) -> InstalacaoAntiga | None:
    """As definições da app antiga neste PC, ou ``None`` se não estiver instalada."""
    ficheiro = Path(pasta) / FICHEIRO_INSTALACAO
    if not ficheiro.is_file():
        return None
    try:
        texto = ficheiro.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    porta = _constante(texto, "BD_PORTA")
    return InstalacaoAntiga(
        pasta=Path(pasta),
        nome=(_constante(texto, "NOME_COLABORADOR") or "").strip(),
        porta=int(porta) if porta and porta.isdigit() else PORTA_PADRAO,
        base=(_constante(texto, "BD_NOME") or BASE_PADRAO).strip() or BASE_PADRAO,
    )


def _minutos(valor) -> int | None:
    """TIME do MySQL → minutos. O PyMySQL dá ``timedelta`` (passa das 24h)."""
    if valor is None:
        return None
    if isinstance(valor, timedelta):
        return int(valor.total_seconds() // 60)
    if isinstance(valor, time):
        return valor.hour * 60 + valor.minute
    partes = str(valor).split(":")
    try:
        return int(partes[0]) * 60 + int(partes[1])
    except (IndexError, ValueError):
        return None


def _data(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def linha_da_app_antiga(linha: Mapping) -> regra.LinhaDia | None:
    """Uma linha de ``dias_trabalho`` → um dia do Martelo (ou ``None`` se estragada)."""
    dia = _data(linha.get("data"))
    tipo = str(linha.get("tipo") or "")
    if dia is None or tipo not in regra.TIPOS:
        return None
    trabalhado = int(linha.get("trabalhado_min") or 0)
    extra = int(linha.get("extra_min") or 0)
    comum = dict(
        data=dia,
        tipo=tipo,
        trabalhado=trabalhado,
        normais=int(linha.get("normais_min") or 0),
        extra=extra,
        observacoes=str(linha.get("observacoes") or "").strip(),
        origem="app_antiga",
    )
    if tipo == regra.TIPO_UTIL:
        return regra.LinhaDia(
            entrada=_minutos(linha.get("hora_entrada")),
            saida=_minutos(linha.get("hora_saida")),
            almoco=bool(linha.get("desconto_almoco")),
            jantar=bool(linha.get("desconto_jantar")),
            acerto=int(linha.get("acerto_min") or 0),
            **comum,
        )
    horas = -extra if tipo == regra.TIPO_FOLGA else trabalhado
    return regra.LinhaDia(horas=max(horas, 0), **comum)


def converter(linhas: Iterable[Mapping]) -> list[regra.LinhaDia]:
    dias = [linha_da_app_antiga(linha) for linha in linhas]
    return sorted((d for d in dias if d is not None), key=lambda d: d.data)


_SELECT = (
    "SELECT data, tipo, hora_entrada, hora_saida, desconto_almoco, "
    "desconto_jantar, acerto_min, trabalhado_min, normais_min, extra_min, "
    "observacoes FROM dias_trabalho ORDER BY data"
)


def _ligar_mysql(instalacao: InstalacaoAntiga):
    import pymysql

    return pymysql.connect(
        host="127.0.0.1",
        port=instalacao.porta,
        user="root",
        password="",
        database=instalacao.base,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
        read_timeout=30,
    )


def ler_dias(
    instalacao: InstalacaoAntiga,
    *,
    ligar: Callable[[InstalacaoAntiga], object] = _ligar_mysql,
) -> list[regra.LinhaDia]:
    """Lê (só SELECT) todos os dias guardados na app antiga deste PC."""
    try:
        ligacao = ligar(instalacao)
    except Exception as erro:  # noqa: BLE001 - qualquer falha de ligação diz o mesmo
        raise ErroImportacao(
            "Não foi possível ligar à base de dados da app antiga "
            f"(MySQL do XAMPP, porta {instalacao.porta}).\n\n"
            "Abra o «XAMPP Control Panel», carregue em «Start» na linha do "
            "MySQL e volte a tentar.\n\n"
            f"Detalhe: {erro}"
        ) from erro
    try:
        with ligacao.cursor() as cursor:
            cursor.execute(_SELECT)
            linhas = list(cursor.fetchall())
    except Exception as erro:  # noqa: BLE001
        raise ErroImportacao(
            f"A base «{instalacao.base}» da app antiga não tem a folha de horas "
            f"que o Martelo esperava.\n\nDetalhe: {erro}"
        ) from erro
    finally:
        try:
            ligacao.close()
        except Exception:  # noqa: BLE001
            pass
    return converter(linhas)
