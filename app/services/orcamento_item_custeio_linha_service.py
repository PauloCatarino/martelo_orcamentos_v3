"""Service for budget item cost line workflows.

This phase only stores cost lines. It does not generate lines automatically
from pieces, modules or operations, and does not recompute budget totals.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
import re
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.domain.custeio_linha_types import (
    DIVISAO_INDEPENDENTE,
    FERRAGEM,
    MANUAL,
    OPERACAO_MANUAL,
    PECA,
    PECA_COMPOSTA,
    SEPARADOR,
    normalize_custeio_linha_type,
)
from app.domain.medidas import (
    avaliar_medida,
    calcular_area_m2,
    calcular_perimetro_ml,
    construir_contexto_item,
    normalizar_numero,
    validar_expressao_medida,
)
from app.domain.acabamentos import (
    SEM_ACABAMENTO,
    calcular_areas_acabamento,
    tem_acabamento,
)
from app.domain.custo_producao import (
    MOTIVO_SEM_DADOS,
    MOTIVO_SEM_TARIFA,
    aplicar_fator_serie,
    calcular_custo_cnc,
    calcular_custo_corte,
    calcular_custo_orlagem_lados,
    calcular_custo_por_minutos,
    calcular_tempo_operacao,
    escolher_tarifa,
    somar_custo_producao,
)
from app.domain.producao_types import TIPO_PRODUCAO_SERIE, tipo_producao_efetivo
from app.domain.tempos_producao import (
    calcular_tempos_producao_ligacoes,
    classificar_operacao,
)
from app.domain.custos import (
    AVISO_UNIDADE_INVALIDA,
    calcular_custo_acabamento_face,
    calcular_custo_ferragem,
    calcular_custo_ml,
    calcular_custo_mp,
    calcular_custo_total_linha,
    unidade_custo_valida,
)
from app.domain.quantidades import LinhaQuantidade, calcular_quantidades
from app.domain.regras_quantidade_expr import avaliar_regra_quantidade
from app.domain.associado_types import (
    COMP as DIM_COMP,
    ESP as DIM_ESP,
    LARG as DIM_LARG,
    MEDIDA_TOPO,
    POR_TOPO,
    TOTAL,
    normalize_dimensao_referencia,
    normalize_modo_quantidade,
)
from app.domain.operacao_acao_types import (
    ADICIONAR,
    DESATIVAR,
    SUBSTITUIR,
    normalize_operacao_acao,
)
from app.domain.valueset_compat import TIPOS_FERRAGEM, opcoes_valueset_compativeis
from app.domain.materia_prima_snapshot import (
    coresp_orla_0_4,
    coresp_orla_1_0,
    familia_materia_prima,
    tipo_materia_prima,
)
from app.domain.numeros import normalize_percentagem_humana, validar_decimal
from app.domain.orlas import calcular_orlas_detalhe
from app.domain.peca_types import COMPOSTA
from app.domain.peca_natureza_types import CONJUNTO
from app.domain.valueset_types import normalize_valueset_key
from app.models import (
    OrcamentoItem,
    OrcamentoItemValuesetLinha,
    OrcamentoItemValuesetLinhaOperacao,
    OrcamentoVersao,
)
from app.repositories.def_maquina_escalao_area_repository import (
    DefMaquinaEscalaoAreaRepository,
)
from app.repositories.def_maquina_repository import DefMaquinaRepository
from app.repositories.def_materia_prima_repository import DefMateriaPrimaRepository
from app.repositories.def_modulo_repository import DefModuloRepository
from app.repositories.def_operacao_repository import DefOperacaoRepository
from app.repositories.def_peca_componente_repository import DefPecaComponenteRepository
from app.repositories.def_regra_quantidade_repository import DefRegraQuantidadeRepository
from app.repositories.def_valueset_chave_repository import DefValuesetChaveRepository
from app.repositories.def_peca_operacao_repository import DefPecaOperacaoRepository
from app.repositories.def_peca_repository import DefPecaRepository, DefPecaResumo
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
    OrcamentoItemCusteioLinhaResumo,
)
from app.repositories.orcamento_item_valueset_linha_repository import (
    OrcamentoItemValuesetLinhaRepository,
    OrcamentoItemValuesetLinhaResumo,
)


@dataclass(frozen=True)
class CriarLinhaCusteioData:
    """Input data for creating one cost line (manual or with a given type)."""

    orcamento_item_id: int | None
    descricao: str
    tipo_linha: str = MANUAL
    orcamento_item_modulo_id: int | None = None
    origem_tipo: str | None = None
    origem_id: int | None = None
    codigo: str | None = None
    materia_prima_id: int | None = None
    ref_materia_prima: str | None = None
    descricao_materia_prima: str | None = None
    unidade: str | None = None
    quantidade: Decimal = Decimal("1")
    comp: Decimal | None = None
    larg: Decimal | None = None
    esp: Decimal | None = None
    area_m2: Decimal | None = None
    perimetro_ml: Decimal | None = None
    ml_orla_fina: Decimal | None = None
    ml_orla_grossa: Decimal | None = None
    custo_unitario: Decimal | None = None
    custo_total: Decimal | None = None
    margem_percentagem: Decimal | None = None
    preco_unitario: Decimal | None = None
    preco_total: Decimal | None = None
    def_operacao_id: int | None = None
    def_maquina_id: int | None = None
    tempo_calculado: Decimal | None = None
    tempo_manual: Decimal | None = None
    override_manual: bool = False
    editado_localmente: bool = False
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarLinhaCusteioData:
    """Input data for editing one cost line."""

    orcamento_item_id: int | None
    descricao: str
    tipo_linha: str = MANUAL
    orcamento_item_modulo_id: int | None = None
    origem_tipo: str | None = None
    origem_id: int | None = None
    codigo: str | None = None
    materia_prima_id: int | None = None
    ref_materia_prima: str | None = None
    descricao_materia_prima: str | None = None
    unidade: str | None = None
    quantidade: Decimal = Decimal("1")
    comp: Decimal | None = None
    larg: Decimal | None = None
    esp: Decimal | None = None
    area_m2: Decimal | None = None
    perimetro_ml: Decimal | None = None
    ml_orla_fina: Decimal | None = None
    ml_orla_grossa: Decimal | None = None
    custo_unitario: Decimal | None = None
    custo_total: Decimal | None = None
    margem_percentagem: Decimal | None = None
    preco_unitario: Decimal | None = None
    preco_total: Decimal | None = None
    def_operacao_id: int | None = None
    def_maquina_id: int | None = None
    tempo_calculado: Decimal | None = None
    tempo_manual: Decimal | None = None
    override_manual: bool = False
    editado_localmente: bool = False
    ativo: bool = True
    observacoes: str | None = None


# Material snapshot fields of a cost line that can be picked, edited and cleared
# locally (the line keeps its key, def_peca, type, quantities, measures...).
MATERIAL_FIELDS = (
    "mat_default",
    "valueset_prioridade",
    "ref_le",
    "descricao_no_orcamento",
    "unidade",
    "preco_liquido",
    "desperdicio_percentagem",
    "tipo_materia_prima",
    "familia_materia_prima",
    "coresp_orla_0_4",
    "coresp_orla_1_0",
    "comp_mp",
    "larg_mp",
    "esp_mp",
)

# Local finishing fields edited via "Editar Dados do Acabamento" (kept separate
# from the main material snapshot). The code/option stays in acabamento_face_*.
ACABAMENTO_LOCAL_FIELDS = (
    "acabamento_face_sup",
    "acabamento_sup_ref_le",
    "acabamento_sup_descricao",
    "acabamento_sup_unidade",
    "acabamento_sup_preco_liquido",
    "acabamento_sup_desperdicio_percentagem",
    "acabamento_face_inf",
    "acabamento_inf_ref_le",
    "acabamento_inf_descricao",
    "acabamento_inf_unidade",
    "acabamento_inf_preco_liquido",
    "acabamento_inf_desperdicio_percentagem",
)


@dataclass(frozen=True)
class AdicionarPecasResult:
    """Summary of adding library pieces as cost lines."""

    criadas: int
    componentes: int
    ignoradas: int
    avisos: list[str]


@dataclass(frozen=True)
class AtualizacaoBibliotecaAnalise:
    """Read-only preview of refreshing one frozen library-piece block."""

    linha_raiz_id: int
    peca_codigo: str
    associados_atuais: int
    associados_catalogo: int
    linhas_editadas_localmente: int


@dataclass(frozen=True)
class AtualizacaoBibliotecaResult:
    """Summary of an explicit refresh from the current piece catalog."""

    linha_raiz_id: int
    peca_codigo: str
    associados_removidos: int
    associados_criados: int
    linhas_editadas_substituidas: int
    avisos: list[str]


@dataclass(frozen=True)
class InserirModuloResult:
    """Summary of importing a saved module into an item's costing (phase 8U.2)."""

    modulo_codigo: str
    criadas: int
    componentes: int
    avisos: list[str]


@dataclass(frozen=True)
class ClipboardLinhaCusteio:
    """One snapshot line in the costing clipboard (phase 8V.5).

    ``fields`` are the create_linha kwargs (structure + faithful material, no
    id/item/parent); ``indice_pai`` points to the parent line's index in the
    clipboard (for composite children), or None for a top-level line.
    """

    fields: dict
    indice_pai: int | None = None


@dataclass(frozen=True)
class ClipboardCusteio:
    """Session clipboard for copy/cut of cost lines (phase 8V.5)."""

    linhas: tuple
    modo: str               # "COPIAR" | "CORTAR"
    origem_item_id: int
    origem_ids: tuple       # source line ids (deleted on paste when CORTAR)


@dataclass(frozen=True)
class ColarCusteioResult:
    """Summary of a paste: lines inserted and (on cut) source lines removed."""

    inseridas: int
    cortadas: int


@dataclass(frozen=True)
class CustoMateriaPrimaResult:
    """Summary of one raw-material cost recompute over an item."""

    processadas: int
    calculadas: int
    ignoradas: int


@dataclass(frozen=True)
class CustoFerragemResult:
    """Summary of one hardware (UND) cost recompute over an item."""

    processadas: int
    calculadas: int
    ignoradas: int


@dataclass(frozen=True)
class CustoMlResult:
    """Summary of one linear-metre (ML) cost recompute over an item."""

    processadas: int
    calculadas: int
    ignoradas: int


# Cost-exclusion flag fields (True -> the matching cost is left out of the total).
EXCLUSAO_FIELDS = (
    "excluir_mp",
    "excluir_orla",
    "excluir_ferragem",
    "excluir_producao",
    "excluir_acabamento",
    "excluir_mo",
)


@dataclass(frozen=True)
class CustoTotalResult:
    """Summary of one total-cost recompute over an item."""

    processadas: int
    ignoradas: int


@dataclass(frozen=True)
class AreasAcabamentoResult:
    """Summary of one finishing-area recompute over an item."""

    processadas: int
    calculadas: int
    ignoradas: int


@dataclass(frozen=True)
class AcabamentoResult:
    """Summary of one automatic finishing-application over an item."""

    processadas: int
    aplicadas: int
    ignoradas: int


@dataclass(frozen=True)
class CustoAcabamentoResult:
    """Summary of one finishing-cost recompute over an item."""

    processadas: int
    calculadas: int
    ignoradas: int


@dataclass(frozen=True)
class OperacoesResult:
    """Summary of one production-operations mapping over an item."""

    processadas: int
    aplicadas: int
    ignoradas: int


@dataclass(frozen=True)
class TemposProducaoResult:
    """Summary of one basic production-times recompute over an item."""

    processadas: int
    calculadas: int
    ignoradas: int


@dataclass(frozen=True)
class RegrasQuantidadeResult:
    """Summary of applying component quantity rules over an item."""

    processadas: int
    calculadas: int
    ignoradas: int


@dataclass(frozen=True)
class RegraQuantidadeAplicavel:
    """Frozen or legacy quantity rule used by one costing line."""

    codigo: str
    expressao: str


@dataclass(frozen=True)
class CustoProducaoResult:
    """Summary of one production-cost (cut/edging) recompute over an item."""

    processadas: int
    calculadas: int
    ignoradas: int


@dataclass(frozen=True)
class ExclusaoLoteResult:
    """Summary of one bulk cost-exclusion flag change over an item."""

    linhas_atualizadas: int
    campo: str
    valor: bool


@dataclass(frozen=True)
class ErroEntradaCusteio:
    """One invalid user-controlled field in a costing line."""

    linha_id: int
    campo: str
    mensagem: str


class EntradasCusteioInvalidas(ValueError):
    """Raised when a costing pipeline would run over invalid line inputs."""

    def __init__(self, erros: list[ErroEntradaCusteio]) -> None:
        self.erros = tuple(erros)
        resumo = "; ".join(erro.mensagem for erro in self.erros[:3])
        if len(self.erros) > 3:
            resumo += f"; e mais {len(self.erros) - 3} erro(s)"
        super().__init__(f"Corrija as linhas de custeio antes de atualizar: {resumo}")


