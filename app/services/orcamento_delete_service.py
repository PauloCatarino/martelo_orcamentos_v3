"""Delete workflows for budget versions and their server folders."""

from __future__ import annotations

from pathlib import Path
import shutil

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models import (
    Orcamento,
    OrcamentoItem,
    OrcamentoItemCusteioLinha,
    OrcamentoItemModulo,
    OrcamentoItemValuesetLinha,
    OrcamentoItemVariavel,
    OrcamentoValuesetLinha,
    OrcamentoVersao,
    OrcamentoVersaoEvento,
    OrcamentoVersaoPlacaNaoStock,
    Producao,
)
from app.services.orcamento_export_service import OrcamentoExportService
from app.services.system_setting_service import SystemSettingService


PRODUCAO_LIGADA_MSG = (
    "Este or\u00e7amento est\u00e1 ligado a uma obra de Produ\u00e7\u00e3o; n\u00e3o \u00e9 "
    "poss\u00edvel elimin\u00e1-lo (nem nenhuma vers\u00e3o). Desligue ou elimine a "
    "Produ\u00e7\u00e3o primeiro."
)


def contar_versoes(session: Session, orcamento_id: int) -> int:
    """Return how many versions one budget has."""
    return int(
        session.scalar(
            select(func.count())
            .select_from(OrcamentoVersao)
            .where(OrcamentoVersao.orcamento_id == orcamento_id)
        )
        or 0
    )


def tem_producao_ligada(session: Session, orcamento_id: int) -> bool:
    """Return whether any production process still points at the budget."""
    return (
        session.scalar(
            select(func.count())
            .select_from(Producao)
            .where(Producao.orcamento_id == orcamento_id)
        )
        or 0
    ) > 0


def eliminar_versao_completo(
    session: Session,
    *,
    orcamento_versao_id: int,
    apagar_registo: bool,
    apagar_pasta: bool,
) -> None:
    """Delete a budget version folder and/or DB record."""
    if not apagar_registo and not apagar_pasta:
        raise ValueError("Escolha o registo, a pasta, ou ambos para eliminar.")

    versao = session.get(OrcamentoVersao, orcamento_versao_id)
    if versao is None:
        raise ValueError("Vers\u00e3o de or\u00e7amento n\u00e3o encontrada.")

    orcamento_id = versao.orcamento_id
    remove_orcamento = contar_versoes(session, orcamento_id) == 1

    if tem_producao_ligada(session, orcamento_id):
        raise ValueError(PRODUCAO_LIGADA_MSG)

    if apagar_pasta:
        export = OrcamentoExportService(session)
        if remove_orcamento:
            caminho = export.pasta_orcamento_atual(orcamento_versao_id)
        else:
            caminho = export.resolver_pasta_versao(orcamento_versao_id, criar=False)
        if caminho is not None and caminho.exists():
            _remover_pasta_orcamento_segura(
                session,
                caminho,
                nome_esperado=caminho.name,
            )

    if apagar_registo:
        _eliminar_registo_versao(session, versao, remove_orcamento=remove_orcamento)

    session.commit()


