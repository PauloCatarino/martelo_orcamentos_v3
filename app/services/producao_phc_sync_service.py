"""Estados que vem de fora: o que o PHC/Streamlit ja' fechou ou arquivou.

**Quem manda em cada estado.** O ``Desenho`` e a ``Producao`` sao do utilizador
-- e' ele que os marca no Martelo enquanto trabalha na obra. O ``Finalizado`` e
o ``Arquivado`` nunca se escolhem aqui: sao atribuidos por outras pessoas da
empresa, no PHC (encomendas de cliente) ou no Streamlit (cliente final, os
numeros com ``_``). Por isso so' estes dois e' que se leem la' fora.

Ate' 2026-09 lia-se tambem o ``2 - DESENHO`` e o ``4 - PRODUCAO`` do PHC. Numa
comparacao com dados reais isso dava 52 sugestoes por cima do trabalho de quem
esta' na obra -- 14 delas a desarquivar obras ja' fechadas.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.producao_estados import avanca_na_vida_da_obra
from app.models.producao import Producao
from app.services.encomendas_phc_service import query_phc_estado_debug_rows
from app.services.estado_producao_service import (
    TIPO_STREAMLIT,
    _ano_norm,
    _norm_streamlit,
)
from app.services.streamlit_sql_service import query_encomendas_cliente_final

TIPO_PASTA_PHC = "Encomenda de Cliente"


def _norm_num(valor) -> str:
    digits = re.sub(r"\D", "", str(valor or ""))
    return str(int(digits)) if digits else ""


def _norm_txt(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "").strip())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().upper()


def _estado_phc_text(row: dict) -> str:
    return (
        str(row.get("Estado_PHC") or "").strip()
        or str(row.get("BO_Tabela1") or "").strip()
        or str(row.get("BI_Tabela1") or "").strip()
    )


def _map_phc_estado(texto) -> str | None:
    """So' o ``5 - FINALIZADO`` e o ``7 - ARQUIVADO`` do PHC interessam ca'.

    O PHC tem mais estados -- ``3 - STANDBY``, ``8 - SERVICOS``,
    ``6 - FALTA PAG`` -- que nao existem no Martelo, e o ``2 - DESENHO`` e o
    ``4 - PRODUCAO``, que sao do utilizador. Todos esses ficam de fora.
    """
    t = _norm_txt(texto)
    if not t:
        return None
    if "ARQUIV" in t:
        return "Arquivado"
    if "FINALIZ" in t:
        return "Finalizado"
    return None


def _mapear_status_streamlit(status_raw) -> str | None:
    """Map Streamlit Status to a terminal production state."""
    t = _norm_txt(status_raw)
    if not t:
        return None
    if "ARQUIV" in t or re.search(r"(?<!\d)7(?!\d)", t):
        return "Arquivado"
    if "FINALIZ" in t or re.search(r"(?<!\d)5(?!\d)", t):
        return "Finalizado"
    return None


def _filtrar_responsavel(processos, responsavel):
    if not responsavel:
        return list(processos)
    alvo = responsavel.strip().casefold()
    return [
        processo
        for processo in processos
        if (processo.responsavel or "").strip().casefold() == alvo
    ]


def detetar_diferencas_estado_phc(
    session: Session,
    *,
    responsavel=None,
) -> list[dict]:
    """Return production processes whose local state differs from PHC."""
    processos = (
        session.execute(
            select(Producao).where(
                Producao.tipo_pasta == TIPO_PASTA_PHC,
                Producao.num_enc_phc.is_not(None),
                Producao.ano.is_not(None),
            )
        )
        .scalars()
        .all()
    )

    if responsavel:
        alvo = responsavel.strip().casefold()
        processos = [
            processo
            for processo in processos
            if (processo.responsavel or "").strip().casefold() == alvo
        ]

    anos = sorted({str(p.ano).strip() for p in processos if str(p.ano or "").strip()})
    idx: dict[tuple[str, str], list[str]] = {}
    for ano in anos:
        for row in query_phc_estado_debug_rows(session, ano=ano, max_rows=0):
            chave = (str(row.get("Ano") or "").strip(), _norm_num(row.get("Enc_No")))
            if chave[0] and chave[1]:
                idx.setdefault(chave, []).append(_estado_phc_text(row))

    diffs = []
    for processo in processos:
        chave = (str(processo.ano).strip(), _norm_num(processo.num_enc_phc))
        sugerido = None
        phc_raw = ""
        for estado_phc in idx.get(chave, []):
            mapeado = _map_phc_estado(estado_phc)
            if mapeado:
                sugerido, phc_raw = mapeado, estado_phc
                break

        atual = (processo.estado or "").strip()
        if sugerido and avanca_na_vida_da_obra(atual, sugerido):
            diffs.append(
                {
                    "id": processo.id,
                    "codigo": (processo.codigo_processo or "").strip(),
                    "num_enc_phc": (processo.num_enc_phc or "").strip(),
                    "cliente": (processo.nome_cliente or "").strip(),
                    "estado_martelo": atual or "(sem estado)",
                    "estado_sugerido": sugerido,
                    "estado_phc_raw": phc_raw,
                    "fonte": "PHC",
                    "responsavel": (processo.responsavel or "").strip(),
                    "data_entrega": (processo.data_entrega or "").strip(),
                    "ref_cliente": (processo.ref_cliente or "").strip(),
                }
            )

    diffs.sort(key=lambda d: d["codigo"].casefold())
    return diffs


def detetar_diferencas_estado_streamlit(
    session: Session,
    *,
    responsavel=None,
) -> list[dict]:
    """Return Cliente Final processes whose local state differs from Streamlit."""
    processos = (
        session.execute(
            select(Producao).where(
                Producao.tipo_pasta == TIPO_STREAMLIT,
                Producao.num_enc_phc.is_not(None),
                Producao.ano.is_not(None),
            )
        )
        .scalars()
        .all()
    )
    processos = _filtrar_responsavel(processos, responsavel)

    anos = sorted({_ano_norm(p.ano) for p in processos if _ano_norm(p.ano)})
    if not processos or not anos:
        return []

    status_idx: dict[tuple[str, str], object] = {}
    try:
        linhas_enc = query_encomendas_cliente_final(
            session,
            ano_minimo=int(min(anos)),
        )
    except Exception:
        linhas_enc = []
    for row in linhas_enc:
        ano = _ano_norm(row.get("Ano"))
        numero = _norm_streamlit(row.get("Numero"))
        if ano in anos and numero:
            status_idx[(ano, numero)] = row.get("Status")

    diffs = []
    for processo in processos:
        ano = _ano_norm(processo.ano)
        numero = _norm_streamlit(processo.num_enc_phc)
        status_raw = status_idx.get((ano, numero))
        # Sem Status legivel nao ha' nada a dizer. Antes adivinhava-se aqui
        # "Desenho" ou "Producao" pelas percentagens de corte/orla/CNC -- e
        # essa adivinha ia escrever por cima do estado que e' do utilizador.
        sugerido = _mapear_status_streamlit(status_raw)

        atual = (processo.estado or "").strip()
        if sugerido and avanca_na_vida_da_obra(atual, sugerido):
            status_texto = "" if status_raw is None else str(status_raw).strip()
            diffs.append(
                {
                    "id": processo.id,
                    "codigo": (processo.codigo_processo or "").strip(),
                    "num_enc_phc": (processo.num_enc_phc or "").strip(),
                    "cliente": (processo.nome_cliente or "").strip(),
                    "estado_martelo": atual or "(sem estado)",
                    "estado_sugerido": sugerido,
                    "estado_phc_raw": status_texto or "(sem dados)",
                    "fonte": "Streamlit",
                    "responsavel": (processo.responsavel or "").strip(),
                    "data_entrega": (processo.data_entrega or "").strip(),
                    "ref_cliente": (processo.ref_cliente or "").strip(),
                }
            )

    diffs.sort(key=lambda d: d["codigo"].casefold())
    return diffs


@dataclass(frozen=True)
class LevantamentoEstados:
    """O que as duas fontes disseram, e o que correu mal em cada uma."""

    diferencas: list[dict]
    erro_phc: str = ""
    erro_streamlit: str = ""

    def __bool__(self) -> bool:
        return bool(self.diferencas)

    @property
    def falharam_as_duas(self) -> bool:
        return bool(self.erro_phc) and bool(self.erro_streamlit)


def levantar_estados_de_fora(
    session_factory,
    *,
    responsavel=None,
) -> LevantamentoEstados:
    """Perguntar a`s duas fontes, sem deixar que uma estrague a outra.

    O PHC e o Streamlit sao dois servidores diferentes: um pode estar em baixo
    e o outro nao. Cada um leva a sua sessao e o seu ``try`` para que a metade
    que responde continue a valer.
    """
    diferencas: list[dict] = []
    erro_phc = ""
    erro_streamlit = ""

    try:
        with session_factory() as session:
            diferencas.extend(
                detetar_diferencas_estado_phc(session, responsavel=responsavel)
            )
    except Exception as erro:  # noqa: BLE001 - ligacao/SQL/config sao externos
        erro_phc = str(erro)

    try:
        with session_factory() as session:
            diferencas.extend(
                detetar_diferencas_estado_streamlit(session, responsavel=responsavel)
            )
    except Exception as erro:  # noqa: BLE001 - ligacao/SQL/config sao externos
        erro_streamlit = str(erro)

    diferencas.sort(key=lambda d: d["codigo"].casefold())
    return LevantamentoEstados(
        diferencas=diferencas,
        erro_phc=erro_phc,
        erro_streamlit=erro_streamlit,
    )


def aplicar_estados(
    session: Session,
    atualizacoes,
    *,
    current_user_id=None,
) -> int:
    """Apply selected state updates and commit them."""
    n = 0
    for proc_id, novo_estado in atualizacoes:
        processo = session.get(Producao, int(proc_id))
        if processo is None:
            continue
        processo.estado = novo_estado
        if current_user_id is not None:
            processo.updated_by_id = current_user_id
        n += 1
    session.commit()
    return n