class OrcamentoItemCusteioLinhaService:
    """Application service for OrcamentoItemCusteioLinha workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrcamentoItemCusteioLinhaRepository(session)
        self.peca_repository = DefPecaRepository(session)
        self.componente_repository = DefPecaComponenteRepository(session)
        self.regra_quantidade_repository = DefRegraQuantidadeRepository(session)
        self.valueset_chave_repository = DefValuesetChaveRepository(session)
        self.item_valueset_repository = OrcamentoItemValuesetLinhaRepository(session)
        self.materia_prima_repository = DefMateriaPrimaRepository(session)
        self.peca_operacao_repository = DefPecaOperacaoRepository(session)
        self.operacao_repository = DefOperacaoRepository(session)
        self.maquina_repository = DefMaquinaRepository(session)
        self.escalao_area_repository = DefMaquinaEscalaoAreaRepository(session)
        self.def_modulo_repository = DefModuloRepository(session)

    def listar_linhas_do_item(
        self, orcamento_item_id: int
    ) -> list[OrcamentoItemCusteioLinhaResumo]:
        """List cost lines of one budget item."""
        return self.repository.list_by_orcamento_item(orcamento_item_id)

    def listar_linhas_ativas_do_item(
        self, orcamento_item_id: int
    ) -> list[OrcamentoItemCusteioLinhaResumo]:
        """List active cost lines of one budget item."""
        return self.repository.list_active_by_orcamento_item(orcamento_item_id)

    def listar_linhas_da_versao(
        self, orcamento_versao_id: int
    ) -> list[OrcamentoItemCusteioLinhaResumo]:
        """List cost lines of all items in one budget version."""
        return self.repository.list_by_orcamento_versao(orcamento_versao_id)

    def obter_por_id(self, id: int) -> OrcamentoItemCusteioLinhaResumo | None:
        """Get one cost line by id."""
        return self.repository.get_by_id(id)

    def analisar_atualizacao_da_biblioteca(
        self, linha_id: int
    ) -> AtualizacaoBibliotecaAnalise:
        """Preview an explicit catalog refresh without changing the quote."""
        raiz, peca, descendentes = self._contexto_atualizacao_biblioteca(linha_id)
        gerados = self._descendentes_gerados_biblioteca(descendentes)
        editados = sum(1 for linha in gerados if self._linha_tem_edicao_local(linha))
        return AtualizacaoBibliotecaAnalise(
            linha_raiz_id=raiz.id,
            peca_codigo=peca.codigo,
            associados_atuais=len(gerados),
            associados_catalogo=len(self._associados_ativos(peca.id)),
            linhas_editadas_localmente=editados,
        )

    def atualizar_peca_da_biblioteca(
        self, linha_id: int, *, confirmar_perda_edicoes: bool = False
    ) -> AtualizacaoBibliotecaResult:
        """Refresh a frozen piece snapshot and rebuild its generated children.

        Measures, quantities, free description, exclusions and local material/
        finishing overrides on the root line remain untouched. Generated child
        lines are replaced from the current catalog. If any such child carries
        a local override, the caller must explicitly confirm its replacement.
        """
        raiz, peca, descendentes = self._contexto_atualizacao_biblioteca(linha_id)
        gerados = self._descendentes_gerados_biblioteca(descendentes)
        editados = [linha for linha in gerados if self._linha_tem_edicao_local(linha)]
        if editados and not confirmar_perda_edicoes:
            raise ValueError(
                "Existem linhas associadas com edições locais; confirme a "
                "substituição para atualizar a partir da biblioteca."
            )

        linhas_antes = self.repository.list_active_by_orcamento_item(
            raiz.orcamento_item_id
        )
        ids_remover = {linha.id for linha in gerados}
        ordem_mantida = [
            linha.id for linha in linhas_antes if linha.id not in ids_remover
        ]

        self.repository.update_linha(
            id=raiz.id,
            **self._campos_atualizacao_raiz(raiz, peca),
        )
        if ids_remover:
            self.repository.delete_linhas(list(ids_remover))

        avisos: list[str] = []
        ids_criados: list[int] = []
        associados = self._associados_ativos(peca.id)
        origem = (
            "PECA_COMPOSTA"
            if self._eh_conjunto_virtual(peca)
            else "PECA_ASSOCIADA"
        )
        if associados:
            self._criar_linhas_componentes(
                raiz.orcamento_item_id,
                associados,
                raiz.id,
                avisos,
                origem=origem,
                pecas_ancestrais={peca.id},
                ids_criados=ids_criados,
            )
        elif self._eh_conjunto_virtual(peca):
            self._adicionar_aviso(
                avisos, f"Peça/conjunto {peca.codigo} sem associados configurados."
            )

        # Keep the refreshed children immediately below their root, without
        # disturbing the relative order of unrelated/manual costing lines.
        if raiz.id in ordem_mantida:
            posicao = ordem_mantida.index(raiz.id) + 1
            ordem_final = (
                ordem_mantida[:posicao]
                + ids_criados
                + ordem_mantida[posicao:]
            )
        else:
            ordem_final = ordem_mantida + ids_criados
        self.repository.reordenar_linhas(ordem_final)
        self.session.commit()

        return AtualizacaoBibliotecaResult(
            linha_raiz_id=raiz.id,
            peca_codigo=peca.codigo,
            associados_removidos=len(ids_remover),
            associados_criados=len(ids_criados),
            linhas_editadas_substituidas=len(editados),
            avisos=avisos,
        )

    def _contexto_atualizacao_biblioteca(self, linha_id: int):
        selecionada = self.repository.get_by_id(linha_id)
        if selecionada is None:
            raise ValueError("Linha de custeio não encontrada.")
        linhas = self.repository.list_active_by_orcamento_item(
            selecionada.orcamento_item_id
        )
        por_id = {linha.id: linha for linha in linhas}
        raiz = self._linha_topo_do_bloco(selecionada, por_id)
        if raiz.def_peca_id is None:
            raise ValueError(
                "A linha selecionada não está ligada à biblioteca de peças."
            )
        peca = self.peca_repository.get_by_id(raiz.def_peca_id)
        if peca is None:
            raise ValueError("A peça ligada a esta linha já não existe na biblioteca.")
        if not peca.ativo:
            raise ValueError("A peça ligada a esta linha está inativa na biblioteca.")
        descendentes = [
            linha
            for linha in linhas
            if linha.id != raiz.id
            and self._linha_topo_do_bloco(linha, por_id).id == raiz.id
        ]
        if raiz.origem_tipo == "MODULO" or any(
            linha.origem_tipo == "MODULO" for linha in descendentes
        ):
            raise ValueError(
                "Este bloco foi importado de um módulo. A atualização de módulos "
                "será tratada numa fase própria para preservar os seus desvios."
            )
        return raiz, peca, descendentes

    @staticmethod
    def _descendentes_gerados_biblioteca(descendentes: list) -> list:
        return [
            linha
            for linha in descendentes
            if linha.origem_tipo in {"PECA_ASSOCIADA", "PECA_COMPOSTA"}
        ]

    @staticmethod
    def _linha_tem_edicao_local(linha) -> bool:
        return bool(
            linha.editado_localmente
            or linha.material_editado_localmente
            or linha.acabamento_editado_localmente
        )

    def _campos_atualizacao_raiz(self, raiz, peca: DefPecaResumo) -> dict:
        """Build catalog fields while preserving quote-specific root inputs."""
        tipo = (
            PECA_COMPOSTA
            if self._eh_conjunto_virtual(peca)
            else self._tipo_linha_da_def_peca(peca)
        )
        fields = {
            "tipo_linha": tipo,
            "codigo": peca.codigo,
            "def_peca_id": peca.id,
            "def_peca_codigo": peca.codigo,
            "descricao": peca.nome or peca.descricao or peca.codigo,
            "codigo_orlas": (
                None
                if getattr(peca, "sem_material", False)
                else self._format_codigo_orlas(peca)
            ),
            "chave_valueset": (
                None
                if getattr(peca, "sem_material", False)
                else peca.chave_valueset_material
            ),
            "operacoes_snapshot_json": self._snapshot_operacoes_peca(peca.id),
            "sem_material": bool(getattr(peca, "sem_material", False)),
        }
        if tipo == PECA_COMPOSTA:
            fields["codigo_orlas"] = self._format_codigo_orlas(peca)
            fields["chave_valueset"] = peca.chave_valueset_material
            return fields

        if not raiz.material_editado_localmente:
            fresh, _aviso = self._build_peca_line_fields(
                raiz.orcamento_item_id, peca, tipo_linha=tipo
            )
            for campo in (
                "materia_prima_id",
                "ref_materia_prima",
                "descricao_materia_prima",
                *MATERIAL_FIELDS,
                "origem_material",
            ):
                fields[campo] = fresh.get(campo)
        return fields

    def eliminar_linhas(self, ids: list[int]) -> int:
        """Physically delete the given cost lines; returns how many were removed."""
        if not ids:
            return 0

        eliminadas = self.repository.delete_linhas(ids)
        self.session.commit()

        return eliminadas

    def aplicar_materia_prima_na_linha(
        self, linha_id: int, materia_prima_id: int
    ) -> OrcamentoItemCusteioLinhaResumo | None:
        """Copy a raw material snapshot into one cost line (local override).

        Keeps the line's key, def_peca, type, quantities, measures and
        hierarchy. Marks the line material as locally edited. Does not change
        the item ValueSet nor the raw material catalog.
        """
        linha = self.repository.get_by_id(linha_id)
        if linha is None:
            return None

        self._validar_linha_aceita_material(linha)

        materia = self.materia_prima_repository.get_by_id(materia_prima_id)
        if materia is None:
            raise ValueError("materia-prima nao encontrada")

        fields = {
            "mat_default": materia.ref_le,
            "valueset_prioridade": None,
            "ref_le": materia.ref_le,
            "descricao_no_orcamento": materia.descricao,
            "unidade": materia.unidade,
            "preco_liquido": materia.preco_liquido,
            "desperdicio_percentagem": normalize_percentagem_humana(
                materia.desperdicio_percentagem
            ),
            "tipo_materia_prima": tipo_materia_prima(materia),
            "familia_materia_prima": familia_materia_prima(materia),
            "coresp_orla_0_4": coresp_orla_0_4(materia),
            "coresp_orla_1_0": coresp_orla_1_0(materia),
            "comp_mp": materia.comprimento,
            "larg_mp": materia.largura,
            "esp_mp": materia.espessura,
            "materia_prima_id": materia.id,
            "ref_materia_prima": materia.ref_le,
            "descricao_materia_prima": materia.descricao,
            "origem_material": "MATERIA_PRIMA_LOCAL",
            "material_editado_localmente": True,
            "editado_localmente": True,
        }

        # Fill Esp from the material thickness when available.
        esp_texto = self._espessura_material_para_esp(materia.espessura)
        if esp_texto is not None:
            fields["esp"] = esp_texto

        result = self.repository.update_linha(id=linha_id, **fields)
        self.session.commit()

        return result

    def atualizar_material_local_linha(
        self, linha_id: int, dados: dict
    ) -> OrcamentoItemCusteioLinhaResumo | None:
        """Manually update the material fields of one cost line."""
        linha = self.repository.get_by_id(linha_id)
        if linha is None:
            return None

        self._validar_linha_aceita_material(linha)

        fields = {field: dados.get(field) for field in MATERIAL_FIELDS if field in dados}
        self._validar_dados_material_local(fields)
        fields["origem_material"] = "EDITADO_LOCALMENTE"
        fields["material_editado_localmente"] = True
        fields["editado_localmente"] = True

        result = self.repository.update_linha(id=linha_id, **fields)
        self.session.commit()

        return result

    def limpar_material_linha(
        self, linha_id: int
    ) -> OrcamentoItemCusteioLinhaResumo | None:
        """Clear the material fields of one cost line (keeps key/def_peca/etc.)."""
        linha = self.repository.get_by_id(linha_id)
        if linha is None:
            return None

        self._validar_linha_aceita_material(linha)

        fields = {field: None for field in MATERIAL_FIELDS}
        fields["materia_prima_id"] = None
        fields["ref_materia_prima"] = None
        fields["descricao_materia_prima"] = None
        fields["origem_material"] = "LIMPO_LOCALMENTE"
        fields["material_editado_localmente"] = True
        fields["editado_localmente"] = True

        result = self.repository.update_linha(id=linha_id, **fields)
        self.session.commit()

        return result

    def _validar_linha_aceita_material(self, linha) -> None:
        """Raise when the line type does not use material (division/composite)."""
        if linha.tipo_linha == DIVISAO_INDEPENDENTE:
            raise ValueError("Linhas de divisão não usam material.")
        if linha.tipo_linha == PECA_COMPOSTA:
            raise ValueError("A linha de peça composta não usa material.")

    def listar_linhas_custeio_por_chave(
        self, orcamento_item_id: int, chave_valueset: str | None
    ) -> list[OrcamentoItemCusteioLinhaResumo]:
        """List active cost lines of an item that use a given ValueSet key.

        Excludes division and composite-parent lines and lines without a key.
        """
        if not chave_valueset:
            return []

        chave = normalize_valueset_key(chave_valueset)
        linhas = self.repository.list_active_by_orcamento_item(orcamento_item_id)

        return [
            linha
            for linha in linhas
            if linha.chave_valueset
            and normalize_valueset_key(linha.chave_valueset) == chave
            and linha.tipo_linha not in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR)
        ]

    def aplicar_valueset_item_em_linhas_custeio(
        self, valueset_linha_id: int, custeio_linha_ids: list[int]
    ) -> int:
        """Copy one item ValueSet line snapshot into the selected cost lines.

        Only the material fields are updated (key, def_peca, type, quantities,
        measures and hierarchy are preserved). Returns how many lines changed.
        The item ValueSet and the raw material catalog are not modified.
        """
        vs_linha = self.item_valueset_repository.get_by_id(valueset_linha_id)
        if vs_linha is None:
            raise ValueError("linha valueset nao encontrada")

        fields = self._build_valueset_material_fields(vs_linha)

        atualizadas = 0
        for custeio_id in custeio_linha_ids:
            linha = self.repository.get_by_id(custeio_id)
            if linha is None:
                continue
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR):
                continue

            self.repository.update_linha(id=custeio_id, **fields)
            atualizadas += 1

        self.session.commit()

        return atualizadas

    def _build_valueset_material_fields(self, vs_linha) -> dict:
        """Build the material fields to copy from an item ValueSet line."""
        fields = {
            "mat_default": vs_linha.codigo_opcao or vs_linha.nome_opcao,
            "valueset_prioridade": vs_linha.prioridade,
            "ref_le": vs_linha.ref_le,
            "descricao_no_orcamento": vs_linha.descricao_no_orcamento,
            "unidade": vs_linha.unidade,
            "preco_liquido": vs_linha.preco_liquido,
            "desperdicio_percentagem": vs_linha.desperdicio_percentagem,
            "tipo_materia_prima": vs_linha.tipo_materia_prima,
            "familia_materia_prima": vs_linha.familia_materia_prima,
            "coresp_orla_0_4": vs_linha.coresp_orla_0_4,
            "coresp_orla_1_0": vs_linha.coresp_orla_1_0,
            "comp_mp": vs_linha.comp_mp,
            "larg_mp": vs_linha.larg_mp,
            "esp_mp": vs_linha.esp_mp,
            "materia_prima_id": vs_linha.materia_prima_id,
            "ref_materia_prima": vs_linha.ref_materia_prima,
            "descricao_materia_prima": vs_linha.descricao_materia_prima,
            "origem_material": "VALUESET_ITEM",
            "material_editado_localmente": False,
        }

        # Update Esp from the material thickness for the selected lines.
        esp_texto = self._espessura_material_para_esp(vs_linha.esp_mp)
        if esp_texto is not None:
            fields["esp"] = esp_texto

        return fields

    # --- 'Mat. default' dropdown: item-ValueSet options per line (8G.x) -------

    def opcoes_valueset_do_item(
        self, orcamento_item_id: int
    ) -> list[OrcamentoItemValuesetLinhaResumo]:
        """Active item ValueSet options (all keys), for the Mat. default dropdown."""
        return self.item_valueset_repository.list_active_by_orcamento_item(
            orcamento_item_id
        )

    def tipos_das_chaves(self) -> dict[str, str | None]:
        """Map each ValueSet key code (uppercased) to its type, for filtering."""
        return {
            (chave.codigo or "").strip().upper(): chave.tipo
            for chave in self.valueset_chave_repository.list_all()
        }

    def opcoes_valueset_para_linha(
        self, orcamento_item_id: int, linha
    ) -> list[OrcamentoItemValuesetLinhaResumo]:
        """Compatible item ValueSet options for one cost line (IMOS rule).

        MATERIAL lines see every MATERIAL option; FERRAGEM/SISTEMA_CORRER/
        ILUMINACAO/ACESSORIO see only their own key; ORLA/ACABAMENTO, divisions,
        composite parents, service pieces and keyless lines get none.
        """
        if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR):
            return []
        if self._linha_sem_material(linha):
            return []

        opcoes = self.opcoes_valueset_do_item(orcamento_item_id)
        return opcoes_valueset_compativeis(
            linha.chave_valueset, opcoes, self.tipos_das_chaves()
        )

    def aplicar_opcao_valueset_na_linha(
        self, custeio_linha_id: int, valueset_linha_id: int
    ) -> OrcamentoItemCusteioLinhaResumo | None:
        """Apply one item ValueSet option to a cost line (Mat. default dropdown).

        Copies the option's material snapshot AND its key into the line and marks
        it as a DELIBERATE local choice (material_editado_localmente +
        editado_localmente) so the item-ValueSet propagation (8G.4) does not
        revert it. Commits; the caller recomputes the dependent costs. Division
        and composite-parent lines reject the change. Does not touch the item
        ValueSet nor the raw-material catalog.
        """
        linha = self.repository.get_by_id(custeio_linha_id)
        if linha is None:
            return None

        self._validar_linha_aceita_material(linha)

        vs_linha = self.item_valueset_repository.get_by_id(valueset_linha_id)
        if vs_linha is None:
            raise ValueError("opção de ValueSet não encontrada")
        if vs_linha.orcamento_item_id != linha.orcamento_item_id:
            raise ValueError("a opção de ValueSet é de outro item")

        fields = self._build_valueset_material_fields(vs_linha)
        # Carry the option's key (cross-material is allowed for MATERIAL lines)
        # and mark the line as a deliberate choice so propagation respects it.
        fields["chave_valueset"] = vs_linha.chave
        fields["origem_material"] = "VALUESET_ITEM_ESCOLHA"
        fields["material_editado_localmente"] = True
        fields["editado_localmente"] = True

        result = self.repository.update_linha(id=custeio_linha_id, **fields)
        self.session.commit()

        return result

    def recalcular_medidas_do_item(self, orcamento_item_id: int) -> int:
        """Recompute quantities, real measures, area and perimeter for an item.

        Updates only the active cost lines of the item, using the item's
        measures as the variable context. Returns how many lines were updated.
        """
        item = self.session.get(OrcamentoItem, orcamento_item_id)
        if item is None:
            raise ValueError("item nao encontrado")

        contexto_global = construir_contexto_item(
            item.altura, item.largura, item.profundidade
        )
        contexto_local: dict = {}
        medidas_calculadas: dict[int, dict] = {}

        linhas = self.repository.list_active_by_orcamento_item(orcamento_item_id)
        quantidades = calcular_quantidades(
            [self._linha_quantidade(linha) for linha in linhas]
        )

        atualizadas = 0
        for linha in linhas:
            # A separator is purely visual: no measures, and it does NOT change
            # the active division context (HM/LM/PM) for the lines below it.
            if linha.tipo_linha == SEPARADOR:
                continue

            contexto = {**contexto_global, **contexto_local}
            if linha.linha_pai_id is not None:
                pai = medidas_calculadas.get(linha.linha_pai_id)
                if pai is not None:
                    contexto.update(self._contexto_dimensoes_pai(pai))
            fields = self._calcular_medidas_fields(
                linha, contexto, quantidades[linha.id].qt_total
            )

            medidas_calculadas[linha.id] = fields
            if linha.tipo_linha == DIVISAO_INDEPENDENTE:
                contexto_local = {
                    "HM": fields["comp_real"],
                    "LM": fields["larg_real"],
                    "PM": fields["esp_real"],
                }

            self.repository.update_linha(id=linha.id, **fields)
            atualizadas += 1

        self.session.commit()

        return atualizadas

    def recalcular_quantidades_do_item(self, orcamento_item_id: int) -> int:
        """Recompute qt_total of every active line, honouring divisions/composites.

        A DIVISAO_INDEPENDENTE qt_mod governs the block below it (until the next
        division) and a composite component multiplies by its main piece's
        qt_und (phase 8T.4). Pure quantity recompute (measures/costs untouched);
        commits. Returns how many lines had their qt_total changed.
        """
        linhas = self.repository.list_active_by_orcamento_item(orcamento_item_id)
        quantidades = calcular_quantidades(
            [self._linha_quantidade(linha) for linha in linhas]
        )

        atualizadas = 0
        for linha in linhas:
            novo = quantidades[linha.id].qt_total
            if linha.quantidade != novo:
                self.repository.update_linha(id=linha.id, quantidade=novo)
                atualizadas += 1

        self.session.commit()

        return atualizadas

    @staticmethod
    def _linha_quantidade(linha) -> LinhaQuantidade:
        """Project a cost line resumo into the quantity-computation view."""
        return LinhaQuantidade(
            id=linha.id,
            tipo_linha=linha.tipo_linha,
            qt_mod=linha.qt_mod,
            qt_und=linha.qt_und,
            linha_pai_id=linha.linha_pai_id,
        )

    def aplicar_regras_quantidade_do_item(
        self, orcamento_item_id: int
    ) -> RegrasQuantidadeResult:
        """Apply each component's quantity rule, setting qt_und (phase 8T.5.1).

        For every active component line (linha_pai set) linked to a
        DefPecaComponente with an ACTIVE quantity rule, qt_und is computed from
        the block's MAIN PIECE — the sibling PECA line (same linha_pai_id) that
        carries the real dimensions, NOT the dimensionless PECA_COMPOSTA header:
        COMP/LARG/ESP = main piece comp_real/larg_real/esp_real, QT_PAI = main
        piece qt_und. Manual edits (editado_localmente) are respected; a missing
        main piece / dimensions or an invalid rule leave qt_und untouched with an
        explanatory note. qt_total is refreshed by the cadeia recompute that
        follows. Components without a rule keep their manual qt_und. Commits.
        """
        linhas = self.repository.list_active_by_orcamento_item(orcamento_item_id)

        processadas = 0
        calculadas = 0
        ignoradas = 0
        for linha in linhas:
            regra = self._regra_quantidade_da_linha(linha)
            if regra is None:
                ignoradas += 1
                continue

            processadas += 1
            novo_qt_und, aviso = self._qt_und_pela_regra(linha, regra, linhas)

            fields: dict = {}
            if novo_qt_und is not None:
                fields["qt_und"] = novo_qt_und
                calculadas += 1
            nova_obs = self._mesclar_observacao(
                linha.observacoes, "Regra de quantidade", aviso
            )
            if nova_obs != linha.observacoes:
                fields["observacoes"] = nova_obs
            if fields:
                self.repository.update_linha(id=linha.id, **fields)

        self.session.commit()

        return RegrasQuantidadeResult(
            processadas=processadas, calculadas=calculadas, ignoradas=ignoradas
        )

    def _regra_quantidade_da_linha(self, linha):
        """Resolve the active quantity rule linked to a component line, or None."""
        expressao_snapshot = getattr(linha, "associado_regra_expressao", None)
        if expressao_snapshot:
            return RegraQuantidadeAplicavel(
                codigo=getattr(linha, "associado_regra_codigo", None) or "SNAPSHOT",
                expressao=expressao_snapshot,
            )

        if linha.linha_pai_id is None or linha.origem_id is None:
            return None

        componente = self.componente_repository.get_by_id(linha.origem_id)
        if componente is None or componente.def_regra_quantidade_id is None:
            return None

        regra = self.regra_quantidade_repository.get_by_id(
            componente.def_regra_quantidade_id
        )
        if regra is None or not regra.ativo:
            return None

        return regra

    def _qt_und_pela_regra(self, linha, regra, linhas):
        """Return (novo_qt_und, aviso) for one component line and its rule.

        novo_qt_und is None (qt_und kept) when the line was edited manually, the
        block's main piece / its dimensions are missing, or the rule could not
        be evaluated.
        """
        if linha.editado_localmente:
            return None, (
                f"Regra de quantidade {regra.codigo}: qt_und definido "
                "manualmente (regra ignorada)."
            )

        principal = self._peca_principal_do_bloco(linha, linhas)
        if principal is None:
            return None, (
                f"Regra de quantidade {regra.codigo} não calculada: dimensões "
                "da peça principal em falta."
            )

        numero_topos, modo_quantidade, dimensao_referencia = (
            self._configuracao_quantidade_associado(linha)
        )
        medida_topo = self._medida_topo_principal(
            principal, dimensao_referencia
        )
        if (
            "MEDIDA_TOPO" in (regra.expressao or "").upper()
            and normalizar_numero(medida_topo) is None
        ):
            return None, (
                f"Regra de quantidade {regra.codigo} não calculada: "
                "medida do topo em falta."
            )
        contexto = {
            "COMP": principal.comp_real,
            "LARG": principal.larg_real,
            "ESP": principal.esp_real,
            "QT_PAI": principal.qt_und,
            "MEDIDA_TOPO": medida_topo,
            "NUM_TOPOS": numero_topos,
        }
        quantidade, motivo = avaliar_regra_quantidade(regra.expressao, contexto)
        if motivo is not None:
            return None, (
                f"Regra de quantidade {regra.codigo} não calculada: {motivo}"
            )

        resultado = Decimal(quantidade)
        if modo_quantidade == POR_TOPO:
            if numero_topos not in (1, 2):
                return None, (
                    f"Regra de quantidade {regra.codigo} não calculada: "
                    "número de topos deve ser 1 ou 2."
                )
            resultado *= Decimal(numero_topos)

        return resultado, None

    def _configuracao_quantidade_associado(self, linha) -> tuple[int, str, str]:
        """Return the frozen association settings, with legacy fallback."""
        componente = None
        if linha.origem_id is not None:
            componente = self.componente_repository.get_by_id(linha.origem_id)

        numero_topos = getattr(linha, "associado_numero_topos", None)
        if numero_topos is None and componente is not None:
            numero_topos = getattr(componente, "numero_topos", 0)

        modo = getattr(linha, "associado_modo_quantidade", None)
        if modo is None and componente is not None:
            modo = getattr(componente, "modo_quantidade", TOTAL)

        dimensao = getattr(linha, "associado_dimensao_referencia", None)
        if dimensao is None and componente is not None:
            dimensao = getattr(componente, "dimensao_referencia", DIM_COMP)

        return (
            int(numero_topos or 0),
            normalize_modo_quantidade(modo),
            normalize_dimensao_referencia(dimensao),
        )

    @staticmethod
    def _medida_topo_principal(principal, dimensao_referencia: str):
        """Resolve MEDIDA_TOPO from the selected real parent dimension.

        ``MEDIDA_TOPO`` means the short end of the piece and therefore maps to
        LARG. The explicit COMP/LARG/ESP options allow overriding that mapping.
        """
        if dimensao_referencia == DIM_COMP:
            return principal.comp_real
        if dimensao_referencia == DIM_ESP:
            return principal.esp_real
        if dimensao_referencia in (DIM_LARG, MEDIDA_TOPO):
            return principal.larg_real
        return principal.larg_real

    def _peca_principal_do_bloco(self, linha, linhas):
        """Return the composite block's main piece for a component line, or None.

        The main piece is the sibling line (same linha_pai_id) of type PECA — not
        the dimensionless PECA_COMPOSTA header nor a FERRAGEM/operation — that
        already has comp_real and larg_real evaluated. When several qualify, the
        one with the lowest ordem (then id) wins, so the rule reads the real
        dimensions of the block's structural piece (e.g. the FUNDO for the PES).
        """
        por_id = {outra.id: outra for outra in linhas}
        pai = por_id.get(linha.linha_pai_id)
        if (
            pai is not None
            and pai.tipo_linha == PECA
            and pai.comp_real is not None
            and pai.larg_real is not None
        ):
            return pai

        candidatas = [
            outra
            for outra in linhas
            if outra.id != linha.id
            and outra.linha_pai_id is not None
            and outra.linha_pai_id == linha.linha_pai_id
            and outra.tipo_linha == PECA
            and outra.comp_real is not None
            and outra.larg_real is not None
        ]
        if not candidatas:
            return None

        return min(
            candidatas,
            key=lambda outra: (
                outra.ordem if outra.ordem is not None else 0,
                outra.id,
            ),
        )

    def recalcular_orlas_do_item(self, orcamento_item_id: int) -> int:
        """Recompute edge banding (ML and, when priced, cost) for an item.

        Skips division and composite-parent lines. Uses each line's codigo_orlas
        with comp_real/larg_real/qt_total. Edge prices are resolved from the raw
        material catalog by the orla references (coresp_orla_0_4 / coresp_orla_1_0);
        when a price is missing the ML is still stored and the cost stays empty.
        Does not change measures, ValueSet, materials nor piece definitions.
        """
        precos_cache: dict[str, tuple[Decimal | None, str | None]] = {}
        atualizadas = 0

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR):
                continue
            if self._linha_sem_material(linha):
                continue  # service piece: no orla

            preco_fina, unidade_fina = self._orla_preco_unidade(
                linha.coresp_orla_0_4, precos_cache
            )
            preco_grossa, unidade_grossa = self._orla_preco_unidade(
                linha.coresp_orla_1_0, precos_cache
            )

            # The orla covers the board edge, whose height is the piece thickness.
            # Use esp_real when available, otherwise fall back to the material
            # thickness (esp_mp) so panels without an esp formula still cost.
            esp_para_orla = linha.esp_real if linha.esp_real is not None else linha.esp_mp

            resultado = calcular_orlas_detalhe(
                linha.codigo_orlas,
                linha.comp_real,
                linha.larg_real,
                esp_para_orla,
                linha.quantidade,
                ref_fina=linha.coresp_orla_0_4,
                preco_fina=preco_fina,
                unidade_fina=unidade_fina,
                ref_grossa=linha.coresp_orla_1_0,
                preco_grossa=preco_grossa,
                unidade_grossa=unidade_grossa,
            )

            fields = {
                "ml_orla_fina": resultado.ml_orla_fina,
                "ml_orla_grossa": resultado.ml_orla_grossa,
                "custo_orla_fina": resultado.custo_orla_fina,
                "custo_orla_grossa": resultado.custo_orla_grossa,
                "custo_orlas": resultado.custo_orlas,
            }
            nova_obs = self._mesclar_observacao(
                linha.observacoes, "Custo de orla", resultado.aviso
            )
            if nova_obs != linha.observacoes:
                fields["observacoes"] = nova_obs

            self.repository.update_linha(id=linha.id, **fields)
            atualizadas += 1

        self.session.commit()

        return atualizadas

    def _orla_preco_unidade(
        self,
        ref_orla: str | None,
        cache: dict[str, tuple[Decimal | None, str | None]],
    ) -> tuple[Decimal | None, str | None]:
        """Resolve an orla (net price, unit) by its raw-material reference, cached."""
        if not ref_orla:
            return None, None

        if ref_orla in cache:
            return cache[ref_orla]

        materia = self.materia_prima_repository.get_by_ref_le(ref_orla)
        resultado = (
            (materia.preco_liquido, materia.unidade)
            if materia is not None
            else (None, None)
        )
        cache[ref_orla] = resultado
        return resultado

    def recalcular_custo_materia_prima_do_item(
        self, orcamento_item_id: int
    ) -> CustoMateriaPrimaResult:
        """Recompute the raw-material cost (custo_mp) of an item's lines.

        Costs M2 materials as ``area_m2 * qt_total * preco_liquido * (1 + desp)``;
        ML / UND / unknown units are left empty with an explanatory note. Skips
        division and composite-parent lines. Does not change measures, ValueSet
        nor the raw material catalog.
        """
        processadas = 0
        calculadas = 0
        ignoradas = 0

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR):
                ignoradas += 1
                continue
            if self._linha_sem_material(linha):
                ignoradas += 1  # service piece: no raw-material cost, no warning
                continue

            processadas += 1
            custo, aviso = calcular_custo_mp(
                linha.area_m2,
                linha.quantidade,
                linha.preco_liquido,
                linha.desperdicio_percentagem,
                linha.unidade,
            )

            fields: dict = {"custo_mp": custo}
            nova_obs = self._mesclar_observacao(linha.observacoes, "Custo MP", aviso)
            # Single unit-invalid diagnostic (units M2/UND/ML do not trigger it);
            # cleaned automatically once the line gets a valid unit.
            aviso_unidade = (
                None if unidade_custo_valida(linha.unidade) else AVISO_UNIDADE_INVALIDA
            )
            nova_obs = self._mesclar_observacao(
                nova_obs, "Custo não calculado: unidade", aviso_unidade
            )
            if nova_obs != linha.observacoes:
                fields["observacoes"] = nova_obs
            if custo is not None:
                calculadas += 1

            self.repository.update_linha(id=linha.id, **fields)

        self.session.commit()

        return CustoMateriaPrimaResult(
            processadas=processadas, calculadas=calculadas, ignoradas=ignoradas
        )

    def recalcular_custos_ferragens_do_item(
        self, orcamento_item_id: int
    ) -> CustoFerragemResult:
        """Recompute the hardware cost (custo_ferragem) of an item's UND lines.

        Costs UND lines as ``qt_total * preco_liquido * (1 + desp)`` (the waste %
        is a technical safety coefficient). M2 lines are left untouched (handled
        by Custo MP); ML / unknown units are left empty with an explanatory note.
        Skips division and composite-parent lines. Does not change measures,
        ValueSet, materials, Custo MP nor orla costs.
        """
        processadas = 0
        calculadas = 0
        ignoradas = 0

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR):
                ignoradas += 1
                continue
            if self._linha_sem_material(linha):
                ignoradas += 1  # service piece: no hardware cost, no warning
                continue

            processadas += 1
            custo, aviso = calcular_custo_ferragem(
                linha.quantidade,
                linha.preco_liquido,
                linha.desperdicio_percentagem,
                linha.unidade,
            )

            fields: dict = {"custo_ferragem": custo}
            nova_obs = self._mesclar_observacao(linha.observacoes, "Custo ferragem", aviso)
            if nova_obs != linha.observacoes:
                fields["observacoes"] = nova_obs
            if custo is not None:
                calculadas += 1

            self.repository.update_linha(id=linha.id, **fields)

        self.session.commit()

        return CustoFerragemResult(
            processadas=processadas, calculadas=calculadas, ignoradas=ignoradas
        )

    def recalcular_custos_ml_do_item(self, orcamento_item_id: int) -> CustoMlResult:
        """Recompute linear-metre consumption and cost for an item's ML lines.

        SPP ML und = manual ``consumo_ml_unitario`` else ``comp_real/1000`` else
        ``larg_real/1000``; SPP ML total = SPP ML und * qt_total; the cost is
        ``consumo_ml_total * preco_liquido * (1 + desp)`` and is stored in
        ``custo_ferragem`` (same column as UND). Non-ML lines, divisions and
        composite-parent lines are skipped. Does not change measures, ValueSet,
        materials, Custo MP nor orla costs.
        """
        processadas = 0
        calculadas = 0
        ignoradas = 0

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR):
                ignoradas += 1
                continue
            if self._linha_sem_material(linha):
                ignoradas += 1  # service piece: no ML material consumption
                continue

            eh_ml, consumo_unitario, consumo_total, custo, aviso = calcular_custo_ml(
                linha.unidade,
                linha.consumo_ml_unitario,
                linha.comp_real,
                linha.larg_real,
                linha.quantidade,
                linha.preco_liquido,
                linha.desperdicio_percentagem,
            )
            if not eh_ml:
                ignoradas += 1
                continue

            processadas += 1
            fields: dict = {
                "consumo_ml_unitario": consumo_unitario,
                "consumo_ml_total": consumo_total,
                "custo_ferragem": custo,
            }
            nova_obs = self._mesclar_observacao(linha.observacoes, "Custo ML", aviso)
            if nova_obs != linha.observacoes:
                fields["observacoes"] = nova_obs
            if custo is not None:
                calculadas += 1

            self.repository.update_linha(id=linha.id, **fields)

        self.session.commit()

        return CustoMlResult(
            processadas=processadas, calculadas=calculadas, ignoradas=ignoradas
        )

    def recalcular_custo_total_do_item(
        self, orcamento_item_id: int
    ) -> CustoTotalResult:
        """Recompute custo_total for an item's lines from the partial costs.

        Sums the existing partial costs (MP, orlas, ferragem; acabamento and
        produção count as 0 until implemented) honouring the per-line exclusion
        flags. Skips division and composite-parent lines. Does not change
        measures, ValueSet, materials nor the partial costs.
        """
        processadas = 0
        ignoradas = 0

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR):
                ignoradas += 1
                continue

            processadas += 1
            total = self._custo_total_da_linha(linha)
            self.repository.update_linha(id=linha.id, custo_total=total)

        self.session.commit()

        return CustoTotalResult(processadas=processadas, ignoradas=ignoradas)

    def recalcular_item_completo(self, orcamento_item_id: int) -> None:
        """Run the FULL costing pipeline for one item (the Atualizar sequence).

        Single source of truth for the per-item pipeline, reused by the costing
        page's Atualizar and by the version reports (phase 8W.1.1). Measures →
        quantity rules → quantities → finishing → areas → orlas → raw-material →
        hardware → ML → finishing cost → operations → production → times → total.
        """
        self.garantir_entradas_validas_do_item(orcamento_item_id)
        self.recalcular_medidas_do_item(orcamento_item_id)
        self.aplicar_regras_quantidade_do_item(orcamento_item_id)
        self.recalcular_quantidades_do_item(orcamento_item_id)
        self.aplicar_acabamentos_do_item(orcamento_item_id)
        self.recalcular_areas_acabamento_do_item(orcamento_item_id)
        self.recalcular_orlas_do_item(orcamento_item_id)
        self.recalcular_custo_materia_prima_do_item(orcamento_item_id)
        self.recalcular_custos_ferragens_do_item(orcamento_item_id)
        self.recalcular_custos_ml_do_item(orcamento_item_id)
        self.recalcular_custo_acabamento_do_item(orcamento_item_id)
        self.aplicar_operacoes_do_item(orcamento_item_id)
        self.recalcular_custos_producao_do_item(orcamento_item_id)
        self.recalcular_tempos_producao_do_item(orcamento_item_id)
        self.recalcular_custo_total_do_item(orcamento_item_id)

    def validar_entradas_do_item(
        self, orcamento_item_id: int
    ) -> list[ErroEntradaCusteio]:
        """Return all invalid editable quantities and measure expressions.

        Validation follows the display order so HM/LM/PM resolve from the most
        recent independent division, exactly like the measure recompute. It is
        read-only and can therefore be used while loading the page to highlight
        legacy or imported bad data before any financial calculation runs.
        """
        item = self.session.get(OrcamentoItem, orcamento_item_id)
        if item is None:
            raise ValueError("item nao encontrado")

        contexto_global = construir_contexto_item(
            item.altura, item.largura, item.profundidade
        )
        contexto_local: dict = {}
        medidas_calculadas: dict[int, dict] = {}
        erros: list[ErroEntradaCusteio] = []

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if linha.tipo_linha == SEPARADOR:
                continue

            self._validar_quantidade_da_linha(
                linha, "qt_mod", "QT mod", permitir_zero=False, erros=erros
            )
            self._validar_quantidade_da_linha(
                linha, "qt_und", "QT und", permitir_zero=True, erros=erros
            )

            if linha.tipo_linha == OPERACAO_MANUAL:
                continue

            contexto = {**contexto_global, **contexto_local}
            if linha.linha_pai_id is not None:
                pai = medidas_calculadas.get(linha.linha_pai_id)
                if pai is not None:
                    contexto.update(self._contexto_dimensoes_pai(pai))
            resultados: dict[str, Decimal | None] = {}
            for atributo, campo, rotulo in (
                ("comp", "Comp", "Comprimento"),
                ("larg", "Larg", "Largura"),
                ("esp", "Esp", "Espessura"),
            ):
                valor = getattr(linha, atributo)
                obrigatoria = linha.tipo_linha == DIVISAO_INDEPENDENTE
                try:
                    _texto, resultado = validar_expressao_medida(
                        valor,
                        contexto,
                        campo=rotulo,
                        permitir_vazio=not obrigatoria,
                        permitir_variaveis_sem_valor=True,
                    )
                    resultados[atributo] = resultado
                except ValueError as error:
                    resultados[atributo] = None
                    erros.append(
                        ErroEntradaCusteio(
                            linha_id=linha.id,
                            campo=campo,
                            mensagem=f"Linha {linha.id} · {campo}: {error}",
                        )
                    )

            if linha.tipo_linha == DIVISAO_INDEPENDENTE:
                contexto_local = {
                    "HM": resultados.get("comp"),
                    "LM": resultados.get("larg"),
                    "PM": resultados.get("esp"),
                }
            medidas_calculadas[linha.id] = {
                "comp_real": resultados.get("comp"),
                "larg_real": resultados.get("larg"),
                "esp_real": resultados.get("esp"),
            }

        return erros

    def garantir_entradas_validas_do_item(self, orcamento_item_id: int) -> None:
        """Raise before costing when any editable input is invalid."""
        erros = self.validar_entradas_do_item(orcamento_item_id)
        if erros:
            raise EntradasCusteioInvalidas(erros)

    def _validar_quantidade_da_linha(
        self,
        linha,
        atributo: str,
        campo: str,
        *,
        permitir_zero: bool,
        erros: list[ErroEntradaCusteio],
    ) -> None:
        try:
            self._validar_quantidade_editada(
                getattr(linha, atributo), campo, permitir_zero=permitir_zero
            )
        except ValueError as error:
            erros.append(
                ErroEntradaCusteio(
                    linha_id=linha.id,
                    campo=campo,
                    mensagem=f"Linha {linha.id} · {campo}: {error}",
                )
            )

    def aplicar_acabamentos_do_item(self, orcamento_item_id: int) -> AcabamentoResult:
        """Fill acabamento_face_sup/inf of PECA lines from def_peca + ValueSet.

        A piece declares which faces it finishes via ``permite_acabamento`` and
        ``chave_valueset_acabamento_sup`` / ``chave_valueset_acabamento_inf``; the
        finish code comes from the item ValueSet line of that key. Faces without a
        finish get SEM_ACABAMENTO. Only PECA lines with a def_peca are processed
        (ferragens, ML, divisions and composite parents are skipped). Does not
        compute areas/costs here (areas are recomputed in the next step) and does
        not touch material, orlas, ValueSet nor measures.
        """
        processadas = 0
        aplicadas = 0
        ignoradas = 0

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if not self._linha_recebe_acabamento(linha):
                ignoradas += 1
                continue
            if linha.acabamento_editado_localmente:
                # Local finishing edits prevail: do not overwrite them.
                ignoradas += 1
                continue

            peca = self.peca_repository.get_by_id(linha.def_peca_id)
            acab_sup, aviso_sup = self._resolver_acabamento_face(
                orcamento_item_id, peca, face_superior=True
            )
            acab_inf, aviso_inf = self._resolver_acabamento_face(
                orcamento_item_id, peca, face_superior=False
            )

            processadas += 1
            fields: dict = {
                "acabamento_face_sup": acab_sup,
                "acabamento_face_inf": acab_inf,
            }
            aviso = aviso_sup or aviso_inf
            nova_obs = self._mesclar_observacao(
                linha.observacoes, "Acabamento não aplicado", aviso
            )
            if nova_obs != linha.observacoes:
                fields["observacoes"] = nova_obs
            if acab_sup != SEM_ACABAMENTO or acab_inf != SEM_ACABAMENTO:
                aplicadas += 1

            self.repository.update_linha(id=linha.id, **fields)

        self.session.commit()

        return AcabamentoResult(
            processadas=processadas, aplicadas=aplicadas, ignoradas=ignoradas
        )

    def _linha_recebe_acabamento(self, linha) -> bool:
        """Return True for real piece lines that can receive a finish.

        Normal pieces resolve the finish from their def_peca + ValueSet; a line
        edited locally keeps its own finishing data even without a def_peca.
        """
        if linha.tipo_linha != PECA:
            return False
        if self._linha_sem_material(linha):
            return False  # service piece: only its operations cost
        return (
            linha.def_peca_id is not None
            or getattr(linha, "acabamento_editado_localmente", False)
        )

    def _resolver_acabamento_face(
        self, orcamento_item_id: int, peca, *, face_superior: bool
    ) -> tuple[str, str | None]:
        """Resolve one face finish (value, aviso) from the piece + item ValueSet."""
        if peca is None or not peca.permite_acabamento:
            return SEM_ACABAMENTO, None

        chave = (
            peca.chave_valueset_acabamento_sup
            if face_superior
            else peca.chave_valueset_acabamento_inf
        )
        if not chave:
            return SEM_ACABAMENTO, None

        linha_vs = self._resolver_valueset_por_chave(orcamento_item_id, chave)
        valor = None
        if linha_vs is not None:
            valor = linha_vs.codigo_opcao or linha_vs.nome_opcao or linha_vs.valor_texto

        if not valor:
            return SEM_ACABAMENTO, (
                f"Acabamento não aplicado: chave {chave} sem valor no ValueSet."
            )

        return valor, None

    def recalcular_areas_acabamento_do_item(
        self, orcamento_item_id: int
    ) -> AreasAcabamentoResult:
        """Recompute the finishing areas (sup/inf) of an item's lines.

        A face with a finish (different from empty / SEM_ACABAMENTO) gets
        ``area_m2 * qt_total``; without a finish it gets 0/empty. Skips division
        and composite-parent lines. Lines without a finish are left empty (so
        hardware/ML lines do not produce finishing areas). Does not compute costs
        nor change measures, ValueSet, materials or existing costs.
        """
        processadas = 0
        calculadas = 0
        ignoradas = 0

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR):
                ignoradas += 1
                continue
            if self._linha_sem_material(linha):
                ignoradas += 1  # service piece: no finishing areas
                continue

            area_sup, area_inf, aviso = calcular_areas_acabamento(
                linha.area_m2,
                linha.quantidade,
                linha.acabamento_face_sup,
                linha.acabamento_face_inf,
            )

            processadas += 1
            fields: dict = {
                "area_acabamento_sup": area_sup,
                "area_acabamento_inf": area_inf,
            }
            nova_obs = self._mesclar_observacao(
                linha.observacoes, "Área de acabamento", aviso
            )
            if nova_obs != linha.observacoes:
                fields["observacoes"] = nova_obs
            if area_sup is not None or area_inf is not None:
                calculadas += 1

            self.repository.update_linha(id=linha.id, **fields)

        self.session.commit()

        return AreasAcabamentoResult(
            processadas=processadas, calculadas=calculadas, ignoradas=ignoradas
        )

    def recalcular_custo_acabamento_do_item(
        self, orcamento_item_id: int
    ) -> CustoAcabamentoResult:
        """Recompute custo_acabamento (sup + inf) for an item's piece lines.

        Each finished face costs ``area_acab * preco_liquido * (1 + desp)``, with
        the price/waste taken from the item ValueSet line of the piece finishing
        key. SEM_ACABAMENTO faces cost 0. The cost is always stored (even when
        Excluir Acabamento is checked — that flag only affects custo_total).
        Skips ferragens, ML, divisions and composite parents. Does not change
        measures, materials, ValueSet, orlas nor Custo MP.
        """
        processadas = 0
        calculadas = 0
        ignoradas = 0

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if not self._linha_recebe_acabamento(linha):
                ignoradas += 1
                continue

            peca = self.peca_repository.get_by_id(linha.def_peca_id)
            custo_sup, aviso_sup = self._custo_acabamento_face(
                orcamento_item_id, peca, linha, face_superior=True
            )
            custo_inf, aviso_inf = self._custo_acabamento_face(
                orcamento_item_id, peca, linha, face_superior=False
            )
            custo_acabamento = self._somar_custos_acabamento(custo_sup, custo_inf)

            processadas += 1
            fields: dict = {"custo_acabamento": custo_acabamento}
            aviso = aviso_sup or aviso_inf
            nova_obs = self._mesclar_observacao(
                linha.observacoes, "Acabamento não calculado", aviso
            )
            if nova_obs != linha.observacoes:
                fields["observacoes"] = nova_obs
            if custo_acabamento is not None:
                calculadas += 1

            self.repository.update_linha(id=linha.id, **fields)

        self.session.commit()

        return CustoAcabamentoResult(
            processadas=processadas, calculadas=calculadas, ignoradas=ignoradas
        )

    def aplicar_operacoes_do_item(self, orcamento_item_id: int) -> OperacoesResult:
        """Map the piece-definition operations onto an item's PECA lines.

        Fills the textual ``operacoes`` (e.g. "CORTE; ORLAGEM; CNC") and the
        ``maquina`` involved, from DefPecaOperacao + DefOperacao. Only PECA lines
        with a def_peca are processed (ferragens, ML, divisions and composite
        parents are skipped). A line whose operations were already filled and is
        edited locally is preserved. No times/costs are computed; measures,
        materials, ValueSet, acabamentos and existing costs are not touched.
        """
        processadas = 0
        aplicadas = 0
        ignoradas = 0
        cache_variantes = self._cache_operacoes_variantes_do_item(orcamento_item_id)

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if not self._linha_recebe_operacoes(linha):
                ignoradas += 1
                continue
            if linha.operacoes and linha.editado_localmente:
                # Preserve a locally edited operations cell.
                ignoradas += 1
                continue

            operacoes_texto, maquina_texto = self._operacoes_da_linha(
                linha, cache_variantes
            )

            processadas += 1
            fields: dict = {
                "operacoes": operacoes_texto or None,
                "maquina": maquina_texto or None,
            }
            nova_obs = self._mesclar_observacao(
                linha.observacoes,
                "Operações da variante",
                self._aviso_operacoes_variante_sem_correspondencia(
                    linha, cache_variantes
                ),
            )
            if nova_obs != linha.observacoes:
                fields["observacoes"] = nova_obs
            if operacoes_texto:
                aplicadas += 1

            self.repository.update_linha(id=linha.id, **fields)

        self.session.commit()

        return OperacoesResult(
            processadas=processadas, aplicadas=aplicadas, ignoradas=ignoradas
        )

    def _linha_recebe_operacoes(self, linha) -> bool:
        """Return True for real piece lines (with a def_peca) that take operations.

        Service pieces (sem_material) are included: they still cost their
        operations even though they carry no raw material.
        """
        return linha.tipo_linha in (PECA, FERRAGEM) and linha.def_peca_id is not None

    def _linha_sem_material(self, linha) -> bool:
        """Return True for a service-piece line (no raw material / ValueSet)."""
        return bool(getattr(linha, "sem_material", False))

    def _cache_operacoes_variantes_do_item(self, orcamento_item_id: int) -> dict:
        """Load active item ValueSet lines and their active operation links once."""
        cache: dict[tuple[str, str], dict] = {}

        for linha_vs in self._linhas_valueset_item_com_operacoes(orcamento_item_id):
            chave = normalize_valueset_key(getattr(linha_vs, "chave", None))
            opcao = self._normalizar_opcao_valueset(
                getattr(linha_vs, "codigo_opcao", None)
                or getattr(linha_vs, "nome_opcao", None)
            )
            if opcao is None:
                continue

            pares: list[tuple] = []
            ligacoes = [
                ligacao
                for ligacao in getattr(linha_vs, "operacoes", []) or []
                if getattr(ligacao, "ativo", False)
            ]
            ligacoes.sort(
                key=lambda ligacao: (
                    getattr(ligacao, "ordem", None) or 0,
                    getattr(ligacao, "id", None) or 0,
                )
            )
            for ligacao in ligacoes:
                operacao = getattr(ligacao, "def_operacao", None)
                if operacao is None:
                    operacao = self.operacao_repository.get_by_id(
                        getattr(ligacao, "def_operacao_id", None)
                    )
                if operacao is not None:
                    pares.append((operacao, ligacao))

            cache[(chave, opcao)] = {"linha": linha_vs, "pares": pares}

        return cache

    def _linhas_valueset_item_com_operacoes(self, orcamento_item_id: int) -> list:
        """Return active item ValueSet lines with operation links eager-loaded."""
        try:
            statement = (
                select(OrcamentoItemValuesetLinha)
                .options(
                    joinedload(OrcamentoItemValuesetLinha.operacoes).joinedload(
                        OrcamentoItemValuesetLinhaOperacao.def_operacao
                    )
                )
                .where(
                    OrcamentoItemValuesetLinha.orcamento_item_id == orcamento_item_id,
                    OrcamentoItemValuesetLinha.ativo.is_(True),
                )
            )
            return self.session.execute(statement).unique().scalars().all()
        except AttributeError:
            # Unit-test fakes expose repository summaries directly.
            return self.item_valueset_repository.list_active_by_orcamento_item(
                orcamento_item_id
            )

    def _normalizar_opcao_valueset(self, valor: str | None) -> str | None:
        """Normalize a ValueSet option code/name for matching against mat_default."""
        if valor is None:
            return None

        texto = " ".join(str(valor).strip().upper().split())
        return texto or None

    def _chave_opcao_operacoes_variante(self, linha) -> tuple[str, str] | None:
        chave = getattr(linha, "chave_valueset", None)
        opcao = getattr(linha, "mat_default", None)
        if not chave or not opcao:
            return None

        opcao_normalizada = self._normalizar_opcao_valueset(opcao)
        if opcao_normalizada is None:
            return None

        return normalize_valueset_key(chave), opcao_normalizada

    def _entrada_operacoes_variante_da_linha(self, linha, cache_variantes: dict):
        chave_opcao = self._chave_opcao_operacoes_variante(linha)
        if chave_opcao is None:
            return None

        return cache_variantes.get(chave_opcao)

    def _pares_operacao_ligacao_da_linha(self, linha, cache_variantes: dict) -> list[tuple]:
        """Resolve the operation links to use for one costing line.

        The piece snapshot is the base. Variant operations then compose it with
        explicit ADICIONAR/SUBSTITUIR/DESATIVAR actions.
        """
        pares_snapshot = self._pares_operacoes_snapshot(linha)
        pares_base = (
            pares_snapshot
            if pares_snapshot is not None
            else self._pares_operacao_ligacao_da_peca(linha.def_peca_id)
        )

        entrada = self._entrada_operacoes_variante_da_linha(linha, cache_variantes)
        if entrada is None or not entrada["pares"]:
            return pares_base

        return self._compor_operacoes_variante(pares_base, entrada["pares"])

    def _compor_operacoes_variante(
        self, pares_base: list[tuple], pares_variante: list[tuple]
    ) -> list[tuple]:
        """Apply explicit variant actions without duplicate operation ids."""
        resultado = list(pares_base)

        for operacao, ligacao in pares_variante:
            acao = normalize_operacao_acao(getattr(ligacao, "acao", None))
            operacao_id = getattr(operacao, "id", None) or getattr(
                ligacao, "def_operacao_id", None
            )

            if acao == DESATIVAR:
                resultado = [
                    par
                    for par in resultado
                    if self._id_operacao_par(par) != operacao_id
                ]
                continue

            if acao == SUBSTITUIR:
                bucket_novo = classificar_operacao(
                    getattr(operacao, "tipo_operacao", None),
                    getattr(operacao, "codigo", None),
                )
                if bucket_novo is not None:
                    resultado = [
                        par
                        for par in resultado
                        if classificar_operacao(
                            getattr(par[0], "tipo_operacao", None),
                            getattr(par[0], "codigo", None),
                        )
                        != bucket_novo
                    ]
                else:
                    resultado = [
                        par
                        for par in resultado
                        if self._id_operacao_par(par) != operacao_id
                    ]

            # ADICIONAR and SUBSTITUIR both add the configured variant operation;
            # replacing the same id first prevents accidental double charging.
            resultado = [
                par
                for par in resultado
                if self._id_operacao_par(par) != operacao_id
            ]
            resultado.append((operacao, ligacao))

        return resultado

    @staticmethod
    def _id_operacao_par(par: tuple):
        operacao, ligacao = par
        return getattr(operacao, "id", None) or getattr(
            ligacao, "def_operacao_id", None
        )

    @staticmethod
    def _pares_operacoes_snapshot(linha) -> list[tuple] | None:
        """Rebuild frozen operation/link objects; None means a legacy line."""
        texto = getattr(linha, "operacoes_snapshot_json", None)
        if texto is None:
            return None
        try:
            dados = json.loads(texto)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        if not isinstance(dados, list):
            return []

        pares: list[tuple] = []
        for item in dados:
            if not isinstance(item, dict):
                continue
            operacao = item.get("operacao") or {}
            ligacao = item.get("ligacao") or {}
            pares.append((SimpleNamespace(**operacao), SimpleNamespace(**ligacao)))
        return pares

    def _aviso_operacoes_variante_sem_correspondencia(
        self, linha, cache_variantes: dict
    ) -> str | None:
        chave_opcao = self._chave_opcao_operacoes_variante(linha)
        if chave_opcao is None:
            return None
        if chave_opcao in cache_variantes:
            return None

        return (
            f"Operações da variante: opção {linha.mat_default} sem correspondência "
            "no ValueSet do item — usadas as operações base congeladas da linha."
        )

    def _operacoes_da_linha(self, linha, cache_variantes: dict) -> tuple[str, str]:
        """Build operation and machine text for the operations resolved for a line."""
        return self._texto_operacoes_de_pares(
            self._pares_operacao_ligacao_da_linha(linha, cache_variantes)
        )

    def _operacoes_da_peca(self, def_peca_id: int) -> tuple[str, str]:
        """Build the "; "-joined operation codes and the distinct machines of a piece."""
        return self._texto_operacoes_de_pares(
            self._pares_operacao_ligacao_da_peca(def_peca_id)
        )

    def _texto_operacoes_de_pares(self, pares: list[tuple]) -> tuple[str, str]:
        """Build the "; "-joined operation codes and distinct machines from pairs."""
        nomes: list[str] = []
        maquinas: list[str] = []

        for operacao, _ligacao in pares:
            nome = operacao.codigo or operacao.nome
            if nome:
                nomes.append(nome)

            if operacao.maquina_id is not None:
                maquina = self.maquina_repository.get_by_id(operacao.maquina_id)
                if maquina is not None:
                    nome_maquina = maquina.codigo or maquina.nome
                    if nome_maquina and nome_maquina not in maquinas:
                        maquinas.append(nome_maquina)

        return "; ".join(nomes), "; ".join(maquinas)

    def _operacoes_def_da_peca(self, def_peca_id: int) -> list:
        """Resolve the active operations of a piece into DefOperacao read models."""
        return [operacao for operacao, _ligacao in self._pares_operacao_ligacao_da_peca(def_peca_id)]

    def _operacoes_def_da_linha(self, linha, cache_variantes: dict) -> list:
        """Resolve active operation definitions selected for a costing line."""
        return [
            operacao
            for operacao, _ligacao in self._pares_operacao_ligacao_da_linha(
                linha, cache_variantes
            )
        ]

    def recalcular_tempos_producao_do_item(
        self, orcamento_item_id: int
    ) -> TemposProducaoResult:
        """Recompute the informative production times (minutes) of PECA lines.

        Reads the time configuration from the piece↔operation links
        (DefPecaOperacao: tempo_setup_minutos / tempo_por_unidade_minutos /
        unidade_tempo / quantidade_base / regra_calculo) — the SAME source the
        production cost uses — and fills tempo_corte / tempo_orlagem / tempo_cnc
        / tempo_montagem / tempo_manual / tempo_setup. These times are purely
        informative (production planning): they DO NOT change any cost. The
        assembly/manual minutes match exactly the ones behind
        custo_montagem_manual (shared helper). Only PECA lines with a def_peca
        are processed; OPERACAO_MANUAL keeps its own tempo_manual and ferragens,
        ML, divisions and composite parents get no time, with no warning. A line
        whose times are already filled and is edited locally is preserved.
        """
        processadas = 0
        calculadas = 0
        ignoradas = 0
        cache_variantes = self._cache_operacoes_variantes_do_item(orcamento_item_id)

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if not self._linha_recebe_operacoes(linha):
                ignoradas += 1
                continue
            if self._tempos_preenchidos(linha) and linha.editado_localmente:
                ignoradas += 1
                continue

            ml_orla_total = (linha.ml_orla_fina or Decimal("0")) + (
                linha.ml_orla_grossa or Decimal("0")
            )
            tempos = calcular_tempos_producao_ligacoes(
                self._pares_operacao_ligacao_da_linha(linha, cache_variantes),
                linha.area_m2,
                linha.quantidade,
                ml_orla_total,
            )

            processadas += 1
            fields: dict = {
                "tempo_corte": tempos["corte"] or None,
                "tempo_orlagem": tempos["orlagem"] or None,
                "tempo_cnc": tempos["cnc"] or None,
                "tempo_montagem": tempos["montagem"] or None,
                "tempo_manual": tempos["manual"] or None,
                "tempo_setup": tempos["setup"] or None,
            }
            # Times are informative and never gate the cost: never write the old
            # "tempos em falta" warning, and clear any still stored.
            nova_obs = self._mesclar_observacao(
                linha.observacoes, "Tempos de produção", None
            )
            nova_obs = self._mesclar_observacao(
                nova_obs,
                "Operações da variante",
                self._aviso_operacoes_variante_sem_correspondencia(
                    linha, cache_variantes
                ),
            )
            if nova_obs != linha.observacoes:
                fields["observacoes"] = nova_obs
            if any(fields[campo] for campo in (
                "tempo_corte",
                "tempo_orlagem",
                "tempo_cnc",
                "tempo_montagem",
                "tempo_manual",
                "tempo_setup",
            )):
                calculadas += 1

            self.repository.update_linha(id=linha.id, **fields)

        self.session.commit()

        return TemposProducaoResult(
            processadas=processadas, calculadas=calculadas, ignoradas=ignoradas
        )

    def _pares_operacao_ligacao_da_peca(self, def_peca_id: int) -> list[tuple]:
        """Resolve a piece's active operations into (operacao, ligacao) pairs."""
        pares: list[tuple] = []
        for ligacao in self.peca_operacao_repository.list_active_by_def_peca(
            def_peca_id
        ):
            operacao = self.operacao_repository.get_by_id(ligacao.def_operacao_id)
            if operacao is not None:
                pares.append((operacao, ligacao))
        return pares

    def recalcular_custos_producao_do_item(
        self, orcamento_item_id: int
    ) -> CustoProducaoResult:
        """Recompute custo_corte / custo_orlagem / custo_producao of an item.

        For each PECA line with a def_peca: if the piece has a CORTE operation,
        cost the cutting from that machine's €/ML (perimeter × qt) plus setup ×
        qt; if it has an ORLAGEM operation, cost the edging by each edged side
        tariff (short/long side by real measure) plus setup × qt. The tariffs follow the item's
        effective production type (STD, or SERIE with per-field fallback to STD
        when the SERIE value is not defined); custo_producao is the sum (empty
        partials count as 0; NULL when none computed) multiplied by the line's
        optional fator_serie. Skips ferragens, ML, UND, divisions and composite
        parents. Does not change materials/orlas/acabamentos/measures;
        custo_total is recomputed by its own step.
        """
        processadas = 0
        calculadas = 0
        ignoradas = 0

        tipo_efetivo = self._tipo_producao_efetivo_do_item(orcamento_item_id)
        usar_serie = tipo_efetivo == TIPO_PRODUCAO_SERIE
        cache_variantes = self._cache_operacoes_variantes_do_item(orcamento_item_id)

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if linha.tipo_linha == OPERACAO_MANUAL:
                processadas += 1
                if self._recalcular_operacao_manual(linha, tipo_efetivo):
                    calculadas += 1
                continue

            if not self._linha_recebe_operacoes(linha):
                ignoradas += 1
                continue

            if linha.tipo_linha == FERRAGEM:
                custos_ferragem, tempos_ferragem, aviso_ferragem = (
                    self._custos_producao_ferragem(linha, usar_serie, cache_variantes)
                )
                custo_producao = aplicar_fator_serie(
                    somar_custo_producao(
                        custos_ferragem["corte"],
                        custos_ferragem["orlagem"],
                        custos_ferragem["cnc"],
                        custos_ferragem["montagem_manual"],
                    ),
                    linha.fator_serie,
                )

                processadas += 1
                fields: dict = {
                    "custo_corte": custos_ferragem["corte"],
                    "custo_orlagem": custos_ferragem["orlagem"],
                    "custo_cnc": custos_ferragem["cnc"],
                    "custo_montagem_manual": custos_ferragem["montagem_manual"],
                    "custo_producao": custo_producao,
                    "tipo_producao": tipo_efetivo,
                    "tempo_corte": tempos_ferragem["corte"] or None,
                    "tempo_orlagem": tempos_ferragem["orlagem"] or None,
                    "tempo_cnc": tempos_ferragem["cnc"] or None,
                    "tempo_montagem": tempos_ferragem["montagem"] or None,
                    "tempo_manual": tempos_ferragem["manual"] or None,
                    "tempo_setup": tempos_ferragem["setup"] or None,
                }
                nova_obs = self._mesclar_observacao(
                    linha.observacoes, "Custo de produção", None
                )
                nova_obs = self._mesclar_observacao(nova_obs, "Custo CNC", None)
                nova_obs = self._mesclar_observacao(
                    nova_obs, "Custo de montagem/manual", aviso_ferragem
                )
                nova_obs = self._mesclar_observacao(
                    nova_obs, "Tempos de produção", None
                )
                nova_obs = self._mesclar_observacao(
                    nova_obs,
                    "Operações da variante",
                    self._aviso_operacoes_variante_sem_correspondencia(
                        linha, cache_variantes
                    ),
                )
                if nova_obs != linha.observacoes:
                    fields["observacoes"] = nova_obs
                if custo_producao is not None:
                    calculadas += 1

                self.repository.update_linha(id=linha.id, **fields)
                continue

            operacoes = self._operacoes_def_da_linha(linha, cache_variantes)
            op_corte = self._operacao_por_bucket(operacoes, "corte")
            op_orlagem = self._operacao_por_bucket(operacoes, "orlagem")
            op_cnc = self._operacao_por_bucket(operacoes, "cnc")

            custo_corte = None
            custo_orlagem = None
            custo_cnc = None
            avisos_ml: list[str] = []
            aviso_cnc = None

            if op_corte is not None:
                maquina = self._maquina_de_operacao(op_corte)
                preco, setup = self._tarifas_ml(maquina, usar_serie)
                custo_corte, motivo = calcular_custo_corte(
                    linha.perimetro_ml, linha.quantidade, preco, setup
                )
                aviso = self._aviso_producao(motivo, maquina, "corte")
                if aviso:
                    avisos_ml.append(aviso)

            if op_orlagem is not None:
                maquina = self._maquina_de_operacao(op_orlagem)
                preco_curto, preco_longo, limite, setup = self._tarifas_lado(
                    maquina, usar_serie
                )
                custo_orlagem, motivo = calcular_custo_orlagem_lados(
                    linha.codigo_orlas,
                    linha.comp_real,
                    linha.larg_real,
                    linha.quantidade,
                    preco_curto,
                    preco_longo,
                    limite,
                    setup,
                )
                aviso = self._aviso_producao(motivo, maquina, "orlagem")
                if aviso:
                    avisos_ml.append(aviso)

            if op_cnc is not None:
                maquina = self._maquina_de_operacao(op_cnc)
                escaloes = (
                    self.escalao_area_repository.list_active_by_maquina(maquina.id)
                    if maquina is not None
                    else []
                )
                custo_cnc, motivo = calcular_custo_cnc(
                    linha.area_m2, linha.quantidade, escaloes, usar_serie=usar_serie
                )
                aviso_cnc = self._aviso_producao(motivo, maquina, "cnc")

            custo_mm, tempos_mm, aviso_mm = self._custos_montagem_manual_da_peca(
                linha, usar_serie, cache_variantes
            )

            custo_producao = aplicar_fator_serie(
                somar_custo_producao(custo_corte, custo_orlagem, custo_cnc, custo_mm),
                linha.fator_serie,
            )

            processadas += 1
            fields: dict = {
                "custo_corte": custo_corte,
                "custo_orlagem": custo_orlagem,
                "custo_cnc": custo_cnc,
                "custo_montagem_manual": custo_mm,
                "custo_producao": custo_producao,
                "tipo_producao": tipo_efetivo,
                "tempo_montagem": tempos_mm["montagem"] or None,
                "tempo_manual": tempos_mm["manual"] or None,
                "tempo_setup": tempos_mm["setup"] or None,
            }
            nova_obs = self._mesclar_observacao(
                linha.observacoes,
                "Custo de produção",
                avisos_ml[0] if avisos_ml else None,
            )
            nova_obs = self._mesclar_observacao(nova_obs, "Custo CNC", aviso_cnc)
            nova_obs = self._mesclar_observacao(
                nova_obs, "Custo de montagem/manual", aviso_mm
            )
            # Production cost no longer depends on the computed times: clear the old
            # "Tempos de produção" warning from any earlier pass (phase 8S.2).
            nova_obs = self._mesclar_observacao(nova_obs, "Tempos de produção", None)
            nova_obs = self._mesclar_observacao(
                nova_obs,
                "Operações da variante",
                self._aviso_operacoes_variante_sem_correspondencia(
                    linha, cache_variantes
                ),
            )
            if nova_obs != linha.observacoes:
                fields["observacoes"] = nova_obs
            if custo_producao is not None:
                calculadas += 1

            self.repository.update_linha(id=linha.id, **fields)

        self.session.commit()

        return CustoProducaoResult(
            processadas=processadas, calculadas=calculadas, ignoradas=ignoradas
        )

    def _operacao_por_bucket(self, operacoes, bucket: str):
        """Return the first operation classified into ``bucket`` (corte/orlagem)."""
        for operacao in operacoes:
            classificacao = classificar_operacao(
                getattr(operacao, "tipo_operacao", None),
                getattr(operacao, "codigo", None),
            )
            if classificacao == bucket:
                return operacao
        return None

    def _maquina_de_operacao(self, operacao):
        """Resolve the machine of an operation (or None)."""
        maquina_id = getattr(operacao, "maquina_id", None)
        if maquina_id is None:
            return None
        return self.maquina_repository.get_by_id(maquina_id)

    def _tipo_producao_efetivo_do_item(self, orcamento_item_id: int) -> str:
        """Resolve the effective production type (item exception or versão default)."""
        item = self.session.get(OrcamentoItem, orcamento_item_id)
        if item is None:
            return tipo_producao_efetivo(None, None)

        versao = self.session.get(OrcamentoVersao, item.orcamento_versao_id)
        return tipo_producao_efetivo(
            getattr(item, "tipo_producao", None),
            getattr(versao, "tipo_producao_default", None) if versao else None,
        )

    def _tarifas_ml(self, maquina, usar_serie: bool):
        """Return the machine's (preco_ml, custo_setup_peca) for the wanted type.

        SERIE values fall back per field to the STD value when not defined.
        """
        if maquina is None:
            return None, None
        preco, _ = escolher_tarifa(
            getattr(maquina, "preco_ml_std", None),
            getattr(maquina, "preco_ml_serie", None),
            usar_serie,
        )
        setup, _ = escolher_tarifa(
            getattr(maquina, "custo_setup_peca_std", None),
            getattr(maquina, "custo_setup_peca_serie", None),
            usar_serie,
        )
        return preco, setup

    def _tarifas_lado(self, maquina, usar_serie: bool):
        """Return ORLAGEM (preco_curto, preco_longo, limite, setup).

        SERIE values fall back per field to the STD value when not defined.
        """
        if maquina is None:
            return None, None, None, None
        preco_curto, _ = escolher_tarifa(
            getattr(maquina, "preco_lado_curto_std", None),
            getattr(maquina, "preco_lado_curto_serie", None),
            usar_serie,
        )
        preco_longo, _ = escolher_tarifa(
            getattr(maquina, "preco_lado_longo_std", None),
            getattr(maquina, "preco_lado_longo_serie", None),
            usar_serie,
        )
        setup, _ = escolher_tarifa(
            getattr(maquina, "custo_setup_peca_std", None),
            getattr(maquina, "custo_setup_peca_serie", None),
            usar_serie,
        )
        return preco_curto, preco_longo, getattr(maquina, "limite_lado_mm", None), setup

    def _custo_hora_maquina(self, maquina, usar_serie: bool):
        """Return the machine's hourly rate for the wanted type (SERIE→STD fallback)."""
        if maquina is None:
            return None
        custo_hora, _ = escolher_tarifa(
            getattr(maquina, "custo_hora", None),
            getattr(maquina, "custo_hora_serie", None),
            usar_serie,
        )
        return custo_hora

    def _aviso_producao(self, motivo, maquina, etapa: str) -> str | None:
        """Build the production observation for a missing tariff/data, or None."""
        if motivo is None:
            return None

        nome = getattr(maquina, "codigo", None) or "—"

        if etapa == "cnc":
            # Missing area: the dimensions warning already exists -> do not duplicate.
            if motivo == MOTIVO_SEM_DADOS:
                return None
            return (
                f"Custo CNC não calculado: escalões de área em falta na "
                f"máquina {nome}."
            )

        if motivo == MOTIVO_SEM_TARIFA:
            if etapa == "orlagem":
                return (
                    "Custo de produção não calculado: tarifa por lado orlado em "
                    f"falta na máquina {nome}."
                )
            return (
                f"Custo de produção não calculado: tarifa €/ML em falta na "
                f"máquina {nome}."
            )
        return f"Custo de produção não calculado: dados de {etapa} em falta."

    def _aviso_montagem_manual(self, maquina) -> str:
        """Build the assembly/manual observation for a missing hourly rate."""
        nome = getattr(maquina, "codigo", None) or "—"
        return (
            f"Custo de montagem/manual não calculado: custo/hora em falta na "
            f"máquina {nome}."
        )

    def _custos_producao_ferragem(
        self, linha, usar_serie: bool = False, cache_variantes: dict | None = None
    ):
        """Return time-based production costs/times for a FERRAGEM line."""
        custos = {
            "corte": None,
            "orlagem": None,
            "cnc": None,
            "montagem_manual": None,
        }
        tempos = {
            "corte": Decimal("0"),
            "orlagem": Decimal("0"),
            "cnc": Decimal("0"),
            "montagem": Decimal("0"),
            "manual": Decimal("0"),
            "setup": Decimal("0"),
        }
        aviso = None
        cache_variantes = cache_variantes or {}

        for operacao, ligacao in self._pares_operacao_ligacao_da_linha(
            linha, cache_variantes
        ):
            bucket = classificar_operacao(
                getattr(operacao, "tipo_operacao", None),
                getattr(operacao, "codigo", None),
            )
            if bucket is None:
                continue

            setup_min, variavel_min = calcular_tempo_operacao(
                getattr(ligacao, "unidade_tempo", None),
                getattr(ligacao, "quantidade_base", None),
                getattr(ligacao, "tempo_setup_minutos", None),
                getattr(ligacao, "tempo_por_unidade_minutos", None),
                linha.area_m2,
                linha.quantidade,
            )
            if setup_min is None and variavel_min is None:
                continue

            setup_min = setup_min or Decimal("0")
            variavel_min = variavel_min or Decimal("0")
            tempos["setup"] += setup_min
            if bucket == "setup":
                tempos["setup"] += variavel_min
            elif bucket in tempos:
                tempos[bucket] += variavel_min

            maquina = self._maquina_de_operacao(operacao)
            custo_hora = self._custo_hora_maquina(maquina, usar_serie)
            custo_op = calcular_custo_por_minutos(setup_min + variavel_min, custo_hora)
            if custo_op is None:
                if aviso is None:
                    aviso = self._aviso_montagem_manual(maquina)
                continue

            custo_bucket = (
                bucket if bucket in ("corte", "orlagem", "cnc") else "montagem_manual"
            )
            custos[custo_bucket] = (custos[custo_bucket] or Decimal("0")) + custo_op

        return custos, tempos, aviso

    def _custos_montagem_manual_da_peca(
        self, linha, usar_serie: bool = False, cache_variantes: dict | None = None
    ):
        """Return (custo_montagem_manual, tempos_por_bucket, aviso) for a PECA line.

        Sums the assembly/manual/packing operations selected for the line, reading
        the time configuration from the operation link (tempo_setup_minutos /
        tempo_por_unidade_minutos / unidade_tempo / quantidade_base). The hourly
        rate follows ``usar_serie`` (custo_hora_serie with fallback to custo_hora).
        Operations without times are ignored silently; an operation with times but
        whose machine has no hourly rate produces a single warning.
        """
        tempos = {"montagem": Decimal("0"), "manual": Decimal("0"), "setup": Decimal("0")}
        custo = None
        aviso = None
        cache_variantes = cache_variantes or {}

        for operacao, ligacao in self._pares_operacao_ligacao_da_linha(
            linha, cache_variantes
        ):
            bucket = classificar_operacao(
                getattr(operacao, "tipo_operacao", None),
                getattr(operacao, "codigo", None),
            )
            if bucket not in ("montagem", "manual"):
                continue

            setup_min, variavel_min = calcular_tempo_operacao(
                getattr(ligacao, "unidade_tempo", None),
                getattr(ligacao, "quantidade_base", None),
                getattr(ligacao, "tempo_setup_minutos", None),
                getattr(ligacao, "tempo_por_unidade_minutos", None),
                linha.area_m2,
                linha.quantidade,
            )
            if setup_min is None and variavel_min is None:
                continue  # no times configured -> ignore without a warning

            setup_min = setup_min or Decimal("0")
            variavel_min = variavel_min or Decimal("0")
            tempos["setup"] += setup_min
            tempos[bucket] += variavel_min

            maquina = self._maquina_de_operacao(operacao)
            custo_hora = self._custo_hora_maquina(maquina, usar_serie)
            custo_op = calcular_custo_por_minutos(setup_min + variavel_min, custo_hora)
            if custo_op is None:
                if aviso is None:
                    aviso = self._aviso_montagem_manual(maquina)
                continue
            custo = (custo or Decimal("0")) + custo_op

        return custo, tempos, aviso

    def _minutos_unitarios_da_linha(self, linha) -> Decimal | None:
        """Minutes per unit of a manual line (derived from the total for old lines)."""
        minutos = normalizar_numero(getattr(linha, "minutos_unitarios", None))
        if minutos is not None:
            return minutos
        total = normalizar_numero(linha.tempo_manual)
        if total is None:
            return None
        qt = normalizar_numero(linha.quantidade) or Decimal("1")
        return total / qt

    def _recalcular_operacao_manual(self, linha, tipo_efetivo: str | None = None) -> bool:
        """Recompute an OPERACAO_MANUAL line's time and cost from its machine tariff.

        Keeps the user's description; the total minutes follow
        ``minutos_unitarios × QT total`` (so a new quantity is reflected) and the
        cost is ``(minutes / 60) × custo_hora`` of the item's effective production
        type (SERIE falls back to STD when not defined), with the line's optional
        fator_serie applied to custo_producao. Legacy lines without
        minutos_unitarios derive it from the stored total. Returns True when a
        cost was computed.
        """
        if tipo_efetivo is None:
            tipo_efetivo = self._tipo_producao_efetivo_do_item(linha.orcamento_item_id)
        usar_serie = tipo_efetivo == TIPO_PRODUCAO_SERIE

        maquina = (
            self.maquina_repository.get_by_id(linha.def_maquina_id)
            if linha.def_maquina_id is not None
            else None
        )
        custo_hora = self._custo_hora_maquina(maquina, usar_serie)

        minutos_unitarios = self._minutos_unitarios_da_linha(linha)
        qt = normalizar_numero(linha.quantidade) or Decimal("1")
        tempo_total = (
            minutos_unitarios * qt if minutos_unitarios is not None else linha.tempo_manual
        )
        custo_mm = calcular_custo_por_minutos(tempo_total, custo_hora)
        custo_producao = aplicar_fator_serie(
            somar_custo_producao(custo_mm), linha.fator_serie
        )

        fields: dict = {
            "minutos_unitarios": minutos_unitarios,
            "tempo_manual": tempo_total,
            "maquina": getattr(maquina, "codigo", None) if maquina else None,
            "custo_montagem_manual": custo_mm,
            "custo_producao": custo_producao,
            "tipo_producao": tipo_efetivo,
        }
        aviso = (
            self._aviso_montagem_manual(maquina)
            if custo_mm is None and tempo_total is not None
            else None
        )
        nova_obs = self._mesclar_observacao(
            linha.observacoes, "Custo de montagem/manual", aviso
        )
        if nova_obs != linha.observacoes:
            fields["observacoes"] = nova_obs

        self.repository.update_linha(id=linha.id, **fields)
        return custo_producao is not None

    def _tempos_preenchidos(self, linha) -> bool:
        """Return True when the line already has any production time set."""
        return any(
            getattr(linha, campo, None)
            for campo in (
                "tempo_corte",
                "tempo_orlagem",
                "tempo_cnc",
                "tempo_montagem",
                "tempo_manual",
                "tempo_setup",
            )
        )

    def _custo_acabamento_face(
        self, orcamento_item_id: int, peca, linha, *, face_superior: bool
    ) -> tuple[Decimal | None, str | None]:
        """Cost (value, aviso) of one finishing face from its area + price.

        Local finishing edits (acabamento_editado_localmente) take priority over
        the item ValueSet; an empty local price falls back to the ValueSet.
        """
        acab = linha.acabamento_face_sup if face_superior else linha.acabamento_face_inf
        if not tem_acabamento(acab):
            return Decimal("0"), None

        area = (
            linha.area_acabamento_sup if face_superior else linha.area_acabamento_inf
        )
        if normalizar_numero(area) is None:
            # The missing-area cause ("dimensões Comp/Larg em falta") is already
            # diagnosed by recalcular_areas_acabamento_do_item; do not duplicate it.
            return None, None

        preco, desp = self._preco_desp_acabamento_face(
            orcamento_item_id, peca, linha, face_superior=face_superior
        )
        if normalizar_numero(preco) is None:
            return None, "Acabamento não calculado: preço do acabamento não encontrado."

        return calcular_custo_acabamento_face(area, preco, desp), None

    def _preco_desp_acabamento_face(
        self, orcamento_item_id: int, peca, linha, *, face_superior: bool
    ) -> tuple[object, object]:
        """Return (preco_liquido, desperdicio) for a face: local first, else ValueSet."""
        if getattr(linha, "acabamento_editado_localmente", False):
            if face_superior:
                preco_local = linha.acabamento_sup_preco_liquido
                desp_local = linha.acabamento_sup_desperdicio_percentagem
            else:
                preco_local = linha.acabamento_inf_preco_liquido
                desp_local = linha.acabamento_inf_desperdicio_percentagem
            if normalizar_numero(preco_local) is not None:
                return preco_local, desp_local

        chave = None
        if peca is not None:
            chave = (
                peca.chave_valueset_acabamento_sup
                if face_superior
                else peca.chave_valueset_acabamento_inf
            )
        linha_vs = self._resolver_valueset_por_chave(orcamento_item_id, chave)
        if linha_vs is None:
            return None, None

        return linha_vs.preco_liquido, linha_vs.desperdicio_percentagem

    def _somar_custos_acabamento(self, *custos) -> Decimal | None:
        """Total of the face finishing costs, or None when any face is unresolved."""
        if any(custo is None for custo in custos):
            return None

        return sum(custos, Decimal("0"))

    def linha_suporta_acabamento(self, linha) -> bool:
        """Return True when the line can carry a finish (real piece lines only)."""
        return linha.tipo_linha == PECA

    def atualizar_acabamento_local_linha(
        self, linha_id: int, dados: dict
    ) -> OrcamentoItemCusteioLinhaResumo | None:
        """Save local finishing data of one line, then recompute areas/cost/total.

        Marks ``acabamento_editado_localmente`` (so the automatic finishing
        application no longer overwrites the line; local price/waste then prevail
        in Custo acabamento) AND the visual ``editado_localmente`` flag, so the
        "Editado localmente" column reads Yes — just like editing the material.
        """
        linha = self.repository.get_by_id(linha_id)
        if linha is None:
            return None

        if not self.linha_suporta_acabamento(linha):
            raise ValueError("Esta linha não suporta acabamento.")

        fields = {
            field: dados.get(field)
            for field in ACABAMENTO_LOCAL_FIELDS
            if field in dados
        }
        self._validar_dados_acabamento_local(fields)
        fields["acabamento_editado_localmente"] = True
        fields["editado_localmente"] = True

        self.repository.update_linha(id=linha_id, **fields)
        self.session.commit()

        item_id = linha.orcamento_item_id
        self.recalcular_areas_acabamento_do_item(item_id)
        self.recalcular_custo_acabamento_do_item(item_id)
        self.recalcular_custo_total_do_item(item_id)

        return self.repository.get_by_id(linha_id)

    @staticmethod
    def _validar_dados_acabamento_local(fields: dict) -> None:
        """Validate and normalize local finishing prices and waste rates."""
        for face in ("sup", "inf"):
            for sufixo, rotulo in (
                ("preco_liquido", "Preço líquido"),
                ("desperdicio_percentagem", "Desperdício %"),
            ):
                campo = f"acabamento_{face}_{sufixo}"
                if campo in fields:
                    fields[campo] = validar_decimal(
                        fields[campo],
                        f"{rotulo} ({face})",
                        minimo=Decimal("0"),
                    )

    def atualizar_exclusao_linha(
        self, linha_id: int, campo: str, excluir: bool
    ) -> OrcamentoItemCusteioLinhaResumo | None:
        """Set one cost-exclusion flag of a line and recompute its custo_total."""
        if campo not in EXCLUSAO_FIELDS:
            raise ValueError("campo de exclusao invalido")

        linha = self.repository.get_by_id(linha_id)
        if linha is None:
            return None

        fields: dict = {campo: bool(excluir)}
        if linha.tipo_linha not in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR):
            fields["custo_total"] = self._custo_total_da_linha(
                linha, **{campo: bool(excluir)}
            )

        self.repository.update_linha(id=linha_id, **fields)
        self.session.commit()

        return self.repository.get_by_id(linha_id)

    def atualizar_fator_serie_linha(
        self, linha_id: int, fator_serie
    ) -> OrcamentoItemCusteioLinhaResumo | None:
        """Set a line's fator_serie and recompute custo_producao/custo_total.

        Empty value clears the factor (1.00). The factor multiplies ONLY the
        line's custo_producao (rebuilt from the stored production partials); the
        partial costs themselves are not touched.
        """
        linha = self.repository.get_by_id(linha_id)
        if linha is None:
            return None
        if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR):
            raise ValueError("linha não suporta fator série")

        fator = normalizar_numero(fator_serie)
        if fator_serie not in (None, "") and fator is None:
            raise ValueError("fator série inválido")
        if fator is not None and fator <= 0:
            raise ValueError("fator série deve ser maior que 0")

        custo_producao = aplicar_fator_serie(
            somar_custo_producao(
                linha.custo_corte,
                linha.custo_orlagem,
                linha.custo_cnc,
                linha.custo_montagem_manual,
            ),
            fator,
        )
        linha_atualizada = self.repository.update_linha(
            id=linha_id, fator_serie=fator, custo_producao=custo_producao
        )
        self.repository.update_linha(
            id=linha_id, custo_total=self._custo_total_da_linha(linha_atualizada)
        )
        self.session.commit()

        return self.repository.get_by_id(linha_id)

    def atualizar_exclusao_em_lote(
        self, orcamento_item_id: int, campo: str, valor: bool
    ) -> ExclusaoLoteResult:
        """Set one exclusion flag on all active lines, then recompute totals."""
        if campo not in EXCLUSAO_FIELDS:
            raise ValueError("campo de exclusao invalido")

        atualizadas = self.repository.atualizar_flag_exclusao(
            orcamento_item_id, campo, bool(valor)
        )
        # The bulk update bypasses the identity map; drop stale instances so the
        # total recompute reads the new flag values.
        self.session.expire_all()
        self.recalcular_custo_total_do_item(orcamento_item_id)

        return ExclusaoLoteResult(
            linhas_atualizadas=atualizadas, campo=campo, valor=bool(valor)
        )

    def _custo_total_da_linha(self, linha, **exclusao_overrides) -> Decimal:
        """Build the total cost of one line, honouring (overridable) exclusions."""

        def excluido(campo: str) -> bool:
            if campo in exclusao_overrides:
                return bool(exclusao_overrides[campo])
            return bool(getattr(linha, campo, False))

        return calcular_custo_total_linha(
            custo_mp=linha.custo_mp,
            custo_orlas=linha.custo_orlas,
            custo_ferragem=linha.custo_ferragem,
            custo_acabamento=getattr(linha, "custo_acabamento", None),
            custo_producao=getattr(linha, "custo_producao", None),
            excluir_mp=excluido("excluir_mp"),
            excluir_orla=excluido("excluir_orla"),
            excluir_ferragem=excluido("excluir_ferragem"),
            excluir_acabamento=excluido("excluir_acabamento"),
            excluir_producao=excluido("excluir_producao"),
        )

    def _mesclar_observacao(
        self, observacoes_atuais: str | None, prefixo: str, nova_mensagem: str | None
    ) -> str | None:
        """Keep existing production notes, replacing only the ``prefixo`` line.

        Lines starting with ``prefixo`` (e.g. a previous orla or material-cost
        warning) are removed; ``nova_mensagem`` (if any) is appended. Notes from
        other phases are preserved. Returns the merged text or None.
        """
        linhas = [
            linha
            for linha in (observacoes_atuais or "").splitlines()
            if linha.strip() and not linha.startswith(prefixo)
        ]
        if nova_mensagem:
            linhas.append(nova_mensagem)

        return "\n".join(linhas) or None

    def recalcular_medidas_linha(
        self, linha_id: int
    ) -> OrcamentoItemCusteioLinhaResumo | None:
        """Recompute quantities and measures of one cost line."""
        linha = self.repository.get_by_id(linha_id)
        if linha is None:
            return None

        item = self.session.get(OrcamentoItem, linha.orcamento_item_id)
        contexto = self._contexto_medidas_ate_linha(linha, item)

        linhas = self.repository.list_active_by_orcamento_item(
            linha.orcamento_item_id
        )
        quantidades = calcular_quantidades(
            [self._linha_quantidade(atual) for atual in linhas]
        )
        resultado_quantidade = quantidades.get(linha.id)
        qt_total = (
            resultado_quantidade.qt_total
            if resultado_quantidade is not None
            else (linha.quantidade if linha.quantidade is not None else Decimal("1"))
        )
        fields = self._calcular_medidas_fields(linha, contexto, qt_total)
        result = self.repository.update_linha(id=linha_id, **fields)
        self.session.commit()

        return result

    def atualizar_medidas_linha(
        self,
        linha_id: int,
        qt_mod=None,
        qt_und=None,
        comp=None,
        larg=None,
        esp=None,
        descricao=None,
        descricao_livre=None,
        propagar_item: bool = True,
    ) -> OrcamentoItemCusteioLinhaResumo | None:
        """Save edited quantities/measures of one cost line, then recompute.

        Comp/Larg/Esp keep the raw text/expression written by the user, while
        comp_real/larg_real/esp_real (and area/perimeter) hold the evaluated
        result. With ``propagar_item`` (default) the whole item is recomputed so
        an independent division's context (HM/LM/PM) reaches the lines below; the
        fast inline edit passes ``propagar_item=False`` to save only this line
        (the general recompute is then deferred to the Atualizar button). ValueSet
        data is not touched and ``editado_localmente`` is NOT changed here.
        """
        linha = self.repository.get_by_id(linha_id)
        if linha is None:
            return None

        # Free-text note (phase 8V.1): informative only, applies to every line
        # type (saved even for manual operations, which have no measures).
        descricao_livre_norm = (
            self._normalizar_expressao(descricao_livre)
            if descricao_livre is not None
            else None
        )

        if linha.tipo_linha == OPERACAO_MANUAL:
            # A manual-operation line has no measures: editing QT recomputes the
            # total minutes (minutos_unitarios × QT) and the cost from the machine.
            if descricao_livre is not None:
                self.repository.update_linha(
                    id=linha_id, descricao_livre=descricao_livre_norm
                )
            return self._atualizar_quantidade_operacao_manual(
                linha, qt_mod=qt_mod, qt_und=qt_und
            )

        item = self.session.get(OrcamentoItem, linha.orcamento_item_id)
        contexto = self._contexto_medidas_ate_linha(linha, item)

        comp_texto, comp_real = validar_expressao_medida(
            comp, contexto, campo="Comprimento"
        )
        larg_texto, larg_real = validar_expressao_medida(
            larg, contexto, campo="Largura"
        )
        esp_texto, esp_real = validar_expressao_medida(
            esp, contexto, campo="Espessura"
        )

        qt_mod_final = self._validar_quantidade_editada(
            qt_mod, "QT mod", permitir_zero=False
        )
        qt_und_final = self._validar_quantidade_editada(
            qt_und, "QT und", permitir_zero=True
        )

        fields = {
            "qt_mod": qt_mod_final,
            "qt_und": qt_und_final,
            "quantidade": qt_mod_final * qt_und_final,
            "comp": comp_texto,
            "larg": larg_texto,
            "esp": esp_texto,
            "comp_real": comp_real,
            "larg_real": larg_real,
            "esp_real": esp_real,
            "area_m2": calcular_area_m2(comp_real, larg_real),
            "perimetro_ml": calcular_perimetro_ml(comp_real, larg_real),
            # NOTE: measure/quantity edits must NOT flag the line as locally
            # edited. ``editado_localmente`` is reserved for local changes to the
            # inherited material/ValueSet data (see atualizar_material_local_linha
            # / aplicar_materia_prima_na_linha), so the ValueSet propagation can
            # tell which lines had their material overridden.
        }
        if descricao is not None:
            fields["descricao"] = self._normalizar_expressao(descricao) or "Divisão independente"
        if descricao_livre is not None:
            fields["descricao_livre"] = descricao_livre_norm

        self.repository.update_linha(id=linha_id, **fields)

        if propagar_item:
            # Recompute the whole item so independent-division context (HM/LM/PM)
            # and the block/composite quantities reach the lines below.
            self.recalcular_medidas_do_item(linha.orcamento_item_id)
        else:
            # Fast inline edit: propagate only the quantities (division block /
            # composite components); costs stay on the Atualizar button (the cost
            # pipeline already uses qt_total).
            self.recalcular_quantidades_do_item(linha.orcamento_item_id)

        return self.repository.get_by_id(linha_id)

    def _atualizar_quantidade_operacao_manual(
        self, linha, *, qt_mod, qt_und
    ) -> OrcamentoItemCusteioLinhaResumo | None:
        """Save an edited quantity of an OPERACAO_MANUAL line, recomputing the cost.

        tempo_manual = minutos_unitarios × QT total and custo_montagem_manual =
        (minutes / 60) × custo_hora; custo_total follows custo_producao honouring
        Excluir Produção. Description and minutos_unitarios are kept.
        """
        qt_mod_final = self._validar_quantidade_editada(
            qt_mod, "QT mod", permitir_zero=False
        )
        qt_und_final = self._validar_quantidade_editada(
            qt_und, "QT und", permitir_zero=True
        )
        quantidade = qt_mod_final * qt_und_final

        minutos_unitarios = self._minutos_unitarios_da_linha(linha)
        tempo_total = (
            minutos_unitarios * quantidade if minutos_unitarios is not None else None
        )
        custo_mm, maquina_texto = self._custo_e_maquina_operacao_manual(
            linha.def_maquina_id, tempo_total
        )
        custo_producao = somar_custo_producao(custo_mm)
        custo_total = (
            Decimal("0")
            if linha.excluir_producao
            else (custo_producao if custo_producao is not None else Decimal("0"))
        )

        fields: dict = {
            "qt_mod": qt_mod_final,
            "qt_und": qt_und_final,
            "quantidade": quantidade,
            "minutos_unitarios": minutos_unitarios,
            "tempo_manual": tempo_total,
            "maquina": maquina_texto,
            "custo_montagem_manual": custo_mm,
            "custo_producao": custo_producao,
            "custo_total": custo_total,
        }
        self.repository.update_linha(id=linha.id, **fields)
        self.session.commit()

        return self.repository.get_by_id(linha.id)

    def inserir_divisao_independente(
        self, orcamento_item_id: int
    ) -> OrcamentoItemCusteioLinhaResumo:
        """Insert an independent-division line that defines a local measure context."""
        item_id = self._validate_required_id(orcamento_item_id, "orcamento_item_id")

        result = self.repository.create_linha(
            orcamento_item_id=item_id,
            tipo_linha=DIVISAO_INDEPENDENTE,
            codigo="DIVISAO",
            descricao="Divisão independente",
            origem_tipo="MANUAL",
            nivel=0,
            qt_mod=Decimal("1"),
            qt_und=Decimal("1"),
            quantidade=Decimal("1"),
            comp="H",
            larg="L",
            esp="P",
            editado_localmente=True,
            ativo=True,
        )
        self.session.commit()

        return result

    def inserir_separador(
        self, orcamento_item_id: int, linha_id: int | None = None
    ) -> OrcamentoItemCusteioLinhaResumo:
        """Insert a visual SEPARADOR line below ``linha_id`` (or at the end).

        The separator carries no def_peca/material/measures/costs and is ignored
        by every recompute. Inserting it renumbers the item's active lines
        (``ordem_visual``) so the new row lands right after the selected one.

        It NEVER splits a composite piece: when the selection is a composite
        header (PECA_COMPOSTA) or one of its children, the separator is placed
        AFTER the whole block (right below the last child), not in the middle.
        Commits.
        """
        item_id = self._validate_required_id(orcamento_item_id, "orcamento_item_id")

        separador = self.repository.create_linha(
            orcamento_item_id=item_id,
            tipo_linha=SEPARADOR,
            descricao="",
            origem_tipo="MANUAL",
            nivel=0,
            quantidade=Decimal("0"),
            editado_localmente=True,
            ativo=True,
        )

        # Splice the separator right after the anchor (which never falls inside a
        # composite block) in display order.
        linhas = self.repository.list_active_by_orcamento_item(item_id)
        outras = [linha for linha in linhas if linha.id != separador.id]
        outras_ids = [linha.id for linha in outras]
        ancora_id = self._ancora_insercao(linha_id, outras)

        if ancora_id in outras_ids:
            indice = outras_ids.index(ancora_id)
            nova_ordem = (
                outras_ids[: indice + 1] + [separador.id] + outras_ids[indice + 1:]
            )
        else:
            nova_ordem = outras_ids + [separador.id]

        self.repository.reordenar_linhas(nova_ordem)
        self.session.commit()

        return self.repository.get_by_id(separador.id)

    def _ancora_insercao(self, linha_id: int | None, linhas: list) -> int | None:
        """Resolve the line AFTER which a new block should be inserted.

        Normally the selected line itself; but when the selection is a composite
        header or one of its children, the anchor is the LAST line of that whole
        composite block (so the insertion never splits the composite). Shared by
        the separator and the copy/paste of lines (phase 8V.5).
        """
        if linha_id is None:
            return None

        por_id = {linha.id: linha for linha in linhas}
        selecionada = por_id.get(linha_id)
        if selecionada is None:
            return linha_id

        topo = self._linha_topo_do_bloco(selecionada, por_id)
        if not any(linha.linha_pai_id == topo.id for linha in linhas):
            return linha_id  # standalone piece / hardware / division / operation

        # Composite block: anchor = the last display-order line of the block.
        ancora_id = topo.id
        for linha in linhas:
            if self._linha_topo_do_bloco(linha, por_id).id == topo.id:
                ancora_id = linha.id
        return ancora_id

    @staticmethod
    def _linha_topo_do_bloco(linha, por_id: dict):
        """Climb linha_pai_id to the top-level ancestor of a line."""
        atual = linha
        visto: set[int] = set()
        while atual.linha_pai_id is not None and atual.id not in visto:
            visto.add(atual.id)
            pai = por_id.get(atual.linha_pai_id)
            if pai is None:
                break
            atual = pai
        return atual

    # --- Copy / cut / paste of cost lines (phase 8V.5) -----------------------

    # Structural + material/snapshot fields copied for a faithful paste. Costs
    # and evaluated measures (comp_real/area/...) are recomputed by the pipeline.
    _CAMPOS_CLIPBOARD = (
        "tipo_linha", "codigo", "descricao", "descricao_livre",
        "def_peca_id", "def_peca_codigo", "chave_valueset", "codigo_orlas",
        "qt_mod", "qt_und", "quantidade", "comp", "larg", "esp",
        "nivel", "origem_tipo", "origem_id", "mat_default",
        "associado_regra_codigo", "associado_regra_expressao",
        "associado_modo_quantidade", "associado_zona_aplicacao",
        "associado_dimensao_referencia", "associado_numero_topos",
        "associado_valueset_prioridade",
        "operacoes_snapshot_json",
        "materia_prima_id", "ref_materia_prima", "descricao_materia_prima",
        "ref_le", "descricao_no_orcamento", "unidade", "preco_liquido",
        "desperdicio_percentagem", "tipo_materia_prima", "familia_materia_prima",
        "coresp_orla_0_4", "coresp_orla_1_0", "comp_mp", "larg_mp", "esp_mp",
        "acabamento_face_sup", "acabamento_face_inf",
        "acabamento_editado_localmente", "editado_localmente",
        "material_editado_localmente", "origem_material", "sem_material",
        "excluir_mp", "excluir_orla", "excluir_ferragem", "excluir_producao",
        "excluir_acabamento", "excluir_mo", "fator_serie", "modulo_imagem_path",
    )

    def construir_clipboard(
        self, orcamento_item_id: int, linha_ids, modo: str
    ) -> "ClipboardCusteio":
        """Build a structural snapshot of the selected lines (copy or cut).

        Selecting a composite header or one of its children pulls the WHOLE block
        (header + children); the relative display order is preserved. Separators
        and independent divisions can be copied too. ``modo`` is "COPIAR" or
        "CORTAR" (the latter also records the source ids, deleted only on paste).
        """
        item_id = self._validate_required_id(orcamento_item_id, "orcamento_item_id")
        linhas = self.repository.list_active_by_orcamento_item(item_id)
        selecionadas = self._expandir_selecao_blocos(linha_ids, linhas)
        if not selecionadas:
            raise ValueError("Selecione pelo menos uma linha para copiar.")

        indice_por_id = {linha.id: i for i, linha in enumerate(selecionadas)}
        snapshot: list[ClipboardLinhaCusteio] = []
        for linha in selecionadas:
            fields = {
                campo: getattr(linha, campo) for campo in self._CAMPOS_CLIPBOARD
            }
            fields["ativo"] = True
            indice_pai = (
                indice_por_id.get(linha.linha_pai_id)
                if linha.linha_pai_id is not None
                else None
            )
            snapshot.append(
                ClipboardLinhaCusteio(fields=fields, indice_pai=indice_pai)
            )

        return ClipboardCusteio(
            linhas=tuple(snapshot),
            modo="CORTAR" if modo == "CORTAR" else "COPIAR",
            origem_item_id=item_id,
            origem_ids=tuple(linha.id for linha in selecionadas),
        )

    def _expandir_selecao_blocos(self, linha_ids, linhas: list) -> list:
        """Expand the selection to whole composite blocks, in display order."""
        por_id = {linha.id: linha for linha in linhas}
        ids: set[int] = set()
        for linha_id in linha_ids or []:
            selecionada = por_id.get(linha_id)
            if selecionada is None:
                continue
            topo = self._linha_topo_do_bloco(selecionada, por_id)
            if any(linha.linha_pai_id == topo.id for linha in linhas):
                for linha in linhas:
                    if self._linha_topo_do_bloco(linha, por_id).id == topo.id:
                        ids.add(linha.id)
            else:
                ids.add(selecionada.id)

        return [linha for linha in linhas if linha.id in ids]

    def colar_clipboard(
        self,
        orcamento_item_id: int,
        clipboard: "ClipboardCusteio",
        linha_id: int | None = None,
    ) -> "ColarCusteioResult":
        """Paste the clipboard lines as a block BELOW ``linha_id`` (never inside
        a composite). Recreates the parent/child structure, keeps each line's
        material (or resolves it from the destination ValueSet when missing), and
        renumbers the display order. On a CUT clipboard the source lines are
        deleted after a successful paste. Commits; the caller runs the pipeline.
        """
        item_id = self._validate_required_id(orcamento_item_id, "orcamento_item_id")
        if clipboard is None or not clipboard.linhas:
            raise ValueError("Não há linhas para colar.")

        linhas_dest = self.repository.list_active_by_orcamento_item(item_id)
        ancora_id = self._ancora_insercao(linha_id, linhas_dest)

        novos_ids: list[int] = []
        mapa_ids: dict[int, int] = {}
        for indice, snap in enumerate(clipboard.linhas):
            fields = dict(snap.fields)
            fields["orcamento_item_id"] = item_id
            fields["linha_pai_id"] = (
                mapa_ids.get(snap.indice_pai)
                if snap.indice_pai is not None
                else None
            )
            self._resolver_material_colagem(item_id, fields)
            nova = self.repository.create_linha(**fields)
            mapa_ids[indice] = nova.id
            novos_ids.append(nova.id)

        # Place the new block right after the anchor in display order.
        linhas_apos = self.repository.list_active_by_orcamento_item(item_id)
        existentes = [l.id for l in linhas_apos if l.id not in novos_ids]
        if ancora_id in existentes:
            indice = existentes.index(ancora_id)
            nova_ordem = existentes[: indice + 1] + novos_ids + existentes[indice + 1:]
        else:
            nova_ordem = existentes + novos_ids
        self.repository.reordenar_linhas(nova_ordem)

        cortadas = 0
        if clipboard.modo == "CORTAR":
            origem = [oid for oid in clipboard.origem_ids if oid not in novos_ids]
            cortadas = self.repository.delete_linhas(origem)

        self.session.commit()

        return ColarCusteioResult(inseridas=len(novos_ids), cortadas=cortadas)

    def _resolver_material_colagem(self, item_id: int, fields: dict) -> None:
        """Fill the material of a pasted line from the destination ValueSet.

        Keeps the line's own material (faithful copy) when it has one; only when
        a PECA/FERRAGEM line has no material but carries a ValueSet key does it
        resolve the destination item's default option for that key.
        """
        if fields.get("tipo_linha") not in (PECA, FERRAGEM):
            return
        if fields.get("sem_material") or fields.get("materia_prima_id") is not None:
            return
        chave = fields.get("chave_valueset")
        if not chave:
            return
        prioridade = fields.get("associado_valueset_prioridade")
        vs_linha = self._resolver_valueset_por_chave(
            item_id, chave, prioridade
        )
        if vs_linha is not None:
            fields.update(self._build_valueset_material_fields(vs_linha))

    def inserir_operacao_manual(
        self,
        orcamento_item_id: int,
        descricao: str,
        def_maquina_id: int | None,
        tempo_minutos,
        quantidade=None,
        apos_linha_id: int | None = None,
    ) -> OrcamentoItemCusteioLinhaResumo:
        """Insert a user-defined manual-operation cost line (OPERACAO_MANUAL).

        ``tempo_manual`` stores the TOTAL minutes (tempo × quantidade); the cost is
        ``(total minutes / 60) × custo_hora_std`` of the chosen machine and feeds
        custo_producao. No materials/orlas/acabamentos are set.
        """
        item_id = self._validate_required_id(orcamento_item_id, "orcamento_item_id")
        texto = (descricao or "").strip()
        if not texto:
            raise ValueError("descricao is required")

        tempo_unitario = normalizar_numero(tempo_minutos)
        if tempo_unitario is None or tempo_unitario <= 0:
            raise ValueError("tempo invalido")
        qt = normalizar_numero(quantidade)
        if qt is None or qt <= 0:
            qt = Decimal("1")
        tempo_total = tempo_unitario * qt

        tipo_efetivo = self._tipo_producao_efetivo_do_item(item_id)
        custo_mm, maquina_texto = self._custo_e_maquina_operacao_manual(
            def_maquina_id, tempo_total, tipo_efetivo == TIPO_PRODUCAO_SERIE
        )

        result = self.repository.create_linha(
            orcamento_item_id=item_id,
            tipo_linha=OPERACAO_MANUAL,
            descricao=texto,
            descricao_livre=texto,
            origem_tipo="MANUAL",
            def_maquina_id=def_maquina_id,
            maquina=maquina_texto,
            nivel=0,
            qt_mod=Decimal("1"),
            qt_und=qt,
            quantidade=qt,
            minutos_unitarios=tempo_unitario,
            tempo_manual=tempo_total,
            custo_montagem_manual=custo_mm,
            custo_producao=somar_custo_producao(custo_mm),
            tipo_producao=tipo_efetivo,
            ativo=True,
        )
        if apos_linha_id is not None:
            self._posicionar_linha_apos(item_id, result.id, apos_linha_id)
        self.session.commit()

        return result

    @staticmethod
    def _validar_dados_material_local(fields: dict) -> None:
        """Validate and normalize local material values before persistence."""
        unidade = fields.get("unidade")
        if unidade is not None:
            unidade = str(unidade).strip().upper() or None
            if unidade is not None and not unidade_custo_valida(unidade):
                raise ValueError("Unidade inválida. Use M2, ML ou UND.")
            fields["unidade"] = unidade

        for campo, rotulo in (
            ("preco_liquido", "Preço líquido"),
            ("desperdicio_percentagem", "Desperdício %"),
            ("comp_mp", "Comp MP"),
            ("larg_mp", "Larg MP"),
            ("esp_mp", "Esp MP"),
        ):
            if campo not in fields:
                continue
            fields[campo] = validar_decimal(
                fields[campo],
                rotulo,
                minimo=Decimal("0"),
            )

    def _posicionar_linha_apos(
        self, orcamento_item_id: int, nova_linha_id: int, apos_linha_id: int
    ) -> None:
        """Move ``nova_linha_id`` immediately after ``apos_linha_id`` in display order."""
        linhas = self.repository.list_active_by_orcamento_item(orcamento_item_id)
        ids = [linha.id for linha in linhas if linha.id != nova_linha_id]
        if apos_linha_id in ids:
            indice = ids.index(apos_linha_id)
            nova_ordem = ids[: indice + 1] + [nova_linha_id] + ids[indice + 1:]
        else:
            nova_ordem = ids + [nova_linha_id]
        self.repository.reordenar_linhas(nova_ordem)

    def editar_operacao_manual(
        self,
        linha_id: int,
        descricao: str,
        def_maquina_id: int | None,
        tempo_minutos,
        quantidade=None,
    ) -> OrcamentoItemCusteioLinhaResumo | None:
        """Edit a manual-operation cost line (description, machine, time, qty)."""
        linha = self.repository.get_by_id(linha_id)
        if linha is None:
            return None
        if linha.tipo_linha != OPERACAO_MANUAL:
            raise ValueError("linha não é uma operação manual")

        texto = (descricao or "").strip()
        if not texto:
            raise ValueError("descricao is required")
        tempo_unitario = normalizar_numero(tempo_minutos)
        if tempo_unitario is None or tempo_unitario <= 0:
            raise ValueError("tempo invalido")
        qt = normalizar_numero(quantidade)
        if qt is None or qt <= 0:
            qt = Decimal("1")
        tempo_total = tempo_unitario * qt

        tipo_efetivo = self._tipo_producao_efetivo_do_item(linha.orcamento_item_id)
        custo_mm, maquina_texto = self._custo_e_maquina_operacao_manual(
            def_maquina_id, tempo_total, tipo_efetivo == TIPO_PRODUCAO_SERIE
        )

        self.repository.update_linha(
            id=linha_id,
            descricao=texto,
            descricao_livre=texto,
            def_maquina_id=def_maquina_id,
            maquina=maquina_texto,
            qt_mod=Decimal("1"),
            qt_und=qt,
            quantidade=qt,
            minutos_unitarios=tempo_unitario,
            tempo_manual=tempo_total,
            custo_montagem_manual=custo_mm,
            custo_producao=aplicar_fator_serie(
                somar_custo_producao(custo_mm), linha.fator_serie
            ),
            tipo_producao=tipo_efetivo,
        )
        self.session.commit()

        return self.repository.get_by_id(linha_id)

    def _custo_e_maquina_operacao_manual(
        self, def_maquina_id, tempo_total_minutos, usar_serie: bool = False
    ):
        """Return (custo_mm, machine code) for a manual-operation line.

        custo_mm = (minutes / 60) × the chosen machine's hourly rate for the
        item's effective production type (SERIE falls back to STD when not
        defined); the code feeds the Máquina column (and the tooltip).
        """
        maquina = (
            self.maquina_repository.get_by_id(def_maquina_id)
            if def_maquina_id is not None
            else None
        )
        custo_hora = self._custo_hora_maquina(maquina, usar_serie)
        custo_mm = calcular_custo_por_minutos(tempo_total_minutos, custo_hora)
        maquina_texto = getattr(maquina, "codigo", None) if maquina else None
        return custo_mm, maquina_texto

    def _normalizar_expressao(self, valor) -> str | None:
        """Normalize a measure expression: trimmed text, or None when empty."""
        if valor is None:
            return None

        texto = str(valor).strip()
        return texto or None

    @staticmethod
    def _validar_quantidade_editada(
        valor, campo: str, *, permitir_zero: bool
    ) -> Decimal:
        """Validate a quantity typed by the user without silently defaulting errors."""
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            return Decimal("1")

        numero = normalizar_numero(valor)
        if numero is None:
            raise ValueError(f"{campo} inválida: introduza um número.")
        if numero < 0 or (numero == 0 and not permitir_zero):
            limite = "maior ou igual a zero" if permitir_zero else "maior que zero"
            raise ValueError(f"{campo} inválida: o valor tem de ser {limite}.")
        return numero

    def _contexto_medidas_ate_linha(self, linha, item) -> dict:
        """Build global plus active HM/LM/PM context at one line's position."""
        if item is None:
            contexto_global: dict = {}
        else:
            contexto_global = construir_contexto_item(
                item.altura, item.largura, item.profundidade
            )

        contexto_local: dict = {}
        linhas = self.repository.list_active_by_orcamento_item(linha.orcamento_item_id)
        por_id = {atual.id: atual for atual in linhas}
        for atual in linhas:
            if atual.id == linha.id:
                break
            if atual.tipo_linha != DIVISAO_INDEPENDENTE:
                continue

            contexto = {**contexto_global, **contexto_local}
            contexto_local = {
                "HM": avaliar_medida(atual.comp, contexto),
                "LM": avaliar_medida(atual.larg, contexto),
                "PM": avaliar_medida(atual.esp, contexto),
            }

        contexto = {**contexto_global, **contexto_local}
        pai = por_id.get(linha.linha_pai_id)
        if pai is not None:
            contexto.update(self._contexto_dimensoes_pai(pai))
        return contexto

    @staticmethod
    def _contexto_dimensoes_pai(pai) -> dict:
        """Expose the evaluated dimensions of the immediate parent only."""
        if isinstance(pai, dict):
            obter = pai.get
        else:
            obter = lambda campo: getattr(pai, campo, None)
        return {
            "PAI_COMP": obter("comp_real"),
            "PAI_LARG": obter("larg_real"),
            "PAI_ESP": obter("esp_real"),
        }

    def _calcular_medidas_fields(
        self, linha, contexto: dict, qt_total: Decimal
    ) -> dict:
        """Build the recomputed quantity/measure fields for one line.

        ``qt_total`` is the quantity resolved by calcular_quantidades (it honours
        the division block and composite components); qt_mod/qt_und keep the
        line's own stored values.
        """
        qt_mod = linha.qt_mod if linha.qt_mod is not None else Decimal("1")
        qt_und = linha.qt_und if linha.qt_und is not None else Decimal("1")

        comp_real = avaliar_medida(linha.comp, contexto)
        larg_real = avaliar_medida(linha.larg, contexto)
        esp_real = avaliar_medida(linha.esp, contexto)

        return {
            "qt_mod": qt_mod,
            "qt_und": qt_und,
            "quantidade": qt_total,
            "comp_real": comp_real,
            "larg_real": larg_real,
            "esp_real": esp_real,
            "area_m2": calcular_area_m2(comp_real, larg_real),
            "perimetro_ml": calcular_perimetro_ml(comp_real, larg_real),
        }

    def adicionar_pecas_da_biblioteca(
        self, orcamento_item_id: int, def_peca_ids: list[int]
    ) -> AdicionarPecasResult:
        """Create cost lines for selected library pieces.

        Simple pieces create one PECA line. Composite pieces create a main
        PECA_COMPOSTA line plus one sub-line per active component. Material data
        is resolved from the item ValueSet (default option of each key).
        """
        item_id = self._validate_required_id(orcamento_item_id, "orcamento_item_id")

        pecas_selecionadas = [
            peca
            for def_peca_id in def_peca_ids
            if (peca := self.peca_repository.get_by_id(def_peca_id)) is not None
        ]
        self._validar_contexto_divisao_para_pecas(item_id, pecas_selecionadas)

        criadas = 0
        componentes = 0
        ignoradas = 0
        avisos: list[str] = []

        pecas_por_id = {peca.id: peca for peca in pecas_selecionadas}
        for def_peca_id in def_peca_ids:
            peca = pecas_por_id.get(def_peca_id)
            if peca is None:
                ignoradas += 1
                continue

            if self._eh_conjunto_virtual(peca):
                componentes += self._adicionar_peca_composta(item_id, peca, avisos)
            else:
                principal = self._adicionar_peca_simples(item_id, peca, avisos)
                associados = self._associados_ativos(peca.id)
                if associados:
                    componentes += self._criar_linhas_componentes(
                        item_id,
                        associados,
                        principal.id,
                        avisos,
                        origem="PECA_ASSOCIADA",
                        pecas_ancestrais={peca.id},
                    )
            criadas += 1

        self.session.commit()

        return AdicionarPecasResult(
            criadas=criadas,
            componentes=componentes,
            ignoradas=ignoradas,
            avisos=avisos,
        )

    def _validar_contexto_divisao_para_pecas(
        self, orcamento_item_id: int, pecas: list[DefPecaResumo]
    ) -> None:
        """Require an earlier independent division for catalog formulas HM/LM/PM."""
        linhas = self.repository.list_active_by_orcamento_item(orcamento_item_id)
        if any(linha.tipo_linha == DIVISAO_INDEPENDENTE for linha in linhas):
            return
        if not any(self._peca_requer_divisao(peca, set()) for peca in pecas):
            return
        raise ValueError(
            "Esta peça usa HM, LM ou PM, mas o custeio ainda não tem uma divisão "
            "independente. Comece por inserir uma Divisão independente e adicione "
            "a peça logo abaixo."
        )

    def _peca_requer_divisao(self, peca: DefPecaResumo, visitadas: set[int]) -> bool:
        if peca.id in visitadas:
            return False
        visitadas = {*visitadas, peca.id}
        if self._formulas_usam_contexto_local(
            getattr(peca, "formula_comp", None),
            getattr(peca, "formula_larg", None),
            getattr(peca, "formula_esp", None),
        ):
            return True
        return self._associados_requerem_divisao(peca, visitadas)

    def _associados_requerem_divisao(
        self, peca: DefPecaResumo, visitadas: set[int]
    ) -> bool:
        """Whether any active associate (recursively) uses HM/LM/PM formulas."""
        for componente in self._associados_ativos(peca.id):
            if self._formulas_usam_contexto_local(
                getattr(componente, "formula_comp", None),
                getattr(componente, "formula_larg", None),
                getattr(componente, "formula_esp", None),
            ):
                return True
            filha = self._obter_def_peca_filha(componente)
            if filha is not None and self._peca_requer_divisao(filha, visitadas):
                return True
        return False

    @staticmethod
    def _formulas_usam_contexto_local(*formulas) -> bool:
        return any(
            re.search(r"\b(?:HM|LM|PM)\b", str(formula), flags=re.IGNORECASE)
            for formula in formulas
            if formula
        )

    @staticmethod
    def _eh_conjunto_virtual(peca: DefPecaResumo) -> bool:
        """Recognize the unified nature, preserving legacy COMPOSTA records."""
        return getattr(peca, "natureza", None) == CONJUNTO or peca.tipo_peca == COMPOSTA

    def _associados_ativos(self, def_peca_id: int) -> list:
        return [
            associado
            for associado in self.componente_repository.list_by_peca_pai_id(def_peca_id)
            if associado.ativo
        ]

    # --- Import a saved module into the item (phase 8U.2) --------------------

    def inserir_modulo_no_item(
        self, orcamento_item_id: int, modulo_id: int
    ) -> InserirModuloResult:
        """Append a saved module's lines to an item's costing (V2-style import).

        Each module line is recreated reusing the library-insertion logic: a
        division keeps its measure context; a simple piece is rebuilt from its
        def_peca (material resolved from the ITEM ValueSet) then overlaid with
        the module's structural fields; a composite recreates its header + the
        CHILD lines stored with it (keeping their measure formulas/rules), or
        RE-EXPANDS from the def_peca for old modules with no stored children. No
        material/price is copied from the module (it has none) — only
        structure/formulas. The full Atualizar pipeline must run afterwards so
        the formulas re-evaluate against the item's variables/ValueSet. Importing
        is a COPY (no link to the module) and several modules can be imported in
        sequence. Commits.
        """
        item_id = self._validate_required_id(orcamento_item_id, "orcamento_item_id")

        modulo = self.def_modulo_repository.get_by_id(modulo_id)
        if modulo is None:
            raise ValueError("Módulo não encontrado.")

        linhas_modulo = self.def_modulo_repository.list_linhas(modulo_id)
        avisos: list[str] = []
        if not linhas_modulo:
            self._adicionar_aviso(
                avisos, f"Módulo {modulo.codigo} não tem linhas para importar."
            )
            return InserirModuloResult(
                modulo_codigo=modulo.codigo, criadas=0, componentes=0, avisos=avisos
            )

        self._validar_contexto_divisao_para_modulo(item_id, linhas_modulo)

        # Group composite children by the ordem of their parent header line.
        filhos_por_pai_ordem: dict[int, list] = {}
        for linha in linhas_modulo:
            if linha.linha_pai_ordem is not None:
                filhos_por_pai_ordem.setdefault(linha.linha_pai_ordem, []).append(linha)

        # Snapshot the existing line ids so we can find the first new line below.
        ids_antes = {
            linha.id
            for linha in self.repository.list_active_by_orcamento_item(item_id)
        }

        criadas = 0
        componentes = 0
        for linha in linhas_modulo:
            if linha.linha_pai_ordem is not None:
                continue  # handled within its composite parent
            tipo = normalize_custeio_linha_type(linha.tipo_linha)
            if tipo == DIVISAO_INDEPENDENTE:
                self._importar_divisao_modulo(item_id, linha)
            elif tipo == PECA_COMPOSTA:
                componentes += self._importar_composta_modulo(
                    item_id, linha, filhos_por_pai_ordem.get(linha.ordem, []), avisos
                )
            else:
                self._importar_peca_modulo(item_id, linha, tipo, avisos)
            criadas += 1

        # Store the module image on the FIRST line of the imported block (the
        # division, or the first line) so the table can show its thumbnail.
        self._marcar_imagem_modulo(item_id, ids_antes, modulo.imagem_path)

        self.session.commit()

        return InserirModuloResult(
            modulo_codigo=modulo.codigo,
            criadas=criadas,
            componentes=componentes,
            avisos=avisos,
        )

    def _validar_contexto_divisao_para_modulo(
        self, orcamento_item_id: int, linhas_modulo
    ) -> None:
        """Refuse the import atomically when HM/LM/PM context is missing (C3).

        Mirrors the library-insertion guard: a module line that uses HM/LM/PM
        needs an independent division, provided either by the ITEM (any active
        division) or by the MODULE itself (a division line above, in module
        order). Nothing is created when the import is refused.
        """
        linhas_item = self.repository.list_active_by_orcamento_item(orcamento_item_id)
        if any(l.tipo_linha == DIVISAO_INDEPENDENTE for l in linhas_item):
            return

        ordens_com_filhos = {
            l.linha_pai_ordem for l in linhas_modulo if l.linha_pai_ordem is not None
        }
        for linha in linhas_modulo:
            tipo = normalize_custeio_linha_type(linha.tipo_linha)
            if tipo == DIVISAO_INDEPENDENTE:
                return  # everything below the module's own division has context
            if self._linha_modulo_requer_divisao(linha, tipo, ordens_com_filhos):
                raise ValueError(
                    "Este módulo usa HM, LM ou PM, mas não inclui uma divisão "
                    "independente acima dessas linhas e o custeio ainda não tem "
                    "nenhuma. Comece por inserir uma Divisão independente e "
                    "importe o módulo logo abaixo."
                )

    def _linha_modulo_requer_divisao(
        self, linha, tipo: str, ordens_com_filhos: set[int]
    ) -> bool:
        """Whether one module line will need HM/LM/PM context when imported.

        Checks the EFFECTIVE formulas: the module's stored text, falling back
        per field to the def_peca formula the import would apply. A composite
        without stored children re-expands from the catalog, so its associates'
        formulas are checked too.
        """
        peca = self._resolver_def_peca_modulo(linha)
        efetivas = [
            texto if texto is not None else (
                getattr(peca, f"formula_{campo}", None) if peca is not None else None
            )
            for campo in ("comp", "larg", "esp")
            for texto in (getattr(linha, campo, None),)
        ]
        if self._formulas_usam_contexto_local(*efetivas):
            return True
        if (
            tipo == PECA_COMPOSTA
            and peca is not None
            and linha.ordem not in ordens_com_filhos
        ):
            return self._associados_requerem_divisao(peca, {peca.id})
        return False

    def _marcar_imagem_modulo(
        self, item_id: int, ids_antes: set[int], imagem_path: str | None
    ) -> None:
        """Set modulo_imagem_path on the first line created by this import."""
        if not imagem_path:
            return
        novas = [
            linha
            for linha in self.repository.list_active_by_orcamento_item(item_id)
            if linha.id not in ids_antes
        ]
        if not novas:
            return
        primeira = min(novas, key=lambda linha: linha.id)
        self.repository.update_linha(
            id=primeira.id, modulo_imagem_path=imagem_path
        )

    def _importar_divisao_modulo(self, orcamento_item_id: int, linha) -> None:
        """Recreate an independent-division line from a module line."""
        self.repository.create_linha(
            orcamento_item_id=orcamento_item_id,
            tipo_linha=DIVISAO_INDEPENDENTE,
            codigo=linha.codigo or "DIVISAO",
            descricao=linha.descricao_livre or linha.descricao or "Divisão independente",
            origem_tipo="MODULO",
            nivel=0,
            qt_mod=self._qt_modulo(linha.qt_mod, Decimal("1")),
            qt_und=self._qt_modulo(linha.qt_und, Decimal("1")),
            quantidade=Decimal("1"),
            comp=linha.comp or "H",
            larg=linha.larg or "L",
            esp=linha.esp or "P",
            editado_localmente=True,
            ativo=True,
        )

    def _importar_peca_modulo(
        self, orcamento_item_id: int, linha, tipo: str, avisos: list[str]
    ) -> None:
        """Recreate a simple piece / standalone hardware line from a module line.

        Rebuild from def_peca (item ValueSet) then overlay the module's stored
        structure. If the piece is gone/inactive, create the possible line and
        warn (the import is not aborted).
        """
        peca = self._resolver_def_peca_modulo(linha)
        if peca is None:
            self._importar_linha_modulo_sem_peca(orcamento_item_id, linha, tipo, avisos)
            return

        fields, aviso = self._build_peca_line_fields(
            orcamento_item_id,
            peca,
            tipo_linha=tipo,
            origem="MODULO",
            nivel=0,
            linha_pai_id=None,
            ordem=None,
            qt_und=self._qt_modulo(linha.qt_und, Decimal("1")),
            prioridade_valueset=getattr(linha, "prioridade_valueset", None),
        )
        if aviso:
            self._adicionar_aviso(avisos, aviso)

        self._aplicar_estrutura_modulo(fields, linha)
        self.repository.create_linha(**fields)

    def _importar_composta_modulo(
        self, orcamento_item_id: int, linha, filhos: list, avisos: list[str]
    ) -> int:
        """Recreate a composite into the item costing.

        When the module stored the composite's CHILD lines, recreate the header
        + those children DIRECTLY (keeping their measure formulas and linking the
        quantity rule via the matching def_peca_componente). Otherwise fall back
        to re-expanding from the def_peca (old modules). Returns how many
        component sub-lines were created.
        """
        peca = self._resolver_def_peca_modulo(linha)

        if not filhos:
            return self._reexpandir_composta_da_def_peca(
                orcamento_item_id, linha, peca, avisos
            )

        principal = self._criar_cabecalho_composta_modulo(
            orcamento_item_id, linha, peca, avisos
        )
        componentes_def = (
            [c for c in self.componente_repository.list_by_peca_pai_id(peca.id) if c.ativo]
            if peca is not None
            else []
        )

        criados = 0
        for ordem, filho in enumerate(filhos, start=1):
            self._importar_filho_composta_modulo(
                orcamento_item_id, filho, principal.id, ordem, componentes_def, avisos
            )
            criados += 1

        return criados

    def _reexpandir_composta_da_def_peca(
        self, orcamento_item_id: int, linha, peca, avisos: list[str]
    ) -> int:
        """Fallback for modules without stored children: re-expand the def_peca."""
        if peca is None:
            self._importar_linha_modulo_sem_peca(
                orcamento_item_id, linha, PECA_COMPOSTA, avisos
            )
            return 0

        principal = self._criar_cabecalho_composta_modulo(
            orcamento_item_id, linha, peca, avisos
        )

        componentes = [
            componente
            for componente in self.componente_repository.list_by_peca_pai_id(peca.id)
            if componente.ativo
        ]
        if not componentes:
            self._adicionar_aviso(
                avisos, f"Peça composta {peca.codigo} sem componentes configurados."
            )
            return 0

        return self._criar_linhas_componentes(
            orcamento_item_id,
            componentes,
            principal.id,
            avisos,
            pecas_ancestrais={peca.id},
        )

    def _criar_cabecalho_composta_modulo(
        self, orcamento_item_id: int, linha, peca, avisos: list[str]
    ):
        """Create the composite header from a module line (Phase C).

        A header saved WITH dimension formulas applies them exactly as stored
        (a faithful snapshot: empty fields stay empty). Old modules, saved with
        the three fields empty, keep the previous dimensionless header — even
        when the def_peca meanwhile gained formulas. Uses the def_peca when
        available; otherwise a best-effort header."""
        if peca is not None:
            principal = self._criar_linha_principal_composta(orcamento_item_id, peca)
            override: dict = self._formulas_cabecalho_modulo(linha)
            qt_und = self._qt_modulo(linha.qt_und)
            if qt_und is not None:
                override["qt_und"] = qt_und
                override["quantidade"] = qt_und
            descricao = linha.descricao or linha.descricao_livre
            if descricao:
                override["descricao"] = descricao
            if override:
                self.repository.update_linha(id=principal.id, **override)
            return principal

        codigo_peca = linha.def_peca_codigo or linha.codigo
        if codigo_peca:
            self._adicionar_aviso(
                avisos, f"Peça {codigo_peca} do módulo já não existe; "
                "cabeçalho criado sem material."
            )
        qt_und = self._qt_modulo(linha.qt_und, Decimal("1"))
        return self.repository.create_linha(
            orcamento_item_id=orcamento_item_id,
            tipo_linha=PECA_COMPOSTA,
            codigo=linha.codigo or linha.def_peca_codigo,
            def_peca_codigo=linha.def_peca_codigo,
            descricao=(
                linha.descricao
                or linha.descricao_livre
                or linha.def_peca_codigo
                or "Peça composta"
            ),
            codigo_orlas=linha.codigo_orlas,
            chave_valueset=linha.chave_valueset,
            origem_tipo="MODULO",
            nivel=0,
            qt_mod=Decimal("1"),
            qt_und=qt_und,
            quantidade=qt_und,
            **self._formulas_cabecalho_modulo(linha),
            editado_localmente=False,
            ativo=True,
        )

    @staticmethod
    def _formulas_cabecalho_modulo(linha) -> dict:
        """Header dimension formulas stored on a module line (Phase C).

        Returns the stored comp/larg/esp trio when the module saved ANY of
        them; an all-None trio otherwise, so old modules (saved before Phase C)
        keep the previous dimensionless header regardless of current def_peca
        formulas."""
        if any(
            getattr(linha, campo, None) is not None
            for campo in ("comp", "larg", "esp")
        ):
            return {"comp": linha.comp, "larg": linha.larg, "esp": linha.esp}
        return {"comp": None, "larg": None, "esp": None}

    def _importar_filho_composta_modulo(
        self,
        orcamento_item_id: int,
        filho,
        linha_pai_id: int,
        ordem: int,
        componentes_def: list,
        avisos: list[str],
    ) -> None:
        """Recreate one composite CHILD from a module line (keeps its formulas).

        Resolves the material from the def_peca/ValueSet (as in the library),
        overlays the module's structure, and links origem_id to the matching
        def_peca_componente so the quantity rule applies in the pipeline.
        """
        tipo = normalize_custeio_linha_type(filho.tipo_linha)
        peca = self._resolver_def_peca_modulo(filho)

        if peca is not None:
            fields, aviso = self._build_peca_line_fields(
                orcamento_item_id,
                peca,
                tipo_linha=tipo,
                origem="MODULO",
                nivel=1,
                linha_pai_id=linha_pai_id,
                ordem=ordem,
                qt_und=self._qt_modulo(filho.qt_und, Decimal("1")),
                prioridade_valueset=getattr(
                    filho, "prioridade_valueset", None
                ),
                sem_chave_observacao=(
                    "Componente sem chave ValueSet: atribua uma chave de "
                    "material à definição da peça."
                ),
            )
            if aviso:
                self._adicionar_aviso(avisos, aviso)
        else:
            codigo_peca = filho.def_peca_codigo or filho.codigo
            if codigo_peca:
                self._adicionar_aviso(
                    avisos, f"Peça {codigo_peca} do módulo já não existe; "
                    "linha criada sem material."
                )
            qt_und = self._qt_modulo(filho.qt_und, Decimal("1"))
            fields = {
                "orcamento_item_id": orcamento_item_id,
                "tipo_linha": tipo,
                "codigo": filho.codigo or filho.def_peca_codigo,
                "def_peca_codigo": filho.def_peca_codigo,
                "descricao": (
                    filho.descricao
                    or filho.descricao_livre
                    or filho.def_peca_codigo
                    or "Componente"
                ),
                "chave_valueset": filho.chave_valueset,
                "origem_tipo": "MODULO",
                "nivel": 1,
                "linha_pai_id": linha_pai_id,
                "ordem": ordem,
                "qt_mod": Decimal("1"),
                "qt_und": qt_und,
                "quantidade": qt_und,
                "editado_localmente": False,
                "ativo": True,
            }

        self._aplicar_estrutura_modulo(fields, filho)

        componente = self._componente_para_filho_modulo(filho, componentes_def)
        if componente is not None:
            fields["origem_id"] = componente.id
            fields.update(self._snapshot_regra_associado(componente))
        if getattr(filho, "prioridade_valueset", None) is not None:
            fields["associado_valueset_prioridade"] = filho.prioridade_valueset

        self.repository.create_linha(**fields)

    @staticmethod
    def _componente_para_filho_modulo(filho, componentes_def):
        """Match a module child to a def_peca_componente (for its quantity rule)."""
        for componente in componentes_def:
            if (
                filho.def_peca_id is not None
                and componente.def_peca_componente_id == filho.def_peca_id
            ):
                return componente
            if (
                filho.def_peca_codigo
                and componente.referencia_componente == filho.def_peca_codigo
            ):
                return componente
        return None

    def _importar_linha_modulo_sem_peca(
        self, orcamento_item_id: int, linha, tipo: str, avisos: list[str]
    ) -> None:
        """Create the best-effort line when a module piece no longer exists."""
        codigo_peca = linha.def_peca_codigo or linha.codigo
        if codigo_peca:
            self._adicionar_aviso(
                avisos, f"Peça {codigo_peca} do módulo já não existe; "
                "linha criada sem material."
            )
        qt_und = self._qt_modulo(linha.qt_und, Decimal("1"))
        self.repository.create_linha(
            orcamento_item_id=orcamento_item_id,
            tipo_linha=tipo,
            codigo=linha.codigo or linha.def_peca_codigo,
            def_peca_codigo=linha.def_peca_codigo,
            descricao=(
                linha.descricao
                or linha.descricao_livre
                or linha.def_peca_codigo
                or "Linha do módulo"
            ),
            chave_valueset=linha.chave_valueset,
            codigo_orlas=linha.codigo_orlas,
            comp=linha.comp,
            larg=linha.larg,
            esp=linha.esp,
            qt_mod=self._qt_modulo(linha.qt_mod, Decimal("1")),
            qt_und=qt_und,
            quantidade=qt_und,
            origem_tipo="MODULO",
            nivel=0,
            editado_localmente=False,
            ativo=True,
        )

    def _aplicar_estrutura_modulo(self, fields: dict, linha) -> None:
        """Overlay a module line's structural fields onto built piece fields.

        Only structure/formulas — never material/price (kept from the ValueSet).
        """
        if linha.comp is not None:
            fields["comp"] = linha.comp
        if linha.larg is not None:
            fields["larg"] = linha.larg
        if linha.esp is not None:
            fields["esp"] = linha.esp
        if linha.codigo_orlas is not None:
            fields["codigo_orlas"] = linha.codigo_orlas
        qt_mod = self._qt_modulo(linha.qt_mod)
        if qt_mod is not None:
            fields["qt_mod"] = qt_mod
        qt_und = self._qt_modulo(linha.qt_und)
        if qt_und is not None:
            fields["qt_und"] = qt_und
            fields["quantidade"] = qt_und

    def _resolver_def_peca_modulo(self, linha) -> DefPecaResumo | None:
        """Resolve a module line's active def_peca (by id, then code)."""
        if linha.def_peca_id is not None:
            peca = self.peca_repository.get_by_id(linha.def_peca_id)
            if peca is not None and peca.ativo:
                return peca

        if linha.def_peca_codigo:
            peca = self.peca_repository.get_by_codigo(linha.def_peca_codigo)
            if peca is not None and peca.ativo:
                return peca

        return None

    @staticmethod
    def _qt_modulo(valor, default: Decimal | None = None) -> Decimal | None:
        """Convert a module's text quantity to Decimal (numbers only)."""
        numero = normalizar_numero(valor)
        return numero if numero is not None else default

    def _adicionar_peca_simples(
        self, orcamento_item_id: int, peca: DefPecaResumo, avisos: list[str]
    ) -> OrcamentoItemCusteioLinhaResumo:
        """Create one cost line for a simple library piece.

        The line type is DERIVED from the piece's material nature (see
        ``_tipo_linha_da_def_peca``): a hardware piece becomes a FERRAGEM line, a
        board/material piece a PECA — never chosen by the user here.
        """
        fields, aviso = self._build_peca_line_fields(
            orcamento_item_id,
            peca,
            tipo_linha=self._tipo_linha_da_def_peca(peca),
            origem="BIBLIOTECA_PECA",
            nivel=0,
            linha_pai_id=None,
            ordem=None,
            qt_und=Decimal("1"),
        )
        if aviso:
            self._adicionar_aviso(avisos, aviso)

        return self.repository.create_linha(**fields)

    def _tipo_linha_da_def_peca(self, peca: DefPecaResumo) -> str:
        """Derive a simple piece's cost-line type from its material nature.

        The type is DERIVED, not configured by the user: a piece whose ValueSet
        material key is a hardware-like type (FERRAGEM / SISTEMA_CORRER /
        ILUMINACAO / ACESSORIO) becomes a FERRAGEM line — so a dobradiça/pé added
        from the library shows "Ferragem" exactly like one inserted from a module
        (which derives the type from the component's tipo_componente). A material/
        board key, an unknown key, or a service piece without material stays PECA.
        The key type is resolved from the configurable ValueSet keys repository.
        """
        if getattr(peca, "natureza", None) == "FERRAGEM":
            return FERRAGEM
        if getattr(peca, "sem_material", False):
            return PECA

        chave = (peca.chave_valueset_material or "").strip().upper()
        if not chave:
            return PECA

        tipo_chave = self.tipos_das_chaves().get(chave)
        if tipo_chave in TIPOS_FERRAGEM:
            return FERRAGEM
        return PECA

    def _adicionar_peca_composta(
        self, orcamento_item_id: int, peca: DefPecaResumo, avisos: list[str]
    ) -> int:
        """Create the main line plus component sub-lines of a composite piece.

        Returns the number of component sub-lines created.
        """
        principal = self._criar_linha_principal_composta(orcamento_item_id, peca)

        componentes = self._associados_ativos(peca.id)
        if not componentes:
            self._adicionar_aviso(
                avisos, f"Peça composta {peca.codigo} sem componentes configurados."
            )
            return 0

        return self._criar_linhas_componentes(
            orcamento_item_id, componentes, principal.id, avisos
        )

    def _criar_linha_principal_composta(
        self, orcamento_item_id: int, peca: DefPecaResumo
    ) -> OrcamentoItemCusteioLinhaResumo:
        """Create the main (grouping) line of a composite piece."""
        return self.repository.create_linha(
            orcamento_item_id=orcamento_item_id,
            tipo_linha=PECA_COMPOSTA,
            codigo=peca.codigo,
            def_peca_id=peca.id,
            def_peca_codigo=peca.codigo,
            descricao=peca.nome or peca.descricao or peca.codigo,
            codigo_orlas=self._format_codigo_orlas(peca),
            chave_valueset=peca.chave_valueset_material,
            origem_tipo="BIBLIOTECA_PECA",
            nivel=0,
            linha_pai_id=None,
            ordem=None,
            qt_mod=Decimal("1"),
            qt_und=Decimal("1"),
            quantidade=Decimal("1"),
            **self._formulas_peca(peca),
            editado_localmente=False,
            ativo=True,
        )

    def _criar_linhas_componentes(
        self,
        orcamento_item_id: int,
        componentes: list,
        linha_pai_id: int,
        avisos: list[str],
        origem: str = "PECA_COMPOSTA",
        nivel: int = 1,
        pecas_ancestrais: set[int] | None = None,
        ids_criados: list[int] | None = None,
    ) -> int:
        """Create one sub-line per component, returning how many were created."""
        criadas = 0
        for ordem, componente in enumerate(componentes, start=1):
            peca_filha = self._obter_def_peca_filha(componente)
            ancestrais = set(pecas_ancestrais or set())
            if peca_filha is not None and peca_filha.id in ancestrais:
                self._adicionar_aviso(
                    avisos,
                    f"Associação circular detetada em {peca_filha.codigo}; "
                    "a linha repetida não foi inserida.",
                )
                continue
            fields, aviso = self._build_componente_line_fields(
                orcamento_item_id,
                componente,
                linha_pai_id,
                ordem,
                origem=origem,
                nivel=nivel,
            )
            if aviso:
                self._adicionar_aviso(avisos, aviso)
            criada = self.repository.create_linha(**fields)
            if ids_criados is not None:
                ids_criados.append(criada.id)
            criadas += 1

            if peca_filha is None:
                continue
            associados_filha = self._associados_ativos(peca_filha.id)
            if associados_filha:
                criadas += self._criar_linhas_componentes(
                    orcamento_item_id,
                    associados_filha,
                    criada.id,
                    avisos,
                    origem=origem,
                    nivel=nivel + 1,
                    pecas_ancestrais={*ancestrais, peca_filha.id},
                    ids_criados=ids_criados,
                )

        return criadas

    def _build_componente_line_fields(
        self,
        orcamento_item_id: int,
        componente,
        linha_pai_id: int,
        ordem: int,
        *,
        origem: str = "PECA_COMPOSTA",
        nivel: int = 1,
    ) -> tuple[dict, str | None]:
        """Build the cost line fields for one composite component sub-line."""
        qt_und = (
            componente.quantidade if componente.quantidade is not None else Decimal("1")
        )
        modo_quantidade = normalize_modo_quantidade(
            getattr(componente, "modo_quantidade", TOTAL)
        )
        numero_topos = int(getattr(componente, "numero_topos", 0) or 0)
        if modo_quantidade == POR_TOPO and numero_topos in (1, 2):
            qt_und *= Decimal(numero_topos)
        snapshot = self._snapshot_regra_associado(componente)

        peca_filha = self._obter_def_peca_filha(componente)

        if peca_filha is not None:
            if componente.tipo_componente != "PECA":
                tipo_linha = normalize_custeio_linha_type(
                    componente.tipo_componente
                )
            else:
                tipo_linha = self._tipo_linha_da_def_peca(peca_filha)
            fields, aviso = self._build_peca_line_fields(
                orcamento_item_id,
                peca_filha,
                tipo_linha=tipo_linha,
                origem=origem,
                nivel=nivel,
                linha_pai_id=linha_pai_id,
                ordem=ordem,
                qt_und=qt_und,
                prioridade_valueset=(
                    getattr(componente, "prioridade_valueset", 1) or 1
                ),
                sem_chave_observacao=(
                    "Componente sem chave ValueSet: atribua uma chave de "
                    "material à definição da peça."
                ),
            )
            # Link the cost line back to the DefPecaComponente so the Atualizar
            # pipeline can resolve its quantity rule (phase 8T.5.1).
            fields["origem_id"] = componente.id
            self._aplicar_formulas_componente(fields, componente)
            fields.update(snapshot)
            return fields, aviso

        tipo_linha = normalize_custeio_linha_type(componente.tipo_componente)
        fields: dict = {
            "orcamento_item_id": orcamento_item_id,
            "tipo_linha": tipo_linha,
            "codigo": componente.referencia_componente,
            "descricao": componente.descricao
            or componente.referencia_componente
            or "Componente",
            "origem_tipo": origem,
            "origem_id": componente.id,
            "nivel": nivel,
            "linha_pai_id": linha_pai_id,
            "ordem": ordem,
            "qt_mod": Decimal("1"),
            "qt_und": qt_und,
            "quantidade": qt_und,
            "editado_localmente": False,
            "ativo": True,
            "observacoes": (
                "Componente sem definição de peça associada: ligue-o a uma peça "
                "da biblioteca (com chave de material) para herdar o material."
            ),
        }
        fields.update(snapshot)
        self._aplicar_formulas_componente(fields, componente)
        return fields, None

    @staticmethod
    def _aplicar_formulas_componente(fields: dict, componente) -> None:
        """Overlay the association formulas on the child snapshot."""
        for campo in ("comp", "larg", "esp"):
            formula = getattr(componente, f"formula_{campo}", None)
            if formula is not None:
                fields[campo] = formula

    @staticmethod
    def _formulas_peca(peca) -> dict:
        return {
            campo: formula
            for campo in ("comp", "larg", "esp")
            if (formula := getattr(peca, f"formula_{campo}", None)) is not None
        }

    def _snapshot_regra_associado(self, componente) -> dict:
        """Freeze the association and its current active quantity rule."""
        regra = None
        regra_id = getattr(componente, "def_regra_quantidade_id", None)
        if regra_id is not None:
            regra = self.regra_quantidade_repository.get_by_id(
                regra_id
            )
            if regra is not None and not regra.ativo:
                regra = None

        return {
            "associado_regra_codigo": getattr(regra, "codigo", None),
            "associado_regra_expressao": getattr(regra, "expressao", None),
            "associado_modo_quantidade": normalize_modo_quantidade(
                getattr(componente, "modo_quantidade", TOTAL)
            ),
            "associado_zona_aplicacao": getattr(
                componente, "zona_aplicacao", None
            ),
            "associado_dimensao_referencia": normalize_dimensao_referencia(
                getattr(componente, "dimensao_referencia", DIM_COMP)
            ),
            "associado_numero_topos": int(
                getattr(componente, "numero_topos", 0) or 0
            ),
            "associado_valueset_prioridade": int(
                getattr(componente, "prioridade_valueset", 1) or 1
            ),
        }

    def _obter_def_peca_filha(self, componente) -> DefPecaResumo | None:
        """Resolve the child piece definition of a component.

        Prefers the explicit def_peca_componente_id link; falls back to looking
        the definition up by code (referencia_componente).
        """
        if componente.def_peca_componente_id is not None:
            peca = self.peca_repository.get_by_id(componente.def_peca_componente_id)
            if peca is not None:
                return peca

        if componente.referencia_componente:
            return self.peca_repository.get_by_codigo(componente.referencia_componente)

        return None

    def resolver_valueset_para_def_peca(
        self,
        orcamento_item_id: int,
        peca: DefPecaResumo,
        prioridade: int | None = None,
    ) -> OrcamentoItemValuesetLinhaResumo | None:
        """Resolve the item ValueSet line for a piece material key."""
        return self._resolver_valueset_por_chave(
            orcamento_item_id, peca.chave_valueset_material, prioridade
        )

    def _resolver_valueset_por_chave(
        self,
        orcamento_item_id: int,
        chave: str | None,
        prioridade: int | None = None,
    ) -> OrcamentoItemValuesetLinhaResumo | None:
        """Resolve one item ValueSet line for a key.

        The active line with the lowest prioridade wins (1 = first choice);
        lines without prioridade come last, tie broken by id.
        """
        if not chave:
            return None

        chave_normalizada = normalize_valueset_key(chave)
        if prioridade is not None:
            return self.item_valueset_repository.get_active_by_item_chave_prioridade(
                orcamento_item_id, chave_normalizada, prioridade
            )
        return self.item_valueset_repository.get_default_by_item_chave(
            orcamento_item_id, chave_normalizada
        )

    def _build_peca_line_fields(
        self,
        orcamento_item_id: int,
        peca: DefPecaResumo,
        *,
        tipo_linha: str = PECA,
        origem: str = "BIBLIOTECA_PECA",
        nivel: int = 0,
        linha_pai_id: int | None = None,
        ordem: int | None = None,
        qt_und: Decimal = Decimal("1"),
        prioridade_valueset: int | None = None,
        sem_chave_observacao: str = "Definição de peça sem chave ValueSet.",
    ) -> tuple[dict, str | None]:
        """Build the cost line fields for one piece, resolving the item ValueSet."""
        qt_und = qt_und if qt_und is not None else Decimal("1")

        fields: dict = {
            "orcamento_item_id": orcamento_item_id,
            "tipo_linha": tipo_linha,
            "codigo": peca.codigo,
            "def_peca_id": peca.id,
            "def_peca_codigo": peca.codigo,
            "operacoes_snapshot_json": self._snapshot_operacoes_peca(peca.id),
            "descricao": peca.nome or peca.descricao or peca.codigo,
            "codigo_orlas": self._format_codigo_orlas(peca),
            "chave_valueset": peca.chave_valueset_material,
            "origem_tipo": origem,
            "nivel": nivel,
            "linha_pai_id": linha_pai_id,
            "ordem": ordem,
            "qt_mod": Decimal("1"),
            "qt_und": qt_und,
            "quantidade": qt_und,
            "editado_localmente": False,
            "sem_material": bool(getattr(peca, "sem_material", False)),
            "ativo": True,
        }
        fields.update(self._formulas_peca(peca))

        if fields["sem_material"]:
            # Service piece: no raw material / ValueSet. Leave the material and
            # orla columns empty and emit no ValueSet warning; the cost comes
            # only from the associated operations (cut/CNC/manual/assembly).
            fields["chave_valueset"] = None
            fields["codigo_orlas"] = None
            return fields, None

        if not peca.chave_valueset_material:
            fields["observacoes"] = sem_chave_observacao
            return fields, None

        linha_vs = self.resolver_valueset_para_def_peca(
            orcamento_item_id, peca, prioridade_valueset
        )
        if linha_vs is None:
            if prioridade_valueset is not None:
                aviso = (
                    f"Prioridade ValueSet {prioridade_valueset} não configurada "
                    f"para a chave {peca.chave_valueset_material}; a linha ficou "
                    "sem material."
                )
            else:
                aviso = (
                    f"Sem ValueSet encontrado para a chave "
                    f"{peca.chave_valueset_material}: configure o material desta "
                    "chave no ValueSet do item."
                )
            fields["observacoes"] = aviso
            return fields, aviso

        if prioridade_valueset is not None and not self._valueset_tem_material(
            linha_vs
        ):
            aviso = (
                f"Prioridade ValueSet {prioridade_valueset} da chave "
                f"{peca.chave_valueset_material} não tem dados de material; "
                "Mat. default ficou vazio."
            )
            fields["observacoes"] = aviso
            return fields, aviso

        fields.update(
            {
                "materia_prima_id": linha_vs.materia_prima_id,
                "ref_materia_prima": linha_vs.ref_materia_prima,
                "descricao_materia_prima": linha_vs.descricao_materia_prima,
                "mat_default": linha_vs.codigo_opcao or linha_vs.nome_opcao,
                "valueset_prioridade": linha_vs.prioridade,
                "ref_le": linha_vs.ref_le,
                "descricao_no_orcamento": linha_vs.descricao_no_orcamento,
                "unidade": linha_vs.unidade,
                "preco_liquido": linha_vs.preco_liquido,
                "desperdicio_percentagem": linha_vs.desperdicio_percentagem,
                "tipo_materia_prima": linha_vs.tipo_materia_prima,
                "familia_materia_prima": linha_vs.familia_materia_prima,
                "coresp_orla_0_4": linha_vs.coresp_orla_0_4,
                "coresp_orla_1_0": linha_vs.coresp_orla_1_0,
                "comp_mp": linha_vs.comp_mp,
                "larg_mp": linha_vs.larg_mp,
                "esp_mp": linha_vs.esp_mp,
            }
        )

        # Default the piece thickness (Esp) from the inherited material, for real
        # pieces/hardware only (never division or composite-parent lines).
        if tipo_linha in (PECA, FERRAGEM) and not fields.get("esp"):
            esp_texto = self._espessura_material_para_esp(linha_vs.esp_mp)
            if esp_texto is not None:
                fields["esp"] = esp_texto

        return fields, None

    @staticmethod
    def _valueset_tem_material(linha_vs) -> bool:
        """Distinguish a configured material from an empty priority placeholder."""
        return any(
            getattr(linha_vs, campo, None) not in (None, "")
            for campo in (
                "materia_prima_id",
                "ref_materia_prima",
                "ref_le",
                "descricao_no_orcamento",
                "preco_liquido",
            )
        )

    def _snapshot_operacoes_peca(self, def_peca_id: int) -> str:
        """Serialize the active operation links used when the quote line is born."""
        itens: list[dict] = []
        for ligacao in self.peca_operacao_repository.list_active_by_def_peca(
            def_peca_id
        ):
            operacao = self.operacao_repository.get_by_id(ligacao.def_operacao_id)
            if operacao is None or not getattr(operacao, "ativo", True):
                continue
            itens.append(
                {
                    "operacao": {
                        "id": getattr(operacao, "id", ligacao.def_operacao_id),
                        "codigo": getattr(operacao, "codigo", None),
                        "nome": getattr(operacao, "nome", None),
                        "tipo_operacao": getattr(operacao, "tipo_operacao", None),
                        "unidade_calculo": getattr(
                            operacao, "unidade_calculo", None
                        ),
                        "tempo_base": self._json_numero(
                            getattr(operacao, "tempo_base", None)
                        ),
                        "tempo_setup": self._json_numero(
                            getattr(operacao, "tempo_setup", None)
                        ),
                        "custo_hora": self._json_numero(
                            getattr(operacao, "custo_hora", None)
                        ),
                        "custo_minimo": self._json_numero(
                            getattr(operacao, "custo_minimo", None)
                        ),
                        "maquina_id": getattr(operacao, "maquina_id", None),
                        "ativo": True,
                    },
                    "ligacao": {
                        "id": ligacao.id,
                        "def_peca_id": getattr(ligacao, "def_peca_id", def_peca_id),
                        "def_operacao_id": ligacao.def_operacao_id,
                        "ordem": getattr(ligacao, "ordem", 1),
                        "regra_calculo": getattr(ligacao, "regra_calculo", None),
                        "quantidade_base": self._json_numero(
                            getattr(ligacao, "quantidade_base", None)
                        ),
                        "tempo_setup_minutos": self._json_numero(
                            getattr(ligacao, "tempo_setup_minutos", None)
                        ),
                        "tempo_por_unidade_minutos": self._json_numero(
                            getattr(ligacao, "tempo_por_unidade_minutos", None)
                        ),
                        "unidade_tempo": getattr(ligacao, "unidade_tempo", None),
                        "obrigatorio": getattr(ligacao, "obrigatorio", True),
                        "ativo": True,
                    },
                }
            )
        return json.dumps(itens, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _json_numero(value) -> str | None:
        numero = normalizar_numero(value)
        return format(numero, "f") if numero is not None else None

    def _espessura_material_para_esp(self, espessura) -> str | None:
        """Format a material thickness as a clean Esp expression (or None)."""
        valor = normalizar_numero(espessura)
        if valor is None or valor == 0:
            return None

        return format(valor.normalize(), "f")

    def _format_codigo_orlas(self, peca: DefPecaResumo) -> str:
        """Build the orla code (e.g. 2200) from the four orla sides."""
        return f"{peca.orla_c1}{peca.orla_c2}{peca.orla_l1}{peca.orla_l2}"

    def _adicionar_aviso(self, avisos: list[str], mensagem: str) -> None:
        """Append a warning message, avoiding duplicates."""
        if mensagem not in avisos:
            avisos.append(mensagem)

    def criar_linha_manual(
        self, data: CriarLinhaCusteioData
    ) -> OrcamentoItemCusteioLinhaResumo:
        """Create one cost line (manual or with a given type)."""
        fields = self._build_fields(data)
        result = self.repository.create_linha(**fields)
        self.session.commit()

        return result

    def editar_linha(
        self, id: int, data: EditarLinhaCusteioData
    ) -> OrcamentoItemCusteioLinhaResumo:
        """Edit one cost line."""
        fields = self._build_fields(data)
        result = self.repository.update_linha(id=id, **fields)
        self.session.commit()

        return result

    def desativar_linha(self, id: int) -> bool:
        """Deactivate one cost line."""
        deactivated = self.repository.deactivate_linha(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_linha(self, id: int) -> bool:
        """Reactivate one cost line."""
        activated = self.repository.activate_linha(id)
        if activated:
            self.session.commit()

        return activated

    def _build_fields(self, data) -> dict:
        orcamento_item_id = self._validate_required_id(
            data.orcamento_item_id, "orcamento_item_id"
        )
        descricao = self._normalize_required_text(data.descricao, "descricao")
        tipo_linha = self._normalize_tipo_linha(data.tipo_linha)
        quantidade = self._normalize_quantidade(data.quantidade)
        custo_total = self._compute_total(data.custo_total, data.custo_unitario, quantidade)
        preco_total = self._compute_total(data.preco_total, data.preco_unitario, quantidade)

        return {
            "orcamento_item_id": orcamento_item_id,
            "orcamento_item_modulo_id": data.orcamento_item_modulo_id,
            "origem_tipo": data.origem_tipo,
            "origem_id": data.origem_id,
            "tipo_linha": tipo_linha,
            "codigo": data.codigo,
            "descricao": descricao,
            "materia_prima_id": data.materia_prima_id,
            "ref_materia_prima": data.ref_materia_prima,
            "descricao_materia_prima": data.descricao_materia_prima,
            "unidade": data.unidade,
            "quantidade": quantidade,
            "comp": data.comp,
            "larg": data.larg,
            "esp": data.esp,
            "area_m2": data.area_m2,
            "perimetro_ml": data.perimetro_ml,
            "ml_orla_fina": data.ml_orla_fina,
            "ml_orla_grossa": data.ml_orla_grossa,
            "custo_unitario": data.custo_unitario,
            "custo_total": custo_total,
            "margem_percentagem": data.margem_percentagem,
            "preco_unitario": data.preco_unitario,
            "preco_total": preco_total,
            "def_operacao_id": data.def_operacao_id,
            "def_maquina_id": data.def_maquina_id,
            "tempo_calculado": data.tempo_calculado,
            "tempo_manual": data.tempo_manual,
            "override_manual": data.override_manual,
            "editado_localmente": data.editado_localmente,
            "ativo": data.ativo,
            "observacoes": data.observacoes,
        }

    def _validate_required_id(self, value: int | None, field_name: str) -> int:
        if not value:
            raise ValueError(f"{field_name} is required")

        return value

    def _normalize_required_text(self, value: str | None, field_name: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} is required")

        return normalized

    def _normalize_tipo_linha(self, tipo_linha: str | None) -> str:
        if tipo_linha is None or not tipo_linha.strip():
            return MANUAL

        return normalize_custeio_linha_type(tipo_linha)

    def _normalize_quantidade(self, quantidade: Decimal | None) -> Decimal:
        if quantidade is None:
            return Decimal("1")

        return quantidade

    def _compute_total(
        self,
        total: Decimal | None,
        unitario: Decimal | None,
        quantidade: Decimal,
    ) -> Decimal | None:
        if total is not None:
            return total

        if unitario is not None:
            return unitario * quantidade

        return None
