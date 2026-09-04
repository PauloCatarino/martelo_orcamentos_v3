"""Repor as operacoes do ValueSet nas versoes que nasceram de uma duplicacao.

O QUE ISTO ARRANJA
------------------
Ate' esta correcao, duplicar uma versao de orcamento copiava as linhas do
ValueSet do orcamento mas **nao** copiava as operacoes penduradas nessas linhas
(a montagem/CNC/embalamento das ferragens). Depois, quando o item herdava esse
ValueSet, a heranca apagava as operacoes que o item ja' tinha e nao repunha
nenhuma. Resultado: a versao duplicada saia MAIS BARATA do que a original.

Foi assim que o 260877_02 ficou 113 operacoes -> 0 e perdeu 5,85 EUR de
producao em relacao ao 260877_01.

O script procura versoes com linhas de ValueSet sem nenhuma operacao, vai buscar
a versao mais antiga do mesmo orcamento que ainda as tenha, e copia as operacoes
para as linhas que emparelhem por (chave, codigo da opcao). Faz o mesmo ao nivel
do item.

COMO SE USA
-----------
    # ver o que ia fazer, sem gravar nada
    .venv\\Scripts\\python.exe scripts\\reparar_operacoes_valueset_versoes.py

    # gravar
    .venv\\Scripts\\python.exe scripts\\reparar_operacoes_valueset_versoes.py --aplicar

    # so' uma versao
    .venv\\Scripts\\python.exe scripts\\reparar_operacoes_valueset_versoes.py --versao 36

Depois de aplicar, ABRIR CADA ORCAMENTO E CARREGAR EM "Atualizar Custos": as
operacoes voltam a` tabela mas os custos so' mudam quando a pipeline correr.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import sys

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Orcamento,
    OrcamentoItem,
    OrcamentoItemValuesetLinha,
    OrcamentoItemValuesetLinhaOperacao,
    OrcamentoValuesetLinha,
    OrcamentoValuesetLinhaOperacao,
    OrcamentoVersao,
)


@dataclass
class PlanoVersao:
    """O que ha' a repor numa versao."""

    versao_id: int
    codigo_versao: str
    estado: str
    origem_id: int | None = None
    origem_codigo: str = ""
    operacoes_versao: int = 0
    linhas_versao: int = 0
    operacoes_item: int = 0
    linhas_item: int = 0
    avisos: list[str] = field(default_factory=list)

    @property
    def tem_trabalho(self) -> bool:
        return bool(self.operacoes_versao or self.operacoes_item)


def _valores_para_copia(origem, *, exclui: set[str]) -> dict:
    """Valores das colunas de um objeto ORM, prontos para criar uma copia."""
    excluidos = {"id", "created_at", "updated_at"} | exclui
    mapper = sa_inspect(type(origem))
    return {
        attr.key: getattr(origem, attr.key)
        for attr in mapper.column_attrs
        if attr.key not in excluidos
    }


def _chave_opcao(linha) -> tuple[str, str]:
    """Identidade de uma opcao de ValueSet, para emparelhar duas versoes."""
    chave = " ".join(str(linha.chave or "").strip().upper().split())
    codigo = " ".join(
        str(linha.codigo_opcao or linha.nome_opcao or "").strip().upper().split()
    )
    return chave, codigo


def _contar_operacoes_versao(session, versao_id: int) -> tuple[int, int]:
    """(linhas de ValueSet, operacoes) de uma versao."""
    linhas = session.execute(
        select(OrcamentoValuesetLinha).where(
            OrcamentoValuesetLinha.orcamento_versao_id == versao_id
        )
    ).scalars().all()
    if not linhas:
        return 0, 0
    ids = [linha.id for linha in linhas]
    operacoes = session.execute(
        select(OrcamentoValuesetLinhaOperacao).where(
            OrcamentoValuesetLinhaOperacao.orcamento_valueset_linha_id.in_(ids)
        )
    ).scalars().all()
    return len(linhas), len(operacoes)


def _versoes_candidatas(session, versao_id: int | None) -> list[OrcamentoVersao]:
    """Versoes com ValueSet mas sem uma unica operacao (ou a versao pedida)."""
    versoes = session.execute(
        select(OrcamentoVersao).order_by(OrcamentoVersao.id.asc())
    ).scalars().all()
    if versao_id is not None:
        return [versao for versao in versoes if versao.id == versao_id]

    candidatas = []
    for versao in versoes:
        linhas, operacoes = _contar_operacoes_versao(session, versao.id)
        if linhas and not operacoes:
            candidatas.append(versao)
    return candidatas