def _eliminar_registo_versao(
    session: Session,
    versao: OrcamentoVersao,
    *,
    remove_orcamento: bool,
) -> None:
    orcamento_versao_id = versao.id
    orcamento_id = versao.orcamento_id
    item_ids = list(
        session.scalars(
            select(OrcamentoItem.id).where(
                OrcamentoItem.orcamento_versao_id == orcamento_versao_id
            )
        )
    )

    if item_ids:
        session.execute(
            update(OrcamentoItemCusteioLinha)
            .where(OrcamentoItemCusteioLinha.orcamento_item_id.in_(item_ids))
            .values(linha_pai_id=None)
        )
        session.execute(
            delete(OrcamentoItemCusteioLinha).where(
                OrcamentoItemCusteioLinha.orcamento_item_id.in_(item_ids)
            )
        )
        session.execute(
            delete(OrcamentoItemValuesetLinha).where(
                OrcamentoItemValuesetLinha.orcamento_item_id.in_(item_ids)
            )
        )
        session.execute(
            delete(OrcamentoItemVariavel).where(
                OrcamentoItemVariavel.item_id.in_(item_ids)
            )
        )
        session.execute(
            delete(OrcamentoItemModulo).where(
                OrcamentoItemModulo.orcamento_item_id.in_(item_ids)
            )
        )
        session.execute(
            delete(OrcamentoItem).where(
                OrcamentoItem.orcamento_versao_id == orcamento_versao_id
            )
        )

    valueset_ids = select(OrcamentoValuesetLinha.id).where(
        OrcamentoValuesetLinha.orcamento_versao_id == orcamento_versao_id
    )
    session.execute(
        update(OrcamentoItemValuesetLinha)
        .where(
            OrcamentoItemValuesetLinha.origem_orcamento_versao_id
            == orcamento_versao_id
        )
        .values(origem_orcamento_versao_id=None)
    )
    session.execute(
        update(OrcamentoItemValuesetLinha)
        .where(OrcamentoItemValuesetLinha.origem_orcamento_valueset_linha_id.in_(valueset_ids))
        .values(origem_orcamento_valueset_linha_id=None)
    )
    session.execute(
        delete(OrcamentoValuesetLinha).where(
            OrcamentoValuesetLinha.orcamento_versao_id == orcamento_versao_id
        )
    )
    session.execute(
        delete(OrcamentoVersaoPlacaNaoStock).where(
            OrcamentoVersaoPlacaNaoStock.orcamento_versao_id == orcamento_versao_id
        )
    )
    session.execute(
        delete(OrcamentoVersaoEvento).where(
            OrcamentoVersaoEvento.orcamento_versao_id == orcamento_versao_id
        )
    )
    session.execute(delete(OrcamentoVersao).where(OrcamentoVersao.id == orcamento_versao_id))

    if remove_orcamento:
        session.execute(
            update(Producao)
            .where(Producao.orcamento_id == orcamento_id)
            .values(orcamento_id=None)
        )
        session.execute(delete(Orcamento).where(Orcamento.id == orcamento_id))


def _remover_pasta_orcamento_segura(
    session: Session,
    caminho: Path,
    *,
    nome_esperado: str,
) -> None:
    """Remove a budget folder only when it is inside the configured base."""
    path = Path(caminho)
    expected_name = str(nome_esperado or "").strip()
    if not expected_name:
        raise ValueError("Nome esperado da pasta de or\u00e7amento em falta.")

    try:
        resolved_path = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Pasta de or\u00e7amento inexistente: {path}") from exc
    except OSError as exc:
        raise OSError(f"N\u00e3o foi poss\u00edvel resolver a pasta: {path} ({exc})") from exc

    if not resolved_path.is_dir():
        raise ValueError(f"O caminho n\u00e3o \u00e9 uma pasta: {resolved_path}")
    if resolved_path.name != expected_name:
        raise ValueError(
            "Nome da pasta de or\u00e7amento inesperado: "
            f"{resolved_path.name!r} (esperado {expected_name!r})."
        )

    base = SystemSettingService(session).obter_valor("pasta_base_orcamentos")
    if not base:
        raise ValueError("Pasta base dos Or\u00e7amentos n\u00e3o configurada.")

    base_path = Path(base)
    try:
        resolved_base = base_path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Pasta base dos Or\u00e7amentos inexistente: {base_path}") from exc
    except OSError as exc:
        raise OSError(
            f"N\u00e3o foi poss\u00edvel resolver a pasta base dos Or\u00e7amentos: "
            f"{base_path} ({exc})"
        ) from exc

    if resolved_path == resolved_base or not resolved_path.is_relative_to(resolved_base):
        raise ValueError(
            "A pasta de or\u00e7amento est\u00e1 fora da pasta base dos Or\u00e7amentos: "
            f"{resolved_path}"
        )

    try:
        shutil.rmtree(resolved_path)
    except PermissionError as exc:
        raise PermissionError(
            f"Falha ao apagar a pasta de or\u00e7amento: {resolved_path} "
            "(sem permiss\u00e3o ou ficheiro em uso?)"
        ) from exc
    except OSError as exc:
        raise OSError(
            f"Falha ao apagar a pasta de or\u00e7amento: {resolved_path} ({exc})"
        ) from exc
