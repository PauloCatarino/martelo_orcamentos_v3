"""Repor a máquina e os minutos nas operações manuais dos módulos guardados.

O QUE ISTO ARRANJA
------------------
Até à migração 20260904_107, um módulo guardava a DESCRIÇÃO e as quantidades de
uma linha «Inserir operação manual», mas não a máquina nem os minutos por
unidade — que numa operação manual são o trabalho todo. Importar o módulo
trazia a linha com o nome certo e **0 €**, e quem orçamenta assume que o tempo
está contado. Aconteceu num bloco de gavetas que devia levar 50 € de montagem.

Os módulos guardados de novo já levam tudo. Este script trata dos ANTIGOS: para
cada linha de operação manual de um módulo sem tempo, procura nas linhas de
custeio reais uma operação manual com a MESMA descrição e usa os valores que lá
estão. Só age quando todas as ocorrências concordam entre si — havendo tempos
diferentes para a mesma descrição, não adivinha: mostra-os e deixa a linha
como está, para alguém decidir.

COMO SE USA
-----------
    # ver o que ia fazer, sem gravar nada
    .venv\\Scripts\\python.exe scripts\\reparar_operacoes_manuais_modulos.py

    # gravar
    .venv\\Scripts\\python.exe scripts\\reparar_operacoes_manuais_modulos.py --aplicar

Em alternativa (e é sempre o mais fiável): abrir um orçamento onde a operação
manual esteja bem preenchida e voltar a gravar o módulo por cima.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.domain.custeio_linha_types import OPERACAO_MANUAL  # noqa: E402
from app.models import (  # noqa: E402
    DefModulo,
    DefModuloLinha,
    OrcamentoItemCusteioLinha,
)


@dataclass
class Plano:
    """O que se vai (ou não) fazer a uma linha de módulo."""

    modulo: str
    linha_id: int
    descricao: str
    def_maquina_id: int | None = None
    minutos_unitarios: object = None
    motivo: str = ""

    @property
    def resolvido(self) -> bool:
        return self.def_maquina_id is not None and self.minutos_unitarios is not None


def _chave(texto: str | None) -> str:
    return " ".join((texto or "").strip().upper().split())


def _tempos_conhecidos(session) -> dict[str, set[tuple]]:
    """Descrição -> conjunto de (máquina, minutos) vistos nos orçamentos reais."""
    conhecidos: dict[str, set[tuple]] = defaultdict(set)
    linhas = session.execute(
        select(OrcamentoItemCusteioLinha).where(
            OrcamentoItemCusteioLinha.tipo_linha == OPERACAO_MANUAL,
            OrcamentoItemCusteioLinha.minutos_unitarios.is_not(None),
            OrcamentoItemCusteioLinha.def_maquina_id.is_not(None),
        )
    ).scalars().all()
    for linha in linhas:
        chave = _chave(linha.descricao_livre or linha.descricao)
        if chave:
            conhecidos[chave].add(
                (linha.def_maquina_id, str(linha.minutos_unitarios))
            )
    return conhecidos


def reparar(aplicar: bool) -> list[Plano]:
    """Correr a reparação (ou a simulação) e devolver o que foi encontrado."""
    planos: list[Plano] = []

    with SessionLocal() as session:
        conhecidos = _tempos_conhecidos(session)

        linhas = session.execute(
            select(DefModuloLinha, DefModulo)
            .join(DefModulo, DefModulo.id == DefModuloLinha.def_modulo_id)
            .where(DefModuloLinha.tipo_linha == OPERACAO_MANUAL)
            .order_by(DefModulo.codigo.asc(), DefModuloLinha.ordem.asc())
        ).all()

        for linha, modulo in linhas:
            descricao = linha.descricao_livre or linha.descricao or ""
            plano = Plano(
                modulo=modulo.codigo, linha_id=linha.id, descricao=descricao
            )

            if linha.def_maquina_id is not None and linha.minutos_unitarios is not None:
                plano.motivo = "já tem máquina e tempo"
                planos.append(plano)
                continue

            candidatos = conhecidos.get(_chave(descricao), set())
            if not candidatos:
                plano.motivo = (
                    "nenhum orçamento tem uma operação manual com esta descrição"
                )
            elif len(candidatos) > 1:
                plano.motivo = (
                    "tempos diferentes nos orçamentos para a mesma descrição: "
                    + "; ".join(
                        f"máquina {m} · {t} min" for m, t in sorted(candidatos)
                    )
                )
            else:
                maquina_id, minutos = next(iter(candidatos))
                plano.def_maquina_id = maquina_id
                plano.minutos_unitarios = minutos
                if aplicar:
                    linha.def_maquina_id = maquina_id
                    linha.minutos_unitarios = minutos

            planos.append(plano)

        if aplicar:
            session.commit()

    return planos


def _imprimir(planos: list[Plano], aplicar: bool) -> None:
    """Relatório em texto simples do que se encontrou/fez."""
    if not planos:
        print("Nenhum módulo tem linhas de operação manual. Nada a fazer.")
        return

    resolvidos = [plano for plano in planos if plano.resolvido]
    for plano in planos:
        print("")
        print(f"{plano.modulo} · linha {plano.linha_id} · {plano.descricao}")
        if plano.resolvido:
            verbo = "reposto" if aplicar else "a repor"
            print(
                f"   {verbo}: máquina {plano.def_maquina_id} · "
                f"{plano.minutos_unitarios} min por unidade"
            )
        else:
            print(f"   deixado como está: {plano.motivo}")

    print("")
    if not aplicar:
        print(
            f"SIMULAÇÃO — nada foi gravado. {len(resolvidos)} linha(s) seriam "
            "repostas. Volte a correr com --aplicar para gravar."
        )
    else:
        print(f"GRAVADO — {len(resolvidos)} linha(s) repostas.")
        print(
            "Os orçamentos que JÁ importaram estes módulos não mudam sozinhos: "
            "aí é preciso corrigir a linha à mão ou voltar a importar o módulo."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="grava mesmo (sem isto é só simulação)",
    )
    args = parser.parse_args()

    try:
        planos = reparar(args.aplicar)
    except SQLAlchemyError as error:
        print(f"Erro a falar com a base de dados: {error}")
        return 1

    _imprimir(planos, args.aplicar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
