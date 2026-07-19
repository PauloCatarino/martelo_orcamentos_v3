"""Read-only resolution of legacy Martelo V2 budget folders."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.domain.export_paths import encontrar_pasta_orcamento, simplificar_cliente
from app.services.system_setting_service import SystemSettingService
from app.services.v2_arquivo_service import OrcamentoV2Resumo


def resolver_pasta_orcamento_v2(
    session: Session, item: OrcamentoV2Resumo
) -> Path | None:
    """Return an existing V2 folder without creating or changing anything.

    Follows the V2 lookup convention ``base/ano/numero_SIMPLEX/versao`` and
    falls back to an existing folder whose name starts with ``numero_``.
    """
    base = SystemSettingService(session).obter_valor("pasta_base_orcamentos")
    ano = ano_do_orcamento_v2(item)
    if not base or ano is None or not item.numero:
        return None

    ano_dir = Path(base) / str(ano)
    if not ano_dir.is_dir():
        return None

    simplex = simplificar_cliente(item.cliente, item.cliente)
    esperada = ano_dir / f"{item.numero}_{simplex}"
    pasta_orcamento = esperada if esperada.is_dir() else encontrar_pasta_orcamento(
        ano_dir, item.numero
    )
    if pasta_orcamento is None:
        return None

    for versao in _nomes_versao(item.versao):
        candidata = pasta_orcamento / versao
        if candidata.is_dir():
            return candidata
    return pasta_orcamento


def ano_do_orcamento_v2(item: OrcamentoV2Resumo) -> int | None:
    """Determine the legacy folder year from its date, then budget number."""
    if isinstance(item.data, (date, datetime)):
        return item.data.year

    match = re.search(r"(?:19|20)\d{2}", str(item.data or ""))
    if match:
        return int(match.group())

    prefixo = str(item.numero or "").strip()[:2]
    return 2000 + int(prefixo) if prefixo.isdigit() else None


def _nomes_versao(versao: str) -> tuple[str, ...]:
    texto = str(versao or "").strip()
    if not texto:
        return ()
    if texto.isdigit():
        normalizada = f"{int(texto):02d}"
        return (normalizada, texto) if normalizada != texto else (texto,)
    return (texto,)
