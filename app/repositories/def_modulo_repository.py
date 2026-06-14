"""Repository for the reusable module/article library (phase 8U.0)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import DefModulo, DefModuloLinha


@dataclass(frozen=True)
class DefModuloResumo:
    """Read model for a reusable module (header)."""

    id: int
    codigo: str
    nome: str
    descricao: str | None
    ambito: str
    user_id: int | None
    categoria: str
    imagem_path: str | None
    ativo: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class DefModuloLinhaResumo:
    """Read model for one structural line of a module."""

    id: int
    def_modulo_id: int
    ordem: int
    tipo_linha: str
    def_peca_id: int | None
    def_peca_codigo: str | None
    codigo: str | None
    descricao: str | None
    descricao_livre: str | None
    qt_mod: str | None
    qt_und: str | None
    comp: str | None
    larg: str | None
    esp: str | None
    chave_valueset: str | None
    codigo_orlas: str | None
    def_regra_quantidade_id: int | None
    linha_pai_ordem: int | None
    nivel: int
    ativo: bool


class DefModuloRepository:
    """Repository for DefModulo / DefModuloLinha operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ----- Module header -----

    def list_active(self) -> list[DefModuloResumo]:
        """List active modules, ordered by category then code."""
        statement = (
            select(DefModulo)
            .where(DefModulo.ativo.is_(True))
            .order_by(
                DefModulo.categoria.asc(),
                DefModulo.codigo.asc(),
                DefModulo.id.asc(),
            )
        )
        modulos = self.session.execute(statement).scalars().all()

        return [self._to_modulo_resumo(modulo) for modulo in modulos]

    def get_by_id(self, id: int) -> DefModuloResumo | None:
        """Get one module by id."""
        modulo = self.session.get(DefModulo, id)
        if modulo is None:
            return None

        return self._to_modulo_resumo(modulo)

    def get_by_codigo(self, codigo: str) -> DefModuloResumo | None:
        """Get one module by its (unique) code."""
        statement = select(DefModulo).where(DefModulo.codigo == codigo)
        modulo = self.session.execute(statement).scalars().first()
        if modulo is None:
            return None

        return self._to_modulo_resumo(modulo)

    def create_modulo(
        self,
        *,
        codigo: str,
        nome: str,
        descricao: str | None = None,
        ambito: str = "UTILIZADOR",
        user_id: int | None = None,
        categoria: str = "OUTROS",
        imagem_path: str | None = None,
        ativo: bool = True,
    ) -> DefModuloResumo:
        """Create one module header."""
        modulo = DefModulo(
            codigo=codigo,
            nome=nome,
            descricao=descricao,
            ambito=ambito,
            user_id=user_id,
            categoria=categoria,
            imagem_path=imagem_path,
            ativo=ativo,
        )
        self.session.add(modulo)
        self.session.flush()

        return self._to_modulo_resumo(modulo)

    def update_cabecalho(
        self,
        *,
        id: int,
        nome: str,
        descricao: str | None,
        ambito: str,
        user_id: int | None,
        categoria: str,
        imagem_path: str | None,
    ) -> DefModuloResumo:
        """Update one module's header (the code is fixed)."""
        modulo = self.session.get(DefModulo, id)
        if modulo is None:
            raise ValueError("def_modulo not found")

        modulo.nome = nome
        modulo.descricao = descricao
        modulo.ambito = ambito
        modulo.user_id = user_id
        modulo.categoria = categoria
        modulo.imagem_path = imagem_path
        self.session.flush()

        return self._to_modulo_resumo(modulo)

    def delete_modulo(self, id: int) -> bool:
        """Delete one module and all its lines (explicit cascade)."""
        modulo = self.session.get(DefModulo, id)
        if modulo is None:
            return False

        # Delete the lines first so it works regardless of DB FK enforcement
        # (SQLite does not cascade by default).
        self.session.execute(
            delete(DefModuloLinha).where(DefModuloLinha.def_modulo_id == id)
        )
        self.session.delete(modulo)
        self.session.flush()

        return True

    # ----- Module lines -----

    def contar_linhas_por_modulo(self) -> dict[int, int]:
        """Return a map of module id -> number of lines (for the listing)."""
        statement = select(
            DefModuloLinha.def_modulo_id, func.count(DefModuloLinha.id)
        ).group_by(DefModuloLinha.def_modulo_id)

        return {
            modulo_id: total
            for modulo_id, total in self.session.execute(statement).all()
        }

    def list_linhas(self, def_modulo_id: int) -> list[DefModuloLinhaResumo]:
        """List a module's lines, ordered by ordem then id."""
        statement = (
            select(DefModuloLinha)
            .where(DefModuloLinha.def_modulo_id == def_modulo_id)
            .order_by(DefModuloLinha.ordem.asc(), DefModuloLinha.id.asc())
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_linha_resumo(linha) for linha in linhas]

    def create_linha(self, **fields) -> DefModuloLinhaResumo:
        """Create one module line."""
        linha = DefModuloLinha(**fields)
        self.session.add(linha)
        self.session.flush()

        return self._to_linha_resumo(linha)

    def delete_linhas_do_modulo(self, def_modulo_id: int) -> int:
        """Delete every line of a module; returns how many were removed."""
        result = self.session.execute(
            delete(DefModuloLinha).where(
                DefModuloLinha.def_modulo_id == def_modulo_id
            )
        )
        self.session.flush()

        return result.rowcount or 0

    # ----- Mapping -----

    def _to_modulo_resumo(self, modulo: DefModulo) -> DefModuloResumo:
        return DefModuloResumo(
            id=modulo.id,
            codigo=modulo.codigo,
            nome=modulo.nome,
            descricao=modulo.descricao,
            ambito=modulo.ambito,
            user_id=modulo.user_id,
            categoria=modulo.categoria,
            imagem_path=modulo.imagem_path,
            ativo=modulo.ativo,
            created_at=modulo.created_at,
            updated_at=modulo.updated_at,
        )

    def _to_linha_resumo(self, linha: DefModuloLinha) -> DefModuloLinhaResumo:
        return DefModuloLinhaResumo(
            id=linha.id,
            def_modulo_id=linha.def_modulo_id,
            ordem=linha.ordem,
            tipo_linha=linha.tipo_linha,
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
