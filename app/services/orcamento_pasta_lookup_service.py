"""Read-only lookup of a budget folder from its year/number/version.

Used by the production page: with ``Nº Orçamento`` and ``V. Orç`` filled, the
user can jump straight to the budget folder. Nothing is created or renamed.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.domain.export_paths import encontrar_pasta_orcamento, subpasta_versao
from app.services.system_setting_service import SystemSettingService


def resolver_pasta_orcamento(
    session: Session,
    *,
    ano: object,
    num_orcamento: object,
    versao_orc: object = None,
) -> Path | None:
    """Return the existing budget folder, or None when it cannot be found.

    Follows ``base/ano/{numero}_*`` and, when a version is given and its
    subfolder exists, returns that subfolder instead of the parent.
    """
    numero = _texto(num_orcamento)
    ano_texto = _texto(ano)
    if not numero or not ano_texto:
        return None

    base = SystemSettingService(session).obter_valor("pasta_base_orcamentos")
    if not base:
        return None

    try:
        ano_dir = Path(base) / ano_texto
        if not ano_dir.is_dir():
            return None
        pasta = encontrar_pasta_orcamento(ano_dir, numero)
    except OSError:
        return None

    if pasta is None:
        return None

    versao = _nome_versao(versao_orc)
    if versao:
        try:
            candidata = pasta / versao
            if candidata.is_dir():
                return candidata
        except OSError:
            pass

    return pasta


def _texto(valor: object) -> str:
    return "" if valor is None else str(valor).strip()


def _nome_versao(versao: object) -> str:
    texto = _texto(versao)
    if not texto:
        return ""
    try:
        return subpasta_versao(int(texto))
    except (TypeError, ValueError):
        return texto
