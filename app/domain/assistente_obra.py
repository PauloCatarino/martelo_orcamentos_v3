"""Pedidos sobre UMA obra: «faz relatório/texto/email da obra 1134».

Distingue-se da pesquisa: aqui o utilizador aponta a uma obra concreta (pelo nº
de encomenda) e pede uma AÇÃO — um texto, um PDF ou um email com o estado e as
fases de produção. Este módulo é puro (sem BD/SQL): identifica o pedido e monta
o texto a partir de um dossier já preenchido pelo serviço.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.domain.pesquisa_texto import normalizar

#: Palavras que indicam uma AÇÃO/estado sobre uma obra (não uma pesquisa).
_GATILHOS = frozenset(
    {
        "relatorio", "pdf", "texto", "escreve", "escrever", "resume", "resumir",
        "resumo", "email", "mail", "estado", "situacao", "ponto", "fase", "fases",
        "como", "andamento", "andar", "producao",
    }
)

#: Palavra «obra»/«encomenda»/«phc» imediatamente antes do número reforça-o.
_ROTULOS_OBRA = frozenset({"obra", "encomenda", "enc", "phc", "processo"})

_MODO_EMAIL = "email"
_MODO_PDF = "pdf"
_MODO_TEXTO = "texto"


@dataclass(frozen=True)
class PedidoObra:
    """Pedido de ação sobre uma obra: o número e o modo de resposta."""

    numero: str
    modo: str = _MODO_TEXTO  # "texto" | "pdf" | "email"


@dataclass(frozen=True)
class DossierObra:
    """Tudo o que se sabe de uma obra para compor a resposta (já resolvido)."""

    codigo: str = ""
    enc: str = ""
    cliente: str = ""
    obra: str = ""
    ref_cliente: str = ""
    localizacao: str = ""
    responsavel: str = ""
    estado_local: str = ""
    data_inicio: str = ""
    data_entrega: str = ""
    descricao_producao: str = ""
    notas: str = ""
    #: Pasta da obra no servidor, para guardar o PDF lá por defeito.
    pasta: str = ""
    #: (nome do setor, percentagem, concluído) pela ordem de produção.
    fases: tuple[tuple[str, float, bool], ...] = ()
    estado_global: str = ""
    encontrado_streamlit: bool = False


def identificar_pedido(pergunta: object) -> PedidoObra | None:
    """Deteta «ação sobre uma obra» e devolve (número, modo), ou None.

    É preciso um número de obra E um gatilho de ação/estado (ou o rótulo
    «obra/encomenda/phc» antes do número); assim «obras atrasadas» (pesquisa)
    não é confundido com um pedido de obra.
    """
    texto = normalizar(pergunta)
    if not texto:
        return None

    palavras = texto.split()
    numero = _extrair_numero(palavras)
    if not numero:
        return None

    tem_gatilho = any(p in _GATILHOS for p in palavras)
    tem_rotulo = _tem_rotulo_antes_do_numero(palavras, numero)
    if not (tem_gatilho or tem_rotulo):
        return None

    return PedidoObra(numero=numero, modo=_modo(palavras))


def resumo_texto(dossier: DossierObra) -> str:
    """Resumo natural do estado da obra (para copiar p/ WhatsApp/email)."""
    identidade = dossier.codigo or (f"obra {dossier.enc}" if dossier.enc else "obra")
    cliente = f" ({dossier.cliente})" if dossier.cliente else ""
    linhas = [f"{identidade}{cliente}"]

    estado = dossier.estado_local or "—"
    linhas.append(f"Estado: {estado}.")
    if dossier.responsavel:
        linhas[-1] += f" Responsável: {dossier.responsavel}."
    if dossier.data_inicio or dossier.data_entrega:
        linhas.append(
            f"Início: {dossier.data_inicio or '—'} · "
            f"Entrega prevista: {dossier.data_entrega or '—'}."
        )
    if dossier.descricao_producao:
        linhas.append(dossier.descricao_producao.strip())

    if dossier.encontrado_streamlit and dossier.fases:
        fases = ", ".join(
            f"{nome} {pct:.0f}%" for nome, pct, _concluido in dossier.fases
        )
        cabeca = f"Produção: {dossier.estado_global}" if dossier.estado_global else "Produção"
        linhas.append(f"{cabeca} — {fases}.")
    else:
        linhas.append("Estado detalhado de produção indisponível de momento.")

    return "\n".join(linhas)


def _extrair_numero(palavras: list[str]) -> str:
    """Primeiro grupo de dígitos plausível como nº de encomenda (2-6 díg.)."""
    for palavra in palavras:
        digitos = re.sub(r"\D", "", palavra)
        if 2 <= len(digitos) <= 6:
            return digitos
    return ""


def _tem_rotulo_antes_do_numero(palavras: list[str], numero: str) -> bool:
    for indice, palavra in enumerate(palavras):
        if re.sub(r"\D", "", palavra) == numero and indice > 0:
            if palavras[indice - 1] in _ROTULOS_OBRA:
                return True
    return False


def _modo(palavras: list[str]) -> str:
    conjunto = set(palavras)
    if conjunto & {"email", "mail"}:
        return _MODO_EMAIL
    if conjunto & {"pdf", "relatorio"}:
        return _MODO_PDF
    return _MODO_TEXTO
