"""(Re)indexa os catalogos de fornecedores para a Pesquisa IA."""

from __future__ import annotations

from app.db.session import SessionLocal
from app.services.pesquisa_ia_index_service import indexar


def main() -> int:
    with SessionLocal() as session:
        resultado = indexar(session, progresso=print)
    print(
        f"OK - ficheiros: {resultado.ficheiros}, chunks: {resultado.chunks}, "
        f"erros: {resultado.erros}. Indice em: {resultado.pasta_indice}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
