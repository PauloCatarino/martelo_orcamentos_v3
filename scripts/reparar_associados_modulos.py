"""Repor nos módulos guardados os associados que lá deviam estar.

O QUE ISTO ARRANJA
------------------
Até 2026-09-04, importar um módulo perdia os associados das peças SIMPLES (as
uniões dos topos, os pés de um fundo): o importador só sabia descer os filhos de
uma peça COMPOSTA. Isso já está corrigido — mas ficou um rasto.

Quem construiu um módulo NOVO a partir de linhas que tinham vindo de um módulo
importado gravou-o já sem esses associados. O módulo em si ficou incompleto, e
importá-lo outra vez não os inventa: um teto que devia levar cavilhas e
parafusos aparece sozinho, e o preço vem abaixo sem nada a dizer porquê.

Este script compara cada linha de módulo com os associados ATIVOS que a peça
tem no catálogo (`def_peca_componentes`) e acrescenta os que faltam, no sítio
certo da árvore. A quantidade fica a que o catálogo diz; quem manda nela a
sério é a regra de quantidade, que corre no «Atualizar Custos».

O QUE ISTO NÃO FAZ
------------------
Não mexe em orçamentos. Um orçamento que já importou um módulo incompleto
continua incompleto: aí é apagar as linhas e importar outra vez, agora que o
módulo está bom.

Também não adivinha. Se alguém tiver apagado um associado DE PROPÓSITO antes de
gravar o módulo, este script volta a pô-lo lá — por isso convém olhar para a
simulação antes de gravar.

COMO SE USA
-----------
    # ver o que ia fazer, sem gravar nada
    .venv\\Scripts\\python.exe scripts\\reparar_associados_modulos.py

    # gravar
    .venv\\Scripts\\python.exe scripts\\reparar_associados_modulos.py --aplicar

    # só um módulo
    .venv\\Scripts\\python.exe scripts\\reparar_associados_modulos.py --modulo LV_MS_01_2_PORTAS
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domain.custeio_linha_types import (  # noqa: E402
    FERRAGEM,
    PECA,
    PECA_COMPOSTA,
)
from app.db.session import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    DefModulo,
    DefModuloLinha,
    DefPeca,
    DefPecaComponente,
)


@dataclass
class Falta:
    """Um associado que devia estar no módulo e não está.

    Os textos ficam copiados (e não os objetos do ORM) porque o relatório é
    impresso DEPOIS do commit, e aí os objetos já estão desligados da sessão.
    """

    pai_ordem: int
    pai_codigo: str
    codigo_filho: str
    descricao_filho: str
    componente_id: int
    def_peca_filha_id: int | None
    tipo_linha: str
    qt_und: str
    formula_comp: str | None
    formula_larg: str | None
    formula_esp: str | None
    chave_valueset: str | None
    prioridade_valueset: int | None
    def_regra_quantidade_id: int | None


@dataclass
class PlanoModulo:
    """O que há a acrescentar num módulo."""

    codigo: str
    ambito: str
    user_id: int | None
    faltas: list[Falta] = field(default_factory=list)


def _tipo_linha_do_componente(componente, peca_filha) -> str:
    """FERRAGEM para ferragens/acessórios; PECA para o resto."""
    if (componente.tipo_componente or "").strip().upper() == "FERRAGEM":
        return FERRAGEM
    if peca_filha is not None and (peca_filha.grupo or "").strip().upper() in (
        "FERRAGENS",
        "ACESSORIOS",
    ):
        return FERRAGEM
    return PECA


def _texto(valor) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        return format(valor.normalize(), "f")
    return str(valor)


def _analisar(session, filtro_modulo: str | None) -> list[PlanoModulo]:
    """Comparar cada módulo com o catálogo e listar o que falta."""
    associados = defaultdict(list)
    for componente in session.execute(
        select(DefPecaComponente).where(DefPecaComponente.ativo.is_(True))
    ).scalars():
        associados[componente.def_peca_pai_id].append(componente)
    for lista in associados.values():
        lista.sort(key=lambda c: (c.ordem or 0, c.id))

    pecas = {peca.id: peca for peca in session.execute(select(DefPeca)).scalars()}
    por_codigo = {peca.codigo: peca for peca in pecas.values()}

    planos: list[PlanoModulo] = []
    modulos = session.execute(
        select(DefModulo).order_by(DefModulo.codigo.asc())
    ).scalars().all()

    for modulo in modulos:
        if filtro_modulo and modulo.codigo != filtro_modulo:
            continue

        linhas = session.execute(
            select(DefModuloLinha)
            .where(DefModuloLinha.def_modulo_id == modulo.id)
            .order_by(DefModuloLinha.ordem.asc())
        ).scalars().all()

        filhos = defaultdict(list)
        for linha in linhas:
            if linha.linha_pai_ordem is not None:
                filhos[linha.linha_pai_ordem].append(linha)

        plano = PlanoModulo(
            codigo=modulo.codigo, ambito=modulo.ambito, user_id=modulo.user_id
        )
        for linha in linhas:
            peca = pecas.get(linha.def_peca_id) or por_codigo.get(
                linha.def_peca_codigo or ""
            )
            if peca is None:
                continue
            esperados = associados.get(peca.id, [])
            if not esperados:
                continue

            # A regra é estreita de propósito. O que a importação estragava era
            # uma coisa muito concreta: uma peça SIMPLES ficava sozinha, com
            # TODOS os filhos por baixo dela a desaparecerem de uma vez. É essa
            # forma — e só essa — que se repõe.
            if linha.tipo_linha == PECA_COMPOSTA:
                # Uma composta ou tem a sua própria estrutura guardada, ou é
                # re-expandida inteira do catálogo na importação. Nos dois casos
                # mexer-lhe fazia mal.
                continue
            if filhos.get(linha.ordem):
                # Tem filhos guardados: esta linha não foi apanhada pelo bug.
                # Pode ter uma estrutura antiga (o catálogo mudou entretanto) e
                # comparar com o catálogo de hoje daria falsos positivos.
                continue

            for componente in esperados:
                filha = pecas.get(componente.def_peca_componente_id)
                codigo_filho = (
                    filha.codigo if filha else componente.referencia_componente
                ) or "?"
                plano.faltas.append(
                    Falta(
                        pai_ordem=linha.ordem,
                        pai_codigo=linha.def_peca_codigo or peca.codigo,
                        codigo_filho=codigo_filho,
                        descricao_filho=(
                            (filha.nome if filha else None) or codigo_filho
                        ),
                        componente_id=componente.id,
                        def_peca_filha_id=filha.id if filha else None,
                        tipo_linha=_tipo_linha_do_componente(componente, filha),
                        qt_und=_texto(componente.quantidade) or "1",
                        formula_comp=componente.formula_comp,
                        formula_larg=componente.formula_larg,
                        formula_esp=componente.formula_esp,
                        chave_valueset=(
                            getattr(filha, "chave_valueset_material", None)
                            if filha
                            else None
                        ),
                        prioridade_valueset=componente.prioridade_valueset,
                        def_regra_quantidade_id=componente.def_regra_quantidade_id,
                    )
                )

        if plano.faltas:
            planos.append(plano)

    return planos


def _aplicar(session, modulo_codigo: str, plano: PlanoModulo) -> int:
    """Acrescentar as linhas em falta e renumerar o módulo em profundidade."""
    modulo = session.execute(
        select(DefModulo).where(DefModulo.codigo == modulo_codigo)
    ).scalars().first()
    if modulo is None:
        return 0

    linhas = session.execute(
        select(DefModuloLinha)
        .where(DefModuloLinha.def_modulo_id == modulo.id)
        .order_by(DefModuloLinha.ordem.asc())
    ).scalars().all()
    por_ordem = {linha.ordem: linha for linha in linhas}

    novas: list[tuple[int, DefModuloLinha]] = []
    for falta in plano.faltas:
        pai = por_ordem.get(falta.pai_ordem)
        if pai is None:
            continue
        nova = DefModuloLinha(
            def_modulo_id=modulo.id,
            ordem=0,  # renumerado a seguir
            tipo_linha=falta.tipo_linha,
            def_peca_id=falta.def_peca_filha_id,
            def_peca_codigo=falta.codigo_filho,
            codigo=falta.codigo_filho,
            descricao=falta.descricao_filho,
            qt_mod="1",
            qt_und=falta.qt_und,
            comp=falta.formula_comp,
            larg=falta.formula_larg,
            esp=falta.formula_esp,
            chave_valueset=falta.chave_valueset,
            prioridade_valueset=falta.prioridade_valueset,
            def_regra_quantidade_id=falta.def_regra_quantidade_id,
            linha_pai_ordem=falta.pai_ordem,
            nivel=(pai.nivel or 0) + 1,
            ativo=True,
        )
        session.add(nova)
        novas.append((falta.pai_ordem, nova))

    session.flush()

    # Renumerar tudo em profundidade, para os filhos ficarem logo a seguir ao pai.
    todas = linhas + [nova for _pai, nova in novas]
    filhos = defaultdict(list)
    topo = []
    for linha in todas:
        if linha.linha_pai_ordem is None:
            topo.append(linha)
        else:
            filhos[linha.linha_pai_ordem].append(linha)

    topo.sort(key=lambda l: (l.ordem or 0, l.id))
    for lista in filhos.values():
        lista.sort(key=lambda l: (l.ordem or 0, l.id))

    ordem_nova: dict[int, int] = {}
    contador = 0

    def descer(linha, pai_ordem_novo: int | None) -> None:
        nonlocal contador
        contador += 1
        atual = contador
        ordem_antiga = linha.ordem
        ordem_nova[id(linha)] = atual
        linha._nova_ordem = atual
        linha._novo_pai = pai_ordem_novo
        for filho in filhos.get(ordem_antiga, []):
            descer(filho, atual)

    for linha in topo:
        descer(linha, None)

    for linha in todas:
        if hasattr(linha, "_nova_ordem"):
            linha.ordem = linha._nova_ordem
            linha.linha_pai_ordem = linha._novo_pai

    return len(novas)


def _imprimir(planos: list[PlanoModulo], aplicar: bool) -> None:
    if not planos:
        print("Nenhum módulo tem associados em falta. Nada a fazer.")
        return

    total = 0
    for plano in planos:
        dono = f"/{plano.user_id}" if plano.user_id else ""
        print(f"\n{plano.codigo} ({plano.ambito}{dono}) — {len(plano.faltas)} em falta")
        for falta in plano.faltas:
            print(f"    {falta.pai_codigo}  ->  {falta.codigo_filho}")
        total += len(plano.faltas)

    print("")
    if not aplicar:
        print(
            f"SIMULAÇÃO — nada foi gravado. {total} linha(s) seriam acrescentadas. "
            "Volte a correr com --aplicar para gravar."
        )
    else:
        print(f"GRAVADO — {total} linha(s) acrescentadas.")
        print(
            "Os orçamentos que já importaram estes módulos NÃO mudam sozinhos: "
            "aí é apagar as linhas e importar o módulo outra vez."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aplicar", action="store_true", help="grava mesmo (sem isto é simulação)"
    )
    parser.add_argument(
        "--modulo", default=None, help="tratar só o módulo com este código"
    )
    args = parser.parse_args()

    try:
        with SessionLocal() as session:
            planos = _analisar(session, args.modulo)
            if args.aplicar:
                for plano in planos:
                    _aplicar(session, plano.codigo, plano)
                session.commit()
    except SQLAlchemyError as error:
        print(f"Erro a falar com a base de dados: {error}")
        return 1

    _imprimir(planos, args.aplicar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
