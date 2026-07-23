"""Saved filter views for the production list, per user.

Uma "vista" é uma combinação de pesquisa + filtros com nome, guardada em
``system_settings`` tal como as colunas da tabela.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json

from sqlalchemy.orm import Session

from app.services.system_setting_service import SystemSettingService


#: Máximo de vistas guardadas por utilizador.
MAX_VISTAS = 20


@dataclass(frozen=True)
class VistaProducao:
    """One named combination of search text and filters."""

    nome: str
    texto: str = ""
    estado: str = "Todos"
    cliente: str = "Todos"
    responsavel: str = "Todos"
    so_atrasadas: bool = False

    def como_dict(self) -> dict:
        return {
            "nome": self.nome,
            "texto": self.texto,
            "estado": self.estado,
            "cliente": self.cliente,
            "responsavel": self.responsavel,
            "so_atrasadas": self.so_atrasadas,
        }


def chave_vistas(user_id: object) -> str:
    """Return the per-user system-setting key for saved views."""
    return f"producao_vistas:{user_id or 'default'}"


def serializar_vistas(vistas) -> str:
    """Serialize saved views to JSON."""
    return json.dumps(
        [vista.como_dict() for vista in vistas],
        ensure_ascii=False,
    )


def desserializar_vistas(texto: str | None) -> list[VistaProducao]:
    """Deserialize saved views, ignoring anything malformed."""
    if not texto:
        return []

    try:
        payload = json.loads(texto)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []

    vistas: list[VistaProducao] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        nome = str(item.get("nome") or "").strip()
        if not nome:
            continue
        vistas.append(
            VistaProducao(
                nome=nome,
                texto=str(item.get("texto") or ""),
                estado=str(item.get("estado") or "Todos"),
                cliente=str(item.get("cliente") or "Todos"),
                responsavel=str(item.get("responsavel") or "Todos"),
                so_atrasadas=bool(item.get("so_atrasadas")),
            )
        )
    return vistas[:MAX_VISTAS]


def substituir_vista(vistas, nova: VistaProducao) -> list[VistaProducao]:
    """Add or replace one view by name (case-insensitive), keeping order."""
    alvo = nova.nome.strip().lower()
    resultado = [
        vista for vista in vistas if vista.nome.strip().lower() != alvo
    ]
    resultado.append(replace(nova, nome=nova.nome.strip()))
    return resultado[:MAX_VISTAS]


def remover_vista(vistas, nome: str) -> list[VistaProducao]:
    """Remove one view by name (case-insensitive)."""
    alvo = (nome or "").strip().lower()
    return [vista for vista in vistas if vista.nome.strip().lower() != alvo]


def carregar_vistas(session: Session, user_id: object) -> list[VistaProducao]:
    """Load the saved views of one user."""
    valor = SystemSettingService(session).obter_valor(chave_vistas(user_id), None)
    return desserializar_vistas(valor)


def guardar_vistas(session: Session, user_id: object, vistas) -> None:
    """Save the views of one user."""
    SystemSettingService(session).guardar_valor(
        chave_vistas(user_id),
        serializar_vistas(vistas),
    )
