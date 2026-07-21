"""Repository for budget item reads."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.domain.precos import MargensOrcamento
from app.models import (
    OrcamentoItem,
    OrcamentoItemCusteioLinha,
    OrcamentoItemCusteioLinhaOperacao,
    OrcamentoItemModulo,
    OrcamentoItemValuesetLinha,
    OrcamentoItemValuesetLinhaOperacao,
    OrcamentoItemVariavel,
    OrcamentoVersao,
)


@dataclass(frozen=True)
class OrcamentoItemResumo:
    """Read model for listing budget items."""

    id: int
    orcamento_versao_id: int
    ordem: int
    codigo: str | None
    item: str
    descricao: str | None
    altura: Decimal | None
    largura: Decimal | None
    profundidade: Decimal | None
    quantidade: Decimal
    unidade: str | None
    preco_unitario: Decimal | None
    preco_total: Decimal | None
    tipo_item: str = "OUTRO"
    tipo_producao: str | None = None
    ajuste_eur: Decimal = Decimal("0")
    preco_manual: bool = False
    modalidade_custeio: str = "STANDARD"
    simplificado_urgente: bool = False
    simplificado_sem_excel: bool = False
    custo_simplificado_urgencia: Decimal = Decimal("0")
    custo_simplificado_sem_excel: Decimal = Decimal("0")


class OrcamentoItemRepository:
    """Repository for OrcamentoItem read operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_items_by_versao(self, orcamento_versao_id: int) -> list[OrcamentoItemResumo]:
        """List items for one budget version."""
        statement = (
            select(OrcamentoItem)
            .where(OrcamentoItem.orcamento_versao_id == orcamento_versao_id)
            .order_by(OrcamentoItem.ordem.asc())
        )

        items = self.session.execute(statement).scalars().all()

        return [self._to_resumo(item) for item in items]

    def get_next_ordem(self, orcamento_versao_id: int) -> int:
        """Return the next item order for a budget version."""
        statement = select(OrcamentoItem.ordem).where(
            OrcamentoItem.orcamento_versao_id == orcamento_versao_id
        )
        existing_orders = self.session.execute(statement).scalars().all()

        if not existing_orders:
            return 1

        return max(existing_orders) + 1

    def get_item_by_id(self, item_id: int) -> OrcamentoItemResumo | None:
        """Get one item by id."""
        item = self.session.get(OrcamentoItem, item_id)
        if item is None:
            return None

        return self._to_resumo(item)

    def create_item(
        self,
        *,
        orcamento_versao_id: int,
        ordem: int,
        codigo: str | None,
        tipo_item: str,
        item: str,
        descricao: str | None,
        altura: Decimal | None,
        largura: Decimal | None,
        profundidade: Decimal | None,
        quantidade: Decimal,
        unidade: str,
        preco_unitario: Decimal,
        preco_total: Decimal,
        preco_manual: bool = False,
    ) -> OrcamentoItemResumo:
        """Create one budget item."""
        orcamento_item = OrcamentoItem(
            orcamento_versao_id=orcamento_versao_id,
            ordem=ordem,
            codigo=codigo,
            tipo_item=tipo_item,
            item=item,
            descricao=descricao,
            altura=altura,
            largura=largura,
            profundidade=profundidade,
            quantidade=quantidade,
            unidade=unidade,
            preco_unitario=preco_unitario,
            preco_total=preco_total,
            preco_manual=preco_manual,
        )
        self.session.add(orcamento_item)
        self.session.flush()

        return self._to_resumo(orcamento_item)

    def update_item(
        self,
        *,
        item_id: int,
        codigo: str | None,
        tipo_item: str,
        item: str,
        descricao: str | None,
        altura: Decimal | None,
        largura: Decimal | None,
        profundidade: Decimal | None,
        quantidade: Decimal,
        unidade: str,
        preco_unitario: Decimal,
        preco_total: Decimal,
        preco_manual: bool = False,
    ) -> OrcamentoItemResumo:
        """Update one budget item."""
        orcamento_item = self.session.get(OrcamentoItem, item_id)
        if orcamento_item is None:
            raise ValueError("item not found")

        orcamento_item.codigo = codigo
        orcamento_item.tipo_item = tipo_item
        orcamento_item.item = item
        orcamento_item.descricao = descricao
        orcamento_item.altura = altura
        orcamento_item.largura = largura
        orcamento_item.profundidade = profundidade
        orcamento_item.quantidade = quantidade
        orcamento_item.unidade = unidade
        orcamento_item.preco_unitario = preco_unitario
        orcamento_item.preco_total = preco_total
        orcamento_item.preco_manual = preco_manual
        self.session.flush()

        return self._to_resumo(orcamento_item)

    def delete_item(self, item_id: int) -> bool:
        """Delete one budget item and everything it owns.

        None of the item-owned foreign keys cascade at the database level, so
        every child table is removed explicitly, deepest first: the operation
        rows of the costing and ValueSet lines, then those lines (breaking the
        costing lines' self/module references first), then the modules,
        variables, and finally the item itself.
        """
        existe = self.session.execute(
            select(OrcamentoItem.id).where(OrcamentoItem.id == item_id)
        ).scalar_one_or_none()
        if existe is None:
            return False

        linha_ids = self.session.execute(
            select(OrcamentoItemCusteioLinha.id).where(
                OrcamentoItemCusteioLinha.orcamento_item_id == item_id
            )
        ).scalars().all()
        vsl_ids = self.session.execute(
            select(OrcamentoItemValuesetLinha.id).where(
                OrcamentoItemValuesetLinha.orcamento_item_id == item_id
            )
        ).scalars().all()

        statements = []
        if linha_ids:
            statements.append(
                delete(OrcamentoItemCusteioLinhaOperacao).where(
                    OrcamentoItemCusteioLinhaOperacao.linha_id.in_(linha_ids)
                )
            )
        if vsl_ids:
            statements.append(
                delete(OrcamentoItemValuesetLinhaOperacao).where(
                    OrcamentoItemValuesetLinhaOperacao.orcamento_item_valueset_linha_id.in_(
                        vsl_ids
                    )
                )
            )
        # Break the costing lines' self/module references before deleting them.
        statements.append(
            update(OrcamentoItemCusteioLinha)
            .where(OrcamentoItemCusteioLinha.orcamento_item_id == item_id)
            .values(linha_pai_id=None, orcamento_item_modulo_id=None)
        )
        statements.extend(
            (
                delete(OrcamentoItemCusteioLinha).where(
                    OrcamentoItemCusteioLinha.orcamento_item_id == item_id
                ),
                delete(OrcamentoItemValuesetLinha).where(
                    OrcamentoItemValuesetLinha.orcamento_item_id == item_id
                ),
                delete(OrcamentoItemModulo).where(
                    OrcamentoItemModulo.orcamento_item_id == item_id
                ),
                delete(OrcamentoItemVariavel).where(
                    OrcamentoItemVariavel.item_id == item_id
                ),
                delete(OrcamentoItem).where(OrcamentoItem.id == item_id),
            )
        )
        for statement in statements:
            self.session.execute(
                statement, execution_options={"synchronize_session": False}
            )
        self.session.flush()

        return True

    def update_tipo_producao(self, item_id: int, tipo_producao: str | None) -> bool:
        """Set one item's production-type exception (None = inherit the default)."""
        orcamento_item = self.session.get(OrcamentoItem, item_id)
        if orcamento_item is None:
            return False

        orcamento_item.tipo_producao = tipo_producao
        self.session.flush()

        return True

    def update_modalidade_custeio(
        self, item_id: int, modalidade: str, *, urgente: bool | None = None,
        sem_excel: bool | None = None,
    ) -> bool:
        """Store the separate per-item costing mode and optional flags."""
        item = self.session.get(OrcamentoItem, item_id)
        if item is None:
            return False
        item.modalidade_custeio = modalidade
        if urgente is not None:
            item.simplificado_urgente = urgente
        if sem_excel is not None:
            item.simplificado_sem_excel = sem_excel
        self.session.flush()
        return True

    def update_custos_simplificado(
        self, item_id: int, urgencia: Decimal, sem_excel: Decimal
    ) -> bool:
        item = self.session.get(OrcamentoItem, item_id)
        if item is None:
            return False
        item.custo_simplificado_urgencia = urgencia
        item.custo_simplificado_sem_excel = sem_excel
        self.session.flush()
        return True

    def get_tipo_producao_default(self, orcamento_versao_id: int) -> str | None:
        """Return the version's default production type (or None when not found)."""
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return None

        return versao.tipo_producao_default

    def update_tipo_producao_default(
        self, orcamento_versao_id: int, tipo_producao: str
    ) -> bool:
        """Set the version's default production type."""
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return False

        versao.tipo_producao_default = tipo_producao
        self.session.flush()

        return True

    def get_margens_versao(self, orcamento_versao_id: int) -> MargensOrcamento | None:
        """Return the version's margins (or None when the version is missing)."""
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return None

        return MargensOrcamento(
            margem_lucro_pct=versao.margem_lucro_pct,
            margem_mp_pct=versao.margem_mp_pct,
            margem_mao_obra_pct=versao.margem_mao_obra_pct,
            margem_acabamentos_pct=versao.margem_acabamentos_pct,
            custos_administrativos_pct=versao.custos_administrativos_pct,
        )

    def update_margens_versao(
        self, orcamento_versao_id: int, margens: MargensOrcamento
    ) -> bool:
        """Store the version's margins."""
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return False

        versao.margem_lucro_pct = margens.margem_lucro_pct
        versao.margem_mp_pct = margens.margem_mp_pct
        versao.margem_mao_obra_pct = margens.margem_mao_obra_pct
        versao.margem_acabamentos_pct = margens.margem_acabamentos_pct
        versao.custos_administrativos_pct = margens.custos_administrativos_pct
        self.session.flush()

        return True

    def get_perfil_margens_versao(self, orcamento_versao_id: int) -> str | None:
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        return versao.perfil_margens if versao is not None else None

    def update_perfil_margens_versao(self, orcamento_versao_id: int, perfil: str) -> bool:
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return False
        versao.perfil_margens = perfil
        self.session.flush()
        return True

    def update_ajuste_item(self, item_id: int, ajuste_eur: Decimal) -> bool:
        """Set one item's manual price adjustment (EUR)."""
        orcamento_item = self.session.get(OrcamentoItem, item_id)
        if orcamento_item is None:
            return False

        orcamento_item.ajuste_eur = ajuste_eur
        self.session.flush()

        return True

    def update_preco_item(
        self, item_id: int, preco_unitario: Decimal, preco_total: Decimal
    ) -> bool:
        """Store one item's computed prices."""
        orcamento_item = self.session.get(OrcamentoItem, item_id)
        if orcamento_item is None:
            return False

        orcamento_item.preco_unitario = preco_unitario
        orcamento_item.preco_total = preco_total
        self.session.flush()

        return True

    def sum_preco_total_by_versao(self, orcamento_versao_id: int) -> Decimal:
        """Return the sum of item totals for one budget version."""
        statement = select(func.coalesce(func.sum(OrcamentoItem.preco_total), 0)).where(
            OrcamentoItem.orcamento_versao_id == orcamento_versao_id
        )
        value = self.session.execute(statement).scalar_one()

        return Decimal(value)

    def update_preco_total_versao(self, orcamento_versao_id: int, preco_total: Decimal) -> bool:
        """Update a budget version total."""
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return False

        versao.preco_total = preco_total
        self.session.flush()

        return True

    def duplicar_item_profundo(self, item_id: int) -> OrcamentoItemResumo | None:
        """Clone one item (and all its owned children) inside the same version.

        Copies the item scalars plus its variables, modules, ValueSet lines and
        costing lines, remapping the internal foreign keys (module and
        parent-line references) to the new rows. The version-level ValueSet
        lines are shared by the version, so the item ValueSet lines keep their
        ``origem_*`` references as-is. Returns the new item (with a fresh
        ``ordem`` at the end of the version), or None when the source is gone.
        """
        origem = self.session.get(OrcamentoItem, item_id)
        if origem is None:
            return None

        ordem = self.get_next_ordem(origem.orcamento_versao_id)
        novo_item = OrcamentoItem(
            **self._valores_para_copia(
                origem, exclui={"orcamento_versao_id", "ordem"}
            ),
            orcamento_versao_id=origem.orcamento_versao_id,
            ordem=ordem,
        )
        self.session.add(novo_item)
        self.session.flush()

        variaveis = self.session.execute(
            select(OrcamentoItemVariavel)
            .where(OrcamentoItemVariavel.item_id == item_id)
            .order_by(OrcamentoItemVariavel.ordem.asc(), OrcamentoItemVariavel.id.asc())
        ).scalars().all()
        for variavel in variaveis:
            dados = self._valores_para_copia(variavel, exclui={"item_id"})
            self.session.add(OrcamentoItemVariavel(**dados, item_id=novo_item.id))

        map_modulo: dict[int, int] = {}
        modulos = self.session.execute(
            select(OrcamentoItemModulo)
            .where(OrcamentoItemModulo.orcamento_item_id == item_id)
            .order_by(OrcamentoItemModulo.ordem.asc(), OrcamentoItemModulo.id.asc())
        ).scalars().all()
        for modulo in modulos:
            dados = self._valores_para_copia(modulo, exclui={"orcamento_item_id"})
            novo_modulo = OrcamentoItemModulo(
                **dados, orcamento_item_id=novo_item.id
            )
            self.session.add(novo_modulo)
            self.session.flush()
            map_modulo[modulo.id] = novo_modulo.id

        valuesets_item = self.session.execute(
            select(OrcamentoItemValuesetLinha)
            .where(OrcamentoItemValuesetLinha.orcamento_item_id == item_id)
            .order_by(
                OrcamentoItemValuesetLinha.ordem.asc(),
                OrcamentoItemValuesetLinha.id.asc(),
            )
        ).scalars().all()
        for linha in valuesets_item:
            dados = self._valores_para_copia(linha, exclui={"orcamento_item_id"})
            nova_vsl = OrcamentoItemValuesetLinha(
                **dados, orcamento_item_id=novo_item.id
            )
            self.session.add(nova_vsl)
            self.session.flush()
            # The variant operations (mounting/CNC times of ferragens, etc.) live
            # in a child table keyed to the ValueSet line — copy them too or a
            # later recompute loses those production costs.
            operacoes_vsl = self.session.execute(
                select(OrcamentoItemValuesetLinhaOperacao)
                .where(
                    OrcamentoItemValuesetLinhaOperacao.orcamento_item_valueset_linha_id
                    == linha.id
                )
                .order_by(
                    OrcamentoItemValuesetLinhaOperacao.ordem.asc(),
                    OrcamentoItemValuesetLinhaOperacao.id.asc(),
                )
            ).scalars().all()
            for operacao in operacoes_vsl:
                dados_op = self._valores_para_copia(
                    operacao, exclui={"orcamento_item_valueset_linha_id"}
                )
                self.session.add(
                    OrcamentoItemValuesetLinhaOperacao(
                        **dados_op,
                        orcamento_item_valueset_linha_id=nova_vsl.id,
                    )
                )

        linhas_custeio = self.session.execute(
            select(OrcamentoItemCusteioLinha)
            .where(OrcamentoItemCusteioLinha.orcamento_item_id == item_id)
            .order_by(OrcamentoItemCusteioLinha.id.asc())
        ).scalars().all()
        map_linha: dict[int, OrcamentoItemCusteioLinha] = {}
        linha_pai_original: dict[int, int | None] = {}
        for linha in linhas_custeio:
            dados = self._valores_para_copia(
                linha,
                exclui={
                    "orcamento_item_id",
                    "orcamento_item_modulo_id",
                    "linha_pai_id",
                },
            )
            nova_linha = OrcamentoItemCusteioLinha(
                **dados,
                orcamento_item_id=novo_item.id,
                orcamento_item_modulo_id=map_modulo.get(
                    linha.orcamento_item_modulo_id
                ),
                linha_pai_id=None,
            )
            self.session.add(nova_linha)
            self.session.flush()
            map_linha[linha.id] = nova_linha
            linha_pai_original[linha.id] = linha.linha_pai_id

            # Locally edited per-line operations (override the piece/variant
            # snapshot) are keyed to the costing line — copy them to the new id.
            operacoes_linha = self.session.execute(
                select(OrcamentoItemCusteioLinhaOperacao)
                .where(OrcamentoItemCusteioLinhaOperacao.linha_id == linha.id)
                .order_by(
                    OrcamentoItemCusteioLinhaOperacao.ordem.asc(),
                    OrcamentoItemCusteioLinhaOperacao.id.asc(),
                )
            ).scalars().all()
            for operacao in operacoes_linha:
                dados_op = self._valores_para_copia(operacao, exclui={"linha_id"})
                self.session.add(
                    OrcamentoItemCusteioLinhaOperacao(
                        **dados_op, linha_id=nova_linha.id
                    )
                )

        for old_linha_id, old_linha_pai_id in linha_pai_original.items():
            if old_linha_pai_id is None:
                continue
            novo_pai = map_linha.get(old_linha_pai_id)
            if novo_pai is not None:
                map_linha[old_linha_id].linha_pai_id = novo_pai.id
        self.session.flush()

        return self._to_resumo(novo_item)

    def _valores_para_copia(self, origem, *, exclui: set[str]) -> dict[str, Any]:
        """Return mapped column values for cloning an ORM object."""
        excluidos = {"id", "created_at", "updated_at"} | exclui
        mapper = sa_inspect(type(origem))
        return {
            attr.key: getattr(origem, attr.key)
            for attr in mapper.column_attrs
            if attr.key not in excluidos
        }

    def _to_resumo(self, item: OrcamentoItem) -> OrcamentoItemResumo:
        """Convert an ORM item to the read model."""
        return OrcamentoItemResumo(
            id=item.id,
            orcamento_versao_id=item.orcamento_versao_id,
            ordem=item.ordem,
            codigo=item.codigo,
            item=item.item,
            descricao=item.descricao,
            altura=item.altura,
            largura=item.largura,
            profundidade=item.profundidade,
            quantidade=item.quantidade,
            unidade=item.unidade,
            preco_unitario=item.preco_unitario,
            preco_total=item.preco_total,
            tipo_item=item.tipo_item,
            tipo_producao=item.tipo_producao,
            ajuste_eur=item.ajuste_eur,
            preco_manual=item.preco_manual,
            modalidade_custeio=item.modalidade_custeio,
            simplificado_urgente=item.simplificado_urgente,
            simplificado_sem_excel=item.simplificado_sem_excel,
            custo_simplificado_urgencia=item.custo_simplificado_urgencia,
            custo_simplificado_sem_excel=item.custo_simplificado_sem_excel,
        )
