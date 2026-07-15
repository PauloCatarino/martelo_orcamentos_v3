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
    """Read model of one module category."""

    id: int
    codigo: str
    nome: str
    ativo: bool
    modulos_em_uso: int = 0


class DefModuloCategoriaService:
    """Application service for the module-library categories."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ----- reads -----

    def listar(self, incluir_arquivadas: bool = True) -> list[ModuloCategoriaResumo]:
        """List categories with per-category module usage counts."""
        self.garantir_seed()
        contagens = dict(
            self.session.execute(
                select(DefModulo.categoria, func.count(DefModulo.id)).group_by(
                    DefModulo.categoria
                )
            ).all()
        )
        statement = select(DefModuloCategoria).order_by(DefModuloCategoria.nome.asc())
        if not incluir_arquivadas:
            statement = statement.where(DefModuloCategoria.ativo.is_(True))
        return [
            ModuloCategoriaResumo(
                id=categoria.id,
                codigo=categoria.codigo,
                nome=categoria.nome,
                ativo=categoria.ativo,
                modulos_em_uso=int(contagens.get(categoria.codigo, 0)),
            )
            for categoria in self.session.execute(statement).scalars()
        ]

    def listar_opcoes(self) -> tuple[tuple[str, str], ...]:
        """Return the ACTIVE categories as (codigo, nome) pairs for pickers."""
        return tuple(
            (categoria.codigo, categoria.nome)
            for categoria in self.listar(incluir_arquivadas=False)
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

    def criar(self, nome: str, codigo: str | None = None) -> ModuloCategoriaResumo:
        """Create a category; the code defaults to the slug of the name."""
        nome_limpo = (nome or "").strip()
        if not nome_limpo:
            raise ValueError("O nome da categoria é obrigatório.")
        codigo_limpo = normalize_modulo_categoria(codigo or nome_limpo)

        existente = self._get_por_codigo(codigo_limpo)
        if existente is not None:
            raise ValueError(
                f"Já existe uma categoria com o código {codigo_limpo}."
            )

        categoria = DefModuloCategoria(
            codigo=codigo_limpo, nome=nome_limpo, ativo=True
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
        """Delete a category only when no module uses it (safe delete)."""
        categoria = self._get(categoria_id)
        if categoria.codigo == OUTROS:
            raise ValueError(
                "A categoria Outros é a categoria de recurso e não pode ser eliminada."
            )
        em_uso = self._modulos_em_uso(categoria.codigo)
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

    def _modulos_em_uso(self, codigo: str) -> int:
        return int(
            self.session.execute(
                select(func.count(DefModulo.id)).where(
                    DefModulo.categoria == codigo
                )
            ).scalar_one()
        )

    def _resumo(self, categoria: DefModuloCategoria) -> ModuloCategoriaResumo:
        return ModuloCategoriaResumo(
            id=categoria.id,
            codigo=categoria.codigo,
            nome=categoria.nome,
            ativo=categoria.ativo,
            modulos_em_uso=self._modulos_em_uso(categoria.codigo),
        )
