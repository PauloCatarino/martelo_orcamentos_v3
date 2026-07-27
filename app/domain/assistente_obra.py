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

#: Palavras que pedem a lista de tickets em vez do ponto de situação.
_PALAVRAS_OCORRENCIAS = frozenset(
    {
        "ocorrencia", "ocorrencias", "ticket", "tickets", "assistencia",
        "assistencias", "problema", "problemas", "reclamacao", "reclamacoes",
        "diario",
    }
)

#: Palavras que indicam uma AÇÃO/estado sobre uma obra (não uma pesquisa).
_GATILHOS = frozenset(
    {
        "relatorio", "pdf", "texto", "escreve", "escrever", "resume", "resumir",
        "resumo", "email", "mail", "estado", "situacao", "ponto", "fase", "fases",
        "como", "andamento", "andar", "producao",
    }
) | _PALAVRAS_OCORRENCIAS

#: Palavra «obra»/«encomenda»/«phc» imediatamente antes do número reforça-o.
_ROTULOS_OBRA = frozenset({"obra", "encomenda", "enc", "phc", "processo"})

_MODO_EMAIL = "email"
_MODO_PDF = "pdf"
_MODO_TEXTO = "texto"
#: PDF com os tickets da obra, em vez do ponto de situação.
_MODO_OCORRENCIAS = "ocorrencias"
#: PDF com os tickets de TODAS as obras (não aponta a nenhuma).
MODO_OCORRENCIAS_TODAS = "ocorrencias_todas"


#: Intervalo plausível para um ANO escrito na pergunta (distingue-o do nº obra).
_ANO_MIN, _ANO_MAX = 2000, 2099


#: Frases que indicam que o valor a seguir é a Referência do CLIENTE.
_REF_FRASES = (
    "referencia do cliente",
    "referencia de cliente",
    "ref do cliente",
    "ref de cliente",
    "referencia cliente",
    "ref cliente",
)


@dataclass(frozen=True)
class PedidoObra:
    """Pedido de ação sobre uma obra: identifica-a pelo nº de encomenda OU pela
    Ref. do cliente; mais o modo e (opcional) o ano."""

    numero: str = ""
    modo: str = _MODO_TEXTO  # "texto" | "pdf" | "email"
    #: Ano escrito na pergunta; vazio = deixar o serviço usar o ano atual.
    ano: str = ""
    #: Referência do cliente («ref de cliente XXXX»), em alternativa ao número.
    ref_cliente: str = ""
    #: Versão da obra pedida («_111_03»); vazio = a mais recente.
    versao_obra: str = ""
    #: Versão do plano de corte pedida («_111_03_01»); vazio = a mais recente.
    versao_plano: str = ""
    #: "_" quando o número foi escrito com underscore («_111»). O underscore
    #: faz parte da identidade: as encomendas do PHC têm 4 algarismos e as que
    #: começam por "_" vêm do Streamlit — «_111» e «111» são obras diferentes.
    prefixo: str = ""


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

    # 1) Obra pela Ref. do cliente («ref de cliente 2410008»).
    ref = _extrair_ref_cliente(texto)
    if ref:
        return PedidoObra(ref_cliente=ref, modo=_modo(palavras))

    # 2) Obra pelo nº de encomenda.
    numero, ano = _extrair_numero_e_ano(palavras)
    if not numero:
        return None

    tem_gatilho = any(p in _GATILHOS for p in palavras)
    tem_rotulo = _tem_rotulo_antes_do_numero(palavras, numero)
    if not (tem_gatilho or tem_rotulo):
        return None

    versao_obra, versao_plano = extrair_versoes(pergunta, numero)
    return PedidoObra(
        numero=numero,
        modo=_modo(palavras),
        ano=ano,
        versao_obra=versao_obra,
        versao_plano=versao_plano,
        prefixo=extrair_prefixo(pergunta, numero),
    )


