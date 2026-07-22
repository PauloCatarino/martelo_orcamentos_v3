"""Compare and import production processes from Martelo V2 into V3.

Transition helper: V2 is read-only here. Nothing is written into V2, and
nothing is written into V3 without an explicit user selection.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.domain.datas import normalizar_data
from app.models.producao import Producao
from app.services.v2_arquivo_service import (
    V2ArquivoConfigError,
    criar_engine_v2_readonly,
)


CAMPOS_DIRETOS_V2_V3: tuple[str, ...] = (
    "codigo_processo",
    "ano",
    "num_enc_phc",
    "versao_obra",
    "versao_plano",
    "responsavel",
    "nome_cliente",
    "nome_cliente_simplex",
    "num_cliente_phc",
    "ref_cliente",
    "num_orcamento",
    "versao_orc",
    "obra",
    "localizacao",
    "descricao_orcamento",
    "data_inicio",
    "data_entrega",
    "preco_total",
    "qt_artigos",
    "descricao_artigos",
    "materias_usados",
    "descricao_producao",
    "notas1",
    "notas2",
    "notas3",
    "imagem_path",
    "pasta_servidor",
    "tipo_pasta",
    "created_at",
    "updated_at",
)

#: Fields shown in the differences table, in display order.
CAMPOS_COMPARADOS: tuple[tuple[str, str], ...] = (
    ("estado", "Estado"),
    ("responsavel", "Responsável"),
    ("nome_cliente", "Cliente"),
    ("nome_cliente_simplex", "Cliente simplex"),
    ("num_cliente_phc", "Nº Cliente PHC"),
    ("ref_cliente", "Ref Cliente"),
    ("num_orcamento", "Nº Orçamento"),
    ("versao_orc", "V. Orç"),
    ("obra", "Obra"),
    ("localizacao", "Localização"),
    ("data_inicio", "Data Início"),
    ("data_entrega", "Data Entrega"),
    ("preco_total", "Preço total"),
    ("qt_artigos", "Qt artigos"),
    ("descricao_artigos", "Descrição artigos"),
    ("materias_usados", "Matérias usados"),
    ("descricao_producao", "Descrição produção"),
    ("notas1", "Notas 1"),
    ("notas2", "Notas 2"),
    ("notas3", "Notas 3"),
    ("imagem_path", "Imagem"),
    ("pasta_servidor", "Pasta servidor"),
    ("tipo_pasta", "Tipo Pasta"),
)

_ROTULOS = dict(CAMPOS_COMPARADOS)


class ProducaoV2ConfigError(RuntimeError):
    """Raised when the V2 connection is not configured."""


@dataclass(frozen=True)
class DiferencaV2:
    """One field that differs between a V2 row and the matching V3 row."""

    codigo_processo: str
    campo: str
    valor_v2: object
    valor_v3: object

    @property
    def rotulo(self) -> str:
        return _ROTULOS.get(self.campo, self.campo)

    @property
    def texto_v2(self) -> str:
        return _texto_visivel(self.valor_v2)

    @property
    def texto_v3(self) -> str:
        return _texto_visivel(self.valor_v3)

    @property
    def v3_vazio(self) -> bool:
        return not _normalizar(self.valor_v3)


@dataclass(frozen=True)
class ObraNovaV2:
    """A V2 process that does not exist in V3 yet."""

    codigo_processo: str
    valores: Mapping[str, Any]

    @property
    def descricao(self) -> str:
        cliente = _texto_visivel(self.valores.get("nome_cliente"))
        entrega = _texto_visivel(self.valores.get("data_entrega"))
        partes = [parte for parte in (cliente, entrega) if parte]
        return " · ".join(partes)


@dataclass
class ComparacaoV2:
    """Result of comparing every V2 production row against V3."""

    total_v2: int = 0
    obras_novas: list[ObraNovaV2] = field(default_factory=list)
    diferencas: list[DiferencaV2] = field(default_factory=list)
    sem_alteracoes: int = 0
    erros: list[str] = field(default_factory=list)

    @property
    def vazia(self) -> bool:
        return not self.obras_novas and not self.diferencas


@dataclass
class ResultadoAplicacaoV2:
    """Counters for one apply run."""

    criados: int = 0
    campos_atualizados: int = 0
    processos_atualizados: int = 0
    erros: list[str] = field(default_factory=list)


def mapear_estado(v2_estado: object) -> object:
    """Map legacy V2 production states into V3 canonical states."""
    if v2_estado is None:
        return None
    if str(v2_estado).strip() == "Planeamento":
        return "Desenho"
    return v2_estado


def mapear_linha(v2_row: Mapping[str, Any]) -> dict[str, Any]:
    """Map one V2 ``producao`` row into V3 production fields, excluding FKs."""
    valores = {campo: v2_row.get(campo) for campo in CAMPOS_DIRETOS_V2_V3}
    valores["estado"] = mapear_estado(v2_row.get("estado"))
    valores["data_inicio"] = normalizar_data(valores.get("data_inicio"))
    valores["data_entrega"] = normalizar_data(valores.get("data_entrega"))
    return valores


def criar_engine_v2() -> Engine:
    """Create the read-only V2 engine, raising a friendly config error."""
    try:
        return criar_engine_v2_readonly()
    except V2ArquivoConfigError as error:
        raise ProducaoV2ConfigError(str(error)) from error


def ler_linhas_v2(engine: Engine) -> list[Mapping[str, Any]]:
    """Read all V2 production rows. This function only executes SELECT."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM producao"))
        return list(result.mappings())


