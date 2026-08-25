"""Service for internal raw material catalog workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.session import app_session
from app.domain.materia_prima_types import (
    ORIGEM_PRECO_MANUAL,
    TIPO_PRECO_TABELA,
    formatar_ref_le,
    prefixo_da_familia,
)
from app.models.def_materia_prima import ORIGEM_DADOS_EXCEL
from app.repositories.def_materia_prima_repository import (
    DefMateriaPrimaRepository,
    DefMateriaPrimaResumo,
    PrecoHistoricoResumo,
)

ORIGEM_DADOS_V3 = "V3"


@dataclass(frozen=True)
class CriarDefMateriaPrimaData:
    """Input data for creating a raw material."""

    descricao: str
    ref_le: str | None = None
    referencia_fornecedor: str | None = None
    tipo_original_excel: str | None = None
    familia_original_excel: str | None = None
    tipo_martelo: str | None = None
    familia_martelo: str | None = None
    coresp_orla_0_4: str | None = None
    coresp_orla_1_0: str | None = None
    unidade: str | None = None
    preco_tabela: Decimal | None = None
    desconto: Decimal | None = None
    margem: Decimal | None = None
    desperdicio_percentagem: Decimal | None = None
    preco_liquido: Decimal | None = None
    comprimento: Decimal | None = None
    largura: Decimal | None = None
    espessura: Decimal | None = None
    fornecedor: str | None = None
    origem_dados: str | None = None
    ativo: bool = True
    observacoes: str | None = None
    tipo_preco: str = TIPO_PRECO_TABELA
    data_ultimo_preco: date | None = None
    stock: bool | None = None
    cor: str | None = None
    nome_fabricante: str | None = None
    ref_phc: str | None = None


@dataclass(frozen=True)
class EditarDefMateriaPrimaData:
    """Input data for editing a raw material."""

    descricao: str
    ref_le: str | None = None
    referencia_fornecedor: str | None = None
    tipo_original_excel: str | None = None
    familia_original_excel: str | None = None
    tipo_martelo: str | None = None
    familia_martelo: str | None = None
    coresp_orla_0_4: str | None = None
    coresp_orla_1_0: str | None = None
    unidade: str | None = None
    preco_tabela: Decimal | None = None
    desconto: Decimal | None = None
    margem: Decimal | None = None
    desperdicio_percentagem: Decimal | None = None
    preco_liquido: Decimal | None = None
    comprimento: Decimal | None = None
    largura: Decimal | None = None
    espessura: Decimal | None = None
    fornecedor: str | None = None
    origem_dados: str | None = None
    ativo: bool = True
    observacoes: str | None = None
    tipo_preco: str = TIPO_PRECO_TABELA
    data_ultimo_preco: date | None = None
    stock: bool | None = None
    cor: str | None = None
    nome_fabricante: str | None = None
    ref_phc: str | None = None


class DefMateriaPrimaService:
    """Application service for DefMateriaPrima workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefMateriaPrimaRepository(session)

    def listar_materias_primas(self) -> list[DefMateriaPrimaResumo]:
        """List all raw materials."""
        return self.repository.list_all()

    def listar_materias_primas_ativas(self) -> list[DefMateriaPrimaResumo]:
        """List active raw materials."""
        return self.repository.list_active()

    def pesquisar(
        self, termo: str | None = None, limite: int = 200
    ) -> list[DefMateriaPrimaResumo]:
        """Search active raw materials (an empty term lists the first results)."""
        return self.repository.pesquisar(termo, limite)

    def obter_por_id(self, id: int) -> DefMateriaPrimaResumo | None:
        """Get one raw material by id."""
        return self.repository.get_by_id(id)

    def obter_por_ref_le(self, ref_le: str | None) -> DefMateriaPrimaResumo | None:
        """Get one raw material by LE reference."""
        normalized = self._normalize_ref_le(ref_le)
        if normalized is None:
            return None

        return self.repository.get_by_ref_le(normalized)

    def criar_materia_prima(self, data: CriarDefMateriaPrimaData) -> DefMateriaPrimaResumo:
        """Create a raw material.

        Sem Ref LE, é atribuída automaticamente a partir da família, com a mesma
        regra de sempre (PLC/FER/ACB/ORL + quatro dígitos).
        """
        descricao = self._normalize_descricao(data.descricao)
        ref_le = self._normalize_ref_le(data.ref_le)
        origem_dados = self._normalize_origem_dados(data.origem_dados)
        if ref_le is None:
            ref_le = self.proxima_ref_le(
                data.familia_martelo or data.familia_original_excel
            )
        self._validate_ref_le_unica(ref_le, exclude_id=None)
        utilizador_id = self._utilizador_atual_id()

        result = self.repository.create_materia_prima(
            criado_por_id=utilizador_id,
            alterado_por_id=utilizador_id,
            descricao=descricao,
            ref_le=ref_le,
            referencia_fornecedor=data.referencia_fornecedor,
            tipo_original_excel=data.tipo_original_excel,
            familia_original_excel=data.familia_original_excel,
            tipo_martelo=data.tipo_martelo,
            familia_martelo=data.familia_martelo,
            coresp_orla_0_4=data.coresp_orla_0_4,
            coresp_orla_1_0=data.coresp_orla_1_0,
            unidade=data.unidade,
            preco_tabela=data.preco_tabela,
            desconto=data.desconto,
            margem=data.margem,
            desperdicio_percentagem=data.desperdicio_percentagem,
            preco_liquido=data.preco_liquido,
            comprimento=data.comprimento,
            largura=data.largura,
            espessura=data.espessura,
            fornecedor=data.fornecedor,
            tipo_preco=data.tipo_preco,
            data_ultimo_preco=data.data_ultimo_preco,
            stock=data.stock,
            cor=data.cor,
            nome_fabricante=data.nome_fabricante,
            ref_phc=data.ref_phc,
            origem_dados=origem_dados,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self._registar_preco_se_mudou(result, anterior=None, origem_dados=origem_dados)
        self.session.commit()

        return result

    def editar_materia_prima(
        self, id: int, data: EditarDefMateriaPrimaData
    ) -> DefMateriaPrimaResumo:
        """Edit a raw material.

        Se o preço mudar, fica registado no histórico — com quem o mudou.
        Orçamentos já feitos não são tocados: cada linha guarda a sua cópia.
        """
        descricao = self._normalize_descricao(data.descricao)
        ref_le = self._normalize_ref_le(data.ref_le)
        origem_dados = self._normalize_origem_dados(data.origem_dados)
        self._validate_ref_le_unica(ref_le, exclude_id=id)
        anterior = self.repository.get_by_id(id)

        result = self.repository.update_materia_prima(
            alterado_por_id=self._utilizador_atual_id(),
            id=id,
            descricao=descricao,
            ref_le=ref_le,
            referencia_fornecedor=data.referencia_fornecedor,
            tipo_original_excel=data.tipo_original_excel,
            familia_original_excel=data.familia_original_excel,
            tipo_martelo=data.tipo_martelo,
            familia_martelo=data.familia_martelo,
            coresp_orla_0_4=data.coresp_orla_0_4,
            coresp_orla_1_0=data.coresp_orla_1_0,
            unidade=data.unidade,
            preco_tabela=data.preco_tabela,
            desconto=data.desconto,
            margem=data.margem,
            desperdicio_percentagem=data.desperdicio_percentagem,
            preco_liquido=data.preco_liquido,
            comprimento=data.comprimento,
            largura=data.largura,
            espessura=data.espessura,
            fornecedor=data.fornecedor,
            tipo_preco=data.tipo_preco,
            data_ultimo_preco=data.data_ultimo_preco,
            stock=data.stock,
            cor=data.cor,
            nome_fabricante=data.nome_fabricante,
            ref_phc=data.ref_phc,
            origem_dados=origem_dados,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self._registar_preco_se_mudou(
            result, anterior=anterior, origem_dados=origem_dados
        )
        self.session.commit()

        return result

    def desativar_materia_prima(self, id: int) -> bool:
        """Deactivate a raw material."""
        return self.definir_ativo(id, ativo=False)

    def definir_ativo(self, id: int, *, ativo: bool) -> bool:
        """Ativar ou desativar um material.

        Um material desativado deixa de aparecer nas escolhas de linhas novas,
        mas continua a existir e os orçamentos que já o usam ficam intactos —
        cada linha guarda a sua própria cópia da descrição e do preço.
        """
        alterado = self.repository.definir_ativo(
            id, ativo=ativo, alterado_por_id=self._utilizador_atual_id()
        )
        if alterado:
            self.session.commit()

        return alterado

    def proxima_ref_le(self, familia: str | None) -> str | None:
        """Próxima Ref LE livre da família (PLC0122), ou None sem família.

        As referências nunca são reaproveitadas: parte-se sempre do maior número
        já usado, mesmo que esse material esteja desativado.
        """
        prefixo = prefixo_da_familia(familia)
        if prefixo is None:
            return None

        return formatar_ref_le(prefixo, self.repository.ultimo_numero_ref_le(prefixo) + 1)

    def historico_precos(self, id: int, limite: int = 50) -> list[PrecoHistoricoResumo]:
        """Histórico de preços de um material, do mais recente para o mais antigo."""
        return self.repository.historico_precos(id, limite)

    def contar_utilizacoes(self, id: int) -> int:
        """Em quantas linhas de orçamento este material já foi usado."""
        return self.repository.contar_utilizacoes(id)

    def _utilizador_atual_id(self) -> int | None:
        """Id de quem está a usar a app, ou None nos scripts (seed, importação)."""
        utilizador = app_session.current_user
        return getattr(utilizador, "id", None)

    def _registar_preco_se_mudou(
        self,
        atual: DefMateriaPrimaResumo,
        *,
        anterior: DefMateriaPrimaResumo | None,
        origem_dados: str,
    ) -> None:
        """Escrever no histórico quando o preço muda (ou quando o material nasce)."""
        campos = ("preco_tabela", "desconto", "margem", "preco_liquido")
        if anterior is not None and all(
            getattr(anterior, campo) == getattr(atual, campo) for campo in campos
        ):
            return

        if all(getattr(atual, campo) is None for campo in campos):
            return

        self.repository.registar_preco(
            materia_prima_id=atual.id,
            ref_le=atual.ref_le,
            preco_tabela=atual.preco_tabela,
            desconto=atual.desconto,
            margem=atual.margem,
            preco_liquido=atual.preco_liquido,
            data_preco=atual.data_ultimo_preco,
            origem=(
                ORIGEM_DADOS_EXCEL
                if origem_dados == ORIGEM_DADOS_EXCEL
                else ORIGEM_PRECO_MANUAL
            ),
            user_id=self._utilizador_atual_id(),
        )

    def _normalize_descricao(self, descricao: str | None) -> str:
        normalized = (descricao or "").strip()
        if not normalized:
            raise ValueError("descricao is required")

        return normalized

    def _normalize_ref_le(self, ref_le: str | None) -> str | None:
        if ref_le is None:
            return None

        normalized = ref_le.strip()
        return normalized or None

    def _normalize_origem_dados(self, origem_dados: str | None) -> str:
        """Sem origem indicada, o material nasceu no próprio V3.

        Era EXCEL enquanto o ficheiro mandava no catálogo; agora o Excel é uma
        origem entre outras e tem de ser dita expressamente (é o que a
        importação faz).
        """
        if not origem_dados or not origem_dados.strip():
            return ORIGEM_DADOS_V3

        return origem_dados.strip()

    def _validate_ref_le_unica(self, ref_le: str | None, exclude_id: int | None) -> None:
        if ref_le is None:
            return

        existing = self.repository.get_by_ref_le(ref_le)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("ref_le ja existe")