def extrair_prefixo(pergunta: object, numero: str) -> str:
    """"_" se o número foi escrito com underscore («_111»), senão "".

    Tem de ler o texto **em bruto**: o ``normalizar`` come o underscore, e é
    ele que distingue uma encomenda do Streamlit («_111») de uma do PHC.
    """
    texto = str(pergunta or "")
    alvo = re.sub(r"\D", "", numero or "")
    if not texto or not alvo:
        return ""
    # ``(?!\d)`` e não ``\b``: em «_111_03_01» o que vem a seguir ao número é um
    # underscore, que conta como letra e faria o ``\b`` falhar.
    return "_" if re.search(rf"_0*{int(alvo)}(?!\d)", texto) else ""


#: «_111_03_01» / «111/03/01»: o número, a versão da obra e a do plano de corte.
#: Só separadores explícitos (nunca o espaço), senão «obra 111 03» seria lido
#: como uma versão que o utilizador não escreveu.
_PADRAO_VERSOES = re.compile(r"(\d{2,6})[_/\-]0*(\d{1,2})(?:[_/\-]0*(\d{1,2}))?")


def extrair_versoes(pergunta: object, numero: str) -> tuple[str, str]:
    """Lê «_111_03_01» e devolve ('03', '01') — ('', '') se não vier versão.

    Trabalha no texto **em bruto**: o ``normalizar`` transforma os underscores
    em espaços, e aí «_111_03_01» ficaria indistinguível de três números
    escritos ao lado uns dos outros.
    """
    texto = str(pergunta or "")
    alvo = re.sub(r"\D", "", numero or "")
    if not texto or not alvo:
        return "", ""

    for encontrado in _PADRAO_VERSOES.finditer(texto):
        if encontrado.group(1).lstrip("0") != alvo.lstrip("0"):
            continue
        obra = encontrado.group(2)
        plano = encontrado.group(3) or ""
        return f"{int(obra):02d}", f"{int(plano):02d}" if plano else ""
    return "", ""


def formatar_numero_encomenda(numero: object, prefixo: str = "") -> str:
    """Escreve o nº de encomenda na forma da casa: «_111» ou «0111».

    As do PHC têm sempre **4 algarismos** (por isso o 111 do PHC escreve-se
    «0111»); as do Streamlit são o underscore seguido do número.
    """
    digitos = re.sub(r"\D", "", str(numero or ""))
    if not digitos:
        return ""
    if (prefixo or "").strip() == "_" or str(numero or "").strip().startswith("_"):
        return f"_{digitos.lstrip('0') or digitos}"
    return digitos.zfill(4)


def aviso_tipo_encomenda(escrito: str, encontrado: str) -> str:
    """Reparo quando o underscore da encomenda não bate certo com o escrito.

    O que distingue os dois tipos é **o underscore**: «_111» vem do Streamlit e
    é uma encomenda de cliente final; «0111» vem do PHC e é de cliente. São
    obras diferentes, por isso quem escreveu uma e recebeu a outra tem de saber.
    """
    a_escrita = (escrito or "").strip()
    a_encontrada = (encontrado or "").strip()
    if not a_escrita or not a_encontrada:
        return ""
    if a_escrita.startswith("_") == a_encontrada.startswith("_"):
        return ""

    if a_encontrada.startswith("_"):
        natureza = "as que começam por «_» vêm do Streamlit (cliente final)"
    else:
        natureza = "as do PHC não levam «_» e escrevem-se com 4 algarismos"
    return (
        f"Escreveu «{formatar_numero_encomenda(a_escrita)}», mas a encomenda que "
        f"existe é «{formatar_numero_encomenda(a_encontrada)}» — {natureza}."
    )