def comparar_linhas(
    session: Session,
    linhas_v2: Sequence[Mapping[str, Any]],
) -> ComparacaoV2:
    """Compare V2 rows against V3 without writing anything."""
    comparacao = ComparacaoV2(total_v2=len(linhas_v2))

    for v2_row in linhas_v2:
        valores = mapear_linha(v2_row)
        codigo = _normalizar(valores.get("codigo_processo"))
        if not codigo:
            comparacao.erros.append("Linha do V2 sem codigo_processo — ignorada.")
            continue

        existente = session.scalar(
            select(Producao).where(Producao.codigo_processo == codigo)
        )
        if existente is None:
            comparacao.obras_novas.append(ObraNovaV2(codigo, valores))
            continue

        diferencas_processo = [
            DiferencaV2(codigo, campo, valores.get(campo), getattr(existente, campo, None))
            for campo, _rotulo in CAMPOS_COMPARADOS
            if _difere(valores.get(campo), getattr(existente, campo, None))
        ]
        if diferencas_processo:
            comparacao.diferencas.extend(diferencas_processo)
        else:
            comparacao.sem_alteracoes += 1

    return comparacao


def comparar_v2_com_v3(session: Session) -> ComparacaoV2:
    """Read V2 and compare it against V3 (no writes on either side)."""
    engine = criar_engine_v2()
    try:
        linhas_v2 = ler_linhas_v2(engine)
    finally:
        engine.dispose()
    return comparar_linhas(session, linhas_v2)


def aplicar_selecao(
    session: Session,
    *,
    obras_novas: Sequence[ObraNovaV2] = (),
    diferencas: Sequence[DiferencaV2] = (),
) -> ResultadoAplicacaoV2:
    """Apply only the user-selected V2 values into V3."""
    resultado = ResultadoAplicacaoV2()

    for obra in obras_novas:
        try:
            processo = Producao()
            _aplicar_valores_novos(session, processo, obra.valores)
            session.add(processo)
            session.flush()
            session.commit()
            resultado.criados += 1
        except Exception as error:  # noqa: BLE001 - reported to the user
            session.rollback()
            resultado.erros.append(f"{obra.codigo_processo}: {error}")

    por_processo: dict[str, list[DiferencaV2]] = {}
    for diferenca in diferencas:
        por_processo.setdefault(diferenca.codigo_processo, []).append(diferenca)

    for codigo, itens in por_processo.items():
        try:
            processo = session.scalar(
                select(Producao).where(Producao.codigo_processo == codigo)
            )
            if processo is None:
                resultado.erros.append(f"{codigo}: já não existe no V3.")
                continue
            for diferenca in itens:
                setattr(processo, diferenca.campo, diferenca.valor_v2)
            session.flush()
            session.commit()
            resultado.processos_atualizados += 1
            resultado.campos_atualizados += len(itens)
        except Exception as error:  # noqa: BLE001 - reported to the user
            session.rollback()
            resultado.erros.append(f"{codigo}: {error}")

    return resultado


def _aplicar_valores_novos(
    session: Session,
    processo: Producao,
    valores: Mapping[str, Any],
) -> None:
    for campo, valor in valores.items():
        if campo in {"created_at", "updated_at"} and valor is None:
            continue
        setattr(processo, campo, valor)

    processo.cliente_id = _resolver_cliente_id(session, valores.get("num_cliente_phc"))
    processo.orcamento_id = _resolver_orcamento_id(
        session,
        valores.get("ano"),
        valores.get("num_orcamento"),
    )
    processo.created_by_id = None
    processo.updated_by_id = None


def _resolver_cliente_id(session: Session, num_cliente_phc: object) -> int | None:
    from app.models.cliente import Cliente

    numero = _normalizar(num_cliente_phc)
    if not numero:
        return None
    return session.scalar(
        select(Cliente.id).where(Cliente.num_cliente_phc == numero).limit(1)
    )


def _resolver_orcamento_id(
    session: Session,
    ano: object,
    num_orcamento: object,
) -> int | None:
    from app.models.orcamento import Orcamento

    numero = _normalizar(num_orcamento)
    if not numero:
        return None
    try:
        ano_int = int(_normalizar(ano))
    except (TypeError, ValueError):
        return None
    return session.scalar(
        select(Orcamento.id)
        .where(Orcamento.ano == ano_int, Orcamento.num_orcamento == numero)
        .limit(1)
    )


def _normalizar(valor: object) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def _texto_visivel(valor: object) -> str:
    texto = _normalizar(valor)
    if not texto:
        return "(vazio)"
    return texto.replace("\r\n", " · ").replace("\n", " · ")


def _difere(valor_v2: object, valor_v3: object) -> bool:
    """Return True when the two values are meaningfully different."""
    if _normalizar(valor_v2) == _normalizar(valor_v3):
        return False

    decimal_v2 = _decimal_ou_none(valor_v2)
    decimal_v3 = _decimal_ou_none(valor_v3)
    if decimal_v2 is not None and decimal_v3 is not None:
        return decimal_v2 != decimal_v3

    return True


def _decimal_ou_none(valor: object) -> Decimal | None:
    texto = _normalizar(valor).replace(",", ".")
    if not texto:
        return None
    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        return None
