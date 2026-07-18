"""Service for the manageable module-library categories (phase 6).

Single-level categories (a customer name is a valid category). Modules
reference a category by its ``codigo``; archiving hides a category from the
pickers without touching modules, deleting is only allowed when no module
uses it. OUTROS is the protected fallback and can never be archived/deleted.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.modulo_categorias import (
    MODULO_CATEGORIA_LABELS,
    OUTROS,
    get_modulo_categoria_label,
    normalize_modulo_categoria,
)
from app.models import DefModulo, DefModuloCategoria


@dataclass(frozen=True)
class ModuloCategoriaResumo:
    """Read model of one module category (or subcategory)."""

    id: int
    codigo: str
    nome: str
    ativo: bool
    modulos_em_uso: int = 0
    parent_id: int | None = None
    parent_nome: str | None = None


class DefModuloCategoriaService:
    """Application service for the module-library categories."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ----- reads -----

    def listar(self, incluir_arquivadas: bool = True) -> list[ModuloCategoriaResumo]:
        """List categories/subcategories with per-node module usage counts.

        Top-level categories count modules referencing them via ``categoria``;
        subcategories count modules referencing them via ``subcategoria``.
        """
        self.garantir_seed()
        contagens_categoria = dict(
            self.session.execute(
                select(DefModulo.categoria, func.count(DefModulo.id)).group_by(
                    DefModulo.categoria
                )
            ).all()
        )
        contagens_subcategoria = dict(
            self.session.execute(
                select(DefModulo.subcategoria, func.count(DefModulo.id)).group_by(
                    DefModulo.subcategoria
                )
            ).all()
        )
        statement = select(DefModuloCategoria).order_by(DefModuloCategoria.nome.asc())
        if not incluir_arquivadas:
            statement = statement.where(DefModuloCategoria.ativo.is_(True))
        categorias = list(self.session.execute(statement).scalars())
        nomes_por_id = {c.id: c.nome for c in categorias}
        return [
            ModuloCategoriaResumo(
                id=categoria.id,
                codigo=categoria.codigo,
                nome=categoria.nome,
                ativo=categoria.ativo,
                modulos_em_uso=int(
                    (contagens_categoria if categoria.parent_id is None
                     else contagens_subcategoria).get(categoria.codigo, 0)
                ),
                parent_id=categoria.parent_id,
                parent_nome=nomes_por_id.get(categoria.parent_id),
            )
            for categoria in categorias
        ]

    def listar_arvore(
        self, incluir_arquivadas: bool = True
    ) -> list[tuple[ModuloCategoriaResumo, list[ModuloCategoriaResumo]]]:
        """Return [(categoria_topo, [subcategorias...]), ...] for tree views."""
        todas = self.listar(incluir_arquivadas)
        filhos: dict[int, list[ModuloCategoriaResumo]] = {}
        for categoria in todas:
            if categoria.parent_id is not None:
                filhos.setdefault(categoria.parent_id, []).append(categoria)
        return [
            (categoria, filhos.get(categoria.id, []))
            for categoria in todas
            if categoria.parent_id is None
        ]

    def listar_opcoes(self) -> tuple[tuple[str, str], ...]:
        """Return the ACTIVE top-level categories as (codigo, nome) pairs.

        Subcategories are intentionally excluded here so the existing pickers
        (library filter, save/import module dialogs) keep behaving as before.
        """
        return tuple(
            (categoria.codigo, categoria.nome)
            for categoria in self.listar(incluir_arquivadas=False)
            if categoria.parent_id is None
        )

    def labels(self) -> dict[str, str]:
        """Return {codigo: nome} for every category (including archived)."""
        self.garantir_seed()
        return dict(
            self.session.execute(
                select(DefModuloCategoria.codigo, DefModuloCategoria.nome)
            ).all()
        )

    # ----- writes -----

    def criar(
        self,
        nome: str,
        codigo: str | None = None,
        parent_id: int | None = None,
    ) -> ModuloCategoriaResumo:
        """Create a category (or a subcategory when ``parent_id`` is given).

        The code defaults to the slug of the name and is globally unique.
        Subcategories are limited to a single level: the parent must itself be
        a top-level category.
        """
        nome_limpo = (nome or "").strip()
        if not nome_limpo:
            raise ValueError("O nome da categoria é obrigatório.")
        codigo_limpo = normalize_modulo_categoria(codigo or nome_limpo)

        if parent_id is not None:
            parent = self._get(parent_id)
            if parent.parent_id is not None:
                raise ValueError(
                    "Só é possível criar subcategorias dentro de categorias de "
                    "topo (apenas um nível)."
                )

        existente = self._get_por_codigo(codigo_limpo)
        if existente is not None:
            raise ValueError(
                f"Já existe uma categoria com o código {codigo_limpo}."
            )

        categoria = DefModuloCategoria(
            codigo=codigo_limpo, nome=nome_limpo, ativo=True, parent_id=parent_id
        )
        self.session.add(categoria)
        self.session.commit()
        return self._resumo(categoria)

    def renomear(self, categoria_id: int, nome: str) -> ModuloCategoriaResumo:
        """Rename a category (the code stays stable; modules are untouched)."""
        categoria = self._get(categoria_id)
        nome_limpo = (nome or "").strip()
        if not nome_limpo:
            raise ValueError("O nome da categoria é obrigatório.")
        categoria.nome = nome_limpo
        self.session.commit()
        return self._resumo(categoria)

    def arquivar(self, categoria_id: int) -> ModuloCategoriaResumo:
        """Archive a category: leaves the pickers, old modules keep it."""
        categoria = self._get(categoria_id)
        if categoria.codigo == OUTROS:
            raise ValueError(
                "A categoria Outros é a categoria de recurso e não pode ser arquivada."
            )
        categoria.ativo = False
        self.session.commit()
        return self._resumo(categoria)

    def reativar(self, categoria_id: int) -> ModuloCategoriaResumo:
        """Bring an archived category back to the pickers."""
        categoria = self._get(categoria_id)
        categoria.ativo = True
        self.session.commit()
        return self._resumo(categoria)

    def eliminar(self, categoria_id: int) -> bool:
        """Delete a category/subcategory only when nothing depends on it."""
        categoria = self._get(categoria_id)
        if categoria.codigo == OUTROS:
            raise ValueError(
                "A categoria Outros é a categoria de recurso e não pode ser eliminada."
            )
        if categoria.parent_id is None and self._tem_subcategorias(categoria.id):
            raise ValueError(
                f"A categoria {categoria.nome} tem subcategorias. Elimine ou "
                "arquive as subcategorias primeiro."
            )
        em_uso = self._modulos_em_uso_por(categoria)
        if em_uso:
            raise ValueError(
                f"A categoria {categoria.nome} está em uso por {em_uso} módulo(s). "
                "Mova esses módulos para outra categoria ou arquive-a."
            )
        self.session.delete(categoria)
        self.session.commit()
        return True

    def garantir_seed(self) -> None:
        """Ensure the seeded categories exist (idempotent; no commit needed
        beyond the inserts themselves — safe on databases created before the
        migration ran and on in-memory test databases)."""
        existentes = set(
            self.session.execute(select(DefModuloCategoria.codigo)).scalars()
        )
        criadas = False
        for codigo, nome in MODULO_CATEGORIA_LABELS.items():
            if codigo not in existentes:
                self.session.add(
                    DefModuloCategoria(codigo=codigo, nome=nome, ativo=True)
                )
                criadas = True
        # Import legacy codes still used by modules (kept out of the seed).
        usados = set(
            self.session.execute(select(DefModulo.categoria).distinct()).scalars()
        )
        for codigo in usados:
            codigo_norm = normalize_modulo_categoria(codigo)
            if codigo_norm not in existentes and codigo_norm not in MODULO_CATEGORIA_LABELS:
                self.session.add(
                    DefModuloCategoria(
                        codigo=codigo_norm,
                        nome=get_modulo_categoria_label(codigo_norm),
                        ativo=True,
                    )
                )
                existentes.add(codigo_norm)
                criadas = True
        if criadas:
            self.session.flush()

    # ----- helpers -----

    def _get(self, categoria_id: int) -> DefModuloCategoria:
        categoria = self.session.get(DefModuloCategoria, categoria_id)
        if categoria is None:
            raise ValueError("Categoria não encontrada.")
        return categoria

    def _get_por_codigo(self, codigo: str) -> DefModuloCategoria | None:
        return self.session.execute(
            select(DefModuloCategoria).where(DefModuloCategoria.codigo == codigo)
        ).scalars().first()

    def _tem_subcategorias(self, categoria_id: int) -> bool:
        return bool(
            self.session.execute(
                select(func.count(DefModuloCategoria.id)).where(
                    DefModuloCategoria.parent_id == categoria_id
                )
            ).scalar_one()
        )

    def _modulos_em_uso_por(self, categoria: DefModuloCategoria) -> int:
        coluna = (
            DefModulo.categoria if categoria.parent_id is None
            else DefModulo.subcategoria
        )
        return int(
            self.session.execute(
                select(func.count(DefModulo.id)).where(coluna == categoria.codigo)
            ).scalar_one()
        )

    def _resumo(self, categoria: DefModuloCategoria) -> ModuloCategoriaResumo:
        parent_nome = None
        if categoria.parent_id is not None:
            parent = self.session.get(DefModuloCategoria, categoria.parent_id)
            parent_nome = parent.nome if parent is not None else None
        return ModuloCategoriaResumo(
            id=categoria.id,
            codigo=categoria.codigo,
            nome=categoria.nome,
            ativo=categoria.ativo,
            modulos_em_uso=self._modulos_em_uso_por(categoria),
            parent_id=categoria.parent_id,
            parent_nome=parent_nome,
        )