def aviso_outras_versoes(dossier: DossierObra, *, pediu_versao: bool = False) -> str:
    """«Esta encomenda tem 3 versões» + como pedir uma delas.

    O resumo mostra sempre a versão mais recente. Sem isto, quem pergunta pela
    encomenda toda não fica a saber que as outras versões existem — e são obras
    a sério, com estados de produção diferentes.
    """
    versoes = tuple(getattr(dossier, "versoes", ()) or ())
    if pediu_versao or len(versoes) < 2:
        return ""

    enc = (dossier.enc or "").strip()
    mostrada = versoes[-1]
    outras = [
        _referencia_versao(enc, versao)
        for versao in versoes[:-1]
    ]
    exemplo = outras[0] if outras else ""

    return (
        f"A encomenda {enc or '—'} tem {len(versoes)} versões; mostrei a mais "
        f"recente ({_referencia_versao(enc, mostrada)}). "
        f"Outras: {', '.join(outras)}. "
        f"Para ver uma delas, escreva o número completo — ex.: «{exemplo}»."
    )


def _referencia_versao(enc: str, versao: VersaoObra) -> str:
    """«_111_03_01» a partir da encomenda e da versão.

    A encomenda vai tal e qual como está: o underscore inicial de «_111» faz
    parte do número, e é assim que a pessoa o escreve.
    """
    referencia = formatar_numero_encomenda(enc) or (enc or "").strip()
    for parte in (versao.versao_obra, versao.versao_plano):
        limpa = (parte or "").strip().strip("_")
        if limpa:
            referencia += f"_{limpa}"
    return referencia


def _extrair_ref_cliente(texto: str) -> str:
    """Valor logo a seguir a «ref (de) cliente» (o código de referência)."""
    for frase in _REF_FRASES:
        indice = texto.find(frase)
        if indice >= 0:
            resto = texto[indice + len(frase):].split()
            if resto:
                return resto[0]
    return ""


def resumo_texto(dossier: DossierObra) -> str:
    """Resumo curto e prático para colar no WhatsApp (só texto).

    Sem imagem e sem a descrição de produção; inclui Ref./Obra/Localização
    quando existem, e as fases de produção uma por linha (na vertical).
    """
    identidade = dossier.codigo or (f"obra {dossier.enc}" if dossier.enc else "obra")
    cliente = f" ({dossier.cliente})" if dossier.cliente else ""
    linhas = [f"{identidade}{cliente}"]

    if dossier.ref_cliente:
        linhas.append(f"Ref. Cliente: {dossier.ref_cliente}")
    if dossier.obra:
        linhas.append(f"Obra: {dossier.obra}")
    if dossier.localizacao:
        linhas.append(f"Localização: {dossier.localizacao}")

    estado = f"Estado: {dossier.estado_local or '—'}"
    if dossier.responsavel:
        estado += f" · Responsável: {dossier.responsavel}"
    linhas.append(estado)
    if dossier.data_inicio or dossier.data_entrega:
        linhas.append(
            f"Início: {dossier.data_inicio or '—'} · "
            f"Entrega prevista: {dossier.data_entrega or '—'}"
        )

    if dossier.encontrado_streamlit and dossier.fases:
        cabeca = "Produção"
        if dossier.estado_global:
            cabeca += f": {dossier.estado_global}"
        linhas.append(cabeca)
        for nome, pct, _concluido in dossier.fases:
            linhas.append(f"• {nome}: {pct:.0f}%")
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


#: Palavras que alargam o pedido a toda a casa em vez de a uma obra.
_PALAVRAS_TODAS = frozenset(
    {"todas", "todos", "toda", "todo", "geral", "lista", "listagem", "resumo"}
)


def pedido_ocorrencias_todas(pergunta: object) -> str | None:
    """Deteta «lista de todas as ocorrências (de 2026)»; devolve o ano ou "".

    Devolve ``None`` quando não é este pedido. Exige a palavra das ocorrências
    **e** uma palavra que alargue a toda a casa (ou «pdf»/«relatório»), para
    «ocorrências da obra 1134» continuar a ser tratado como pedido de UMA obra
    e uma pesquisa normal não ser desviada para aqui.
    """
    palavras = normalizar(pergunta).split()
    if not palavras:
        return None

    conjunto = set(palavras)
    if not conjunto & _PALAVRAS_OCORRENCIAS:
        return None
    if not conjunto & (_PALAVRAS_TODAS | {"pdf", "relatorio"}):
        return None
    if conjunto & _ROTULOS_OBRA:
        return None

    numeros = [re.sub(r"\D", "", palavra) for palavra in palavras]
    numeros = [digitos for digitos in numeros if digitos]
    anos = [digitos for digitos in numeros if _e_ano(digitos)]
    if len(numeros) != len(anos):
        # Há um número que não é ano — é o nº de uma obra, não é este pedido.
        return None

    return anos[0] if anos else ""


