"""Service for machine catalog workflows."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import DefMaquina
from app.repositories.def_maquina_repository import DefMaquinaRepository, DefMaquinaResumo

#: Tamanho da coluna ``def_maquinas.nomes_streamlit``.
TAMANHO_NOMES_STREAMLIT = 255


def chave_nome_streamlit(nome: str | None) -> str:
    """«HKL 300», «hkl300» e «HKL-300» são a mesma máquina: só letras e algarismos."""
    sem_acentos = unicodedata.normalize("NFD", str(nome or "").casefold())
    return "".join(c for c in sem_acentos if c.isalnum() and not unicodedata.combining(c))


def separar_nomes_streamlit(texto: str | None) -> list[str]:
    """Os nomes escritos no campo, pela ordem, sem repetidos nem vazios."""
    nomes: list[str] = []
    vistos: set[str] = set()
    for parte in re.split(r"[,;\n]+", str(texto or "")):
        nome = " ".join(parte.split())
        chave = chave_nome_streamlit(nome)
        if chave and chave not in vistos:
            vistos.add(chave)
            nomes.append(nome)
    return nomes


def normalizar_nomes_streamlit(texto: str | None) -> str | None:
    return ", ".join(separar_nomes_streamlit(texto)) or None


@dataclass(frozen=True)
class CriarDefMaquinaData:
    """Input data for creating a machine."""

    codigo: str
    nome: str
    descricao: str | None = None
    tipo: str | None = None
    custo_hora: Decimal | None = None
    custo_hora_serie: Decimal | None = None
    preco_ml_std: Decimal | None = None
    preco_ml_serie: Decimal | None = None
    permite_rasgos: bool = False
    preco_rasgo_ml_std: Decimal | None = None
    preco_rasgo_ml_serie: Decimal | None = None
    preco_lado_curto_std: Decimal | None = None
    preco_lado_curto_serie: Decimal | None = None
    preco_lado_longo_std: Decimal | None = None
    preco_lado_longo_serie: Decimal | None = None
    limite_lado_mm: Decimal | None = None
    custo_setup_peca_std: Decimal | None = None
    custo_setup_peca_serie: Decimal | None = None
    permite_furacao: bool = False
    permite_pocket: bool = False
    permite_escaloes_area: bool = False
    preco_furo_std: Decimal | None = None
    preco_furo_serie: Decimal | None = None
    preco_m2_face_std: Decimal | None = None
    preco_m2_face_serie: Decimal | None = None
    ativo: bool = True
    observacoes: str | None = None
    nomes_streamlit: str | None = None


@dataclass(frozen=True)
class EditarDefMaquinaData:
    """Input data for editing a machine."""

    codigo: str
    nome: str
    descricao: str | None = None
    tipo: str | None = None
    custo_hora: Decimal | None = None
    custo_hora_serie: Decimal | None = None
    preco_ml_std: Decimal | None = None
    preco_ml_serie: Decimal | None = None
    permite_rasgos: bool = False
    preco_rasgo_ml_std: Decimal | None = None
    preco_rasgo_ml_serie: Decimal | None = None
    preco_lado_curto_std: Decimal | None = None
    preco_lado_curto_serie: Decimal | None = None
    preco_lado_longo_std: Decimal | None = None
    preco_lado_longo_serie: Decimal | None = None
    limite_lado_mm: Decimal | None = None
    custo_setup_peca_std: Decimal | None = None
    custo_setup_peca_serie: Decimal | None = None
    permite_furacao: bool = False
    permite_pocket: bool = False
    permite_escaloes_area: bool = False
    preco_furo_std: Decimal | None = None
    preco_furo_serie: Decimal | None = None
    preco_m2_face_std: Decimal | None = None
    preco_m2_face_serie: Decimal | None = None
    ativo: bool = True
    observacoes: str | None = None
    nomes_streamlit: str | None = None


class DefMaquinaService:
    """Application service for DefMaquina workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefMaquinaRepository(session)

    def listar_maquinas(self) -> list[DefMaquinaResumo]:
        """List all machines."""
        return self.repository.list_all()

    def listar_maquinas_ativas(self) -> list[DefMaquinaResumo]:
        """List active machines."""
        return self.repository.list_active()

    def obter_por_id(self, id: int) -> DefMaquinaResumo | None:
        """Get one machine by id."""
        return self.repository.get_by_id(id)

    def obter_por_codigo(self, codigo: str | None) -> DefMaquinaResumo | None:
        """Get one machine by code."""
        normalized = self._normalize_codigo(codigo, required=False)
        if normalized is None:
            return None

        return self.repository.get_by_codigo(normalized)

    def criar_maquina(self, data: CriarDefMaquinaData) -> DefMaquinaResumo:
        """Create a machine."""
        codigo = self._normalize_codigo(data.codigo)
        nome = self._normalize_required_text(data.nome, "nome")
        self._validate_codigo_unico(codigo, exclude_id=None)

        result = self.repository.create_maquina(
            codigo=codigo,
            nome=nome,
            descricao=data.descricao,
            tipo=self._normalize_optional_text(data.tipo),
            custo_hora=data.custo_hora,
            custo_hora_serie=data.custo_hora_serie,
            preco_ml_std=data.preco_ml_std,
            preco_ml_serie=data.preco_ml_serie,
            permite_rasgos=data.permite_rasgos,
            preco_rasgo_ml_std=data.preco_rasgo_ml_std,
            preco_rasgo_ml_serie=data.preco_rasgo_ml_serie,
            preco_lado_curto_std=data.preco_lado_curto_std,
            preco_lado_curto_serie=data.preco_lado_curto_serie,
            preco_lado_longo_std=data.preco_lado_longo_std,
            preco_lado_longo_serie=data.preco_lado_longo_serie,
            limite_lado_mm=data.limite_lado_mm,
            custo_setup_peca_std=data.custo_setup_peca_std,
            custo_setup_peca_serie=data.custo_setup_peca_serie,
            permite_furacao=data.permite_furacao,
            permite_pocket=data.permite_pocket,
            permite_escaloes_area=data.permite_escaloes_area,
            preco_furo_std=data.preco_furo_std,
            preco_furo_serie=data.preco_furo_serie,
            preco_m2_face_std=data.preco_m2_face_std,
            preco_m2_face_serie=data.preco_m2_face_serie,
            ativo=data.ativo,
            observacoes=data.observacoes,
            nomes_streamlit=normalizar_nomes_streamlit(data.nomes_streamlit),
        )
        self.session.commit()

        return result

    def editar_maquina(self, id: int, data: EditarDefMaquinaData) -> DefMaquinaResumo:
        """Edit a machine."""
        codigo = self._normalize_codigo(data.codigo)
        nome = self._normalize_required_text(data.nome, "nome")
        self._validate_codigo_unico(codigo, exclude_id=id)

        result = self.repository.update_maquina(
            id=id,
            codigo=codigo,
            nome=nome,
            descricao=data.descricao,
            tipo=self._normalize_optional_text(data.tipo),
            custo_hora=data.custo_hora,
            custo_hora_serie=data.custo_hora_serie,
            preco_ml_std=data.preco_ml_std,
            preco_ml_serie=data.preco_ml_serie,
            permite_rasgos=data.permite_rasgos,
            preco_rasgo_ml_std=data.preco_rasgo_ml_std,
            preco_rasgo_ml_serie=data.preco_rasgo_ml_serie,
            preco_lado_curto_std=data.preco_lado_curto_std,
            preco_lado_curto_serie=data.preco_lado_curto_serie,
            preco_lado_longo_std=data.preco_lado_longo_std,
            preco_lado_longo_serie=data.preco_lado_longo_serie,
            limite_lado_mm=data.limite_lado_mm,
            custo_setup_peca_std=data.custo_setup_peca_std,
            custo_setup_peca_serie=data.custo_setup_peca_serie,
            permite_furacao=data.permite_furacao,
            permite_pocket=data.permite_pocket,
            permite_escaloes_area=data.permite_escaloes_area,
            preco_furo_std=data.preco_furo_std,
            preco_furo_serie=data.preco_furo_serie,
            preco_m2_face_std=data.preco_m2_face_std,
            preco_m2_face_serie=data.preco_m2_face_serie,
            ativo=data.ativo,
            observacoes=data.observacoes,
            nomes_streamlit=normalizar_nomes_streamlit(data.nomes_streamlit),
        )
        self.session.commit()

        return result

    def desativar_maquina(self, id: int) -> bool:
        """Deactivate a machine."""
        deactivated = self.repository.deactivate_maquina(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_maquina(self, id: int) -> bool:
        """Reactivate a machine."""
        activated = self.repository.activate_maquina(id)
        if activated:
            self.session.commit()

        return activated

    def memorizar_nome_streamlit(self, id: int, nome: str) -> list[str]:
        """Ligar um nome do Streamlit a esta máquina, para as obras seguintes.

        Um nome só serve uma máquina: se outra o tinha, perde-o (a escolha mais
        recente ganha). Devolve os códigos das máquinas a que foi tirado.
        """
        chave = chave_nome_streamlit(nome)
        maquina = self.session.get(DefMaquina, id)
        if maquina is None or not chave:
            raise ValueError("Máquina ou nome do Streamlit em falta.")
        retirado_de: list[str] = []
        for outra in self.session.query(DefMaquina).filter(DefMaquina.id != id):
            nomes = separar_nomes_streamlit(outra.nomes_streamlit)
            restantes = [n for n in nomes if chave_nome_streamlit(n) != chave]
            if len(restantes) != len(nomes):
                outra.nomes_streamlit = ", ".join(restantes) or None
                retirado_de.append(outra.codigo)
        nomes = separar_nomes_streamlit(maquina.nomes_streamlit)
        if all(chave_nome_streamlit(n) != chave for n in nomes):
            nomes.append(" ".join(str(nome).split()))
        texto = ", ".join(nomes)
        if len(texto) > TAMANHO_NOMES_STREAMLIT:
            self.session.rollback()
            raise ValueError(
                f"A máquina {maquina.codigo} já tem nomes do Streamlit a mais: limpe-os em "
                "Configurações › Operações / Máquinas antes de juntar outro."
            )
        maquina.nomes_streamlit = texto
        self.session.commit()
        return retirado_de

    def _normalize_codigo(self, codigo: str | None, required: bool = True) -> str | None:
        normalized = (codigo or "").strip().upper()
        if not normalized and required:
            raise ValueError("codigo is required")

        return normalized or None

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
