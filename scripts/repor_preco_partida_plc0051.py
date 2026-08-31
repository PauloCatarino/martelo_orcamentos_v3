"""Repor no histórico o preço que o PLC0051 tinha antes da alteração da Andreia.

PORQUE E' QUE ISTO EXISTE
-------------------------
A migração 20260901_100 deu histórico de partida a todas as matérias-primas que
não tinham nenhum. O PLC0051 ficou de fora por um motivo simples: já TINHA uma
linha -- a alteração que a Andreia fez a 31-08-2026, de 20,36 EUR para 21,36 EUR
-- e o preço anterior não está guardado em sítio nenhum da base de dados.

O Paulo confirmou o valor antigo a 2026-08-31: 20,36 EUR de tabela e 22,40 EUR
líquido (que bate certo com a margem de 10% do material). Este script escreve
essa linha, e mais nada. Não toca no preço do material nem em orçamento nenhum.

COMO SE USA
-----------
    .venv\\Scripts\\python.exe scripts\\repor_preco_partida_plc0051.py

Corre-lo duas vezes não duplica nada: se a linha já lá estiver, não faz nada.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

import app.models  # noqa: F401  (regista os modelos)
from app.db.database import get_engine
from app.models.def_materia_prima_preco_historico import DefMateriaPrimaPrecoHistorico
from app.repositories.def_materia_prima_repository import DefMateriaPrimaRepository

REF_LE = "PLC0051"
PRECO_TABELA = Decimal("20.3600")
PRECO_LIQUIDO = Decimal("22.4000")
MARGEM = Decimal("10.0000")
#: A data que a ficha mostrava antes da alteração (coluna "Último preço").
DATA_PRECO = date(2025, 7, 23)

OBSERVACAO = (
    "Preço de partida reposto à mão: o valor anterior (20,36 EUR tabela / "
    "22,40 EUR líquido) não tinha ficado no histórico porque este material foi "
    "alterado antes de o Martelo passar a guardar o preço de partida. "
    "Confirmado pelo Paulo a 2026-08-31."
)


def main() -> int:
    with Session(get_engine()) as session:
        materia = DefMateriaPrimaRepository(session).get_by_ref_le(REF_LE)
        if materia is None:
            print(f"Nao encontrei a materia-prima {REF_LE}.")
            return 1

        ja_existe = (
            session.query(DefMateriaPrimaPrecoHistorico)
            .filter(
                DefMateriaPrimaPrecoHistorico.materia_prima_id == materia.id,
                DefMateriaPrimaPrecoHistorico.preco_tabela == PRECO_TABELA,
            )
            .first()
        )
        if ja_existe is not None:
            print(f"{REF_LE}: a linha de partida ja' esta' la'. Nada a fazer.")
            return 0

        session.add(
            DefMateriaPrimaPrecoHistorico(
                materia_prima_id=materia.id,
                ref_le=materia.ref_le,
                preco_tabela=PRECO_TABELA,
                desconto=None,
                margem=MARGEM,
                preco_liquido=PRECO_LIQUIDO,
                data_preco=DATA_PRECO,
                origem="EXCEL",
                user_id=None,
                observacoes=OBSERVACAO,
                # Antes da alteracao da Andreia, para ficar por baixo dela.
                created_at=datetime(2026, 6, 5, 23, 3, 52),
            )
        )
        session.commit()
        print(f"{REF_LE}: linha de partida escrita ({PRECO_TABELA} EUR tabela).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
