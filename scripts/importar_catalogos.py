"""Importa as tabelas de preços dos fornecedores para ``martelo_catalogos``.

    python -m scripts.importar_catalogos --fornecedor egger
    python -m scripts.importar_catalogos --fornecedor innovus --ver
    python -m scripts.importar_catalogos --fornecedor finsa
    python -m scripts.importar_catalogos --fornecedor egger --ficheiro C:\\tmp\\tabela.xlsx

Sem ``--ficheiro`` vai buscar o ``12_Placas_Referencias_COMPLETO.xlsx`` à pasta
que está nas Definições (``pasta_pesquisa_profunda_ia``), que é a mesma que a
Pesquisa IA lê.

O ``--ver`` lê e mostra o que ia gravar sem escrever nada — é a maneira de
olhar para uma tabela nova antes de a deixar entrar. Correr sem ``--ver`` duas
vezes seguidas também não faz mal: a segunda diz que já estava importada.

Nada disto escreve em matérias-primas nem toca em orçamento nenhum.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.services.catalogos import egger, finsa, importador, innovus
from app.services.catalogos.base import FormatoInesperado, TabelaCatalogo
from app.services.placas_referencias_service import FICHEIRO_REFERENCIAS
from app.services.system_setting_service import SystemSettingService

#: Adaptadores disponíveis, pela ordem em que foram escritos — que é a do
#: dinheiro: o Egger é o que mais se gasta, a Finsa o que menos.
#:
#: Os três separadores de **disponibilidade** de Innovus
#: (``Stock_Somapil_Innovus``, ``Stock_J.Pinto_Leitao_Innovus``,
#: ``Stock_WoodSide_Innovus``) não estão aqui: não têm preço nenhum e são uma
#: matriz de formato × espessura, com o substrato numa banda por cima das
#: colunas — banda que o separador da Somapil não tem, o que torna cinco das
#: suas colunas indistinguíveis umas das outras. Enquanto isso não for
#: resolvido na origem, não há maneira honesta de os ler.
ADAPTADORES = {
    "egger": egger.ler_tabelas,
    "innovus": innovus.ler_tabelas,
    "finsa": finsa.ler_tabelas,
}


def _caminho_por_omissao() -> Path:
    with SessionLocal() as session:
        pasta = (
            SystemSettingService(session).obter_valor("pasta_pesquisa_profunda_ia", "")
            or ""
        ).strip()
    if not pasta:
        raise SystemExit(
            "A pasta da Pesquisa Profunda IA não está definida nas Definições. "
            "Indique o ficheiro com --ficheiro."
        )
    return Path(pasta) / FICHEIRO_REFERENCIAS


def _mostrar(tabela: TabelaCatalogo) -> None:
    print(f"\n{tabela.fornecedor} · {tabela.nome}")
    print(f"  fabricante ....... {tabela.fabricante}")
    print(f"  referência ....... {tabela.referencia_tabela or '(sem código)'}")
    print(f"  data da tabela ... {tabela.data_tabela or '(não indicada)'}")
    print(f"  origem ........... {tabela.ficheiro_origem}")
    print(f"  hash ............. {(tabela.ficheiro_hash or '')[:16]}...")
    print(f"  artigos .......... {len(tabela.artigos)} ({tabela.com_preco} com preço)")
    for artigo in tabela.artigos[:3]:
        print(
            f"     {artigo.chave_natural:<34} "
            f"{artigo.preco if artigo.preco is not None else '—':>9} "
            f"{artigo.unidade}  {artigo.descricao[:60]}"
        )
    if len(tabela.artigos) > 3:
        print(f"     ... e mais {len(tabela.artigos) - 3}")
    for aviso in tabela.avisos:
        print(f"  AVISO: {aviso}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fornecedor",
        required=True,
        choices=sorted(ADAPTADORES),
        help="que adaptador correr",
    )
    parser.add_argument(
        "--ficheiro",
        type=Path,
        default=None,
        help="xlsx a ler (por omissão o da pasta da Pesquisa Profunda IA)",
    )
    parser.add_argument(
        "--ver",
        action="store_true",
        help="mostra o que ia gravar e não escreve nada",
    )
    parser.add_argument(
        "--forcar",
        action="store_true",
        help="importa mesmo que o hash já esteja na base (não apaga nada)",
    )
    args = parser.parse_args(argv)

    caminho = args.ficheiro or _caminho_por_omissao()
    print(f"Ficheiro: {caminho}")

    try:
        tabelas = ADAPTADORES[args.fornecedor](caminho)
    except FormatoInesperado as erro:
        print(f"ERRO de formato: {erro}")
        return 2

    for tabela in tabelas:
        _mostrar(tabela)

    if args.ver:
        total = sum(len(t.artigos) for t in tabelas)
        print(f"\n--ver: nada foi escrito. {total} artigos em {len(tabelas)} tabelas.")
        return 0

    with SessionLocal() as session:
        resultados = importador.importar_tabelas(
            session, tabelas, forcar=args.forcar
        )
        session.commit()

    print()
    for resultado in resultados:
        print(f"OK - {resultado.resumo()}")
        if resultado.tabelas_desativadas:
            print(
                f"     ({resultado.tabelas_desativadas} tabela(s) anterior(es) "
                "deixaram de ser as ativas; nada foi apagado)"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