def _versao_origem(session, versao: OrcamentoVersao) -> OrcamentoVersao | None:
    """A versao mais antiga do mesmo orcamento que ainda tenha operacoes."""
    irmas = session.execute(
        select(OrcamentoVersao)
        .where(
            OrcamentoVersao.orcamento_id == versao.orcamento_id,
            OrcamentoVersao.id != versao.id,
        )
        .order_by(OrcamentoVersao.numero_versao.asc())
    ).scalars().all()

    for irma in irmas:
        _linhas, operacoes = _contar_operacoes_versao(session, irma.id)
        if operacoes:
            return irma
    return None


def _reparar_nivel_versao(session, plano: PlanoVersao, origem_id: int, aplicar: bool):
    """Copiar as operacoes das linhas de ValueSet da versao de origem."""
    origem_linhas = session.execute(
        select(OrcamentoValuesetLinha).where(
            OrcamentoValuesetLinha.orcamento_versao_id == origem_id
        )
    ).scalars().all()
    destino_linhas = session.execute(
        select(OrcamentoValuesetLinha).where(
            OrcamentoValuesetLinha.orcamento_versao_id == plano.versao_id
        )
    ).scalars().all()

    por_chave = {}
    for linha in origem_linhas:
        por_chave.setdefault(_chave_opcao(linha), linha)

    sem_par = 0
    for destino in destino_linhas:
        origem = por_chave.get(_chave_opcao(destino))
        if origem is None:
            sem_par += 1
            continue

        ja_tem = session.execute(
            select(OrcamentoValuesetLinhaOperacao).where(
                OrcamentoValuesetLinhaOperacao.orcamento_valueset_linha_id == destino.id
            )
        ).scalars().first()
        if ja_tem is not None:
            continue

        operacoes = session.execute(
            select(OrcamentoValuesetLinhaOperacao)
            .where(
                OrcamentoValuesetLinhaOperacao.orcamento_valueset_linha_id == origem.id
            )
            .order_by(
                OrcamentoValuesetLinhaOperacao.ordem.asc(),
                OrcamentoValuesetLinhaOperacao.id.asc(),
            )
        ).scalars().all()
        if not operacoes:
            continue

        plano.linhas_versao += 1
        plano.operacoes_versao += len(operacoes)
        if aplicar:
            for operacao in operacoes:
                dados = _valores_para_copia(
                    operacao, exclui={"orcamento_valueset_linha_id"}
                )
                session.add(
                    OrcamentoValuesetLinhaOperacao(
                        **dados, orcamento_valueset_linha_id=destino.id
                    )
                )

    if sem_par:
        plano.avisos.append(
            f"{sem_par} linha(s) de ValueSet da versao sem par na origem "
            "(chave/opcao diferente) — ficam como estao."
        )


def _reparar_nivel_item(session, plano: PlanoVersao, origem_id: int, aplicar: bool):
    """Copiar as operacoes das linhas de ValueSet item a item."""
    itens_origem = session.execute(
        select(OrcamentoItem)
        .where(OrcamentoItem.orcamento_versao_id == origem_id)
        .order_by(OrcamentoItem.ordem.asc(), OrcamentoItem.id.asc())
    ).scalars().all()
    itens_destino = session.execute(
        select(OrcamentoItem)
        .where(OrcamentoItem.orcamento_versao_id == plano.versao_id)
        .order_by(OrcamentoItem.ordem.asc(), OrcamentoItem.id.asc())
    ).scalars().all()

    # Os itens emparelham pelo codigo; havendo repetidos, pela ordem de entrada.
    origem_por_codigo = defaultdict(list)
    for item in itens_origem:
        origem_por_codigo[(item.codigo or item.item or "").strip().upper()].append(item)

    for destino in itens_destino:
        candidatos = origem_por_codigo.get((destino.codigo or destino.item or "").strip().upper())
        if not candidatos:
            plano.avisos.append(
                f"Item {destino.codigo or destino.item!r} sem correspondencia na "
                "versao de origem — ficou como estava."
            )
            continue
        origem_item = candidatos.pop(0)

        origem_linhas = session.execute(
            select(OrcamentoItemValuesetLinha).where(
                OrcamentoItemValuesetLinha.orcamento_item_id == origem_item.id
            )
        ).scalars().all()
        destino_linhas = session.execute(
            select(OrcamentoItemValuesetLinha).where(
                OrcamentoItemValuesetLinha.orcamento_item_id == destino.id
            )
        ).scalars().all()

        por_chave = {}
        for linha in origem_linhas:
            por_chave.setdefault(_chave_opcao(linha), linha)

        for destino_linha in destino_linhas:
            origem_linha = por_chave.get(_chave_opcao(destino_linha))
            if origem_linha is None:
                continue

            ja_tem = session.execute(
                select(OrcamentoItemValuesetLinhaOperacao).where(
                    OrcamentoItemValuesetLinhaOperacao.orcamento_item_valueset_linha_id
                    == destino_linha.id
                )
            ).scalars().first()
            if ja_tem is not None:
                continue

            operacoes = session.execute(
                select(OrcamentoItemValuesetLinhaOperacao)
                .where(
                    OrcamentoItemValuesetLinhaOperacao.orcamento_item_valueset_linha_id
                    == origem_linha.id
                )
                .order_by(
                    OrcamentoItemValuesetLinhaOperacao.ordem.asc(),
                    OrcamentoItemValuesetLinhaOperacao.id.asc(),
                )
            ).scalars().all()
            if not operacoes:
                continue

            plano.linhas_item += 1
            plano.operacoes_item += len(operacoes)
            if aplicar:
                for operacao in operacoes:
                    dados = _valores_para_copia(
                        operacao, exclui={"orcamento_item_valueset_linha_id"}
                    )
                    session.add(
                        OrcamentoItemValuesetLinhaOperacao(
                            **dados,
                            orcamento_item_valueset_linha_id=destino_linha.id,
                        )
                    )


