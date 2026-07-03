"""Corrige codigo_processo de encomendas Streamlit gravado antes da correcao do underline.

Antes da correcao em ``gerar_codigo_processo``, um numero Streamlit como
``_118`` perdia o ``_`` e ficava com zero-padding de 4 digitos (``0118``),
fazendo ``codigo_processo`` ficar "26.0118_01_03_CLIENTE" em vez de
"26._118_01_03_CLIENTE". A correcao do gerador so afeta processos criados
ou editados depois dela; os processos ja gravados na BD mantem o valor
antigo ate seres corrigidos aqui. So mexe no segmento "AA.NNNN_" de linhas
cujo ``num_enc_phc`` comeca por "_" e cujo ``codigo_processo`` ainda
corresponde exatamente ao prefixo antigo (zero-padded); tudo o resto da
string (versoes, sufixo de cliente) fica inalterado.

Uso:
    python -m scripts.normalizar_codigo_processo_streamlit --dry-run
    python -m scripts.normalizar_codigo_processo_streamlit
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.producao import Producao  # noqa: E402
from app.services.producao_service import _format_digits, _num_enc_norm  # noqa: E402


@dataclass
class NormalizarCodigoProcessoSummary:
    """Counters for one codigo_processo backfill run."""

    total: int = 0
    linhas_atualizadas: int = 0
    ids_atualizados: list[int] = field(default_factory=list)
    ids_colisao: list[int] = field(default_factory=list)


def _prefixos_streamlit(processo: Producao) -> tuple[str, str] | None:
    """Return (prefixo_antigo, prefixo_novo) if this row can carry the bug, else None."""
    num_enc = str(processo.num_enc_phc or "").strip()
    if not num_enc.startswith("_"):
        return None

    import re

    ano_text = re.sub(r"\D+", "", str(processo.ano or ""))
    aa = (ano_text[-2:] if ano_text else "00").zfill(2)
    nnnn_antigo = _format_digits(num_enc, 4)
    nnnn_novo = _num_enc_norm(num_enc)
    if not nnnn_novo or nnnn_antigo == nnnn_novo:
        return None

    return f"{aa}.{nnnn_antigo}_", f"{aa}.{nnnn_novo}_"


def normalizar_codigo_processo(session, *, dry_run: bool) -> NormalizarCodigoProcessoSummary:
    """Fix the stale zero-padded prefix on Streamlit codigo_processo rows."""
    processos = list(session.scalars(select(Producao).order_by(Producao.id.asc())).all())
    summary = NormalizarCodigoProcessoSummary(total=len(processos))

    codigos_existentes = {p.codigo_processo for p in processos}

    for processo in processos:
        prefixos = _prefixos_streamlit(processo)
        if prefixos is None:
            continue
        prefixo_antigo, prefixo_novo = prefixos

        codigo_atual = str(processo.codigo_processo or "")
        if not codigo_atual.startswith(prefixo_antigo):
            continue

        novo_codigo = prefixo_novo + codigo_atual[len(prefixo_antigo):]
        if novo_codigo in codigos_existentes and novo_codigo != codigo_atual:
            summary.ids_colisao.append(processo.id)
            continue

        summary.linhas_atualizadas += 1
        summary.ids_atualizados.append(processo.id)
        codigos_existentes.discard(codigo_atual)
        codigos_existentes.add(novo_codigo)
        if dry_run:
            continue
        processo.codigo_processo = novo_codigo

    if dry_run:
        session.rollback()
    else:
        session.commit()

    return summary


def print_summary(summary: NormalizarCodigoProcessoSummary, *, dry_run: bool) -> None:
    """Print the final user-facing summary."""
    modo = "DRY-RUN (sem gravar)" if dry_run else "NORMALIZACAO REAL"
    print(f"Modo: {modo}")
    print(f"total: {summary.total}")
    print(f"linhas_atualizadas: {summary.linhas_atualizadas}")
    if summary.ids_atualizados:
        print(f"ids_atualizados: {summary.ids_atualizados}")
    if summary.ids_colisao:
        print(f"ids_colisao (nao alterados, ja existe codigo_processo igual): {summary.ids_colisao}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Corrigir codigo_processo de encomendas Streamlit ('_NNN') gravado "
            "antes da correcao do underline em gerar_codigo_processo."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Conta as linhas a alterar sem gravar na base de dados.",
    )
    return parser.parse_args(sys.argv[1:] if argv is None else argv)


def main(argv: list[str] | None = None) -> int:
    """Run the codigo_processo backfill script."""
    args = parse_args(argv)

    try:
        with SessionLocal() as session:
            summary = normalizar_codigo_processo(session, dry_run=args.dry_run)
    except SQLAlchemyError as error:
        print("Nao foi possivel normalizar o codigo_processo de producao.")
        print(f"Detalhe: {error}")
        return 1

    print_summary(summary, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
