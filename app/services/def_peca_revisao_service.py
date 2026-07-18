"""Versioned catalog-piece workflows.

A revision is a new catalog row. Existing costing rows are never rewritten:
they keep their frozen snapshots and references to the definition used when
the quote was calculated.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DefPeca, DefPecaComponente, DefPecaOperacao


@dataclass(frozen=True)
class CriarRevisaoPecaResult:
    peca_anterior_id: int
    nova_peca_id: int
    codigo: str
    revisao_serie: str
    revisao_numero: int
    operacoes_copiadas: int
    componentes_copiados: int


@dataclass(frozen=True)
class PrepararRevisaoPecaResult:
    peca_id: int
    codigo_atual: str
    revisao_atual: int
    proxima_revisao: int
    codigo_sugerido: str
    operacoes_a_copiar: int
    componentes_a_copiar: int


class DefPecaRevisaoService:
    """Create immutable-successor revisions of technical catalog pieces."""

    _CAMPOS_PECA = (
        "nome",
        "nome_biblioteca",
        "descricao",
        "grupo",
        "tipo_peca",
        "natureza",
        "orientacao",
        "funcao",
        "formula_comp",
        "formula_larg",
        "formula_esp",
        "orla_c1",
        "orla_c2",
        "orla_l1",
        "orla_l2",
        "chave_valueset_material",
        "permite_acabamento",
        "chave_valueset_acabamento_sup",
        "chave_valueset_acabamento_inf",
        "sem_material",
    )

    def __init__(self, session: Session) -> None:
        self.session = session

    def preparar_revisao(self, peca_id: int) -> PrepararRevisaoPecaResult:
        """Describe the exact effect of creating the next revision."""
        original = self._obter_ultima_revisao(peca_id)
        proxima_revisao = original.revisao_numero + 1
        return PrepararRevisaoPecaResult(
            peca_id=original.id,
            codigo_atual=original.codigo,
            revisao_atual=original.revisao_numero,
            proxima_revisao=proxima_revisao,
            codigo_sugerido=self._codigo_sugerido(original, proxima_revisao),
            operacoes_a_copiar=len(original.operacoes),
            componentes_a_copiar=len(original.componentes),
        )

    def criar_revisao(
        self,
        peca_id: int,
        *,
        novo_codigo: str | None = None,
        novo_nome: str | None = None,
    ) -> CriarRevisaoPecaResult:
        """Clone a complete piece and deactivate its immediately previous revision."""
        original = self._obter_ultima_revisao(peca_id)

        proxima_revisao = original.revisao_numero + 1
        codigo = (novo_codigo or self._codigo_sugerido(original, proxima_revisao)).strip()
        if not codigo:
            raise ValueError("O código da nova revisão é obrigatório.")
        if self.session.scalar(select(DefPeca.id).where(DefPeca.codigo == codigo)) is not None:
            raise ValueError(f"Já existe uma peça com o código {codigo}.")

        dados = {campo: getattr(original, campo) for campo in self._CAMPOS_PECA}
        if novo_nome is not None:
            dados["nome"] = novo_nome.strip()
            if not dados["nome"]:
                raise ValueError("O nome da nova revisão é obrigatório.")

        nova = DefPeca(
            codigo=codigo,
            revisao_serie=original.revisao_serie,
            revisao_numero=proxima_revisao,
            revisao_anterior_id=original.id,
            ativo=True,
            **dados,
        )
        self.session.add(nova)
        self.session.flush()

        operacoes = list(original.operacoes)
        for operacao in operacoes:
            self.session.add(
                DefPecaOperacao(
                    def_peca_id=nova.id,
                    **self._copiar_colunas(
                        operacao, excluir={"id", "def_peca_id", "created_at", "updated_at"}
                    ),
                )
            )

        componentes = list(original.componentes)
        for componente in componentes:
            self.session.add(
                DefPecaComponente(
                    def_peca_pai_id=nova.id,
                    **self._copiar_colunas(
                        componente,
                        excluir={"id", "def_peca_pai_id", "created_at", "updated_at"},
                    ),
                )
            )

        original.ativo = False
        self.session.commit()
        return CriarRevisaoPecaResult(
            peca_anterior_id=original.id,
            nova_peca_id=nova.id,
            codigo=nova.codigo,
            revisao_serie=nova.revisao_serie,
            revisao_numero=nova.revisao_numero,
            operacoes_copiadas=len(operacoes),
            componentes_copiados=len(componentes),
        )

    def listar_revisoes(self, peca_id: int) -> list[DefPeca]:
        peca = self.session.get(DefPeca, peca_id)
        if peca is None:
            return []
        return list(
            self.session.scalars(
                select(DefPeca)
                .where(DefPeca.revisao_serie == peca.revisao_serie)
                .order_by(DefPeca.revisao_numero.asc())
            )
        )

    def _obter_ultima_revisao(self, peca_id: int) -> DefPeca:
        original = self.session.get(DefPeca, peca_id)
        if original is None:
            raise ValueError("Peça não encontrada.")
        ultima_revisao = self.session.scalar(
            select(func.max(DefPeca.revisao_numero)).where(
                DefPeca.revisao_serie == original.revisao_serie
            )
        )
        if int(ultima_revisao or 1) != original.revisao_numero:
            raise ValueError(
                "Só é possível criar uma revisão a partir da revisão mais recente."
            )
        return original

    def _codigo_sugerido(self, original: DefPeca, revisao: int) -> str:
        primeira = self.session.scalar(
            select(DefPeca)
            .where(DefPeca.revisao_serie == original.revisao_serie)
            .order_by(DefPeca.revisao_numero.asc())
            .limit(1)
        )
        codigo_base = primeira.codigo if primeira is not None else original.codigo
        return f"{codigo_base}_R{revisao}"

    @staticmethod
    def _copiar_colunas(registo, *, excluir: set[str]) -> dict[str, object]:
        return {
            coluna.name: getattr(registo, coluna.name)
            for coluna in registo.__table__.columns
            if coluna.name not in excluir
        }
