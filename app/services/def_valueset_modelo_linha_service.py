"""Service for reusable ValueSet model line workflows."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.valueset_precos import calcular_preco_liquido
from app.domain.valueset_opcoes import base_codigo_opcao
from app.domain.valueset_types import normalize_valueset_key
from app.repositories.def_valueset_modelo_linha_repository import (
    DefValuesetModeloLinhaRepository,
    DefValuesetModeloLinhaResumo,
)


@dataclass(frozen=True)
class CriarDefValuesetModeloLinhaData:
    """Input data for creating one reusable ValueSet model line."""

    def_valueset_modelo_id: int | None
    chave: str
    codigo_opcao: str | None = None
    nome_opcao: str | None = None
    padrao: bool = False
    prioridade: int | None = None
    ordem: int = 1
    descricao: str | None = None
    materia_prima_id: int | None = None
    ref_materia_prima: str | None = None
    descricao_materia_prima: str | None = None
    valor_texto: str | None = None
    origem: str | None = None
    ref_le: str | None = None
    descricao_no_orcamento: str | None = None
    preco_tabela: Decimal | None = None
    margem_percentagem: Decimal | None = None
    desconto_percentagem: Decimal | None = None
    preco_liquido: Decimal | None = None
    unidade: str | None = None
    desperdicio_percentagem: Decimal | None = None
    tipo_materia_prima: str | None = None
    familia_materia_prima: str | None = None
    coresp_orla_0_4: str | None = None
    coresp_orla_1_0: str | None = None
    preco_orla_0_4_m2: Decimal | None = None
    preco_orla_1_0_m2: Decimal | None = None
    comp_mp: Decimal | None = None
    larg_mp: Decimal | None = None
    esp_mp: Decimal | None = None
    origem_dados: str | None = None
    editado_localmente: bool = False
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarDefValuesetModeloLinhaData:
    """Input data for editing one reusable ValueSet model line."""

    def_valueset_modelo_id: int | None
    chave: str
    codigo_opcao: str | None = None
    nome_opcao: str | None = None
    padrao: bool = False
    prioridade: int | None = None
    ordem: int = 1
    descricao: str | None = None
    materia_prima_id: int | None = None
    ref_materia_prima: str | None = None
    descricao_materia_prima: str | None = None
    valor_texto: str | None = None
    origem: str | None = None
    ref_le: str | None = None
    descricao_no_orcamento: str | None = None
    preco_tabela: Decimal | None = None
    margem_percentagem: Decimal | None = None
    desconto_percentagem: Decimal | None = None
    preco_liquido: Decimal | None = None
    unidade: str | None = None
    desperdicio_percentagem: Decimal | None = None
    tipo_materia_prima: str | None = None
    familia_materia_prima: str | None = None
    coresp_orla_0_4: str | None = None
    coresp_orla_1_0: str | None = None
    preco_orla_0_4_m2: Decimal | None = None
    preco_orla_1_0_m2: Decimal | None = None
    comp_mp: Decimal | None = None
    larg_mp: Decimal | None = None
    esp_mp: Decimal | None = None
    origem_dados: str | None = None
    editado_localmente: bool = False
    ativo: bool = True
    observacoes: str | None = None


class DefValuesetModeloLinhaService:
    """Application service for reusable ValueSet model lines."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefValuesetModeloLinhaRepository(session)

    def listar_linhas(self) -> list[DefValuesetModeloLinhaResumo]:
        """List all reusable ValueSet model lines."""
        return self.repository.list_all()

    def listar_linhas_ativas(self) -> list[DefValuesetModeloLinhaResumo]:
        """List active reusable ValueSet model lines."""
        return self.repository.list_active()

    def listar_linhas_do_modelo(
        self, modelo_id: int
    ) -> list[DefValuesetModeloLinhaResumo]:
        """List lines of one reusable ValueSet model."""
        return self.repository.list_by_modelo(modelo_id)

    def listar_por_chave(
        self, modelo_id: int, chave: str
    ) -> list[DefValuesetModeloLinhaResumo]:
        """List all options of one model and key."""
        return self.repository.list_by_modelo_chave(
            modelo_id, normalize_valueset_key(chave)
        )

    def obter_padrao_por_chave(
        self, modelo_id: int, chave: str
    ) -> DefValuesetModeloLinhaResumo | None:
        """Get the winning active option of one model and key (best priority)."""
        return self.repository.get_default_by_modelo_chave(
            modelo_id, normalize_valueset_key(chave)
        )

    def obter_por_id(self, id: int) -> DefValuesetModeloLinhaResumo | None:
        """Get one reusable ValueSet model line by id."""
        return self.repository.get_by_id(id)

    def criar_linha(
        self, data: CriarDefValuesetModeloLinhaData
    ) -> DefValuesetModeloLinhaResumo:
        """Create one reusable ValueSet model line, at the end of the list."""
        fields = self._build_fields(data)
        self._validate_opcao_unica(
            modelo_id=fields["def_valueset_modelo_id"],
            chave=fields["chave"],
            codigo_opcao=fields["codigo_opcao"],
            exclude_id=None,
        )
        if data.ordem is None:
            # A linha nova vai para o fim: nunca desarruma o que ja foi
            # organizado com as setas.
            fields["ordem"] = self.repository.proxima_ordem(
                fields["def_valueset_modelo_id"]
            )

        result = self.repository.create(**fields)
        self.session.commit()

        return result

    def editar_linha(
        self, id: int, data: EditarDefValuesetModeloLinhaData
    ) -> DefValuesetModeloLinhaResumo:
        """Edit one reusable ValueSet model line."""
        existing = self.repository.get_by_id(id)
        if existing is None:
            raise ValueError("linha nao encontrada")

        # The technical identity is immutable from the friendly-name dialog.
        fields = self._build_fields(data, codigo_opcao_original=existing.codigo_opcao)
        self._validate_opcao_unica(
            modelo_id=fields["def_valueset_modelo_id"],
            chave=fields["chave"],
            codigo_opcao=fields["codigo_opcao"],
            exclude_id=id,
        )

        result = self.repository.update(id=id, **fields)
        self.session.commit()

        return result

    def mover_linhas(
        self,
        modelo_id: int,
        linha_ids: Iterable[int],
        *,
        para_cima: bool,
        ids_visiveis: Iterable[int] | None = None,
    ) -> bool:
        """Move the given lines one position up/down. True if anything moved.

        The selected lines travel together, keeping their relative order, and
        stop when they reach the end of the list. ``ids_visiveis`` restricts the
        movement to the lines the user is actually seeing (inactive ones may be
        hidden), so a line never swaps with a neighbour that is off screen. The
        whole list is renumbered 1..N afterwards, so the positions stay clean
        whatever numbers the lines had before (repeated, with gaps, ...).
        """
        linhas = self.repository.list_by_modelo(modelo_id)
        ids = [linha.id for linha in linhas]
        selecionados = {linha_id for linha_id in linha_ids if linha_id in ids}
        if not selecionados:
            return False

        visiveis = set(ids_visiveis) if ids_visiveis is not None else set(ids)
        # Posições, na lista completa, das linhas que estão à vista: é entre
        # elas que a troca acontece.
        posicoes = [indice for indice, id_ in enumerate(ids) if id_ in visiveis]
        sequencia = [ids[indice] for indice in posicoes]

        indices = [
            indice for indice, id_ in enumerate(sequencia) if id_ in selecionados
        ]
        if not para_cima:
            indices.reverse()

        movido = False
        for indice in indices:
            destino = indice - 1 if para_cima else indice + 1
            if destino < 0 or destino >= len(sequencia):
                continue
            if sequencia[destino] in selecionados:
                continue  # bloco encostado a outra linha selecionada
            sequencia[indice], sequencia[destino] = (
                sequencia[destino],
                sequencia[indice],
            )
            movido = True

        if not movido:
            return False

        for posicao, id_ in zip(posicoes, sequencia, strict=True):
            ids[posicao] = id_
        self.repository.reordenar_linhas(ids)
        self.session.commit()

        return True

    def agrupar_linhas_por_chave(self, modelo_id: int) -> int:
        """Rearrange every line of one model by key. Returns lines renumbered.

        The safety net for the arrows: it puts the list back into the
        alphabetical arrangement by key, best priority first inside each key.
        """
        linhas = sorted(
            self.repository.list_by_modelo(modelo_id),
            key=lambda linha: (
                linha.chave,
                linha.prioridade is None,
                linha.prioridade or 0,
                linha.id,
            ),
        )
        if not linhas:
            return 0

        self.repository.reordenar_linhas([linha.id for linha in linhas])
        self.session.commit()

        return len(linhas)

    def desativar_linha(self, id: int) -> bool:
        """Deactivate one reusable ValueSet model line."""
        deactivated = self.repository.deactivate(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_linha(self, id: int) -> bool:
        """Reactivate one reusable ValueSet model line."""
        activated = self.repository.activate(id)
        if activated:
            self.session.commit()

        return activated

    def definir_como_padrao(self, id: int) -> bool:
        """Make one line the default option of its key, clearing the others."""
        linha = self.repository.get_by_id(id)
        if linha is None:
            return False

        self.repository.clear_padrao_for_chave(
            linha.def_valueset_modelo_id, linha.chave, exclude_id=id
        )
        self.repository.set_padrao(id, True)
        self.session.commit()

        return True

    def atualizar_precos_linhas(
        self, atualizacoes: Iterable[tuple[int, Decimal | None, Decimal | None]]
    ) -> int:
        """Update only table and liquid prices for the given model lines."""
        atualizadas = 0
        for linha_id, preco_tabela_novo, preco_liquido_novo in atualizacoes:
            self.repository.update(
                id=linha_id,
                preco_tabela=preco_tabela_novo,
                preco_liquido=preco_liquido_novo,
            )
            atualizadas += 1

        self.session.commit()
        return atualizadas

    def _build_fields(self, data, *, codigo_opcao_original: str | None = None) -> dict:
        modelo_id = self._validate_required_id(
            data.def_valueset_modelo_id, "def_valueset_modelo_id"
        )
        chave = self._normalize_required_chave(data.chave)
        preco_liquido = self._compute_preco_liquido(
            data.preco_tabela,
            data.margem_percentagem,
            data.desconto_percentagem,
            data.preco_liquido,
        )

        codigo_opcao = self._resolver_codigo_opcao(
            data,
            chave=chave,
            codigo_opcao_original=codigo_opcao_original,
            modelo_id=modelo_id,
        )

        return {
            "def_valueset_modelo_id": modelo_id,
            "chave": chave,
            "codigo_opcao": codigo_opcao,
            "nome_opcao": self._normalize_nome_opcao(data.nome_opcao),
            "padrao": data.padrao,
            "prioridade": self._normalize_prioridade(data.prioridade),
            "ordem": self._normalize_ordem(data.ordem),
            "descricao": data.descricao,
            "materia_prima_id": data.materia_prima_id,
            "ref_materia_prima": data.ref_materia_prima,
            "descricao_materia_prima": data.descricao_materia_prima,
            "valor_texto": data.valor_texto,
            "origem": data.origem,
            "ref_le": data.ref_le,
            "descricao_no_orcamento": data.descricao_no_orcamento,
            "preco_tabela": data.preco_tabela,
            "margem_percentagem": data.margem_percentagem,
            "desconto_percentagem": data.desconto_percentagem,
            "preco_liquido": preco_liquido,
            "unidade": data.unidade,
            "desperdicio_percentagem": data.desperdicio_percentagem,
            "tipo_materia_prima": data.tipo_materia_prima,
            "familia_materia_prima": data.familia_materia_prima,
            "coresp_orla_0_4": data.coresp_orla_0_4,
            "coresp_orla_1_0": data.coresp_orla_1_0,
            "preco_orla_0_4_m2": data.preco_orla_0_4_m2,
            "preco_orla_1_0_m2": data.preco_orla_1_0_m2,
            "comp_mp": data.comp_mp,
            "larg_mp": data.larg_mp,
            "esp_mp": data.esp_mp,
            "origem_dados": data.origem_dados,
            "editado_localmente": data.editado_localmente,
            "ativo": data.ativo,
            "observacoes": data.observacoes,
        }

    def _compute_preco_liquido(
        self,
        preco_tabela: Decimal | None,
        margem: Decimal | None,
        desconto: Decimal | None,
        preco_liquido: Decimal | None,
    ) -> Decimal | None:
        """Compute preco_liquido from table price, discount and margin.

        preco_liquido = preco_tabela * (1 - desconto/100) * (1 + margem/100).

        When a table price exists, preco_liquido is always recomputed from the
        (human) margin and discount percentages, treating empty values as 0.
        When there is no table price, the provided preco_liquido is kept.
        """
        if preco_tabela is None:
            return preco_liquido

        return calcular_preco_liquido(preco_tabela, margem, desconto)

    def _validate_required_id(self, value: int | None, field_name: str) -> int:
        if not value:
            raise ValueError(f"{field_name} is required")

        return value

    def _normalize_required_chave(self, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("chave is required")

        return normalize_valueset_key(value)

    def _normalize_codigo_opcao(self, codigo_opcao: str | None, chave: str) -> str:
        if codigo_opcao is None or not codigo_opcao.strip():
            return chave
        return codigo_opcao.strip().upper()

    def _normalize_nome_opcao(self, nome_opcao: str | None) -> str | None:
        texto = (nome_opcao or "").strip()
        return texto or None

    def _resolver_codigo_opcao(
        self,
        data,
        *,
        chave: str,
        codigo_opcao_original: str | None,
        modelo_id: int,
    ) -> str:
        if codigo_opcao_original:
            return codigo_opcao_original

        codigo_interno = (data.codigo_opcao or "").strip()
        if codigo_interno:
            return self._normalize_codigo_opcao(codigo_interno, chave)

        base = base_codigo_opcao(
            chave=chave,
            nome_opcao=data.nome_opcao,
            ref_le=data.ref_le,
            ref_materia_prima=data.ref_materia_prima,
        )
        return self._codigo_disponivel(modelo_id, chave, base)

    def _codigo_disponivel(self, modelo_id: int, chave: str, base: str) -> str:
        candidato = base
        sufixo = 2
        while self.repository.get_by_modelo_chave_opcao(modelo_id, chave, candidato):
            separador = f"_{sufixo}"
            candidato = f"{base[:100 - len(separador)]}{separador}"
            sufixo += 1
        return candidato

    def _normalize_ordem(self, ordem: int | None) -> int:
        if ordem is None:
            return 1

        return ordem

    def _normalize_prioridade(self, prioridade: int | None) -> int | None:
        if prioridade is None:
            return None
        if prioridade < 1:
            raise ValueError("prioridade deve ser um inteiro >= 1")

        return prioridade

    def _validate_opcao_unica(
        self, modelo_id: int, chave: str, codigo_opcao: str, exclude_id: int | None
    ) -> None:
        existing = self.repository.get_by_modelo_chave_opcao(modelo_id, chave, codigo_opcao)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("opcao ja existe nesta chave deste modelo")
