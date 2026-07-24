"""Pedidos sobre UMA obra: «faz relatório/texto/email da obra 1134».

Distingue-se da pesquisa: aqui o utilizador aponta a uma obra concreta (pelo nº
de encomenda) e pede uma AÇÃO — um texto, um PDF ou um email com o estado e as
fases de produção. Este módulo é puro (sem BD/SQL): identifica o pedido e monta
o texto a partir de um dossier já preenchido pelo serviço.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

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


#: Intervalo plausível para um ANO escrito na pergunta (distingue-o do nº obra).
_ANO_MIN, _ANO_MAX = 2000, 2099


@dataclass(frozen=True)
class PedidoObra:
    """Pedido de ação sobre uma obra: número, modo e (opcional) ano."""

    numero: str
    modo: str = _MODO_TEXTO  # "texto" | "pdf" | "email"
    #: Ano escrito na pergunta; vazio = deixar o serviço usar o ano atual.
    ano: str = ""


@dataclass(frozen=True)
class VersaoObra:
    """Uma versão da obra (V. Obra + V. CUT-RITE) com o seu estado de produção."""

    versao_obra: str = ""
    versao_plano: str = ""  # versão do plano de corte (CUT-RITE)
    codigo: str = ""
    estado_local: str = ""
    fases: tuple[tuple[str, float, bool], ...] = ()
    estado_global: str = ""
    encontrado_streamlit: bool = False


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
    #: Caminho da imagem IMOS (*.png) da obra principal (num_phc_versao).
    imagem_path: str = ""
    #: Email do cliente (dos dados do cliente); o utilizador pode alterá-lo.
    email_cliente: str = ""
    #: (nome do setor, percentagem, concluído) pela ordem de produção.
    fases: tuple[tuple[str, float, bool], ...] = ()
    estado_global: str = ""
    encontrado_streamlit: bool = False
    #: Todas as versões da obra (V. Obra / V. CUT-RITE), da mais antiga à recente.
    versoes: tuple[VersaoObra, ...] = ()


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
    numero, ano = _extrair_numero_e_ano(palavras)
    if not numero:
        return None

    tem_gatilho = any(p in _GATILHOS for p in palavras)
    tem_rotulo = _tem_rotulo_antes_do_numero(palavras, numero)
    if not (tem_gatilho or tem_rotulo):
        return None

    return PedidoObra(numero=numero, modo=_modo(palavras), ano=ano)


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


def _identidade(dossier: DossierObra) -> str:
    return dossier.codigo or (f"obra {dossier.enc}" if dossier.enc else "obra")


def saudacao_por_hora(hora: int) -> str:
    """Saudação portuguesa consoante a hora do dia (0-23)."""
    if 6 <= hora < 13:
        return "Bom dia"
    if 13 <= hora < 20:
        return "Boa tarde"
    return "Boa noite"


def assunto_email(dossier: DossierObra) -> str:
    """Assunto por defeito do email; junta Ref./Obra/Localização se existirem."""
    assunto = f"Ponto de situação — {_identidade(dossier)}"
    if dossier.cliente:
        assunto += f" ({dossier.cliente})"
    extras = [
        campo
        for campo in (dossier.ref_cliente, dossier.obra, dossier.localizacao)
        if campo
    ]
    if extras:
        assunto += " | " + " | ".join(extras)
    return assunto


def corpo_email_html(
    dossier: DossierObra,
    *,
    saudacao: str = "Boa tarde",
    utilizador: str = "",
    imagem_path: str = "",
) -> str:
    """Corpo HTML por defeito do email (sem notas internas nem preço).

    ``saudacao`` vem do horário (o utilizador pode alterar tudo antes de enviar).
    A Ref. do cliente fica em destaque — é a referência dele e o que lhe faz mais
    sentido. ``imagem_path`` (validado por quem chama) mostra a imagem IMOS da
    obra; ao enviar, o email_service passa-a a inline. Na fase seguinte, o LLM
    reescreve isto guiado pelas «Instruções».
    """
    linhas = [f"<p>{escape(saudacao)},</p>"]
    intro = (
        f"Segue o ponto de situação da obra <b>{escape(_identidade(dossier))}</b>"
    )
    if dossier.cliente:
        intro += f" ({escape(dossier.cliente)})"
    linhas.append(f"<p>{intro}.</p>")

    if imagem_path:
        try:
            uri = Path(imagem_path).as_uri()
            linhas.append(f'<p><img src="{uri}" width="480" /></p>')
        except (ValueError, OSError):
            pass

    if dossier.ref_cliente:
        linhas.append(
            f'<p style="font-size:14pt"><b>Ref. Cliente: '
            f"{escape(dossier.ref_cliente)}</b></p>"
        )

    factos = []
    if dossier.estado_local:
        factos.append(f"Estado: {escape(dossier.estado_local)}")
    if dossier.data_entrega:
        factos.append(f"Entrega prevista: {escape(dossier.data_entrega)}")
    if factos:
        linhas.append("<p>" + " · ".join(factos) + ".</p>")

    if dossier.encontrado_streamlit and dossier.fases:
        fases = ", ".join(
            f"{escape(str(nome))} {pct:.0f}%" for nome, pct, _c in dossier.fases
        )
        linhas.append(f"<p>Fases de produção: {fases}.</p>")

    linhas.append(
        "<p>Em anexo segue o ponto de situação detalhado, em PDF.</p>"
    )
    linhas.append(
        f"<p>Com os melhores cumprimentos,<br>{escape(utilizador)}</p>"
    )
    return "\n".join(linhas)


def _e_ano(digitos: str) -> bool:
    return len(digitos) == 4 and _ANO_MIN <= int(digitos) <= _ANO_MAX


def _extrair_numero_e_ano(palavras: list[str]) -> tuple[str, str]:
    """Separa o nº de encomenda (2-6 díg.) de um eventual ANO (20xx).

    O nº da obra prefere-se logo a seguir a «obra/encomenda/phc»; o ano é um
    20xx diferente do número. «obra 2027» (só um 20xx) é o próprio número.
    """
    tokens: list[tuple[int, str]] = []
    for indice, palavra in enumerate(palavras):
        digitos = re.sub(r"\D", "", palavra)
        if 2 <= len(digitos) <= 6:
            tokens.append((indice, digitos))
    if not tokens:
        return "", ""

    numero = ""
    for indice, digitos in tokens:
        if indice > 0 and palavras[indice - 1] in _ROTULOS_OBRA:
            numero = digitos
            break

    nao_anos = [d for _i, d in tokens if not _e_ano(d)]
    if not numero:
        numero = nao_anos[0] if nao_anos else tokens[0][1]

    ano = ""
    for _i, digitos in tokens:
        if _e_ano(digitos) and digitos != numero:
            ano = digitos
            break
    return numero, ano


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