def _fases_str(dossier: DossierObra) -> str:
    if not (dossier.encontrado_streamlit and dossier.fases):
        return "(sem detalhe de produção)"
    return ", ".join(f"{nome} {pct:.0f}%" for nome, pct, _c in dossier.fases)


def prompt_corpo_email(
    dossier: DossierObra,
    instrucoes: list[str],
    saudacao: str,
    utilizador: str,
) -> tuple[str, str]:
    """(system, user) para o LLM redigir o corpo do email guiado pelo perfil."""
    system = (
        "És o «IA Martelo», assistente interno de uma empresa de mobiliário "
        "(Lança Encanto). Escreves, em português de Portugal, um email "
        "profissional e simpático ao CLIENTE com o ponto de situação da obra "
        "dele. NUNCA inventes dados nem números — usa exatamente os factos "
        "indicados. Começa pela saudação dada e assina com o nome indicado. "
        "Segue as instruções do utilizador. Devolve APENAS o texto do email "
        "(sem linha de Assunto), em parágrafos."
    )
    linhas_instr = "\n".join(f"- {i}" for i in instrucoes) or "- (sem instruções)"
    user = (
        f"Saudação: {saudacao}\n"
        f"Assinar como: {utilizador or '(o teu nome)'}\n\n"
        f"Instruções do utilizador:\n{linhas_instr}\n\n"
        "Factos da obra (usa-os, não inventes):\n"
        f"- Obra: {_identidade(dossier)}\n"
        f"- Cliente: {dossier.cliente or '—'}\n"
        f"- Ref. do cliente: {dossier.ref_cliente or '—'}\n"
        f"- Estado: {dossier.estado_local or '—'}\n"
        f"- Entrega prevista: {dossier.data_entrega or '—'}\n"
        f"- Fases de produção: {_fases_str(dossier)}\n\n"
        "Nota: uma imagem da obra e um PDF detalhado seguem no email; podes "
        "referir o anexo, não precisas de repetir todas as percentagens.\n"
        "Escreve o email."
    )
    return system, user


def texto_para_html_email(texto: str, imagem_path: str = "") -> str:
    """Converte o texto do LLM em HTML e insere a imagem após o 1.º parágrafo."""
    paragrafos = [p.strip() for p in re.split(r"\n\s*\n", texto or "") if p.strip()]
    if not paragrafos:
        paragrafos = [linha.strip() for linha in (texto or "").splitlines() if linha.strip()]

    img_html = ""
    if imagem_path:
        try:
            uri = Path(imagem_path).as_uri()
            img_html = f'<p><img src="{uri}" width="480" /></p>'
        except (ValueError, OSError):
            img_html = ""

    linhas = []
    for indice, paragrafo in enumerate(paragrafos):
        linhas.append(f"<p>{escape(paragrafo).replace(chr(10), '<br>')}</p>")
        if indice == 0 and img_html:
            linhas.append(img_html)
    if img_html and not linhas:
        linhas.append(img_html)
    return "\n".join(linhas)


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
    # As ocorrências vêm primeiro: «relatório das ocorrências da obra 1134» tem
    # as duas palavras, e o que se quer é a lista de tickets.
    if conjunto & _PALAVRAS_OCORRENCIAS:
        return _MODO_OCORRENCIAS
    if conjunto & {"email", "mail"}:
        return _MODO_EMAIL
    if conjunto & {"pdf", "relatorio"}:
        return _MODO_PDF
    return _MODO_TEXTO
