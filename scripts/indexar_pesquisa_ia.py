"""(Re)indexa os catalogos de fornecedores para a Pesquisa IA."""

from __future__ import annotations

from app.db.session import SessionLocal
from app.services.pesquisa_ia_index_service import indexar


def main() -> int:
    with SessionLocal() as session:
        resultado = indexar(session, progresso=print)
    print(
        f"OK - artigos da base: {resultado.artigos}, ficheiros: "
        f"{resultado.ficheiros}, chunks: {resultado.chunks}, erros: "
        f"{resultado.erros}. Indice em: {resultado.pasta_indice}"
    )
    # Nada fica de fora em silencio: quem correr isto tem de poder discordar.
    if resultado.ignorados:
        print(f"\nNao foram lidos {len(resultado.ignorados)} ficheiros:")
        for nome, razao in resultado.ignorados:
            print(f"  - {nome}: {razao}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
