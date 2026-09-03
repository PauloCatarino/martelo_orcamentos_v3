"""Service for internal raw material catalog workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.session import app_session
from app.domain.materia_prima_types import (
    ORIGEM_PRECO_MANUAL,
    ORIGENS_PRECO_VALIDAS,
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


def _origem_do_preco(origem_dados: str) -> str:
    """A que origem pertence este preço, para o histórico.

    A origem dos dados e a origem do preço partilham as palavras (EXCEL,
    FORNECEDOR); tudo o resto — incluindo o próprio V3 — é uma alteração
    manual de alguém.
    """
    return origem_dados if origem_dados in ORIGENS_PRECO_VALIDAS else ORIGEM_PRECO_MANUAL


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
    link: str | None = None
    fornecedor_id: int | None = None


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
    link: str | None = None
    fornecedor_id: int | None = None


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
        fornecedor_id = self._resolver_fornecedor_id(data)

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
            link=data.link,
            fornecedor_id=fornecedor_id,
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
        fornecedor_id = self._resolver_fornecedor_id(data, anterior)

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
            link=data.link,
            fornecedor_id=fornecedor_id,
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

    def _resolver_fornecedor_id(
        self, data, anterior: DefMateriaPrimaResumo | None = None
    ) -> int | None:
        """Descobrir a que fornecedor pertence o material.

        Quem edita na aplicação escolhe o fornecedor de uma lista e manda o id.
        Quem importa (do Excel, ou amanhã da resposta de um fornecedor) só tem o
        **nome** — e sem esta tradução a ligação perdia-se a cada importação,
        deixando o pedido de preços sem saber a quem escrever.
        """
        if data.fornecedor_id is not None:
            return data.fornecedor_id

        nome = (data.fornecedor or "").strip()
        if not nome:
            # Nada dito sobre o fornecedor: fica como estava.
            return getattr(anterior, "fornecedor_id", None)

        from app.repositories.def_fornecedor_repository import DefFornecedorRepository

        fornecedor = DefFornecedorRepository(self.session).get_by_nome(nome)
        return fornecedor.id if fornecedor is not None else None

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

        self._registar_preco_de_partida(anterior)
        self.repository.registar_preco(
            materia_prima_id=atual.id,
            ref_le=atual.ref_le,
            preco_tabela=atual.preco_tabela,
            desconto=atual.desconto,
            margem=atual.margem,
            preco_liquido=atual.preco_liquido,
            data_preco=atual.data_ultimo_preco,
            origem=_origem_do_preco(origem_dados),
            user_id=self._utilizador_atual_id(),
        )

    def _registar_preco_de_partida(
        self, anterior: DefMateriaPrimaResumo | None
    ) -> None:
        """Guardar o preço que lá estava, quando o material ainda não tem histórico.

        Sem isto, a primeira alteração de preço de um material apagava o passado
        sem deixar rasto: o histórico ficava com uma linha só — a nova — e a
        pergunta "quanto é que isto custava antes?" deixava de ter resposta.
        Acontecia a todos os materiais que nasceram fora da aplicação (a
        importação inicial do Excel), que são a maioria do catálogo.

        Escreve a linha de partida com o preço ANTIGO e sem utilizador: não foi
        ninguém que o pôs pela aplicação, veio com o material.
        """
        if anterior is None or self.repository.tem_historico_precos(anterior.id):
            return

        campos = ("preco_tabela", "desconto", "margem", "preco_liquido")
        if all(getattr(anterior, campo) is None for campo in campos):
            return

        self.repository.registar_preco(
            materia_prima_id=anterior.id,
            ref_le=anterior.ref_le,
            preco_tabela=anterior.preco_tabela,
            desconto=anterior.desconto,
            margem=anterior.margem,
            preco_liquido=anterior.preco_liquido,
            data_preco=anterior.data_ultimo_preco,
            origem=_origem_do_preco(
                self._normalize_origem_dados(anterior.origem_dados)
            ),
            user_id=None,
            observacoes="Preço de partida, registado quando o material foi alterado pela primeira vez.",
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
