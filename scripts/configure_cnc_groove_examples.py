"""Idempotently configure the agreed CNC groove examples for test data."""

from pathlib import Path
import sys

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.models import DefOperacao, DefPeca, DefPecaOperacao  # noqa: E402


EXAMPLES = {
    "COSTA_INS_0000+RASGO": (2, 2),
    "LED": (1, 0),
}


def ensure_examples(session) -> list[str]:
    operation = session.execute(
        select(DefOperacao).where(DefOperacao.codigo == "CNC_RASGO")
    ).scalar_one()
    results = []
    for piece_code, (qt_comp, qt_larg) in EXAMPLES.items():
        piece = session.execute(
            select(DefPeca).where(DefPeca.codigo == piece_code)
        ).scalar_one()
        link = session.execute(
            select(DefPecaOperacao).where(
                DefPecaOperacao.def_peca_id == piece.id,
                DefPecaOperacao.def_operacao_id == operation.id,
            )
        ).scalar_one_or_none()
        if link is None:
            max_order = max((item.ordem for item in piece.operacoes), default=0)
            link = DefPecaOperacao(
                def_peca_id=piece.id,
                def_operacao_id=operation.id,
                ordem=max_order + 1,
                obrigatorio=True,
                ativo=True,
            )
            session.add(link)
        link.regra_calculo = "RASGO_CNC"
        link.rasgo_qt_comp = qt_comp
        link.rasgo_qt_larg = qt_larg
        link.unidade_tempo = None
        link.observacoes = f"Rasgo CNC: {qt_comp} x COMP + {qt_larg} x LARG"
        results.append(f"{piece_code}: {qt_comp} x COMP + {qt_larg} x LARG")
    session.commit()
    return results


if __name__ == "__main__":
    with SessionLocal() as session:
        for result in ensure_examples(session):
            print(result)
