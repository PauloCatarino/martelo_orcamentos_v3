"""Leituras e escritas dos componentes de uma matéria-prima composta."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain.materia_prima_types import (
    PAPEL_PRINCIPAL,
    PAPEL_SECUNDARIO,
    normalizar_ref_fornecedor,
)
from app.models import DefMateriaPrima, DefMateriaPrimaComponente

_UM = Decimal("1")


@dataclass(frozen=True)
class ComponenteResumo:
    """Um componente pronto a mostrar, sem a sessão atrás."""

    id: int
    materia_prima_id: int
    papel: str
    descricao: str | None
    quantidade: Decimal
    nome_imos: str | None
    ref_phc: str | None
    ref_fornecedor: str | None
    ref_fornecedor_norm: str | None
    componente_materia_prima_id: int | None
    preco_liquido: Decimal | None
    ordem: int
    ativo: bool
    observacoes: str | None = None

    @property
    def principal(self) -> bool:
        return self.papel == PAPEL_PRINCIPAL


@dataclass(frozen=True)
class ComponenteDados:
    """O que o ecrã manda gravar para um componente."""

    papel: str = PAPEL_SECUNDARIO
    descricao: str | None = None
    quantidade: Decimal = _UM
    nome_imos: str | None = None
    ref_phc: str | None = None
    ref_fornecedor: str | None = None
    componente_materia_prima_id: int | None = None
    preco_liquido: Decimal | None = None
    #: 0 quer dizer "poe na fila" -- o servico atribui a proxima ordem livre.
    ordem: int = 0
    ativo: bool = True
    observacoes: str | None = None


def _texto(valor: str | None) -> str | None:
    limpo = (valor or "").strip()
    return limpo or None


def _resumo(linha: DefMateriaPrimaComponente) -> ComponenteResumo:
    return ComponenteResumo(
        id=linha.id,
        materia_prima_id=linha.materia_prima_id,
        papel=linha.papel,
        descricao=linha.descricao,
        quantidade=linha.quantidade if linha.quantidade is not None else _UM,
        nome_imos=linha.nome_imos,
        ref_phc=linha.ref_phc,
        ref_fornecedor=linha.ref_fornecedor,
        ref_fornecedor_norm=linha.ref_fornecedor_norm,
        componente_materia_prima_id=linha.componente_materia_prima_id,
        preco_liquido=linha.preco_liquido,
        ordem=linha.ordem,
        ativo=linha.ativo,
        observacoes=linha.observacoes,
    )


class DefMateriaPrimaComponenteRepository:
    """Os componentes de uma matéria-prima, e a busca pelas três chaves."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ----- leituras -----

    def listar(self, materia_prima_id: int) -> list[ComponenteResumo]:
        """Os componentes de um conjunto, pela ordem em que se mostram."""
        linhas = self.session.scalars(
            select(DefMateriaPrimaComponente)
            .where(DefMateriaPrimaComponente.materia_prima_id == materia_prima_id)
            .order_by(
                DefMateriaPrimaComponente.ordem,
                DefMateriaPrimaComponente.id,
            )
        ).all()
        return [_resumo(linha) for linha in linhas]

    def obter(self, componente_id: int) -> ComponenteResumo | None:
        linha = self.session.get(DefMateriaPrimaComponente, componente_id)
        return _resumo(linha) if linha is not None else None

    def procurar_principal(
        self,
        *,
        nome_imos: str | None = None,
        ref_phc: str | None = None,
        ref_fornecedor: str | None = None,
        excluir_id: int | None = None,
    ) -> ComponenteResumo | None:
        """O componente PRINCIPAL que já reclama alguma destas chaves.

        É esta pergunta que impede a mesma referência de ser principal em dois
        conjuntos — aí a contagem de uma obra ficava ambígua e ninguém saberia
        qual dos conjuntos tinha razão.
        """
        condicoes = []
        if _texto(nome_imos):
            condicoes.append(DefMateriaPrimaComponente.nome_imos == _texto(nome_imos))
        if _texto(ref_phc):
            condicoes.append(DefMateriaPrimaComponente.ref_phc == _texto(ref_phc))
        norm = normalizar_ref_fornecedor(ref_fornecedor)
        if norm:
            condicoes.append(DefMateriaPrimaComponente.ref_fornecedor_norm == norm)
        if not condicoes:
            return None

        consulta = (
            select(DefMateriaPrimaComponente)
            .where(DefMateriaPrimaComponente.papel == PAPEL_PRINCIPAL)
            .where(DefMateriaPrimaComponente.ativo.is_(True))
            .where(or_(*condicoes))
        )
        if excluir_id is not None:
            consulta = consulta.where(DefMateriaPrimaComponente.id != excluir_id)

        linha = self.session.scalars(consulta.limit(1)).first()
        return _resumo(linha) if linha is not None else None

    def ref_le_do_conjunto(self, materia_prima_id: int) -> str | None:
        """A referência do conjunto, para as mensagens de erro dizerem onde é."""
        materia = self.session.get(DefMateriaPrima, materia_prima_id)
        if materia is None:
            return None
        return materia.ref_le or materia.descricao

    def proxima_ordem(self, materia_prima_id: int) -> int:
        atuais = self.listar(materia_prima_id)
        return max((c.ordem for c in atuais), default=0) + 1

    # ----- escritas -----

    def criar(
        self,
        materia_prima_id: int,
        dados: ComponenteDados,
        *,
        user_id: int | None = None,
    ) -> ComponenteResumo:
        linha = DefMateriaPrimaComponente(
            materia_prima_id=materia_prima_id,
            criado_por_id=user_id,
            alterado_por_id=user_id,
        )
        self._aplicar(linha, dados)
        self.session.add(linha)
        self.session.flush()
        return _resumo(linha)

    def atualizar(
        self,
        componente_id: int,
        dados: ComponenteDados,
        *,
        user_id: int | None = None,
    ) -> ComponenteResumo:
        linha = self.session.get(DefMateriaPrimaComponente, componente_id)
        if linha is None:
            raise ValueError("componente não encontrado")
        self._aplicar(linha, dados)
        if user_id is not None:
            linha.alterado_por_id = user_id
        self.session.flush()
        return _resumo(linha)

    def eliminar(self, componente_id: int) -> bool:
        linha = self.session.get(DefMateriaPrimaComponente, componente_id)
        if linha is None:
            return False
        self.session.delete(linha)
        self.session.flush()
        return True

    def _aplicar(self, linha: DefMateriaPrimaComponente, dados: ComponenteDados) -> None:
        linha.papel = dados.papel
        linha.descricao = _texto(dados.descricao)
        linha.quantidade = dados.quantidade if dados.quantidade is not None else _UM
        linha.nome_imos = _texto(dados.nome_imos)
        linha.ref_phc = _texto(dados.ref_phc)
        linha.ref_fornecedor = _texto(dados.ref_fornecedor)
        # A normalizada é derivada, nunca escrita à mão: assim as duas nunca
        # discordam e a procura é sempre pela mesma regra.
        linha.ref_fornecedor_norm = normalizar_ref_fornecedor(dados.ref_fornecedor)
        linha.componente_materia_prima_id = dados.componente_materia_prima_id
        linha.preco_liquido = dados.preco_liquido
        linha.ordem = dados.ordem
        linha.ativo = dados.ativo
        linha.observacoes = _texto(dados.observacoes)
