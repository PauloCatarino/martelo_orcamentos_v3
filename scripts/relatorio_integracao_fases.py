"""Relatório de integração das fases 1–6 (Fase 7 — migração assistida).

Uso (na raiz do projeto, depois de ``python -m alembic upgrade head``):

    python -m scripts.relatorio_integracao_fases            # só relatório
    python -m scripts.relatorio_integracao_fases --corrigir # aplica correções

As correções são determinísticas e idempotentes: materializam as encomendas
PHC antigas (enc_phc sem registo filho) e completam a tabela de categorias de
módulos. Nada é recalculado nos orçamentos.
"""

from __future__ import annotations

import argparse

from app.db.session import SessionLocal
from app.services.integracao_fases_service import (
    IntegracaoFasesService,
    formatar_relatorio,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corrigir",
        action="store_true",
        help="aplicar as correções assistidas antes do relatório final",
    )
    args = parser.parse_args()

    with SessionLocal() as session:
        service = IntegracaoFasesService(session)
        if args.corrigir:
            resultado = service.aplicar_correcoes()
            print(
                "Correções aplicadas: "
                f"{resultado.encomendas_materializadas} encomenda(s) PHC "
                f"materializada(s), {resultado.categorias_criadas} "
                "categoria(s) criada(s)."
            )
            print()
        print(formatar_relatorio(service.gerar_relatorio()))


if __name__ == "__main__":
    main()
