"""Repository for internal raw material catalog reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.materia_prima_types import (
    ORIGEM_PRECO_MANUAL,
    TIPO_PRECO_LIVRE,
    TIPO_PRECO_TABELA,
)
from app.models import DefMateriaPrima, DefMateriaPrimaPrecoHistorico, User


@dataclass(frozen=True)
class DefMateriaPrimaResumo:
    """Read model for listing internal raw materials."""

    id: int
    ref_le: str | None
    referencia_fornecedor: str | None
    descricao: str
    tipo_original_excel: str | None
    familia_original_excel: str | None
    tipo_martelo: str | None
    familia_martelo: str | None
    unidade: str | None
    preco_tabela: Decimal | None
    desconto: Decimal | None
    margem: Decimal | None
    preco_liquido: Decimal | None
    comprimento: Decimal | None
    largura: Decimal | None
    espessura: Decimal | None
    fornecedor: str | None
    origem_dados: str
    ativo: bool
    observacoes: str | None
    coresp_orla_0_4: str | None = None
    coresp_orla_1_0: str | None = None
    desperdicio_percentagem: Decimal | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    tipo_preco: str = TIPO_PRECO_TABELA
    data_ultimo_preco: date | None = None
    stock: bool | None = None
    cor: str | None = None
    nome_fabricante: str | None = None
    ref_phc: str | None = None
    link: str | None = None
    imagem_ficheiro: str | None = None
    nome_imos: str | None = None
    fornecedor_id: int | None = None
    # Nomes de quem criou e de quem alterou pela última vez, prontos a mostrar.
    criado_por: str | None = None
    alterado_por: str | None = None

    @property
    def preco_livre(self) -> bool:
        """True quando o preço é para escrever dentro de cada orçamento."""
        return self.tipo_preco == TIPO_PRECO_LIVRE


@dataclass(frozen=True)
class PrecoHistoricoResumo:
    """Read model for one recorded price of a raw material."""

    id: int
    materia_prima_id: int
    ref_le: str | None
    preco_tabela: Decimal | None
    desconto: Decimal | None
    margem: Decimal | None
    preco_liquido: Decimal | None
    data_preco: date | None
    origem: str
    utilizador: str | None
    observacoes: str | None
    created_at: datetime | None = None


class DefMateriaPrimaRepository:
    """Repository for DefMateriaPrima operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[DefMateriaPrimaResumo]:
        """List all raw materials."""
        statement = select(DefMateriaPrima).order_by(
            DefMateriaPrima.descricao.asc(), DefMateriaPrima.id.asc()
        )
        materias = self.session.execute(statement).scalars().all()

        return [self._to_resumo(materia) for materia in materias]

    def list_active(self) -> list[DefMateriaPrimaResumo]:
        """List active raw materials."""
        statement = (
            select(DefMateriaPrima)
            .where(DefMateriaPrima.ativo.is_(True))
            .order_by(DefMateriaPrima.descricao.asc(), DefMateriaPrima.id.asc())
        )
        materias = self.session.execute(statement).scalars().all()

        return [self._to_resumo(materia) for materia in materias]

    def pesquisar(
        self, termo: str | None = None, limite: int = 200
    ) -> list[DefMateriaPrimaResumo]:
        """Search active raw materials by reference, description, type or family.

        An empty term lists the first ``limite`` active materials.
        """
        statement = select(DefMateriaPrima).where(DefMateriaPrima.ativo.is_(True))

        if termo and termo.strip():
            like = f"%{termo.strip()}%"
            statement = statement.where(
                or_(
                    DefMateriaPrima.ref_le.ilike(like),
                    DefMateriaPrima.descricao.ilike(like),
                    DefMateriaPrima.referencia_fornecedor.ilike(like),
                    DefMateriaPrima.tipo_martelo.ilike(like),
                    DefMateriaPrima.familia_martelo.ilike(like),
                )
            )

        statement = statement.order_by(
            DefMateriaPrima.descricao.asc(), DefMateriaPrima.id.asc()
        ).limit(limite)
        materias = self.session.execute(statement).scalars().all()

        return [self._to_resumo(materia) for materia in materias]

    def get_by_id(self, id: int) -> DefMateriaPrimaResumo | None:
        """Get one raw material by id."""
        materia = self.session.get(DefMateriaPrima, id)
        if materia is None:
            return None

        return self._to_resumo(materia)

    def get_by_ref_le(self, ref_le: str) -> DefMateriaPrimaResumo | None:
        """Get one raw material by its LE reference."""
        statement = select(DefMateriaPrima).where(DefMateriaPrima.ref_le == ref_le)
        materia = self.session.execute(statement).scalars().first()
        if materia is None:
            return None

        return self._to_resumo(materia)

    def create_materia_prima(
        self,
        *,
        descricao: str,
        ref_le: str | None = None,
        referencia_fornecedor: str | None = None,
        tipo_original_excel: str | None = None,
        familia_original_excel: str | None = None,
        tipo_martelo: str | None = None,
        familia_martelo: str | None = None,
        coresp_orla_0_4: str | None = None,
        coresp_orla_1_0: str | None = None,
        unidade: str | None = None,
        preco_tabela: Decimal | None = None,
        desconto: Decimal | None = None,
        margem: Decimal | None = None,
        desperdicio_percentagem: Decimal | None = None,
        preco_liquido: Decimal | None = None,
        comprimento: Decimal | None = None,
        largura: Decimal | None = None,
        espessura: Decimal | None = None,
        fornecedor: str | None = None,
        origem_dados: str = "EXCEL",
        ativo: bool = True,
        observacoes: str | None = None,
        tipo_preco: str = TIPO_PRECO_TABELA,
        data_ultimo_preco: date | None = None,
        stock: bool | None = None,
        cor: str | None = None,
        nome_fabricante: str | None = None,
        ref_phc: str | None = None,
        link: str | None = None,
        imagem_ficheiro: str | None = None,
        nome_imos: str | None = None,
        fornecedor_id: int | None = None,
        criado_por_id: int | None = None,
        alterado_por_id: int | None = None,
    ) -> DefMateriaPrimaResumo:
        """Create one raw material."""
        materia = DefMateriaPrima(
            tipo_preco=tipo_preco,
            data_ultimo_preco=data_ultimo_preco,
            stock=stock,
            cor=cor,
            nome_fabricante=nome_fabricante,
            ref_phc=ref_phc,
            link=link,
            imagem_ficheiro=imagem_ficheiro,
            nome_imos=nome_imos,
            fornecedor_id=fornecedor_id,
            criado_por_id=criado_por_id,
            alterado_por_id=alterado_por_id,
            descricao=descricao,
            ref_le=ref_le,
            referencia_fornecedor=referencia_fornecedor,
            tipo_original_excel=tipo_original_excel,
            familia_original_excel=familia_original_excel,
            tipo_martelo=tipo_martelo,
            familia_martelo=familia_martelo,
            coresp_orla_0_4=coresp_orla_0_4,
            coresp_orla_1_0=coresp_orla_1_0,
            unidade=unidade,
            preco_tabela=preco_tabela,
            desconto=desconto,
            margem=margem,
            desperdicio_percentagem=desperdicio_percentagem,
            preco_liquido=preco_liquido,
            comprimento=comprimento,
            largura=largura,
            espessura=espessura,
            fornecedor=fornecedor,
            origem_dados=origem_dados,
            ativo=ativo,
            observacoes=observacoes,
        )
        self.session.add(materia)
        self.session.flush()

        return self._to_resumo(materia)

    def update_materia_prima(
        self,
        *,
        id: int,
        descricao: str,
        ref_le: str | None = None,
        referencia_fornecedor: str | None = None,
        tipo_original_excel: str | None = None,
        familia_original_excel: str | None = None,
        tipo_martelo: str | None = None,
        familia_martelo: str | None = None,
        coresp_orla_0_4: str | None = None,
        coresp_orla_1_0: str | None = None,
        unidade: str | None = None,
        preco_tabela: Decimal | None = None,
        desconto: Decimal | None = None,
        margem: Decimal | None = None,
        desperdicio_percentagem: Decimal | None = None,
        preco_liquido: Decimal | None = None,
        comprimento: Decimal | None = None,
        largura: Decimal | None = None,
        espessura: Decimal | None = None,
        fornecedor: str | None = None,
        origem_dados: str = "EXCEL",
        ativo: bool = True,
        observacoes: str | None = None,
        tipo_preco: str = TIPO_PRECO_TABELA,
        data_ultimo_preco: date | None = None,
        stock: bool | None = None,
        cor: str | None = None,
        nome_fabricante: str | None = None,
        ref_phc: str | None = None,
        link: str | None = None,
        imagem_ficheiro: str | None = None,
        nome_imos: str | None = None,
        fornecedor_id: int | None = None,
        alterado_por_id: int | None = None,
    ) -> DefMateriaPrimaResumo:
        """Update one raw material."""
        materia = self.session.get(DefMateriaPrima, id)
        if materia is None:
            raise ValueError("def_materia_prima not found")

        materia.descricao = descricao
        materia.ref_le = ref_le
        materia.referencia_fornecedor = referencia_fornecedor
        materia.tipo_original_excel = tipo_original_excel
        materia.familia_original_excel = familia_original_excel
        materia.tipo_martelo = tipo_martelo
        materia.familia_martelo = familia_martelo
        materia.coresp_orla_0_4 = coresp_orla_0_4
        materia.coresp_orla_1_0 = coresp_orla_1_0
        materia.unidade = unidade
        materia.preco_tabela = preco_tabela
        materia.desconto = desconto
        materia.margem = margem
        materia.desperdicio_percentagem = desperdicio_percentagem
        materia.preco_liquido = preco_liquido
        materia.comprimento = comprimento
        materia.largura = largura
        materia.espessura = espessura
        materia.fornecedor = fornecedor
        materia.origem_dados = origem_dados
        materia.ativo = ativo
        materia.observacoes = observacoes
        materia.tipo_preco = tipo_preco
        materia.data_ultimo_preco = data_ultimo_preco
        materia.stock = stock
        materia.cor = cor
        materia.nome_fabricante = nome_fabricante
        materia.ref_phc = ref_phc
        materia.link = link
        materia.imagem_ficheiro = imagem_ficheiro
        materia.nome_imos = nome_imos
        materia.fornecedor_id = fornecedor_id
        if alterado_por_id is not None:
            materia.alterado_por_id = alterado_por_id
        self.session.flush()

        return self._to_resumo(materia)

    def deactivate_materia_prima(self, id: int) -> bool:
        """Deactivate one raw material."""
        return self.definir_ativo(id, ativo=False)

    def definir_ativo(
        self, id: int, *, ativo: bool, alterado_por_id: int | None = None
    ) -> bool:
        """Ativar ou desativar um material. Devolve False se não existir.

        Desativar não apaga nada: o material deixa de aparecer nas escolhas de
        linhas novas, mas os orçamentos onde já foi usado ficam exatamente como
        estavam, porque cada linha guarda a sua própria cópia dos dados.
        """
        materia = self.session.get(DefMateriaPrima, id)
        if materia is None:
            return False

        materia.ativo = ativo
        if alterado_por_id is not None:
            materia.alterado_por_id = alterado_por_id
        self.session.flush()

        return True

    def ultimo_numero_ref_le(self, prefixo: str) -> int:
        """Maior número já usado numa família (PLC -> 121), 0 quando não há.

        Olha para TODAS as referências, ativas ou não: uma Ref LE nunca pode ser
        reaproveitada, porque identifica o material nos orçamentos antigos.
        """
        statement = select(DefMateriaPrima.ref_le).where(
            DefMateriaPrima.ref_le.like(f"{prefixo}%")
        )
        maior = 0
        for (ref_le,) in self.session.execute(statement):
            sufixo = (ref_le or "")[len(prefixo) :]
            if sufixo.isdigit():
                maior = max(maior, int(sufixo))

        return maior

    def contar_utilizacoes(self, materia_prima_id: int) -> int:
        """Quantas linhas de orçamento usam este material (todas as versões)."""
        from app.models import (
            OrcamentoItemCusteioLinha,
            OrcamentoItemValuesetLinha,
            OrcamentoValuesetLinha,
        )

        total = 0
        for modelo in (
            OrcamentoItemCusteioLinha,
            OrcamentoItemValuesetLinha,
            OrcamentoValuesetLinha,
        ):
            statement = select(func.count()).select_from(modelo).where(
                modelo.materia_prima_id == materia_prima_id
            )
            total += self.session.execute(statement).scalar_one()

        return total

    def registar_preco(
        self,
        *,
        materia_prima_id: int,
        ref_le: str | None = None,
        preco_tabela: Decimal | None = None,
        desconto: Decimal | None = None,
        margem: Decimal | None = None,
        preco_liquido: Decimal | None = None,
        data_preco: date | None = None,
        origem: str = ORIGEM_PRECO_MANUAL,
        user_id: int | None = None,
        observacoes: str | None = None,
    ) -> None:
        """Escrever uma linha no histórico de preços (nunca reescreve nada)."""
        self.session.add(
            DefMateriaPrimaPrecoHistorico(
                materia_prima_id=materia_prima_id,
                ref_le=ref_le,
                preco_tabela=preco_tabela,
                desconto=desconto,
                margem=margem,
                preco_liquido=preco_liquido,
                data_preco=data_preco,
                origem=origem,
                user_id=user_id,
                observacoes=observacoes,
            )
        )
        self.session.flush()

    def tem_historico_precos(self, materia_prima_id: int) -> bool:
        """Se este material já tem alguma linha no histórico de preços."""
        statement = (
            select(DefMateriaPrimaPrecoHistorico.id)
            .where(DefMateriaPrimaPrecoHistorico.materia_prima_id == materia_prima_id)
            .limit(1)
        )

        return self.session.execute(statement).first() is not None

    def historico_precos(
        self, materia_prima_id: int, limite: int = 50
    ) -> list[PrecoHistoricoResumo]:
        """Histórico de preços de um material, do mais recente para o mais antigo."""
        statement = (
            select(DefMateriaPrimaPrecoHistorico, User.nome)
            .join(User, User.id == DefMateriaPrimaPrecoHistorico.user_id, isouter=True)
            .where(DefMateriaPrimaPrecoHistorico.materia_prima_id == materia_prima_id)
            .order_by(
                DefMateriaPrimaPrecoHistorico.created_at.desc(),
                DefMateriaPrimaPrecoHistorico.id.desc(),
            )
            .limit(limite)
        )

        return [
            PrecoHistoricoResumo(
                id=linha.id,
                materia_prima_id=linha.materia_prima_id,
                ref_le=linha.ref_le,
                preco_tabela=linha.preco_tabela,
                desconto=linha.desconto,
                margem=linha.margem,
                preco_liquido=linha.preco_liquido,
                data_preco=linha.data_preco,
                origem=linha.origem,
                utilizador=nome,
                observacoes=linha.observacoes,
                created_at=linha.created_at,
            )
            for linha, nome in self.session.execute(statement)
        ]

    def _to_resumo(self, materia: DefMateriaPrima) -> DefMateriaPrimaResumo:
        """Convert an ORM raw material to the read model."""
        return DefMateriaPrimaResumo(
            id=materia.id,
            ref_le=materia.ref_le,
            referencia_fornecedor=materia.referencia_fornecedor,
            descricao=materia.descricao,
            tipo_original_excel=materia.tipo_original_excel,
            familia_original_excel=materia.familia_original_excel,
            tipo_martelo=materia.tipo_martelo,
            familia_martelo=materia.familia_martelo,
            coresp_orla_0_4=materia.coresp_orla_0_4,
            coresp_orla_1_0=materia.coresp_orla_1_0,
            desperdicio_percentagem=materia.desperdicio_percentagem,
            unidade=materia.unidade,
            preco_tabela=materia.preco_tabela,
            desconto=materia.desconto,
            margem=materia.margem,
            preco_liquido=materia.preco_liquido,
            comprimento=materia.comprimento,
            largura=materia.largura,
            espessura=materia.espessura,
            fornecedor=materia.fornecedor,
            origem_dados=materia.origem_dados,
            ativo=materia.ativo,
            observacoes=materia.observacoes,
            created_at=materia.created_at,
            updated_at=materia.updated_at,
            tipo_preco=materia.tipo_preco,
            data_ultimo_preco=materia.data_ultimo_preco,
            stock=materia.stock,
            cor=materia.cor,
            nome_fabricante=materia.nome_fabricante,
            ref_phc=materia.ref_phc,
            link=materia.link,
            imagem_ficheiro=materia.imagem_ficheiro,
            nome_imos=materia.nome_imos,
            fornecedor_id=materia.fornecedor_id,
            criado_por=_nome_do_utilizador(materia.criado_por),
            alterado_por=_nome_do_utilizador(materia.alterado_por),
        )


def _nome_do_utilizador(user) -> str | None:
    """Nome de quem mexeu, ou None quando o registo não tem utilizador."""
    if user is None:
        return None

    return user.nome or user.username