def reparar(versao_id: int | None, aplicar: bool) -> list[PlanoVersao]:
    """Correr a reparacao (ou a simulacao) e devolver o que foi encontrado."""
    planos: list[PlanoVersao] = []

    with SessionLocal() as session:
        for versao in _versoes_candidatas(session, versao_id):
            orcamento = session.get(Orcamento, versao.orcamento_id)
            plano = PlanoVersao(
                versao_id=versao.id,
                codigo_versao=versao.codigo_versao,
                estado=versao.estado,
            )

            origem = _versao_origem(session, versao)
            if origem is None:
                plano.avisos.append(
                    "Nenhuma outra versao deste orcamento tem operacoes de "
                    "ValueSet — nao ha' de onde copiar."
                )
                planos.append(plano)
                continue

            plano.origem_id = origem.id
            plano.origem_codigo = origem.codigo_versao
            _reparar_nivel_versao(session, plano, origem.id, aplicar)
            _reparar_nivel_item(session, plano, origem.id, aplicar)
            planos.append(plano)

            if orcamento is None:
                plano.avisos.append("Orcamento nao encontrado (so' informativo).")

        if aplicar:
            session.commit()

    return planos


def _imprimir(planos: list[PlanoVersao], aplicar: bool) -> None:
    """Relatorio em texto simples do que se encontrou/fez."""
    if not planos:
        print("Nao ha' versoes com o ValueSet sem operacoes. Nada a fazer.")
        return

    verbo = "Reposto" if aplicar else "A repor"
    for plano in planos:
        print("")
        print(f"Versao {plano.codigo_versao} (id {plano.versao_id}) — {plano.estado}")
        if plano.origem_id is None:
            print("   sem versao de origem utilizavel")
        else:
            print(f"   copiado de: {plano.origem_codigo} (id {plano.origem_id})")
            print(
                f"   {verbo} no ValueSet do orcamento: "
                f"{plano.operacoes_versao} operacao(oes) em {plano.linhas_versao} linha(s)"
            )
            print(
                f"   {verbo} no ValueSet dos itens:    "
                f"{plano.operacoes_item} operacao(oes) em {plano.linhas_item} linha(s)"
            )
        for aviso in plano.avisos:
            print(f"   aviso: {aviso}")

    total = sum(plano.operacoes_versao + plano.operacoes_item for plano in planos)
    print("")
    if not aplicar:
        print(
            f"SIMULACAO — nada foi gravado. {total} operacao(oes) seriam repostas. "
            "Volte a correr com --aplicar para gravar."
        )
    else:
        print(f"GRAVADO — {total} operacao(oes) repostas.")
        print(
            "Falta agora abrir cada um destes orcamentos e carregar em "
            "'Atualizar Custos' para os precos acompanharem."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="grava mesmo (sem isto e' so' simulacao)",
    )
    parser.add_argument(
        "--versao",
        type=int,
        default=None,
        help="tratar so' esta versao (id da tabela orcamento_versoes)",
    )
    args = parser.parse_args()

    try:
        planos = reparar(args.versao, args.aplicar)
    except SQLAlchemyError as error:
        print(f"Erro a falar com a base de dados: {error}")
        return 1

    _imprimir(planos, args.aplicar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
