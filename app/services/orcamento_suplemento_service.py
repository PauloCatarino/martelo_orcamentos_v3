"""Global material supplements applied once per budget version and board."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.consumos import chave_placa
from app.domain.numeros import validar_decimal
from app.repositories.def_materia_prima_repository import DefMateriaPrimaRepository
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.repositories.orcamento_versao_placa_nao_stock_repository import (
    OrcamentoVersaoPlacaNaoStockRepository,
)
from app.services.orcamento_historico_service import OrcamentoHistoricoService
from app.services.orcamento_item_service import OrcamentoItemService

SUPLEMENTO_REF_LE = "PLC0120"


def _chave_suplemento(ref_le: str, descricao: str, esp) -> tuple[str, ...]:
    """Identify supplements by supplier reference, with a fallback for blanks."""
    referencia = (ref_le or "").strip().casefold()
    if referencia:
        return ("ref", referencia)
    return ("sem_ref", *chave_placa(ref_le, descricao, esp))


@dataclass(frozen=True)
class SuplementoPlacaResumo:
    """One distinct board reference used by the budget."""

    ref_le: str
    descricao: str
    esp: Decimal
    numero_itens: int
    ativo: bool
    suplemento_ref_le: str
    suplemento_descricao: str
    valor_base: Decimal
    valor_local: Decimal
    editado_localmente: bool
    nota_cliente: str = ""
    quantidade: Decimal = Decimal("1")


@dataclass(frozen=True)
class GuardarSuplementoPlacaData:
    ref_le: str
    descricao: str
    esp: Decimal
    ativo: bool
    valor_local: Decimal
    nota_cliente: str = ""
    quantidade: Decimal = Decimal("1")


class OrcamentoSuplementoService:
    """Manage non-stock board supplements at budget-version scope."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.materias_repository = DefMateriaPrimaRepository(session)
        self.linhas_repository = OrcamentoItemCusteioLinhaRepository(session)
        self.placas_repository = OrcamentoVersaoPlacaNaoStockRepository(session)

    def listar(self, orcamento_versao_id: int) -> list[SuplementoPlacaResumo]:
        """List distinct boards in use, merged with already stored settings."""
        fonte = self.materias_repository.get_by_ref_le(SUPLEMENTO_REF_LE)
        valor_base = Decimal("0")
        descricao_fonte = "Suplemento de material não stock"
        if fonte is not None:
            valor_base = fonte.preco_liquido or Decimal("0")
            descricao_fonte = fonte.descricao

        guardados = {
            _chave_suplemento(row.ref_le, row.descricao, row.esp): row
            for row in self.placas_repository.list_by_versao(orcamento_versao_id)
        }
        candidatos: dict[tuple[str, ...], dict] = {}
        for linha in self.linhas_repository.list_by_orcamento_versao(
            orcamento_versao_id
        ):
            if not linha.ativo or (linha.familia_materia_prima or "").upper() != "PLACAS":
                continue
            ref_le = (linha.ref_le or linha.ref_materia_prima or "").strip()
            descricao = (
                linha.descricao_no_orcamento
                or linha.descricao_materia_prima
                or linha.descricao
                or ""
            ).strip()
            esp = linha.esp_mp or Decimal("0")
            if not ref_le and not descricao:
                continue
            chave = _chave_suplemento(ref_le, descricao, esp)
            dados = candidatos.setdefault(
                chave,
                {
                    "ref_le": ref_le,
                    "descricao": descricao,
                    "esp": esp,
                    "item_ids": set(),
                },
            )
            dados["item_ids"].add(linha.orcamento_item_id)

        # Keep an active setting visible even if a later costing edit removed
        # its source line, so the user can explicitly disable it.
        for chave, guardado in guardados.items():
            if guardado.suplemento_ativo and chave not in candidatos:
                candidatos[chave] = {
                    "ref_le": guardado.ref_le,
                    "descricao": guardado.descricao,
                    "esp": guardado.esp,
                    "item_ids": set(),
                }

        resultado: list[SuplementoPlacaResumo] = []
        for chave, dados in candidatos.items():
            guardado = guardados.get(chave)
            ativo = bool(guardado and guardado.suplemento_ativo)
            base_guardada = (
                guardado.suplemento_valor_base
                if guardado and guardado.suplemento_valor_base is not None
                else valor_base
            )
            local = (
                guardado.suplemento_valor_local
                if guardado and guardado.suplemento_valor_local is not None
                else valor_base
            )
            resultado.append(
                SuplementoPlacaResumo(
                    ref_le=dados["ref_le"],
                    descricao=dados["descricao"],
                    esp=dados["esp"],
                    numero_itens=len(dados["item_ids"]),
                    ativo=ativo,
                    suplemento_ref_le=(
                        guardado.suplemento_ref_le
                        if guardado and guardado.suplemento_ref_le
                        else SUPLEMENTO_REF_LE
                    ),
                    suplemento_descricao=descricao_fonte,
                    valor_base=base_guardada,
                    valor_local=local,
                    editado_localmente=bool(
                        guardado and guardado.suplemento_editado_localmente
                    ),
                    nota_cliente=(
                        guardado.suplemento_nota_cliente
                        if guardado and guardado.suplemento_nota_cliente
                        else ""
                    ),
                    quantidade=(
                        guardado.suplemento_quantidade
                        if guardado
                        else Decimal("1")
                    ),
                )
            )
        return sorted(
            resultado,
            key=lambda row: (row.ref_le.casefold(), row.descricao.casefold(), row.esp),
        )

    def guardar(
        self,
        orcamento_versao_id: int,
        dados: list[GuardarSuplementoPlacaData],
    ) -> int:
        """Store all dialog choices and recalculate the version total."""
        fonte = self.materias_repository.get_by_ref_le(SUPLEMENTO_REF_LE)
        if fonte is None or not fonte.ativo:
            raise ValueError(
                f"A matéria-prima {SUPLEMENTO_REF_LE} não existe ou está inativa."
            )
        valor_base = fonte.preco_liquido or Decimal("0")
        ativos = 0
        for data in dados:
            valor_local = validar_decimal(
                data.valor_local,
                "Valor local do suplemento",
                permitir_vazio=False,
                minimo=Decimal("0"),
            )
            quantidade = validar_decimal(
                data.quantidade,
                "Quantidade do suplemento",
                permitir_vazio=False,
                minimo=Decimal("0"),
                minimo_exclusivo=True,
            )
            self.placas_repository.set_suplemento(
                orcamento_versao_id,
                data.ref_le,
                data.descricao,
                data.esp,
                ativo=data.ativo,
                suplemento_ref_le=SUPLEMENTO_REF_LE,
                valor_base=valor_base,
                valor_local=valor_local,
                editado_localmente=valor_local != valor_base,
                nota_cliente=data.nota_cliente,
                quantidade=quantidade,
            )
            ativos += int(data.ativo)

        OrcamentoItemService(self.session).recalcular_total_versao(
            orcamento_versao_id
        )
        OrcamentoHistoricoService(self.session).registar(
            orcamento_versao_id,
            "custeio",
            f"Suplementos de placas não stock atualizados: {ativos} referência(s).",
        )
        self.session.commit()
        return ativos
