"""Tempo ativo no iMos e na Lista Material: gravar e ligar às obras.

Grava-se por nome de encomenda (o que a janela mostra); a ligação à obra da
Produção faz-se aqui, na leitura, com a mesma regra que dá o nome à encomenda
no iMos. Duas obras podem dar o mesmo nome — o plano não entra nele
(``1211_01_01`` e ``1211_01_02`` são ambas ``1211_01_26_STHINK``). Nesse caso
cada uma mostra o tempo da encomenda e sabe com quem o partilha: dividir seria
inventar um número que ninguém mediu (decisão do Paulo, 24-09-2026).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.tempo_programas import (
    PROGRAMA_EXCEL,
    PROGRAMA_IMOS,
    TAMANHO_NOME,
    chave_encomenda,
)
from app.models import ProducaoTempoAtividade
from app.models.user import User

_PROGRAMAS = (PROGRAMA_IMOS, PROGRAMA_EXCEL)


@dataclass
class TempoObra:
    """O tempo de uma obra, pronto a mostrar."""

    desenho: int = 0
    excel: int = 0
    #: nome da pessoa → [segundos de desenho, segundos de Excel]
    por_pessoa: dict[str, list[int]] = field(default_factory=dict)
    #: Códigos das outras obras com a mesma encomenda no iMos.
    partilhado_com: tuple[str, ...] = ()

    def segundos(self, programa: str) -> int:
        return self.desenho if programa == PROGRAMA_IMOS else self.excel


class ProducaoTempoAtividadeService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def adicionar_segundos(
        self,
        user_id: int,
        programa: str,
        nome_encomenda: str,
        dia: date,
        segundos: int,
    ) -> None:
        """Somar segundos ao dia desta pessoa nesta encomenda (sem commit)."""
        utilizador = int(user_id)
        incremento = int(segundos)
        nome = str(nome_encomenda or "").strip()[:TAMANHO_NOME]
        if utilizador <= 0 or programa not in _PROGRAMAS or not nome:
            raise ValueError("Utilizador, programa e encomenda são obrigatórios.")
        if incremento <= 0:
            return

        filtro = (
            ProducaoTempoAtividade.user_id == utilizador,
            ProducaoTempoAtividade.programa == programa,
            ProducaoTempoAtividade.nome_encomenda == nome,
            ProducaoTempoAtividade.dia == dia,
        )
        somar = (
            update(ProducaoTempoAtividade)
            .where(*filtro)
            .values(segundos=ProducaoTempoAtividade.segundos + incremento)
        )
        if self.session.execute(somar).rowcount:
            return

        try:
            # Dentro do savepoint, para a linha sair da sessão se falhar.
            with self.session.begin_nested():
                self.session.add(
                    ProducaoTempoAtividade(
                        user_id=utilizador,
                        programa=programa,
                        nome_encomenda=nome,
                        dia=dia,
                        segundos=incremento,
                    )
                )
                self.session.flush()
        except IntegrityError:
            # O mesmo utilizador em dois PCs ao mesmo tempo: a restrição
            # única decide, e soma-se na linha que ficou.
            self.session.execute(somar)

    def tempos_por_obra(self, processos: Iterable) -> dict[int, TempoObra]:
        """``{id da obra: TempoObra}`` para as obras com tempo registado."""
        obras = [p for p in processos if getattr(p, "id", None) is not None]
        chaves_por_obra = {p.id: chaves_da_obra(p) for p in obras}
        obras_por_chave: dict[str, list] = defaultdict(list)
        for processo in obras:
            for chave in chaves_por_obra[processo.id]:
                obras_por_chave[chave].append(processo)

        linhas = self.session.execute(
            select(
                ProducaoTempoAtividade.nome_encomenda,
                ProducaoTempoAtividade.programa,
                ProducaoTempoAtividade.user_id,
                func.sum(ProducaoTempoAtividade.segundos),
            ).group_by(
                ProducaoTempoAtividade.nome_encomenda,
                ProducaoTempoAtividade.programa,
                ProducaoTempoAtividade.user_id,
            )
        ).all()
        por_chave: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
        for nome, programa, user_id, segundos in linhas:
            chave = chave_encomenda(nome)
            if chave in obras_por_chave:
                por_chave[chave].append((programa, int(user_id), int(segundos or 0)))

        nomes = self._nomes_utilizadores(
            {user_id for regs in por_chave.values() for _p, user_id, _s in regs}
        )

        resultado: dict[int, TempoObra] = {}
        for processo in obras:
            chaves = chaves_por_obra[processo.id]
            registos = [r for chave in chaves for r in por_chave.get(chave, ())]
            if not registos:
                continue
            tempo = TempoObra()
            for programa, user_id, segundos in registos:
                pessoa = tempo.por_pessoa.setdefault(
                    nomes.get(user_id, f"#{user_id}"), [0, 0]
                )
                if programa == PROGRAMA_IMOS:
                    tempo.desenho += segundos
                    pessoa[0] += segundos
                elif programa == PROGRAMA_EXCEL:
                    tempo.excel += segundos
                    pessoa[1] += segundos
            outras = {
                str(getattr(o, "codigo_processo", "") or o.id)
                for chave in chaves
                for o in obras_por_chave.get(chave, ())
                if o.id != processo.id
            }
            tempo.partilhado_com = tuple(sorted(outras))
            resultado[processo.id] = tempo
        return resultado

    def _nomes_utilizadores(self, ids: set[int]) -> dict[int, str]:
        if not ids:
            return {}
        linhas = self.session.execute(
            select(User.id, User.nome, User.username).where(User.id.in_(ids))
        ).all()
        return {uid: (nome or username or f"#{uid}") for uid, nome, username in linhas}


def chaves_da_obra(processo) -> set[str]:
    """Os nomes por que esta obra pode aparecer no título da janela.

    O guardado quando o Martelo criou a encomenda no iMos, e o que a regra de
    nomes dá — inteiro e cortado aos 30 caracteres do iMos, para as encomendas
    criadas à mão no iX Organizer com nomes compridos.
    """
    from app.services.imos_encomenda_service import nome_encomenda_sugerido
    from app.services.imos_sql import IMOS_NOME_MAX

    chaves: set[str] = set()
    guardado = getattr(processo, "imos_nome_encomenda", None)
    if guardado:
        chaves.add(chave_encomenda(guardado))
    derivado = nome_encomenda_sugerido(processo)
    if derivado:
        chaves.add(chave_encomenda(derivado))
        chaves.add(chave_encomenda(derivado[:IMOS_NOME_MAX]))
    chaves.discard("")
    return chaves
