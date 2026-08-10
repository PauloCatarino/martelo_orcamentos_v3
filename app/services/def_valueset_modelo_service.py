"""Service for reusable ValueSet model workflows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import DefValuesetModeloLinha, DefValuesetModeloLinhaOperacao
from app.repositories.def_valueset_modelo_linha_operacao_repository import (
    DefValuesetModeloLinhaOperacaoRepository,
)
from app.repositories.def_valueset_modelo_linha_repository import (
    DefValuesetModeloLinhaRepository,
)
from app.repositories.def_valueset_modelo_repository import (
    DefValuesetModeloRepository,
    DefValuesetModeloResumo,
)
from app.services.def_valueset_modelo_linha_service import (
    CriarDefValuesetModeloLinhaData,
    DefValuesetModeloLinhaService,
)
from app.services.def_valueset_modelo_linha_operacao_service import (
    CriarDefValuesetModeloLinhaOperacaoData,
    DefValuesetModeloLinhaOperacaoService,
)


@dataclass(frozen=True)
class CriarDefValuesetModeloData:
    """Input data for creating a reusable ValueSet model."""

    codigo: str
    nome: str
    descricao: str | None = None
    tipo: str | None = None
    ambito: str = "UTILIZADOR"
    user_id: int | None = None
    visivel_para_todos: bool = False
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarDefValuesetModeloData:
    """Input data for editing a reusable ValueSet model."""

    codigo: str
    nome: str
    descricao: str | None = None
    tipo: str | None = None
    ambito: str = "UTILIZADOR"
    user_id: int | None = None
    visivel_para_todos: bool = False
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class DuplicarDefValuesetModeloResult:
    """Result of saving a model as a new model with copied lines."""

    modelo: DefValuesetModeloResumo
    linhas_copiadas: int


@dataclass(frozen=True)
class DefValuesetModeloConteudoResumo:
    """Model header plus the amount of content that would be replaced."""

    modelo: DefValuesetModeloResumo
    linhas: int
    operacoes: int


@dataclass(frozen=True)
class SubstituirDefValuesetModeloResult:
    """Result of publishing one model over a selected global model."""

    modelo: DefValuesetModeloResumo
    linhas_removidas: int
    operacoes_removidas: int
    linhas_copiadas: int
    operacoes_copiadas: int


class DefValuesetModeloService:
    """Application service for reusable ValueSet models."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefValuesetModeloRepository(session)

    def listar_modelos(self) -> list[DefValuesetModeloResumo]:
        """List all reusable ValueSet models."""
        return self.repository.list_all()

    def listar_modelos_ativos(self) -> list[DefValuesetModeloResumo]:
        """List active reusable ValueSet models."""
        return self.repository.list_active()

    # Havia aqui um `listar_modelos_utilizador()` que, apesar do nome, devolvia
    # os modelos NAO-globais de TODA a gente — nao filtrava por dono nenhum. Era
    # o que o dialogo de importar usava, e por isso mostrava os modelos dos
    # colegas e do administrador. Removido: quem precisa das duas listas usa
    # `listar_modelos_para_separadores`, que recebe o utilizador.

    def listar_modelos_para_separadores(
        self,
        user_id: int | None,
        is_admin: bool = False,
        incluir_inativos: bool = False,
    ) -> tuple[list[DefValuesetModeloResumo], list[DefValuesetModeloResumo]]:
        """Return (utilizador, globais) models for the two-tab library page.

        Globais tab: models scoped GLOBAL or shared with everyone.
        Utilizador tab: the caller's own (non-global) models; an administrator
        sees every user's non-global models here.
        """
        if incluir_inativos:
            modelos = self.repository.list_all()
        else:
            modelos = self.repository.list_active()

        utilizador: list[DefValuesetModeloResumo] = []
        globais: list[DefValuesetModeloResumo] = []
        for modelo in modelos:
            if self._e_global(modelo):
                globais.append(modelo)
            elif is_admin or modelo.user_id == user_id:
                utilizador.append(modelo)
        return utilizador, globais

    def _e_global(self, modelo: DefValuesetModeloResumo) -> bool:
        ambito = (modelo.ambito or "").strip().upper()
        return ambito == "GLOBAL" or bool(modelo.visivel_para_todos)

    def obter_por_id(self, id: int) -> DefValuesetModeloResumo | None:
        """Get one reusable ValueSet model by id."""
        return self.repository.get_by_id(id)

    def obter_por_codigo(self, codigo: str | None) -> DefValuesetModeloResumo | None:
        """Get one reusable ValueSet model by code."""
        normalized = self._normalize_optional_text(codigo)
        if normalized is None:
            return None

        return self.repository.get_by_codigo(normalized)

    def resumir_conteudo_modelo(
        self, modelo_id: int
    ) -> DefValuesetModeloConteudoResumo:
        """Return a model and exact line/operation counts for confirmation UI."""
        modelo = self.repository.get_by_id(modelo_id)
        if modelo is None:
            raise ValueError("modelo not found")

        linha_repository = DefValuesetModeloLinhaRepository(self.session)
        operacao_repository = DefValuesetModeloLinhaOperacaoRepository(self.session)
        linhas = linha_repository.list_by_modelo(modelo_id)
        operacoes = sum(
            len(operacao_repository.list_by_linha(linha.id)) for linha in linhas
        )
        return DefValuesetModeloConteudoResumo(
            modelo=modelo,
            linhas=len(linhas),
            operacoes=operacoes,
        )

    def listar_destinos_globais_para_substituicao(
        self, *, excluir_modelo_id: int | None = None
    ) -> list[DefValuesetModeloConteudoResumo]:
        """List global targets, including inactive ones, with impact counts."""
        return [
            self.resumir_conteudo_modelo(modelo.id)
            for modelo in self.repository.list_all()
            if self._e_global(modelo) and modelo.id != excluir_modelo_id
        ]

    def criar_modelo(self, data: CriarDefValuesetModeloData) -> DefValuesetModeloResumo:
        """Create one reusable ValueSet model."""
        fields = self._build_fields(data)
        self._validate_codigo_unico(fields["codigo"], exclude_id=None)

        result = self.repository.create(**fields)
        self.session.commit()

        return result

    def editar_modelo(
        self, id: int, data: EditarDefValuesetModeloData
    ) -> DefValuesetModeloResumo:
        """Edit one reusable ValueSet model."""
        fields = self._build_fields(data)
        self._validate_codigo_unico(fields["codigo"], exclude_id=id)

        result = self.repository.update(id=id, **fields)
        self.session.commit()

        return result

    def duplicar_modelo(
        self, original_id: int, dados_novos: CriarDefValuesetModeloData
    ) -> DuplicarDefValuesetModeloResult:
        """Create a new model with ``dados_novos`` and copy all original lines."""
        original = self.repository.get_by_id(original_id)
        if original is None:
            raise ValueError("modelo not found")

        novo_modelo = self.criar_modelo(dados_novos)
        linha_service = DefValuesetModeloLinhaService(self.session)
        operacao_service = DefValuesetModeloLinhaOperacaoService(self.session)
        linhas = linha_service.listar_linhas_do_modelo(original_id)

        for linha in linhas:
            nova_linha = linha_service.criar_linha(
                CriarDefValuesetModeloLinhaData(
                    def_valueset_modelo_id=novo_modelo.id,
                    chave=linha.chave,
                    codigo_opcao=linha.codigo_opcao,
                    nome_opcao=linha.nome_opcao,
                    padrao=linha.padrao,
                    prioridade=linha.prioridade,
                    ordem=linha.ordem,
                    descricao=linha.descricao,
                    materia_prima_id=linha.materia_prima_id,
                    ref_materia_prima=linha.ref_materia_prima,
                    descricao_materia_prima=linha.descricao_materia_prima,
                    valor_texto=linha.valor_texto,
                    origem=linha.origem,
                    ref_le=linha.ref_le,
                    descricao_no_orcamento=linha.descricao_no_orcamento,
                    preco_tabela=linha.preco_tabela,
                    margem_percentagem=linha.margem_percentagem,
                    desconto_percentagem=linha.desconto_percentagem,
                    preco_liquido=linha.preco_liquido,
                    unidade=linha.unidade,
                    desperdicio_percentagem=linha.desperdicio_percentagem,
                    tipo_materia_prima=linha.tipo_materia_prima,
                    familia_materia_prima=linha.familia_materia_prima,
                    coresp_orla_0_4=linha.coresp_orla_0_4,
                    coresp_orla_1_0=linha.coresp_orla_1_0,
                    preco_orla_0_4_m2=getattr(linha, "preco_orla_0_4_m2", None),
                    preco_orla_1_0_m2=getattr(linha, "preco_orla_1_0_m2", None),
                    comp_mp=linha.comp_mp,
                    larg_mp=linha.larg_mp,
                    esp_mp=linha.esp_mp,
                    origem_dados=linha.origem_dados,
                    editado_localmente=linha.editado_localmente,
                    ativo=linha.ativo,
                    observacoes=linha.observacoes,
                )
            )
            for operacao in operacao_service.listar_operacoes_da_linha(linha.id):
                operacao_service.adicionar_operacao_a_linha(
                    CriarDefValuesetModeloLinhaOperacaoData(
                        def_valueset_modelo_linha_id=nova_linha.id,
                        def_operacao_id=operacao.def_operacao_id,
                        ordem=operacao.ordem,
                        acao=getattr(operacao, "acao", None),
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

        return DuplicarDefValuesetModeloResult(
            modelo=novo_modelo,
            linhas_copiadas=len(linhas),
        )

    def substituir_modelo_global(
        self,
        original_id: int,
        destino_id: int,
        dados_novos: CriarDefValuesetModeloData,
        *,
        autorizado: bool,
    ) -> SubstituirDefValuesetModeloResult:
        """Replace one explicitly selected global target in one transaction.

        The target id and code remain stable because budgets can already reference
        that library entry and model codes are globally unique. All descriptive
        header fields, lines, material snapshots and operations come from the
        source model/form.
        """
        if not autorizado:
            raise PermissionError(
                "É necessária permissão administrativa para substituir modelos globais."
            )
        if original_id == destino_id:
            raise ValueError("origem e destino nao podem ser o mesmo modelo")

        original = self.repository.get_by_id(original_id)
        destino = self.repository.get_by_id(destino_id)
        if original is None or destino is None:
            raise ValueError("modelo not found")
        if not self._e_global(destino):
            raise ValueError("destino nao e global")

        linha_repository = DefValuesetModeloLinhaRepository(self.session)
        operacao_repository = DefValuesetModeloLinhaOperacaoRepository(self.session)
        linhas_origem = linha_repository.list_by_modelo(original_id)
        operacoes_origem = {
            linha.id: operacao_repository.list_by_linha(linha.id)
            for linha in linhas_origem
        }
        linhas_destino = linha_repository.list_by_modelo(destino_id)
        operacoes_removidas = sum(
            len(operacao_repository.list_by_linha(linha.id))
            for linha in linhas_destino
        )

        try:
            ids_linhas_destino = select(DefValuesetModeloLinha.id).where(
                DefValuesetModeloLinha.def_valueset_modelo_id == destino_id
            )
            self.session.execute(
                delete(DefValuesetModeloLinhaOperacao).where(
                    DefValuesetModeloLinhaOperacao.def_valueset_modelo_linha_id.in_(
                        ids_linhas_destino
                    )
                )
            )
            self.session.execute(
                delete(DefValuesetModeloLinha).where(
                    DefValuesetModeloLinha.def_valueset_modelo_id == destino_id
                )
            )

            fields = self._build_fields(dados_novos)
            fields.update(
                codigo=destino.codigo,
                ambito="GLOBAL",
                user_id=None,
                visivel_para_todos=True,
            )
            modelo_atualizado = self.repository.update(id=destino_id, **fields)

            operacoes_copiadas = 0
            for linha in linhas_origem:
                nova_linha = linha_repository.create(
                    **self._campos_linha_copiada(linha, destino_id)
                )
                for operacao in operacoes_origem[linha.id]:
                    operacao_repository.create(
                        **self._campos_operacao_copiada(operacao, nova_linha.id)
                    )
                    operacoes_copiadas += 1

            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return SubstituirDefValuesetModeloResult(
            modelo=modelo_atualizado,
            linhas_removidas=len(linhas_destino),
            operacoes_removidas=operacoes_removidas,
            linhas_copiadas=len(linhas_origem),
            operacoes_copiadas=operacoes_copiadas,
        )

    @staticmethod
    def _campos_linha_copiada(linha, destino_id: int) -> dict:
        return {
            "def_valueset_modelo_id": destino_id,
            "chave": linha.chave,
            "codigo_opcao": linha.codigo_opcao,
            "nome_opcao": linha.nome_opcao,
            "padrao": linha.padrao,
            "prioridade": linha.prioridade,
            "ordem": linha.ordem,
            "descricao": linha.descricao,
            "materia_prima_id": linha.materia_prima_id,
            "ref_materia_prima": linha.ref_materia_prima,
            "descricao_materia_prima": linha.descricao_materia_prima,
            "valor_texto": linha.valor_texto,
            "origem": linha.origem,
            "ref_le": linha.ref_le,
            "descricao_no_orcamento": linha.descricao_no_orcamento,
            "preco_tabela": linha.preco_tabela,
            "margem_percentagem": linha.margem_percentagem,
            "desconto_percentagem": linha.desconto_percentagem,
            "preco_liquido": linha.preco_liquido,
            "unidade": linha.unidade,
            "desperdicio_percentagem": linha.desperdicio_percentagem,
            "tipo_materia_prima": linha.tipo_materia_prima,
            "familia_materia_prima": linha.familia_materia_prima,
            "coresp_orla_0_4": linha.coresp_orla_0_4,
            "coresp_orla_1_0": linha.coresp_orla_1_0,
            "preco_orla_0_4_m2": linha.preco_orla_0_4_m2,
            "preco_orla_1_0_m2": linha.preco_orla_1_0_m2,
            "comp_mp": linha.comp_mp,
            "larg_mp": linha.larg_mp,
            "esp_mp": linha.esp_mp,
            "origem_dados": linha.origem_dados,
            "editado_localmente": linha.editado_localmente,
            "ativo": linha.ativo,
            "observacoes": linha.observacoes,
        }

    @staticmethod
    def _campos_operacao_copiada(operacao, nova_linha_id: int) -> dict:
        return {
            "def_valueset_modelo_linha_id": nova_linha_id,
            "def_operacao_id": operacao.def_operacao_id,
            "ordem": operacao.ordem,
            "acao": operacao.acao,
            "metodo_calculo": operacao.metodo_calculo,
            "regra_calculo": operacao.regra_calculo,
            "quantidade_base": operacao.quantidade_base,
            "rasgo_qt_comp": operacao.rasgo_qt_comp,
            "rasgo_qt_larg": operacao.rasgo_qt_larg,
            "tempo_setup_minutos": operacao.tempo_setup_minutos,
            "tempo_por_unidade_minutos": operacao.tempo_por_unidade_minutos,
            "unidade_tempo": operacao.unidade_tempo,
            "obrigatorio": operacao.obrigatorio,
            "ativo": operacao.ativo,
            "observacoes": operacao.observacoes,
        }

    def desativar_modelo(self, id: int) -> bool:
        """Deactivate one reusable ValueSet model."""
        deactivated = self.repository.deactivate(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_modelo(self, id: int) -> bool:
        """Reactivate one reusable ValueSet model."""
        activated = self.repository.activate(id)
        if activated:
            self.session.commit()

        return activated

    def _build_fields(self, data) -> dict:
        codigo = self._normalize_codigo(data.codigo)
        nome = self._normalize_required_text(data.nome, "nome")

        return {
            "codigo": codigo,
            "nome": nome,
            "descricao": data.descricao,
            "tipo": self._normalize_optional_text(data.tipo),
            "ambito": self._normalize_ambito(data.ambito),
            "user_id": data.user_id,
            "visivel_para_todos": data.visivel_para_todos,
            "ativo": data.ativo,
            "observacoes": data.observacoes,
        }

    def _normalize_codigo(self, codigo: str | None) -> str:
        normalized = (codigo or "").strip().upper()
        if not normalized:
            raise ValueError("codigo is required")

        return "_".join(normalized.split())

    def _normalize_ambito(self, ambito: str | None) -> str:
        normalized = (ambito or "").strip().upper()
        return normalized or "UTILIZADOR"

    def _normalize_required_text(self, value: str | None, field_name: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} is required")

        return normalized

    def _normalize_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    def _validate_codigo_unico(self, codigo: str, exclude_id: int | None) -> None:
        existing = self.repository.get_by_codigo(codigo)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("codigo ja existe")
