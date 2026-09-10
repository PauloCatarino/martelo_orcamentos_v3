"""Comparar as referências lidas do Excel com as lidas da base.

A Fase 3 troca a origem das referências da Pesquisa IA: deixam de sair do
``12_Placas_Referencias_COMPLETO.xlsx`` e passam a sair da ``martelo_catalogos``.
Uma troca destas não se faz de olhos fechados — este script põe as duas leituras
lado a lado e diz onde diferem.

Compara **por referência**, e não linha a linha, de propósito: no Excel uma
linha é uma referência com as suas espessuras em colunas, e na base é um artigo
por espessura que aqui se volta a juntar. Os agrupamentos podem não coincidir
(a Finsa repete a mesma referência em vários substratos); o que tem de coincidir
são os preços que cada referência oferece.

Uso::

    python -m scripts.comparar_referencias
    python -m scripts.comparar_referencias --folha Stock_WoodSide_Egger
    python -m scripts.comparar_referencias --detalhe 20

Não escreve nada, em lado nenhum.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict

from app.db.session import SessionLocal
from app.services.placas_referencias_service import (
    ORIGEM_BASE,
    ORIGEM_EXCEL,
    LinhaReferencia,
    listar_referencias,
)
from app.services.catalogos.consulta import CHAVE_PRECO_UNITARIO

#: Etiquetas de preço que não são espessuras — «Preço Tabela», «Preço PVP1» —
#: passam todas a valer o mesmo dos dois lados, senão a diferença que se via era
#: só a do nome da coluna.
_ESPESSURA = re.compile(r"^\d+(?:[.,]\d+)?mm$", re.IGNORECASE)


def _etiqueta(bruta: str) -> str:
    return bruta if _ESPESSURA.match(bruta.strip()) else CHAVE_PRECO_UNITARIO


def _por_referencia(
    linhas: list[LinhaReferencia],
) -> dict[tuple[str, str], set[tuple[str, str]]]:
    """``(folha, referência) -> {(etiqueta, preço)}``."""
    fora: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for linha in linhas:
        chave = (linha.folha, linha.referencia)
        fora[chave]  # noqa: B018 - garante a chave mesmo sem preços
        for etiqueta, valor in linha.precos.items():
            fora[chave].add((_etiqueta(etiqueta), valor))
    return dict(fora)


#: Os campos que se veem na tabela do ecrã, além dos preços.
CAMPOS = ("st_acab", "nome_design", "grupo", "tipo", "fornecedor")


def _campos_por_referencia(
    linhas: list[LinhaReferencia],
) -> dict[tuple[str, str], dict[str, set[str]]]:
    fora: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for linha in linhas:
        for campo in CAMPOS:
            fora[(linha.folha, linha.referencia)][campo].add(getattr(linha, campo))
    return fora


def _contar_por_folha(linhas: list[LinhaReferencia]) -> dict[str, int]:
    contas: dict[str, int] = defaultdict(int)
    for linha in linhas:
        contas[linha.folha] += 1
    return dict(contas)


def comparar(excel: list[LinhaReferencia], base: list[LinhaReferencia], detalhe: int) -> int:
    """Imprime a comparação e devolve o número de referências com preços diferentes."""
    mapa_excel = _por_referencia(excel)
    mapa_base = _por_referencia(base)
    contas_excel = _contar_por_folha(excel)
    contas_base = _contar_por_folha(base)

    print(f"Excel: {len(excel)} linhas, {len(mapa_excel)} referências")
    print(f"Base : {len(base)} linhas, {len(mapa_base)} referências")

    print("\nLinhas por separador")
    print(f"  {'separador':<32} {'Excel':>7} {'base':>7}")
    for folha in sorted(set(contas_excel) | set(contas_base)):
        marca = "" if folha in contas_excel and folha in contas_base else "   <-- só num lado"
        print(
            f"  {folha:<32} {contas_excel.get(folha, 0):>7} "
            f"{contas_base.get(folha, 0):>7}{marca}"
        )

    so_excel = sorted(set(mapa_excel) - set(mapa_base))
    so_base = sorted(set(mapa_base) - set(mapa_excel))
    comuns = sorted(set(mapa_excel) & set(mapa_base))

    diferentes = [chave for chave in comuns if mapa_excel[chave] != mapa_base[chave]]
    iguais = len(comuns) - len(diferentes)

    print(
        f"\nReferências: {iguais} com os mesmos preços, {len(diferentes)} com "
        f"preços diferentes, {len(so_excel)} só no Excel, {len(so_base)} só na base"
    )

    if so_excel:
        print(f"\nSó no Excel (primeiras {detalhe}):")
        for folha, referencia in so_excel[:detalhe]:
            precos = sorted(mapa_excel[(folha, referencia)])
            print(f"  {folha} · {referencia}: {precos or 'sem preços'}")

    if so_base:
        print(f"\nSó na base (primeiras {detalhe}):")
        for folha, referencia in so_base[:detalhe]:
            print(f"  {folha} · {referencia}: {sorted(mapa_base[(folha, referencia)])}")

    if diferentes:
        print(f"\nPreços diferentes (primeiras {detalhe}):")
        for folha, referencia in diferentes[:detalhe]:
            do_excel = mapa_excel[(folha, referencia)]
            da_base = mapa_base[(folha, referencia)]
            print(f"  {folha} · {referencia}")
            print(f"    só no Excel: {sorted(do_excel - da_base)}")
            print(f"    só na base : {sorted(da_base - do_excel)}")

    _comparar_campos(excel, base, comuns, detalhe)
    return len(diferentes)


def _comparar_campos(
    excel: list[LinhaReferencia],
    base: list[LinhaReferencia],
    comuns: list[tuple[str, str]],
    detalhe: int,
) -> None:
    """Os campos que se veem, fora os preços.

    Diferenças aqui não são necessariamente erros — a base sabe o fornecedor de
    separadores que não têm coluna nenhuma a dizê-lo, e o design da Innovus vem
    da coluna certa em vez da descrição inteira. O que interessa é **ver** cada
    uma e decidir, em vez de descobrir mais tarde que uma coluna esvaziou.
    """
    campos_excel = _campos_por_referencia(excel)
    campos_base = _campos_por_referencia(base)

    print("\nCampos visíveis, nas referências comuns")
    for campo in CAMPOS:
        chaves = [
            chave
            for chave in comuns
            if campos_excel[chave][campo] != campos_base[chave][campo]
        ]
        por_folha: dict[str, int] = defaultdict(int)
        for folha, _ in chaves:
            por_folha[folha] += 1
        resumo = ", ".join(
            f"{folha} {conta}" for folha, conta in sorted(por_folha.items())
        )
        print(f"  {campo:<12} {len(chaves):>6} diferentes{'  ·  ' + resumo if resumo else ''}")
        for chave in sorted(chaves)[: min(detalhe, 3)]:
            print(f"      {chave[0]} · {chave[1]}")
            print(f"        excel: {sorted(campos_excel[chave][campo])}")
            print(f"        base : {sorted(campos_base[chave][campo])}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--folha", help="comparar apenas este separador (nome exato)", default=None
    )
    parser.add_argument(
        "--detalhe",
        type=int,
        default=10,
        help="quantos exemplos mostrar de cada diferença (por omissão 10)",
    )
    args = parser.parse_args(argv)

    with SessionLocal() as session:
        excel = listar_referencias(session, origem=ORIGEM_EXCEL)
        base = listar_referencias(session, origem=ORIGEM_BASE)

    if args.folha:
        excel = [linha for linha in excel if linha.folha == args.folha]
        base = [linha for linha in base if linha.folha == args.folha]
        if not excel and not base:
            print(f"Nenhum separador chamado {args.folha!r} nos dois lados.")
            return 2

    diferentes = comparar(excel, base, args.detalhe)
    if diferentes:
        print(
            "\nHá referências com preços diferentes. Antes de desligar o Excel, "
            "perceber cada uma."
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
