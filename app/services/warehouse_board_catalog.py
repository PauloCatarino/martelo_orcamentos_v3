"""Fronteira de leitura do catálogo de placas do armazém/HOMAG.

O V3 não conhece ainda o motor, servidor ou esquema real. Esta fronteira torna
essa ausência explícita e impede que o restante assistente fique dependente da
ligação futura. Nenhuma implementação deste módulo escreve na origem.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Callable, Iterable, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lista_material_assistente import ListaMaterialPlacaSnapshot


@dataclass(frozen=True)
class BoardRecord:
    external_id: str
    code: str
    description: str
    length: Decimal | None = None
    width: Decimal | None = None
    thickness: Decimal | None = None
    unit: str = "mm"
    active: bool = True
    stock: Decimal | None = None
    reserved: Decimal | None = None
    available: Decimal | None = None


@dataclass(frozen=True)
class BoardCatalogStatus:
    available: bool
    message: str
    source: str


class BoardCatalogProvider(Protocol):
    """Contrato mínimo do catálogo; só expõe operações de leitura."""

    def status(self) -> BoardCatalogStatus: ...

    def list_boards(self) -> list[BoardRecord]: ...


class UnavailableBoardCatalogProvider:
    def status(self) -> BoardCatalogStatus:
        return BoardCatalogStatus(
            available=False,
            source="HOMAG",
            message=(
                "Ligação ao armazém/HOMAG ainda não configurada. "
                "A análise usa texto normalizado, histórico e valores manuais."
            ),
        )

    def list_boards(self) -> list[BoardRecord]:
        return []


class WarehouseBoardCatalogProvider:
    """Adaptador futuro para uma consulta SELECT já auditada.

    Recebe uma função de leitura em vez de construir SQL arbitrário. Assim, a
    configuração concreta pode impor utilizador técnico read-only e validar a
    query fora do motor de sugestões.
    """

    def __init__(self, select_boards: Callable[[], Iterable[BoardRecord]], *, source: str = "HOMAG"):
        self._select_boards = select_boards
        self._source = source

    def status(self) -> BoardCatalogStatus:
        return BoardCatalogStatus(True, "Catálogo disponível em modo de leitura.", self._source)

    def list_boards(self) -> list[BoardRecord]:
        return list(self._select_boards())


def _decimal_ou_nada(valor) -> Decimal | None:
    try:
        return Decimal(str(valor)) if valor not in (None, "") else None
    except (ArithmeticError, ValueError):
        return None


def board_from_woodstore(linha: dict) -> BoardRecord:
    """Uma linha da consulta do Woodstore (`woodstore_service.STOCK_SQL`)."""
    return BoardRecord(
        external_id=str(linha.get("Referencia") or "").strip(),
        code=str(linha.get("Codigo") or "").strip(),
        description=str(linha.get("Material") or "").strip(),
        length=_decimal_ou_nada(linha.get("Comprimento")),
        width=_decimal_ou_nada(linha.get("Largura")),
        thickness=_decimal_ou_nada(linha.get("Espessura")),
        stock=_decimal_ou_nada(linha.get("Quantidade")),
        reserved=_decimal_ou_nada(linha.get("Reservadas")),
        available=_decimal_ou_nada(linha.get("Disponivel")),
    )


class WoodstoreBoardCatalogProvider:
    """O catálogo de placas lido do Woodstore (HOMAG), só de leitura.

    O assistente dizia sempre «Ligação ao armazém/HOMAG ainda não configurada»
    porque só conhecia o `UnavailableBoardCatalogProvider` — mesmo quando a
    Análise da Lista Material já lia o Woodstore sem problemas. Este lê pela
    mesma consulta da Análise, uma vez, e diz o que aconteceu de facto.
    """

    def __init__(self, read_rows: Callable[[], Iterable[dict]]):
        self._read_rows = read_rows
        self._boards: list[BoardRecord] | None = None
        self._error = ""

    def _load(self) -> None:
        if self._boards is not None or self._error:
            return
        try:
            self._boards = [board_from_woodstore(linha) for linha in self._read_rows()]
        except Exception as error:  # rede, credenciais, consulta recusada
            self._error = str(error) or "Woodstore sem ligação."

    def status(self) -> BoardCatalogStatus:
        self._load()
        if self._boards is None:
            return BoardCatalogStatus(
                False,
                "Woodstore sem ligação neste momento: "
                f"{self._error} Os materiais são validados na Análise da "
                "Lista Material, quando houver ligação.",
                "Woodstore",
            )
        codigos = {board.code for board in self._boards if board.code}
        return BoardCatalogStatus(
            True,
            f"Woodstore ligado (só leitura): {len(self._boards)} placas, "
            f"{len(codigos)} materiais.",
            "Woodstore",
        )

    def list_boards(self) -> list[BoardRecord]:
        self._load()
        return list(self._boards or [])


def sync_board_snapshot(
    session: Session, provider: BoardCatalogProvider
) -> int:
    """Atualiza o snapshot local apenas a partir da leitura do provider.

    Registos que desapareçam da leitura não são apagados automaticamente; uma
    futura política HOMAG decidirá se devem apenas ser marcados inativos.
    """
    status = provider.status()
    if not status.available:
        return 0
    changed = 0
    for board in provider.list_boards():
        payload = {
            "external_id": board.external_id,
            "code": board.code,
            "description": board.description,
            "length": str(board.length) if board.length is not None else None,
            "width": str(board.width) if board.width is not None else None,
            "thickness": str(board.thickness) if board.thickness is not None else None,
            "unit": board.unit,
            "active": board.active,
            "stock": str(board.stock) if board.stock is not None else None,
            "reserved": str(board.reserved) if board.reserved is not None else None,
            "available": str(board.available) if board.available is not None else None,
        }
        source_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        row = session.execute(
            select(ListaMaterialPlacaSnapshot).where(
                ListaMaterialPlacaSnapshot.external_id == board.external_id
            )
        ).scalar_one_or_none()
        if row is not None and row.source_hash == source_hash:
            continue
        if row is None:
            row = ListaMaterialPlacaSnapshot(
                external_id=board.external_id,
                descricao=board.description,
                source_hash=source_hash,
            )
            session.add(row)
        row.codigo_externo = board.code or None
        row.descricao = board.description
        row.comprimento = board.length
        row.largura = board.width
        row.espessura = board.thickness
        row.unidade = board.unit
        row.ativo = board.active
        row.stock = board.stock
        row.reservado = board.reserved
        row.disponivel = board.available
        row.source_hash = source_hash
        row.synced_at = datetime.now()
        changed += 1
    session.commit()
    return changed
