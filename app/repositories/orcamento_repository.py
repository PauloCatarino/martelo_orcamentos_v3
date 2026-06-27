"""Repository for budget reads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.domain.orcamento_estados import ESTADO_INICIAL
from app.domain.precos import MargensOrcamento
from app.models import (
    Cliente,
    Orcamento,
    OrcamentoItem,
    OrcamentoItemCusteioLinha,
    OrcamentoItemModulo,
    OrcamentoItemValuesetLinha,
    OrcamentoItemVariavel,
    OrcamentoValuesetLinha,
    OrcamentoVersao,
    OrcamentoVersaoPlacaNaoStock,
    User,
)


@dataclass(frozen=True)
class OrcamentoResumo:
    """Read model for listing budget versions in the UI."""

    orcamento_id: int
    orcamento_versao_id: int
    ano: int
    num_orcamento: str
    numero_versao: int
    codigo_versao: str
    cliente_nome: str
    obra: str | None
    descricao: str | None
    localizacao: str | None
    ref_cliente: str | None
    estado: str
    preco_total: Decimal | None
    created_at: datetime
    enc_phc: str | None = None
    info_1: str | None = None
    info_2: str | None = None
    utilizador: str | None = None
    utilizador_id: int | None = None
    tem_preco_manual: bool = False


@dataclass(frozen=True)
class ClienteResumo:
    """Read model for the customer block of a budget report (phase 8W.1)."""

    id: int
    nome: str
    nome_simplex: str | None
    morada: str | None
    email: str | None
    telefone: str | None
    num_cliente: str | None


@dataclass(frozen=True)
class OrcamentoCriado:
    """Result of creating a simple budget."""

    ano: int
    num_orcamento: str
    numero_versao: int
    codigo_versao: str
    cliente_nome: str
    orcamento_versao_id: int | None = None
    orcamento_id: int | None = None


@dataclass(frozen=True)
class OrcamentoVersaoCriada:
    """Result of duplicating a budget version."""

    orcamento_id: int
    orcamento_versao_id: int
    numero_versao: int
    codigo_versao: str


class OrcamentoRepository:
    """Repository for Orcamento read operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_orcamentos(self) -> list[OrcamentoResumo]:
        """List budget versions with customer and budget data."""
        statement = (
            self._select_orcamento_resumo()
            .order_by(
                Orcamento.ano.desc(),
                Orcamento.num_orcamento.desc(),
                OrcamentoVersao.numero_versao.desc(),
            )
        )

        rows = self.session.execute(statement).mappings().all()

        return [self._row_to_orcamento_resumo(row) for row in rows]

    def find_by_ref_cliente(self, ref_cliente: str) -> list[OrcamentoResumo]:
        """Find budget versions with the same customer reference."""
        ref = (ref_cliente or "").strip()
        if not ref:
            return []

        statement = (
            self._select_orcamento_resumo()
            .where(func.lower(func.trim(Orcamento.ref_cliente)) == ref.lower())
            .order_by(
                Orcamento.ano.desc(),
                Orcamento.num_orcamento.desc(),
                OrcamentoVersao.numero_versao.desc(),
            )
        )

        rows = self.session.execute(statement).mappings().all()

        return [self._row_to_orcamento_resumo(row) for row in rows]

    def get_orcamento_by_versao_id(self, orcamento_versao_id: int) -> OrcamentoResumo | None:
        """Return one budget version summary by version id."""
        statement = self._select_orcamento_resumo().where(OrcamentoVersao.id == orcamento_versao_id)
        row = self.session.execute(statement).mappings().one_or_none()

        if row is None:
            return None

        return self._row_to_orcamento_resumo(row)

    def get_next_num_orcamento(self, ano: int) -> str:
        """Return the next budget number for a year."""
        statement = select(Orcamento.num_orcamento).where(Orcamento.ano == ano)
        existing_numbers = self.session.execute(statement).scalars().all()

        numeric_numbers = [
            int(str(value))
            for value in existing_numbers
            if str(value).isdigit()
        ]

        if numeric_numbers:
            return str(max(numeric_numbers) + 1)

        return f"{ano % 100:02d}0001"

    def create_orcamento_com_versao_01(
        self,
        *,
        ano: int,
        num_orcamento: str,
        cliente_id: int,
        obra: str,
        descricao: str | None,
        localizacao: str | None,
        ref_cliente: str | None,
        created_by_id: int | None,
        enc_phc: str | None = None,
        info_1: str | None = None,
        info_2: str | None = None,
        margens: MargensOrcamento | None = None,
    ) -> OrcamentoCriado:
        """Create a simple budget with version 01.

        ``margens`` are the initial margin values copied into the version;
        None keeps the column defaults (zeros).
        """
        cliente = self.session.get(Cliente, cliente_id)
        if cliente is None:
            raise ValueError("Cliente n\u00e3o encontrado.")

        orcamento = Orcamento(
            ano=ano,
            num_orcamento=num_orcamento,
            cliente_id=cliente.id,
            descricao=descricao,
            obra=obra,
            localizacao=localizacao,
            ref_cliente=ref_cliente,
            info_1=info_1,
            info_2=info_2,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        self.session.add(orcamento)
        self.session.flush()

        codigo_versao = self._format_codigo_versao(num_orcamento, 1)
        versao = OrcamentoVersao(
            orcamento_id=orcamento.id,
            numero_versao=1,
            codigo_versao=codigo_versao,
            estado=ESTADO_INICIAL,
            enc_phc=enc_phc,
            preco_total=Decimal("0"),
            preco_origem=Decimal("0"),
            is_locked=False,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        if margens is not None:
            self._aplicar_margens_versao(versao, margens)
        self.session.add(versao)
        self.session.flush()

        return OrcamentoCriado(
            ano=ano,
            num_orcamento=num_orcamento,
            numero_versao=versao.numero_versao,
            codigo_versao=codigo_versao,
            cliente_nome=cliente.nome,
            orcamento_versao_id=versao.id,
            orcamento_id=orcamento.id,
        )

    def criar_nova_versao(
        self,
        orcamento_versao_id: int,
        created_by_id: int | None = None,
    ) -> OrcamentoVersaoCriada:
        """Duplicate a budget version header into the next version number.

        The new version starts with the initial status and zero total (items
        are not copied here) and INHERITS the source version's margins and
        production default; preco_origem records the source version's total.
        """
        origem = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if origem is None:
            raise ValueError("orcamento_versao not found")

        proximo_numero = self.session.execute(
            select(func.coalesce(func.max(OrcamentoVersao.numero_versao), 0)).where(
                OrcamentoVersao.orcamento_id == origem.orcamento_id
            )
        ).scalar_one() + 1

        orcamento = self.session.get(Orcamento, origem.orcamento_id)
        codigo_versao = self._format_codigo_versao(
            orcamento.num_orcamento, proximo_numero
        )
        versao = OrcamentoVersao(
            orcamento_id=origem.orcamento_id,
            numero_versao=proximo_numero,
            codigo_versao=codigo_versao,
            estado=ESTADO_INICIAL,
            preco_total=Decimal("0"),
            preco_origem=origem.preco_total,
            tipo_producao_default=origem.tipo_producao_default,
            is_locked=False,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        self._aplicar_margens_versao(
            versao,
            MargensOrcamento(
                margem_lucro_pct=origem.margem_lucro_pct,
                margem_mp_pct=origem.margem_mp_pct,
                margem_mao_obra_pct=origem.margem_mao_obra_pct,
                margem_acabamentos_pct=origem.margem_acabamentos_pct,
                custos_administrativos_pct=origem.custos_administrativos_pct,
            ),
        )
        self.session.add(versao)
        self.session.flush()

        return OrcamentoVersaoCriada(
            orcamento_id=versao.orcamento_id,
            orcamento_versao_id=versao.id,
            numero_versao=versao.numero_versao,
            codigo_versao=versao.codigo_versao,
        )

    def duplicar_versao_profunda(
        self,
        orcamento_versao_id: int,
        created_by_id: int | None = None,
    ) -> OrcamentoVersaoCriada:
        """Duplicate a budget version and all version/item-owned children."""
        origem = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if origem is None:
            raise ValueError("orcamento_versao not found")

        proximo_numero = self.session.execute(
            select(func.coalesce(func.max(OrcamentoVersao.numero_versao), 0)).where(
                OrcamentoVersao.orcamento_id == origem.orcamento_id
            )
        ).scalar_one() + 1

        orcamento = self.session.get(Orcamento, origem.orcamento_id)
        if orcamento is None:
            raise ValueError("orcamento not found")

        codigo_versao = self._format_codigo_versao(
            orcamento.num_orcamento,
            proximo_numero,
        )
        nova_versao = OrcamentoVersao(
            orcamento_id=origem.orcamento_id,
            numero_versao=proximo_numero,
            codigo_versao=codigo_versao,
            estado=ESTADO_INICIAL,
            preco_total=origem.preco_total,
            preco_origem=origem.preco_total,
            margem_lucro_pct=origem.margem_lucro_pct,
            margem_mp_pct=origem.margem_mp_pct,
            margem_mao_obra_pct=origem.margem_mao_obra_pct,
            margem_acabamentos_pct=origem.margem_acabamentos_pct,
            custos_administrativos_pct=origem.custos_administrativos_pct,
            tipo_producao_default=origem.tipo_producao_default,
            is_locked=False,
            locked_at=None,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        self.session.add(nova_versao)
        self.session.flush()
        nova_versao_id = nova_versao.id

        map_vsl_versao: dict[int, int] = {}
        valueset_versao = self.session.execute(
            select(OrcamentoValuesetLinha)
            .where(OrcamentoValuesetLinha.orcamento_versao_id == origem.id)
            .order_by(OrcamentoValuesetLinha.ordem.asc(), OrcamentoValuesetLinha.id.asc())
        ).scalars().all()
        for linha in valueset_versao:
            dados = self._valores_para_copia(
                linha,
                exclui={"orcamento_versao_id"},
            )
            copia = OrcamentoValuesetLinha(
                **dados,
                orcamento_versao_id=nova_versao_id,
            )
            self.session.add(copia)
            self.session.flush()
            map_vsl_versao[linha.id] = copia.id

        placas_nao_stock = self.session.execute(
            select(OrcamentoVersaoPlacaNaoStock)
            .where(OrcamentoVersaoPlacaNaoStock.orcamento_versao_id == origem.id)
            .order_by(OrcamentoVersaoPlacaNaoStock.id.asc())
        ).scalars().all()
        for placa in placas_nao_stock:
            dados = self._valores_para_copia(
                placa,
                exclui={"orcamento_versao_id"},
            )
            self.session.add(
                OrcamentoVersaoPlacaNaoStock(
                    **dados,
                    orcamento_versao_id=nova_versao_id,
                )
            )
        self.session.flush()

        map_item: dict[int, int] = {}
        itens = self.session.execute(
            select(OrcamentoItem)
            .where(OrcamentoItem.orcamento_versao_id == origem.id)
            .order_by(OrcamentoItem.ordem.asc(), OrcamentoItem.id.asc())
        ).scalars().all()

        for item in itens:
            dados_item = self._valores_para_copia(
                item,
                exclui={"orcamento_versao_id"},
            )
            novo_item = OrcamentoItem(
                **dados_item,
                orcamento_versao_id=nova_versao_id,
            )
            self.session.add(novo_item)
            self.session.flush()
            map_item[item.id] = novo_item.id

            variaveis = self.session.execute(
                select(OrcamentoItemVariavel)
                .where(OrcamentoItemVariavel.item_id == item.id)
                .order_by(OrcamentoItemVariavel.ordem.asc(), OrcamentoItemVariavel.id.asc())
            ).scalars().all()
            for variavel in variaveis:
                dados = self._valores_para_copia(variavel, exclui={"item_id"})
                self.session.add(OrcamentoItemVariavel(**dados, item_id=novo_item.id))

            map_modulo: dict[int, int] = {}
            modulos = self.session.execute(
                select(OrcamentoItemModulo)
                .where(OrcamentoItemModulo.orcamento_item_id == item.id)
                .order_by(OrcamentoItemModulo.ordem.asc(), OrcamentoItemModulo.id.asc())
            ).scalars().all()
            for modulo in modulos:
                dados = self._valores_para_copia(
                    modulo,
                    exclui={"orcamento_item_id"},
                )
                novo_modulo = OrcamentoItemModulo(
                    **dados,
                    orcamento_item_id=novo_item.id,
                )
                self.session.add(novo_modulo)
                self.session.flush()
                map_modulo[modulo.id] = novo_modulo.id

            valuesets_item = self.session.execute(
                select(OrcamentoItemValuesetLinha)
                .where(OrcamentoItemValuesetLinha.orcamento_item_id == item.id)
                .order_by(
                    OrcamentoItemValuesetLinha.ordem.asc(),
                    OrcamentoItemValuesetLinha.id.asc(),
                )
            ).scalars().all()
            for linha in valuesets_item:
                origem_vsl_id = linha.origem_orcamento_valueset_linha_id
                origem_versao_id = linha.origem_orcamento_versao_id
                dados = self._valores_para_copia(
                    linha,
                    exclui={
                        "orcamento_item_id",
                        "origem_orcamento_valueset_linha_id",
                        "origem_orcamento_versao_id",
                    },
                )
                self.session.add(
                    OrcamentoItemValuesetLinha(
                        **dados,
                        orcamento_item_id=novo_item.id,
                        origem_orcamento_valueset_linha_id=map_vsl_versao.get(
                            origem_vsl_id
                        ),
                        origem_orcamento_versao_id=(
                            nova_versao_id
                            if origem_versao_id == origem.id
                            else origem_versao_id
                        ),
                    )
                )

            linhas_custeio = self.session.execute(
                select(OrcamentoItemCusteioLinha)
                .where(OrcamentoItemCusteioLinha.orcamento_item_id == item.id)
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

            for old_linha_id, old_linha_pai_id in linha_pai_original.items():
                if old_linha_pai_id is None:
                    continue
                nova_linha = map_linha[old_linha_id]
                novo_pai = map_linha.get(old_linha_pai_id)
                if novo_pai is not None:
                    nova_linha.linha_pai_id = novo_pai.id
            self.session.flush()

        return OrcamentoVersaoCriada(
            orcamento_id=nova_versao.orcamento_id,
            orcamento_versao_id=nova_versao.id,
            numero_versao=nova_versao.numero_versao,
            codigo_versao=nova_versao.codigo_versao,
        )

    def update_orcamento(
        self,
        orcamento_id: int,
        *,
        descricao: str | None,
        obra: str,
        localizacao: str | None,
        ref_cliente: str | None,
        info_1: str | None,
        info_2: str | None,
        updated_by_id: int | None = None,
    ) -> bool:
        """Update a budget's general data; False when it does not exist."""
        orcamento = self.session.get(Orcamento, orcamento_id)
        if orcamento is None:
            return False

        orcamento.descricao = descricao
        orcamento.obra = obra
        orcamento.localizacao = localizacao
        orcamento.ref_cliente = ref_cliente
        orcamento.info_1 = info_1
        orcamento.info_2 = info_2
        if updated_by_id is not None:
            orcamento.updated_by_id = updated_by_id
        self.session.flush()

        return True

    def update_enc_phc(self, orcamento_versao_id: int, enc_phc: str | None) -> bool:
        """Update the PHC order number for one budget version."""
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return False

        versao.enc_phc = enc_phc
        self.session.flush()

        return True

    def update_estado(self, orcamento_versao_id: int, estado: str) -> bool:
        """Update the status for one budget version."""
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return False

        versao.estado = estado
        self.session.flush()

        return True

    def update_utilizador(
        self, orcamento_versao_id: int, utilizador_id: int | None
    ) -> bool:
        """Update the creator user shown for one budget version."""
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return False

        versao.created_by_id = utilizador_id
        self.session.flush()

        return True

    def update_cliente(self, orcamento_id: int, cliente_id: int) -> bool:
        """Reassign a budget to another customer; False when it does not exist."""
        orcamento = self.session.get(Orcamento, orcamento_id)
        if orcamento is None:
            return False

        cliente = self.session.get(Cliente, cliente_id)
        if cliente is None:
            raise ValueError("Cliente n\u00e3o encontrado.")

        orcamento.cliente_id = cliente.id
        self.session.flush()

        return True

    def get_cliente_id_by_versao(self, orcamento_versao_id: int) -> int | None:
        """Return the customer id of one budget version (or None)."""
        statement = (
            select(Orcamento.cliente_id)
            .join(OrcamentoVersao, OrcamentoVersao.orcamento_id == Orcamento.id)
            .where(OrcamentoVersao.id == orcamento_versao_id)
        )
        return self.session.execute(statement).scalars().first()

    def get_cliente_da_versao(self, orcamento_versao_id: int) -> ClienteResumo | None:
        """Return the customer details of one budget version (for the report)."""
        statement = (
            select(Cliente)
            .join(Orcamento, Orcamento.cliente_id == Cliente.id)
            .join(OrcamentoVersao, OrcamentoVersao.orcamento_id == Orcamento.id)
            .where(OrcamentoVersao.id == orcamento_versao_id)
        )
        cliente = self.session.execute(statement).scalars().first()
        if cliente is None:
            return None

        return ClienteResumo(
            id=cliente.id,
            nome=cliente.nome,
            nome_simplex=cliente.nome_simplex,
            morada=cliente.morada,
            email=cliente.email,
            telefone=cliente.telefone or cliente.telemovel,
            num_cliente=cliente.num_cliente_phc,
        )

    def _valores_para_copia(self, origem, *, exclui: set[str]) -> dict[str, Any]:
        """Return mapped column values for cloning an ORM object."""
        excluidos = {"id", "created_at", "updated_at"} | exclui
        mapper = sa_inspect(type(origem))
        return {
            attr.key: getattr(origem, attr.key)
            for attr in mapper.column_attrs
            if attr.key not in excluidos
        }

    @staticmethod
    def _aplicar_margens_versao(
        versao: OrcamentoVersao, margens: MargensOrcamento
    ) -> None:
        """Copy margin values into a budget version."""
        versao.margem_lucro_pct = margens.margem_lucro_pct
        versao.margem_mp_pct = margens.margem_mp_pct
        versao.margem_mao_obra_pct = margens.margem_mao_obra_pct
        versao.margem_acabamentos_pct = margens.margem_acabamentos_pct
        versao.custos_administrativos_pct = margens.custos_administrativos_pct

    def _format_codigo_versao(self, num_orcamento: str, numero_versao: int) -> str:
        """Format a budget version code."""
        return f"{num_orcamento}_{numero_versao:02d}"

    def _select_orcamento_resumo(self):
        """Build the base summary select used by listings and detail refresh."""
        return (
            select(
                Orcamento.id.label("orcamento_id"),
                OrcamentoVersao.id.label("orcamento_versao_id"),
                Orcamento.ano.label("ano"),
                Orcamento.num_orcamento.label("num_orcamento"),
                OrcamentoVersao.numero_versao.label("numero_versao"),
                OrcamentoVersao.codigo_versao.label("codigo_versao"),
                Cliente.nome.label("cliente_nome"),
                Orcamento.obra.label("obra"),
                Orcamento.descricao.label("descricao"),
                Orcamento.localizacao.label("localizacao"),
                Orcamento.ref_cliente.label("ref_cliente"),
                OrcamentoVersao.enc_phc.label("enc_phc"),
                Orcamento.info_1.label("info_1"),
                Orcamento.info_2.label("info_2"),
                OrcamentoVersao.estado.label("estado"),
                OrcamentoVersao.preco_total.label("preco_total"),
                OrcamentoVersao.created_at.label("created_at"),
                OrcamentoVersao.created_by_id.label("utilizador_id"),
                User.username.label("utilizador"),
                exists()
                .where(
                    OrcamentoItem.orcamento_versao_id == OrcamentoVersao.id,
                    OrcamentoItem.preco_manual.is_(True),
                )
                .label("tem_preco_manual"),
            )
            .join(Orcamento, OrcamentoVersao.orcamento_id == Orcamento.id)
            .join(Cliente, Orcamento.cliente_id == Cliente.id)
            .outerjoin(User, OrcamentoVersao.created_by_id == User.id)
        )

    def _row_to_orcamento_resumo(self, row: Mapping[str, Any]) -> OrcamentoResumo:
        """Convert a database row mapping into the UI read model."""
        return OrcamentoResumo(
            orcamento_id=row["orcamento_id"],
            orcamento_versao_id=row["orcamento_versao_id"],
            ano=row["ano"],
            num_orcamento=row["num_orcamento"],
            numero_versao=row["numero_versao"],
            codigo_versao=row["codigo_versao"],
            cliente_nome=row["cliente_nome"],
            obra=row["obra"],
            descricao=row["descricao"],
            localizacao=row["localizacao"],
            ref_cliente=row["ref_cliente"],
            estado=row["estado"],
            preco_total=row["preco_total"],
            created_at=row["created_at"],
            enc_phc=row["enc_phc"],
            info_1=row["info_1"],
            info_2=row["info_2"],
            utilizador=row["utilizador"],
            utilizador_id=row["utilizador_id"],
            tem_preco_manual=bool(row["tem_preco_manual"]),
        )
