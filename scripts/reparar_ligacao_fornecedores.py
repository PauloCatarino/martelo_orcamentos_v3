"""Voltar a ligar as matérias-primas aos fornecedores, pelo nome.

Serve para reparar as bases onde a ligação se perdeu: houve uma altura em que a
importação do Excel, que só traz o **nome** do fornecedor, apagava o
``fornecedor_id`` que a migração 96 tinha atribuído. A causa já está corrigida
no serviço; isto repõe o que ficou por trás.

É seguro correr as vezes que forem precisas: só preenche ligações em falta e
nunca inventa fornecedores — os nomes que não existirem na tabela de
fornecedores são listados no fim, para serem tratados à mão.

Uso:
    python scripts/reparar_ligacao_fornecedores.py --simular
    python scripts/reparar_ligacao_fornecedores.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select  # noqa: E402

from app.models import DefFornecedor, DefMateriaPrima  # noqa: E402


def reparar(session, simular: bool = False) -> dict:
    """Ligar cada matéria-prima ao fornecedor com o mesmo nome.

    Devolve um resumo com o que foi ligado, o que já estava e os nomes sem
    fornecedor correspondente.
    """
    fornecedores = {
        fornecedor.nome.strip().upper(): fornecedor.id
        for fornecedor in session.execute(select(DefFornecedor)).scalars()
    }

    ligadas = 0
    ja_ligadas = 0
    sem_fornecedor: dict[str, int] = {}

    for materia in session.execute(select(DefMateriaPrima)).scalars():
        nome = (materia.fornecedor or "").strip()
        if not nome:
            continue

        if materia.fornecedor_id is not None:
            ja_ligadas += 1
            continue

        fornecedor_id = fornecedores.get(nome.upper())
        if fornecedor_id is None:
            sem_fornecedor[nome] = sem_fornecedor.get(nome, 0) + 1
            continue

        materia.fornecedor_id = fornecedor_id
        ligadas += 1

    if simular:
        session.rollback()
    else:
        session.commit()

    return {
        "ligadas": ligadas,
        "ja_ligadas": ja_ligadas,
        "sem_fornecedor": sem_fornecedor,
    }


def main(argv: list | None = None) -> int:
    """Reparar as ligações na base configurada."""
    parser = argparse.ArgumentParser(
        description="Ligar as matérias-primas aos fornecedores pelo nome."
    )
    parser.add_argument(
        "--simular",
        action="store_true",
        help="Mostrar o que seria feito, sem gravar.",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    from app.db.session import SessionLocal

    with SessionLocal() as session:
        resumo = reparar(session, simular=args.simular)

    print("SIMULAÇÃO (nada foi gravado)" if args.simular else "REPARAÇÃO CONCLUÍDA")
    print(f"Matérias-primas ligadas agora: {resumo['ligadas']}")
    print(f"Já estavam ligadas: {resumo['ja_ligadas']}")

    if resumo["sem_fornecedor"]:
        print("\nNomes sem fornecedor correspondente (criar em «Fornecedores…»):")
        for nome, quantas in sorted(resumo["sem_fornecedor"].items()):
            print(f"  - {nome}: {quantas} matérias-primas")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
