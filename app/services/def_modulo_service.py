"""Service for the reusable module/article library (phase 8U.0).

Modules store only the parametric STRUCTURE (no material/price); on import they
become a copy/paste into an item costing (the inserted lines are NOT linked back
to the module). This phase covers create / read / list / search / delete only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.domain.custeio_linha_types import (
    DIVISAO_INDEPENDENTE,
    PECA,
    PECA_COMPOSTA,
    normalize_custeio_linha_type,
)
from app.domain.modulo_categorias import (
    AMBITO_GLOBAL,
    AMBITO_UTILIZADOR,
    OUTROS,
    normalize_modulo_ambito,
    normalize_modulo_categoria,
)
from app.domain.modulo_estrutura import selecionar_linhas_topo
from app.domain.modulo_pesquisa import filtrar_por_termo
from app.repositories.def_modulo_repository import (
    DefModuloLinhaResumo,
    DefModuloRepository,
    DefModuloResumo,
)
from app.repositories.def_peca_componente_repository import DefPecaComponenteRepository
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)


@dataclass(frozen=True)
class CriarDefModuloLinhaData:
    """Input data for one structural line of a module."""

    ordem: int
    tipo_linha: str = PECA
    def_peca_id: int | None = None
    def_peca_codigo: str | None = None
    codigo: str | None = None
    descricao: str | None = None
    descricao_livre: str | None = None
    qt_mod: str | None = None
    qt_und: str | None = None
    comp: str | None = None
    larg: str | None = None
    esp: str | None = None
    chave_valueset: str | None = None
    codigo_orlas: str | None = None
    def_regra_quantidade_id: int | None = None
    linha_pai_ordem: int | None = None
    nivel: int = 0
    ativo: bool = True


@dataclass(frozen=True)
class CriarDefModuloData:
    """Input data for creating a module (header + lines)."""

    codigo: str
    nome: str
    descricao: str | None = None
    ambito: str = AMBITO_UTILIZADOR
    user_id: int | None = None
    categoria: str = "OUTROS"
    imagem_path: str | None = None
    ativo: bool = True
    linhas: list[CriarDefModuloLinhaData] = field(default_factory=list)


@dataclass(frozen=True)
class EditarDefModuloCabecalhoData:
    """Input data for editing a module header (code is fixed)."""

    nome: str
    descricao: str | None = None
    ambito: str = AMBITO_UTILIZADOR
    user_id: int | None = None
    categoria: str = "OUTROS"
    imagem_path: str | None = None


@dataclass(frozen=True)
class DefModuloComLinhas:
    """A module header together with its structural lines."""

    modulo: DefModuloResumo
    linhas: list[DefModuloLinhaResumo]


@dataclass(frozen=True)
class ModuloComContagem:
    """A module header plus its line count, for the save-dialog listing."""

    modulo: DefModuloResumo
    num_linhas: int


class DefModuloService:
    """Application service for the reusable module/article library."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefModuloRepository(session)

    def listar_por_ambito_utilizador(
        self,
        user_id: int | None,
        categoria: str | None = None,
        termo: str | None = None,
    ) -> list[DefModuloResumo]:
        """List the user's own active modules, filtered by category and term."""
        modulos = [
            modulo
            for modulo in self.repository.list_active()
            if normalize_modulo_ambito(modulo.ambito) == AMBITO_UTILIZADOR
            and modulo.user_id == user_id
        ]
        return self._filtrar(modulos, categoria, termo)

    def listar_globais(
        self,
        categoria: str | None = None,
        termo: str | None = None,
    ) -> list[DefModuloResumo]:
        """List the active GLOBAL modules, filtered by category and term."""
        modulos = [
            modulo
            for modulo in self.repository.list_active()
            if normalize_modulo_ambito(modulo.ambito) == AMBITO_GLOBAL
        ]
        return self._filtrar(modulos, categoria, termo)

    def listar_modulos_para_dialogo(
        self, user_id: int | None
    ) -> tuple[list[ModuloComContagem], list[ModuloComContagem]]:
        """Return (utilizador, globais) active modules with line counts.

        For the save dialog: the user's own modules and the global ones, each
        with the number of stored lines. The dialog filters by category/term
        in-memory (reusing the same '%' search).
        """
        contagens = self.repository.contar_linhas_por_modulo()

        def com_contagem(modulos):
            return [
                ModuloComContagem(modulo=modulo, num_linhas=contagens.get(modulo.id, 0))
                for modulo in modulos
            ]

        return (
            com_contagem(self.listar_por_ambito_utilizador(user_id)),
            com_contagem(self.listar_globais()),
        )

    def obter_com_linhas(self, modulo_id: int) -> DefModuloComLinhas | None:
        """Get one module with its ordered structural lines, or None."""
        modulo = self.repository.get_by_id(modulo_id)
        if modulo is None:
            return None

        return DefModuloComLinhas(
            modulo=modulo,
            linhas=self.repository.list_linhas(modulo_id),
        )

    def criar(self, data: CriarDefModuloData) -> DefModuloComLinhas:
        """Create a module (header + lines) in one transaction."""
        codigo = self._normalize_codigo(data.codigo)
        nome = self._normalize_required(data.nome, "nome")
        ambito = normalize_modulo_ambito(data.ambito)
        user_id = data.user_id if ambito == AMBITO_UTILIZADOR else None
        if ambito == AMBITO_UTILIZADOR and user_id is None:
            raise ValueError("user_id é obrigatório no âmbito UTILIZADOR")
        if self.repository.get_by_codigo(codigo) is not None:
            raise ValueError(f"Já existe um módulo com o código {codigo}.")

        modulo = self.repository.create_modulo(
            codigo=codigo,
            nome=nome,
            descricao=self._normalize_optional(data.descricao),
            ambito=ambito,
            user_id=user_id,
            categoria=normalize_modulo_categoria(data.categoria),
            imagem_path=self._normalize_optional(data.imagem_path),
            ativo=data.ativo,
        )

        self._persistir_linhas(modulo.id, data.linhas)

        self.session.commit()

        return DefModuloComLinhas(
            modulo=self.repository.get_by_id(modulo.id),
            linhas=self.repository.list_linhas(modulo.id),
        )

    def _persistir_linhas(self, modulo_id: int, linhas) -> None:
        """Create every structural line for a module (shared by criar/substituir)."""
        for linha in linhas:
            self.repository.create_linha(
                def_modulo_id=modulo_id,
                ordem=linha.ordem,
                tipo_linha=normalize_custeio_linha_type(linha.tipo_linha),
                def_peca_id=linha.def_peca_id,
                def_peca_codigo=linha.def_peca_codigo,
                codigo=linha.codigo,
                descricao=linha.descricao,
                descricao_livre=linha.descricao_livre,
                qt_mod=linha.qt_mod,
                qt_und=linha.qt_und,
                comp=linha.comp,
                larg=linha.larg,
                esp=linha.esp,
                chave_valueset=linha.chave_valueset,
                codigo_orlas=linha.codigo_orlas,
                def_regra_quantidade_id=linha.def_regra_quantidade_id,
                linha_pai_ordem=linha.linha_pai_ordem,
                nivel=linha.nivel,
                ativo=linha.ativo,
            )

    def guardar_de_linhas_custeio(
        self,
        *,
        orcamento_item_id: int,
        linha_ids,
        codigo: str,
        nome: str,
        descricao: str | None = None,
        ambito: str = AMBITO_UTILIZADOR,
        user_id: int | None = None,
        categoria: str = OUTROS,
        imagem_path: str | None = None,
    ) -> DefModuloComLinhas:
        """Save selected costing lines as a reusable module (phase 8U.1/8U.2).

        Stores the top-level lines (divisions, simple pieces, composite headers,
        standalone hardware) AND, for each composite, its CHILD lines (nivel>0)
        so their measure formulas/rules are preserved (linha_pai_ordem points to
        the parent's module ordem). Only STRUCTURAL fields are copied — never
        material/price/orla-cost or real dimensions. Creates the module header +
        lines and commits.
        """
        custeio_repository = OrcamentoItemCusteioLinhaRepository(self.session)
        componente_repository = DefPecaComponenteRepository(self.session)

        linhas = custeio_repository.list_active_by_orcamento_item(orcamento_item_id)
        topo = selecionar_linhas_topo(linhas, linha_ids)
        if not topo:
            raise ValueError("Selecione pelo menos uma linha de custeio para guardar.")

        linhas_modulo = self._linhas_modulo_de_custeio(
            linhas, topo, componente_repository
        )

        return self.criar(
            CriarDefModuloData(
                codigo=codigo,
                nome=nome,
                descricao=descricao,
                ambito=ambito,
                user_id=user_id,
                categoria=categoria,
                imagem_path=imagem_path,
                linhas=linhas_modulo,
            )
        )

    def substituir_modulo(
        self,
        modulo_id: int,
        data: CriarDefModuloData,
    ) -> DefModuloComLinhas:
        """Overwrite an existing module: replace its lines and update the header.

        Keeps the same id/code (the code is fixed). The current
        def_modulo_linhas are deleted and recreated from ``data.linhas`` (same
        structure-only rule as criar/guardar). The header fields
        (nome/descricao/categoria/ambito/imagem_path + user_id per scope) are
        updated. Commits.
        """
        atual = self.repository.get_by_id(modulo_id)
        if atual is None:
            raise ValueError("Módulo não encontrado.")

        nome = self._normalize_required(data.nome, "nome")
        ambito = normalize_modulo_ambito(data.ambito)
        user_id = data.user_id if ambito == AMBITO_UTILIZADOR else None
        if ambito == AMBITO_UTILIZADOR and user_id is None:
            raise ValueError("user_id é obrigatório no âmbito UTILIZADOR")

        self.repository.update_cabecalho(
            id=modulo_id,
            nome=nome,
            descricao=self._normalize_optional(data.descricao),
            ambito=ambito,
            user_id=user_id,
            categoria=normalize_modulo_categoria(data.categoria),
            imagem_path=self._normalize_optional(data.imagem_path),
        )

        self.repository.delete_linhas_do_modulo(modulo_id)
        self._persistir_linhas(modulo_id, data.linhas)

        self.session.commit()

        return DefModuloComLinhas(
            modulo=self.repository.get_by_id(modulo_id),
            linhas=self.repository.list_linhas(modulo_id),
        )

    def substituir_de_linhas_custeio(
        self,
        *,
        modulo_id: int,
        orcamento_item_id: int,
        linha_ids,
        nome: str,
        descricao: str | None = None,
        ambito: str = AMBITO_UTILIZADOR,
        user_id: int | None = None,
        categoria: str = OUTROS,
        imagem_path: str | None = None,
    ) -> DefModuloComLinhas:
        """Overwrite an existing module from the current costing selection.

        Same structure rule as guardar_de_linhas_custeio (top-level lines plus
        each composite's children, structure not material/price); replaces the
        module's stored lines and updates its header, keeping id/code.
        """
        custeio_repository = OrcamentoItemCusteioLinhaRepository(self.session)
        componente_repository = DefPecaComponenteRepository(self.session)

        linhas = custeio_repository.list_active_by_orcamento_item(orcamento_item_id)
        topo = selecionar_linhas_topo(linhas, linha_ids)
        if not topo:
            raise ValueError("Selecione pelo menos uma linha de custeio para guardar.")

        linhas_modulo = self._linhas_modulo_de_custeio(
            linhas, topo, componente_repository
        )

        # The code is fixed on replace; pass the existing one through CriarDefModuloData.
        atual = self.repository.get_by_id(modulo_id)
        codigo = atual.codigo if atual is not None else ""

        return self.substituir_modulo(
            modulo_id,
            CriarDefModuloData(
                codigo=codigo,
                nome=nome,
                descricao=descricao,
                ambito=ambito,
                user_id=user_id,
                categoria=categoria,
                imagem_path=imagem_path,
                linhas=linhas_modulo,
            ),
        )

    def _linhas_modulo_de_custeio(
        self, linhas, topo, componente_repository
    ) -> list[CriarDefModuloLinhaData]:
        """Build the module lines for the selection, INCLUDING composite children.

        Each top-level line gets a sequential ordem; a composite's children
        (nivel>0, linha_pai_id == header) follow right after their header with
        linha_pai_ordem set to the header's ordem (so the structure re-creates
        directly on import, keeping the children's measure formulas).
        """
        filhos_por_pai: dict[int, list] = {}
        for linha in linhas:
            if linha.linha_pai_id is not None:
                filhos_por_pai.setdefault(linha.linha_pai_id, []).append(linha)
        for filhos in filhos_por_pai.values():
            filhos.sort(
                key=lambda l: (l.ordem if l.ordem is not None else 0, l.id)
            )

        resultado: list[CriarDefModuloLinhaData] = []
        ordem = 0
        for pai in topo:
            ordem += 1
            ordem_pai = ordem
            resultado.append(
                self._linha_modulo_de_custeio(pai, ordem_pai, componente_repository)
            )
            if pai.tipo_linha == PECA_COMPOSTA:
                for filho in filhos_por_pai.get(pai.id, []):
                    ordem += 1
                    resultado.append(
                        self._linha_modulo_de_custeio(
                            filho,
                            ordem,
                            componente_repository,
                            linha_pai_ordem=ordem_pai,
                        )
                    )

        return resultado

    def _linha_modulo_de_custeio(
        self,
        linha,
        ordem: int,
        componente_repository,
        linha_pai_ordem: int | None = None,
    ) -> CriarDefModuloLinhaData:
        """Build one module line from a costing line (structure only).

        ``linha_pai_ordem`` is set for composite children; top-level lines pass
        None. The composite HEADER is an aggregator and keeps comp/larg/esp
        empty; every other line keeps its measure TEXT/formulas.
        """
        eh_divisao = linha.tipo_linha == DIVISAO_INDEPENDENTE
        eh_composta = linha.tipo_linha == PECA_COMPOSTA
        return CriarDefModuloLinhaData(
            ordem=ordem,
            tipo_linha=linha.tipo_linha,
            def_peca_id=linha.def_peca_id,
            def_peca_codigo=linha.def_peca_codigo,
            codigo=linha.codigo,
            descricao=None if eh_divisao else linha.descricao,
            descricao_livre=linha.descricao if eh_divisao else None,
            qt_mod=self._texto_quantidade(linha.qt_mod),
            qt_und=self._texto_quantidade(linha.qt_und),
            # comp/larg/esp keep the TEXT/formula (H, L/3, HM, LM...), never the
            # evaluated comp_real/larg_real/esp_real. The composite header is an
            # aggregator: no dimensions.
            comp=None if eh_composta else linha.comp,
            larg=None if eh_composta else linha.larg,
            esp=None if eh_composta else linha.esp,
            chave_valueset=linha.chave_valueset,
            codigo_orlas=linha.codigo_orlas,
            def_regra_quantidade_id=self._regra_quantidade_id(
                linha, componente_repository
            ),
            linha_pai_ordem=linha_pai_ordem,
            nivel=linha.nivel,
            ativo=True,
        )

    @staticmethod
    def _regra_quantidade_id(linha, componente_repository) -> int | None:
        """Resolve the quantity-rule id via the line's component origin, if any."""
        if linha.origem_id is None:
            return None

        componente = componente_repository.get_by_id(linha.origem_id)
        if componente is None:
            return None

        return componente.def_regra_quantidade_id

    @staticmethod
    def _texto_quantidade(valor) -> str | None:
        """Store qt_mod/qt_und as trimmed text (keeps formulas; numbers cleaned)."""
        if valor is None:
            return None
        if isinstance(valor, str):
            return valor.strip() or None
        try:
            return format(Decimal(str(valor)).normalize(), "f")
        except (InvalidOperation, ValueError):
            return str(valor)

    def editar_cabecalho(
        self, modulo_id: int, data: EditarDefModuloCabecalhoData
    ) -> DefModuloResumo:
        """Edit a module's header (name/description/scope/category/image)."""
        nome = self._normalize_required(data.nome, "nome")
        ambito = normalize_modulo_ambito(data.ambito)
        user_id = data.user_id if ambito == AMBITO_UTILIZADOR else None
        if ambito == AMBITO_UTILIZADOR and user_id is None:
            raise ValueError("user_id é obrigatório no âmbito UTILIZADOR")

        result = self.repository.update_cabecalho(
            id=modulo_id,
            nome=nome,
            descricao=self._normalize_optional(data.descricao),
            ambito=ambito,
            user_id=user_id,
            categoria=normalize_modulo_categoria(data.categoria),
            imagem_path=self._normalize_optional(data.imagem_path),
        )
        self.session.commit()

        return result

    def eliminar(self, modulo_id: int) -> bool:
        """Delete a module and its lines (cascade)."""
        deleted = self.repository.delete_modulo(modulo_id)
        if deleted:
            self.session.commit()

        return deleted

    # ----- helpers -----

    def _filtrar(
        self,
        modulos: list[DefModuloResumo],
        categoria: str | None,
        termo: str | None,
    ) -> list[DefModuloResumo]:
        """Filter modules by category and a V2-style '%'-separated search term."""
        if categoria:
            alvo = normalize_modulo_categoria(categoria)
            modulos = [
                modulo
                for modulo in modulos
                if normalize_modulo_categoria(modulo.categoria) == alvo
            ]

        return filtrar_por_termo(modulos, termo)

    def _normalize_codigo(self, codigo: str | None) -> str:
        normalized = (codigo or "").strip().upper()
        if not normalized:
            raise ValueError("O código do módulo é obrigatório.")

        return "_".join(normalized.split())

    @staticmethod
    def _normalize_required(value: str | None, field_name: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} é obrigatório.")

        return normalized

    @staticmethod
    def _normalize_optional(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None
