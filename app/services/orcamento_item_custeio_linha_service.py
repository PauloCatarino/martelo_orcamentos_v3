"""Service for budget item cost line workflows.

This phase only stores cost lines. It does not generate lines automatically
from pieces, modules or operations, and does not recompute budget totals.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.custeio_linha_types import (
    DIVISAO_INDEPENDENTE,
    FERRAGEM,
    MANUAL,
    PECA,
    PECA_COMPOSTA,
    normalize_custeio_linha_type,
)
from app.domain.medidas import (
    avaliar_medida,
    calcular_area_m2,
    calcular_perimetro_ml,
    construir_contexto_item,
    normalizar_numero,
)
from app.domain.acabamentos import (
    SEM_ACABAMENTO,
    calcular_areas_acabamento,
    tem_acabamento,
)
from app.domain.custo_producao import (
    MOTIVO_SEM_TARIFA,
    calcular_custo_corte,
    calcular_custo_orlagem,
    somar_custo_producao,
)
from app.domain.tempos_producao import (
    AVISO_TEMPO_OPERACAO_SEM_DADOS,
    calcular_tempos_producao,
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
from app.domain.materia_prima_snapshot import (
    coresp_orla_0_4,
    coresp_orla_1_0,
    familia_materia_prima,
    tipo_materia_prima,
)
from app.domain.numeros import normalize_percentagem_humana
from app.domain.orlas import calcular_orlas_detalhe
from app.domain.peca_types import COMPOSTA
from app.domain.valueset_types import normalize_valueset_key
from app.models import OrcamentoItem
from app.repositories.def_maquina_repository import DefMaquinaRepository
from app.repositories.def_materia_prima_repository import DefMateriaPrimaRepository
from app.repositories.def_operacao_repository import DefOperacaoRepository
from app.repositories.def_peca_componente_repository import DefPecaComponenteRepository
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


class OrcamentoItemCusteioLinhaService:
    """Application service for OrcamentoItemCusteioLinha workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrcamentoItemCusteioLinhaRepository(session)
        self.peca_repository = DefPecaRepository(session)
        self.componente_repository = DefPecaComponenteRepository(session)
        self.item_valueset_repository = OrcamentoItemValuesetLinhaRepository(session)
        self.materia_prima_repository = DefMateriaPrimaRepository(session)
        self.peca_operacao_repository = DefPecaOperacaoRepository(session)
        self.operacao_repository = DefOperacaoRepository(session)
        self.maquina_repository = DefMaquinaRepository(session)

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
            and linha.tipo_linha not in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA)
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
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA):
                continue

            self.repository.update_linha(id=custeio_id, **fields)
            atualizadas += 1

        self.session.commit()

        return atualizadas

    def _build_valueset_material_fields(self, vs_linha) -> dict:
        """Build the material fields to copy from an item ValueSet line."""
        fields = {
            "mat_default": vs_linha.codigo_opcao or vs_linha.nome_opcao,
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

        atualizadas = 0
        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            contexto = {**contexto_global, **contexto_local}
            fields = self._calcular_medidas_fields(linha, contexto)

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
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA):
                continue

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
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA):
                ignoradas += 1
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
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA):
                ignoradas += 1
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
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA):
                ignoradas += 1
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
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA):
                ignoradas += 1
                continue

            processadas += 1
            total = self._custo_total_da_linha(linha)
            self.repository.update_linha(id=linha.id, custo_total=total)

        self.session.commit()

        return CustoTotalResult(processadas=processadas, ignoradas=ignoradas)

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
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA):
                ignoradas += 1
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

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if not self._linha_recebe_operacoes(linha):
                ignoradas += 1
                continue
            if linha.operacoes and linha.editado_localmente:
                # Preserve a locally edited operations cell.
                ignoradas += 1
                continue

            operacoes_texto, maquina_texto = self._operacoes_da_peca(linha.def_peca_id)

            processadas += 1
            fields: dict = {
                "operacoes": operacoes_texto or None,
                "maquina": maquina_texto or None,
            }
            if operacoes_texto:
                aplicadas += 1

            self.repository.update_linha(id=linha.id, **fields)

        self.session.commit()

        return OperacoesResult(
            processadas=processadas, aplicadas=aplicadas, ignoradas=ignoradas
        )

    def _linha_recebe_operacoes(self, linha) -> bool:
        """Return True for real piece lines (with a def_peca) that take operations."""
        return linha.tipo_linha == PECA and linha.def_peca_id is not None

    def _operacoes_da_peca(self, def_peca_id: int) -> tuple[str, str]:
        """Build the "; "-joined operation codes and the distinct machines of a piece."""
        nomes: list[str] = []
        maquinas: list[str] = []

        for ligacao in self.peca_operacao_repository.list_active_by_def_peca(def_peca_id):
            operacao = self.operacao_repository.get_by_id(ligacao.def_operacao_id)
            if operacao is None:
                continue

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
        resumos = []
        for ligacao in self.peca_operacao_repository.list_active_by_def_peca(def_peca_id):
            operacao = self.operacao_repository.get_by_id(ligacao.def_operacao_id)
            if operacao is not None:
                resumos.append(operacao)
        return resumos

    def recalcular_tempos_producao_do_item(
        self, orcamento_item_id: int
    ) -> TemposProducaoResult:
        """Recompute the basic production times (minutes) of an item's PECA lines.

        Reads the piece operations (DefPecaOperacao + DefOperacao) and fills
        tempo_corte / tempo_orlagem / tempo_cnc / tempo_montagem / tempo_manual /
        tempo_setup from each operation's ``tempo_base`` (per piece, or per ML for
        orlagem) and ``tempo_setup``. No costs are computed and custo_total is not
        touched. Only PECA lines with a def_peca are processed; a line whose times
        are already filled and is edited locally is preserved.
        """
        processadas = 0
        calculadas = 0
        ignoradas = 0

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if not self._linha_recebe_operacoes(linha):
                ignoradas += 1
                continue
            if self._tempos_preenchidos(linha) and linha.editado_localmente:
                ignoradas += 1
                continue

            operacoes = self._operacoes_def_da_peca(linha.def_peca_id)
            ml_orla_total = (linha.ml_orla_fina or Decimal("0")) + (
                linha.ml_orla_grossa or Decimal("0")
            )
            tempos, faltam_dados = calcular_tempos_producao(
                operacoes, linha.quantidade, ml_orla_total
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
            aviso = AVISO_TEMPO_OPERACAO_SEM_DADOS if (operacoes and faltam_dados) else None
            nova_obs = self._mesclar_observacao(
                linha.observacoes, "Tempos de produção", aviso
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

    def recalcular_custos_producao_do_item(
        self, orcamento_item_id: int
    ) -> CustoProducaoResult:
        """Recompute custo_corte / custo_orlagem / custo_producao (STD tariffs).

        For each PECA line with a def_peca: if the piece has a CORTE operation,
        cost the cutting from that machine's €/ML (perimeter × qt) plus setup ×
        qt; if it has an ORLAGEM operation, cost the edging from the line's total
        edging metres × €/ML plus setup × qt. custo_producao is the sum (empty
        partials count as 0; NULL when none computed). Skips ferragens, ML, UND,
        divisions and composite parents. Does not change materials/orlas/
        acabamentos/measures; custo_total is recomputed by its own step.
        """
        processadas = 0
        calculadas = 0
        ignoradas = 0

        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if not self._linha_recebe_operacoes(linha):
                ignoradas += 1
                continue

            operacoes = self._operacoes_def_da_peca(linha.def_peca_id)
            op_corte = self._operacao_por_bucket(operacoes, "corte")
            op_orlagem = self._operacao_por_bucket(operacoes, "orlagem")

            custo_corte = None
            custo_orlagem = None
            avisos: list[str] = []

            if op_corte is not None:
                maquina = self._maquina_de_operacao(op_corte)
                preco, setup = self._tarifas_std(maquina)
                custo_corte, motivo = calcular_custo_corte(
                    linha.perimetro_ml, linha.quantidade, preco, setup
                )
                aviso = self._aviso_producao(motivo, maquina, "corte")
                if aviso:
                    avisos.append(aviso)

            if op_orlagem is not None:
                maquina = self._maquina_de_operacao(op_orlagem)
                preco, setup = self._tarifas_std(maquina)
                ml_orla_total = (linha.ml_orla_fina or Decimal("0")) + (
                    linha.ml_orla_grossa or Decimal("0")
                )
                custo_orlagem, motivo = calcular_custo_orlagem(
                    ml_orla_total, linha.quantidade, preco, setup
                )
                aviso = self._aviso_producao(motivo, maquina, "orlagem")
                if aviso:
                    avisos.append(aviso)

            custo_producao = somar_custo_producao(custo_corte, custo_orlagem)

            processadas += 1
            fields: dict = {
                "custo_corte": custo_corte,
                "custo_orlagem": custo_orlagem,
                "custo_producao": custo_producao,
            }
            nova_obs = self._mesclar_observacao(
                linha.observacoes, "Custo de produção", avisos[0] if avisos else None
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

    def _tarifas_std(self, maquina):
        """Return (preco_ml_std, custo_setup_peca_std) of a machine, or (None, None)."""
        if maquina is None:
            return None, None
        return (
            getattr(maquina, "preco_ml_std", None),
            getattr(maquina, "custo_setup_peca_std", None),
        )

    def _aviso_producao(self, motivo, maquina, etapa: str) -> str | None:
        """Build the production observation for a missing tariff/data, or None."""
        if motivo is None:
            return None
        if motivo == MOTIVO_SEM_TARIFA:
            nome = getattr(maquina, "codigo", None) or "—"
            return (
                f"Custo de produção não calculado: tarifa €/ML em falta na "
                f"máquina {nome}."
            )
        return f"Custo de produção não calculado: dados de {etapa} em falta."

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
        fields["acabamento_editado_localmente"] = True
        fields["editado_localmente"] = True

        self.repository.update_linha(id=linha_id, **fields)
        self.session.commit()

        item_id = linha.orcamento_item_id
        self.recalcular_areas_acabamento_do_item(item_id)
        self.recalcular_custo_acabamento_do_item(item_id)
        self.recalcular_custo_total_do_item(item_id)

        return self.repository.get_by_id(linha_id)

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
        if linha.tipo_linha not in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA):
            fields["custo_total"] = self._custo_total_da_linha(
                linha, **{campo: bool(excluir)}
            )

        self.repository.update_linha(id=linha_id, **fields)
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
        contexto = (
            construir_contexto_item(item.altura, item.largura, item.profundidade)
            if item is not None
            else {}
        )

        fields = self._calcular_medidas_fields(linha, contexto)
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
    ) -> OrcamentoItemCusteioLinhaResumo | None:
        """Save edited quantities/measures of one cost line, then recompute.

        Comp/Larg/Esp keep the raw text/expression written by the user, while
        comp_real/larg_real/esp_real (and area/perimeter) hold the evaluated
        result. The whole item is recomputed afterwards because changing an
        independent division affects the lines below it. ValueSet data is not
        touched and ``editado_localmente`` is NOT changed here (that flag is only
        for local edits to the inherited material data).
        """
        linha = self.repository.get_by_id(linha_id)
        if linha is None:
            return None

        item = self.session.get(OrcamentoItem, linha.orcamento_item_id)
        contexto = (
            construir_contexto_item(item.altura, item.largura, item.profundidade)
            if item is not None
            else {}
        )

        comp_texto = self._normalizar_expressao(comp)
        larg_texto = self._normalizar_expressao(larg)
        esp_texto = self._normalizar_expressao(esp)

        qt_mod_valor = normalizar_numero(qt_mod)
        qt_und_valor = normalizar_numero(qt_und)
        qt_mod_final = qt_mod_valor if qt_mod_valor is not None else Decimal("1")
        qt_und_final = qt_und_valor if qt_und_valor is not None else Decimal("1")

        comp_real = avaliar_medida(comp_texto, contexto)
        larg_real = avaliar_medida(larg_texto, contexto)
        esp_real = avaliar_medida(esp_texto, contexto)

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

        self.repository.update_linha(id=linha_id, **fields)

        # Recompute the whole item so independent-division context (HM/LM/PM)
        # propagates to the lines below.
        self.recalcular_medidas_do_item(linha.orcamento_item_id)

        return self.repository.get_by_id(linha_id)

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

    def _normalizar_expressao(self, valor) -> str | None:
        """Normalize a measure expression: trimmed text, or None when empty."""
        if valor is None:
            return None

        texto = str(valor).strip()
        return texto or None

    def _calcular_medidas_fields(self, linha, contexto: dict) -> dict:
        """Build the recomputed quantity/measure fields for one line."""
        qt_mod = linha.qt_mod if linha.qt_mod is not None else Decimal("1")
        qt_und = linha.qt_und if linha.qt_und is not None else Decimal("1")
        qt_total = qt_mod * qt_und

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

        criadas = 0
        componentes = 0
        ignoradas = 0
        avisos: list[str] = []

        for def_peca_id in def_peca_ids:
            peca = self.peca_repository.get_by_id(def_peca_id)
            if peca is None:
                ignoradas += 1
                continue

            if peca.tipo_peca == COMPOSTA:
                componentes += self._adicionar_peca_composta(item_id, peca, avisos)
            else:
                self._adicionar_peca_simples(item_id, peca, avisos)
            criadas += 1

        self.session.commit()

        return AdicionarPecasResult(
            criadas=criadas,
            componentes=componentes,
            ignoradas=ignoradas,
            avisos=avisos,
        )

    def _adicionar_peca_simples(
        self, orcamento_item_id: int, peca: DefPecaResumo, avisos: list[str]
    ) -> None:
        """Create one PECA cost line for a simple library piece."""
        fields, aviso = self._build_peca_line_fields(
            orcamento_item_id,
            peca,
            tipo_linha=PECA,
            origem="BIBLIOTECA_PECA",
            nivel=0,
            linha_pai_id=None,
            ordem=None,
            qt_und=Decimal("1"),
        )
        if aviso:
            self._adicionar_aviso(avisos, aviso)

        self.repository.create_linha(**fields)

    def _adicionar_peca_composta(
        self, orcamento_item_id: int, peca: DefPecaResumo, avisos: list[str]
    ) -> int:
        """Create the main line plus component sub-lines of a composite piece.

        Returns the number of component sub-lines created.
        """
        principal = self._criar_linha_principal_composta(orcamento_item_id, peca)

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
            editado_localmente=False,
            ativo=True,
        )

    def _criar_linhas_componentes(
        self,
        orcamento_item_id: int,
        componentes: list,
        linha_pai_id: int,
        avisos: list[str],
    ) -> int:
        """Create one sub-line per component, returning how many were created."""
        criadas = 0
        for ordem, componente in enumerate(componentes, start=1):
            fields, aviso = self._build_componente_line_fields(
                orcamento_item_id, componente, linha_pai_id, ordem
            )
            if aviso:
                self._adicionar_aviso(avisos, aviso)
            self.repository.create_linha(**fields)
            criadas += 1

        return criadas

    def _build_componente_line_fields(
        self, orcamento_item_id: int, componente, linha_pai_id: int, ordem: int
    ) -> tuple[dict, str | None]:
        """Build the cost line fields for one composite component sub-line."""
        qt_und = (
            componente.quantidade if componente.quantidade is not None else Decimal("1")
        )
        tipo_linha = normalize_custeio_linha_type(componente.tipo_componente)

        peca_filha = self._obter_def_peca_filha(componente)

        if peca_filha is not None:
            return self._build_peca_line_fields(
                orcamento_item_id,
                peca_filha,
                tipo_linha=tipo_linha,
                origem="PECA_COMPOSTA",
                nivel=1,
                linha_pai_id=linha_pai_id,
                ordem=ordem,
                qt_und=qt_und,
                sem_chave_observacao="Componente sem chave ValueSet.",
            )

        fields: dict = {
            "orcamento_item_id": orcamento_item_id,
            "tipo_linha": tipo_linha,
            "codigo": componente.referencia_componente,
            "descricao": componente.descricao
            or componente.referencia_componente
            or "Componente",
            "origem_tipo": "PECA_COMPOSTA",
            "nivel": 1,
            "linha_pai_id": linha_pai_id,
            "ordem": ordem,
            "qt_mod": Decimal("1"),
            "qt_und": qt_und,
            "quantidade": qt_und,
            "editado_localmente": False,
            "ativo": True,
            "observacoes": "Componente sem definição de peça associada.",
        }
        return fields, None

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
        self, orcamento_item_id: int, peca: DefPecaResumo
    ) -> OrcamentoItemValuesetLinhaResumo | None:
        """Resolve the item ValueSet line for a piece material key."""
        return self._resolver_valueset_por_chave(
            orcamento_item_id, peca.chave_valueset_material
        )

    def _resolver_valueset_por_chave(
        self, orcamento_item_id: int, chave: str | None
    ) -> OrcamentoItemValuesetLinhaResumo | None:
        """Resolve one item ValueSet line for a key (default option first)."""
        if not chave:
            return None

        chave_norm = normalize_valueset_key(chave)

        padrao = self.item_valueset_repository.get_default_by_item_chave(
            orcamento_item_id, chave_norm
        )
        if padrao is not None:
            return padrao

        for linha in self.item_valueset_repository.list_by_item_chave(
            orcamento_item_id, chave_norm
        ):
            if linha.ativo:
                return linha

        return None

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
            "ativo": True,
        }

        if not peca.chave_valueset_material:
            fields["observacoes"] = sem_chave_observacao
            return fields, None

        linha_vs = self.resolver_valueset_para_def_peca(orcamento_item_id, peca)
        if linha_vs is None:
            aviso = f"Sem ValueSet encontrado para a chave {peca.chave_valueset_material}"
            fields["observacoes"] = aviso
            return fields, aviso

        fields.update(
            {
                "materia_prima_id": linha_vs.materia_prima_id,
                "ref_materia_prima": linha_vs.ref_materia_prima,
                "descricao_materia_prima": linha_vs.descricao_materia_prima,
                "mat_default": linha_vs.codigo_opcao or linha_vs.nome_opcao,
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
        if tipo_linha in (PECA, FERRAGEM):
            esp_texto = self._espessura_material_para_esp(linha_vs.esp_mp)
            if esp_texto is not None:
                fields["esp"] = esp_texto

        return fields, None

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
