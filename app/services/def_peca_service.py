"""Service for reusable piece definition workflows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.orla_types import normalize_orla_type
from app.domain.peca_types import COMPOSTA, SIMPLES, normalize_peca_type
from app.domain.peca_natureza_types import (
    CONJUNTO,
    MATERIAL,
    SERVICO,
    normalize_peca_natureza,
    normalize_peca_orientacao,
)
from app.domain.valueset_types import normalize_valueset_key
from app.domain.medidas import validar_formula_dimensional
from app.repositories.def_peca_repository import DefPecaRepository, DefPecaResumo
from app.services.def_peca_componente_service import (
    CriarDefPecaComponenteData,
    DefPecaComponenteService,
)
from app.services.def_peca_operacao_service import (
    CriarDefPecaOperacaoData,
    DefPecaOperacaoService,
)


@dataclass(frozen=True)
class CriarDefPecaData:
    """Input data for creating a reusable piece definition."""

    codigo: str
    nome: str
    descricao: str | None = None
    grupo: str | None = None
    tipo_peca: str | None = None
    natureza: str | None = None
    orientacao: str | None = None
    funcao: str | None = None
    formula_comp: str | None = None
    formula_larg: str | None = None
    formula_esp: str | None = None
    orla_c1: int | str | None = None
    orla_c2: int | str | None = None
    orla_l1: int | str | None = None
    orla_l2: int | str | None = None
    chave_valueset_material: str | None = None
    permite_acabamento: bool = False
    chave_valueset_acabamento_sup: str | None = None
    chave_valueset_acabamento_inf: str | None = None
    sem_material: bool = False
    ativo: bool = True


@dataclass(frozen=True)
class EditarDefPecaData:
    """Input data for editing a reusable piece definition."""

    codigo: str
    nome: str
    descricao: str | None = None
    grupo: str | None = None
    tipo_peca: str | None = None
    natureza: str | None = None
    orientacao: str | None = None
    funcao: str | None = None
    formula_comp: str | None = None
    formula_larg: str | None = None
    formula_esp: str | None = None
    orla_c1: int | str | None = None
    orla_c2: int | str | None = None
    orla_l1: int | str | None = None
    orla_l2: int | str | None = None
    chave_valueset_material: str | None = None
    permite_acabamento: bool = False
    chave_valueset_acabamento_sup: str | None = None
    chave_valueset_acabamento_inf: str | None = None
    sem_material: bool = False
    ativo: bool = True


class DefPecaService:
    """Application service for DefPeca workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefPecaRepository(session)

    def listar_pecas(self) -> list[DefPecaResumo]:
        """List reusable piece definitions."""
        return self.repository.list_all()

    def listar_ativas_para_biblioteca(self) -> list[DefPecaResumo]:
        """List active piece definitions for the costing library."""
        return self.repository.list_ativas_para_biblioteca()

    def criar_peca(self, data: CriarDefPecaData) -> DefPecaResumo:
        """Create a reusable piece definition."""
        codigo = data.codigo.strip()
        nome = data.nome.strip()
        tipo_peca = normalize_peca_type(data.tipo_peca)
        natureza = self._normalize_natureza(
            data.natureza, tipo_peca=tipo_peca, sem_material=data.sem_material
        )
        if data.natureza is not None:
            tipo_peca = COMPOSTA if natureza == CONJUNTO else SIMPLES
        orientacao = normalize_peca_orientacao(data.orientacao)
        orla_c1 = normalize_orla_type(data.orla_c1)
        orla_c2 = normalize_orla_type(data.orla_c2)
        orla_l1 = normalize_orla_type(data.orla_l1)
        orla_l2 = normalize_orla_type(data.orla_l2)
        chave_valueset_material = self._normalize_optional_valueset_key(
            data.chave_valueset_material
        )
        chave_valueset_acabamento_sup = self._normalize_optional_valueset_key(
            data.chave_valueset_acabamento_sup
        )
        chave_valueset_acabamento_inf = self._normalize_optional_valueset_key(
            data.chave_valueset_acabamento_inf
        )
        # A service piece has no raw material: drop any material ValueSet key.
        sem_material = data.sem_material or natureza in (SERVICO, CONJUNTO)
        if sem_material:
            chave_valueset_material = None
        self._validate(codigo=codigo, nome=nome)
        formulas = self._normalizar_formulas(data)

        result = self.repository.create_def_peca(
            codigo=codigo,
            nome=nome,
            descricao=data.descricao,
            grupo=data.grupo,
            tipo_peca=tipo_peca,
            natureza=natureza,
            orientacao=orientacao,
            funcao=self._normalize_optional_text(data.funcao),
            **formulas,
            orla_c1=orla_c1,
            orla_c2=orla_c2,
            orla_l1=orla_l1,
            orla_l2=orla_l2,
            chave_valueset_material=chave_valueset_material,
            permite_acabamento=data.permite_acabamento,
            chave_valueset_acabamento_sup=chave_valueset_acabamento_sup,
            chave_valueset_acabamento_inf=chave_valueset_acabamento_inf,
            sem_material=sem_material,
            ativo=data.ativo,
        )
        self.session.commit()

        return result

    def editar_peca(self, id: int, data: EditarDefPecaData) -> DefPecaResumo:
        """Edit a reusable piece definition."""
        codigo = data.codigo.strip()
        nome = data.nome.strip()
        tipo_peca = normalize_peca_type(data.tipo_peca)
        natureza = self._normalize_natureza(
            data.natureza, tipo_peca=tipo_peca, sem_material=data.sem_material
        )
        if data.natureza is not None:
            tipo_peca = COMPOSTA if natureza == CONJUNTO else SIMPLES
        orientacao = normalize_peca_orientacao(data.orientacao)
        orla_c1 = normalize_orla_type(data.orla_c1)
        orla_c2 = normalize_orla_type(data.orla_c2)
        orla_l1 = normalize_orla_type(data.orla_l1)
        orla_l2 = normalize_orla_type(data.orla_l2)
        chave_valueset_material = self._normalize_optional_valueset_key(
            data.chave_valueset_material
        )
        chave_valueset_acabamento_sup = self._normalize_optional_valueset_key(
            data.chave_valueset_acabamento_sup
        )
        chave_valueset_acabamento_inf = self._normalize_optional_valueset_key(
            data.chave_valueset_acabamento_inf
        )
        # A service piece has no raw material: drop any material ValueSet key.
        sem_material = data.sem_material or natureza in (SERVICO, CONJUNTO)
        if sem_material:
            chave_valueset_material = None
        self._validate(codigo=codigo, nome=nome)
        formulas = self._normalizar_formulas(data)

        result = self.repository.update_def_peca(
            id=id,
            codigo=codigo,
            nome=nome,
            descricao=data.descricao,
            grupo=data.grupo,
            tipo_peca=tipo_peca,
            natureza=natureza,
            orientacao=orientacao,
            funcao=self._normalize_optional_text(data.funcao),
            **formulas,
            orla_c1=orla_c1,
            orla_c2=orla_c2,
            orla_l1=orla_l1,
            orla_l2=orla_l2,
            chave_valueset_material=chave_valueset_material,
            permite_acabamento=data.permite_acabamento,
            chave_valueset_acabamento_sup=chave_valueset_acabamento_sup,
            chave_valueset_acabamento_inf=chave_valueset_acabamento_inf,
            sem_material=sem_material,
            ativo=data.ativo,
        )
        self.session.commit()

        return result

    def duplicar_peca(
        self, id: int, novo_codigo: str, novo_nome: str | None = None
    ) -> DefPecaResumo:
        """Duplicate one reusable piece definition with operations and components."""
        original = self.repository.get_by_id(id)
        if original is None:
            raise ValueError("peca not found")

        return self.gravar_peca_como(
            id,
            CriarDefPecaData(
                codigo=novo_codigo,
                nome=novo_nome or f"{original.nome} (cópia)",
                descricao=original.descricao,
                grupo=original.grupo,
                tipo_peca=original.tipo_peca,
                natureza=original.natureza,
                orientacao=original.orientacao,
                funcao=original.funcao,
                formula_comp=original.formula_comp,
                formula_larg=original.formula_larg,
                formula_esp=original.formula_esp,
                orla_c1=original.orla_c1,
                orla_c2=original.orla_c2,
                orla_l1=original.orla_l1,
                orla_l2=original.orla_l2,
                chave_valueset_material=original.chave_valueset_material,
                permite_acabamento=original.permite_acabamento,
                chave_valueset_acabamento_sup=original.chave_valueset_acabamento_sup,
                chave_valueset_acabamento_inf=original.chave_valueset_acabamento_inf,
                sem_material=original.sem_material,
                ativo=True,
            ),
        )

    def gravar_peca_como(
        self, original_id: int, data: CriarDefPecaData
    ) -> DefPecaResumo:
        """Create a new piece from ``data`` and copy operations/components."""
        original = self.repository.get_by_id(original_id)
        if original is None:
            raise ValueError("peca not found")

        nova_peca = self.criar_peca(data)
        self._copiar_operacoes_e_componentes(original_id, nova_peca.id)

        return nova_peca

    def _copiar_operacoes_e_componentes(self, original_id: int, nova_peca_id: int) -> None:
        """Copy operation and component links from one piece to another."""
        operacao_service = DefPecaOperacaoService(self.session)
        operacoes = sorted(
            operacao_service.listar_operacoes_da_peca(original_id),
            key=lambda operacao: operacao.ordem,
        )
        for operacao in operacoes:
            operacao_service.adicionar_operacao_a_peca(
                CriarDefPecaOperacaoData(
                    def_peca_id=nova_peca_id,
                    def_operacao_id=operacao.def_operacao_id,
                    ordem=operacao.ordem,
                    regra_calculo=operacao.regra_calculo,
                    quantidade_base=operacao.quantidade_base,
                    rasgo_qt_comp=getattr(operacao, "rasgo_qt_comp", 0),
                    rasgo_qt_larg=getattr(operacao, "rasgo_qt_larg", 0),
                    tempo_setup_minutos=operacao.tempo_setup_minutos,
                    tempo_por_unidade_minutos=operacao.tempo_por_unidade_minutos,
                    unidade_tempo=operacao.unidade_tempo,
                    obrigatorio=operacao.obrigatorio,
                    ativo=operacao.ativo,
                    observacoes=operacao.observacoes,
                )
            )

        componente_service = DefPecaComponenteService(self.session)
        componentes = sorted(
            componente_service.listar_componentes(original_id),
            key=lambda componente: componente.ordem,
        )
        for componente in componentes:
            componente_service.criar_componente(
                CriarDefPecaComponenteData(
                    def_peca_pai_id=nova_peca_id,
                    tipo_componente=componente.tipo_componente,
                    def_peca_componente_id=componente.def_peca_componente_id,
                    referencia_componente=componente.referencia_componente,
                    descricao=componente.descricao,
                    formula_comp=componente.formula_comp,
                    formula_larg=componente.formula_larg,
                    formula_esp=componente.formula_esp,
                    quantidade=componente.quantidade,
                    regra_quantidade=componente.regra_quantidade,
                    def_regra_quantidade_id=componente.def_regra_quantidade_id,
                    zona_aplicacao=componente.zona_aplicacao,
                    dimensao_referencia=componente.dimensao_referencia,
                    numero_topos=componente.numero_topos,
                    modo_quantidade=componente.modo_quantidade,
                    obrigatorio=componente.obrigatorio,
                    ativo=componente.ativo,
                    observacoes=componente.observacoes,
                )
            )

    def desativar_peca(self, id: int) -> bool:
        """Deactivate a reusable piece definition."""
        deactivated = self.repository.deactivate_def_peca(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_peca(self, id: int) -> bool:
        """Activate a reusable piece definition."""
        activated = self.repository.activate_def_peca(id)
        if activated:
            self.session.commit()

        return activated

    def atualizar_formulas_dimensionais(
        self,
        id: int,
        *,
        formula_comp: str | None,
        formula_larg: str | None,
        formula_esp: str | None,
    ) -> DefPecaResumo:
        formulas = self._normalizar_formulas(
            CriarDefPecaData(
                codigo="FORMULAS",
                nome="Fórmulas",
                formula_comp=formula_comp,
                formula_larg=formula_larg,
                formula_esp=formula_esp,
            )
        )
        result = self.repository.update_formulas_dimensionais(id, **formulas)
        self.session.commit()
        return result

    def _validate(self, *, codigo: str, nome: str) -> None:
        if not codigo:
            raise ValueError("codigo is required")

        if not nome:
            raise ValueError("nome is required")

    @staticmethod
    def _normalizar_formulas(data) -> dict[str, str | None]:
        return {
            "formula_comp": validar_formula_dimensional(
                data.formula_comp, campo="Fórmula Comp"
            ),
            "formula_larg": validar_formula_dimensional(
                data.formula_larg, campo="Fórmula Larg"
            ),
            "formula_esp": validar_formula_dimensional(
                data.formula_esp, campo="Fórmula Esp"
            ),
        }

    def _normalize_optional_valueset_key(self, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None

        return normalize_valueset_key(normalized)

    def _normalize_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    def _normalize_natureza(
        self,
        value: str | None,
        *,
        tipo_peca: str,
        sem_material: bool,
    ) -> str:
        """Normalize the new field while preserving calls from the legacy API."""
        if value is not None:
            return normalize_peca_natureza(value)
        if tipo_peca == COMPOSTA:
            return CONJUNTO
        if sem_material:
            return SERVICO
        return MATERIAL
