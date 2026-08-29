"""Mandar um ticket para o chat do Microsoft Teams.

O objetivo não é "integrar o Teams" — é a pessoa responsável ser avisada e
ficar prova disso no ticket, em vez do copiar-e-colar manual de hoje.

Usa um *deep link*: uma ligação que o Teams instalado sabe abrir na conversa
certa, já com a mensagem escrita. A pessoa que está a enviar só tem de carregar
em Enter. Não precisa de API, de registo de aplicação nem de autorização de
administrador — funciona com Teams de trabalho e com Teams gratuito.

As fotos não cabem num link. Depois de abrir o chat, a interface copia os
próprios pixels para a área de transferência; no Teams, Ctrl+V insere-os no
corpo da mensagem em vez de anexar os ficheiros.
"""

from __future__ import annotations

from urllib.parse import quote

from app.domain import ocorrencia_tipos as tipos
from app.domain.ocorrencia_anexos import existe as anexo_existe
from app.domain.texto_endereco import limpar_endereco


#: Deep link de conversa do Teams de trabalho (Microsoft 365).
BASE_CHAT = "https://teams.microsoft.com/l/chat/0/0"

#: Formatos possíveis do link. Qual deles preenche o "Para:" depende do tipo de
#: conta (trabalho ou pessoal) e da versão do Teams instalada — por isso é uma
#: definição, e não uma escolha fechada no código.
FORMATOS_LINK: tuple[tuple[str, str, str], ...] = (
    (
        "trabalho",
        "Teams de trabalho (Microsoft 365)",
        "https://teams.microsoft.com/l/chat/0/0",
    ),
    (
        "pessoal",
        "Teams pessoal (conta Microsoft)",
        "https://teams.live.com/l/chat/0/0",
    ),
    (
        "aplicacao",
        "Aplicação instalada (msteams:)",
        "msteams:/l/chat/0/0",
    ),
)
FORMATO_PADRAO = "trabalho"

#: Chave em system_settings onde fica o formato escolhido.
CHAVE_FORMATO_LINK = "teams_formato_link"

#: Acima disto o Windows corta o URL. O texto completo fica sempre no ticket.
MAX_MENSAGEM = 1500

#: O limite verdadeiro e' do URL JA' CODIFICADO, e nao do texto que se escreve.
#: Ao codificar, uma quebra de linha passa a ocupar 3 caracteres e um "ç" passa
#: a ocupar 6 -- um ticket de 1500 caracteres pode dar um URL de 4000. Quando
#: isso acontece o Windows corta, e o que se perde e' precisamente o
#: `&message=`: o Teams abre a conversa com a caixa VAZIA e ninguem percebe
#: porque. Por isso o corte e' medido no fim, no URL montado.
MAX_URL = 1900


def base_do_formato(formato: str | None) -> str:
    """Return the link prefix for a format key (unknown keys fall back)."""
    chave = (formato or "").strip().lower()
    for candidato, _rotulo, base in FORMATOS_LINK:
        if candidato == chave:
            return base
    return BASE_CHAT


def montar_texto_ticket(processo, ocorrencia, anexos=()) -> str:
    """Build the message that goes into the chat.

    Cabeçalho curto e identificável (T3 · obra · cliente) porque no chat a
    pessoa vê primeiro a pré-visualização e só depois abre.
    """
    referencia = tipos.rotulo_ticket(getattr(ocorrencia, "numero", None))
    codigo = _texto(getattr(processo, "codigo_processo", ""))
    linhas = [f"[{referencia}] {tipos.rotulo_tipo(getattr(ocorrencia, 'tipo', None))} — {codigo}"]

    identificacao = []
    cliente = _texto(getattr(processo, "nome_cliente", ""))
    if cliente:
        identificacao.append(f"Cliente: {cliente}")
    ref_cliente = _texto(getattr(processo, "ref_cliente", ""))
    if ref_cliente:
        identificacao.append(f"Ref.: {ref_cliente}")
    if identificacao:
        linhas.append(" · ".join(identificacao))

    assunto = _texto(getattr(ocorrencia, "assunto", ""))
    if assunto:
        linhas.append(f"Assunto: {assunto}")

    gravidade = getattr(ocorrencia, "gravidade", None)
    if tipos.normalizar_gravidade(gravidade) == "alta":
        linhas.append("Gravidade: ALTA")

    linhas.append("")
    linhas.append(_texto(getattr(ocorrencia, "texto", "")))

    caminhos = [
        _texto(getattr(anexo, "caminho", "")) for anexo in anexos or ()
    ]
    caminhos = [caminho for caminho in caminhos if caminho]
    if caminhos:
        linhas.append("")
        plural = (
            "fotografias associadas" if len(caminhos) > 1 else "fotografia associada"
        )
        linhas.append(f"({len(caminhos)} {plural} ao ticket)")

    autor = _texto(getattr(ocorrencia, "autor", ""))
    if autor:
        linhas.append("")
        linhas.append(f"— {autor}")

    return "\n".join(linhas).strip()


def normalizar_destinos(emails) -> list[str]:
    """Accept one address or many; drop the empty ones and the repeated ones."""
    if emails is None:
        return []
    if isinstance(emails, str):
        candidatos = emails.replace(";", ",").split(",")
    else:
        candidatos = list(emails)

    destinos: list[str] = []
    for candidato in candidatos:
        # Limpa também aqui: os endereços gravados antes desta limpeza podem
        # trazer um espaço invisível do copiar-e-colar, e o Teams desiste de
        # reconhecer o endereço sem dizer porquê.
        endereco = limpar_endereco(candidato)
        if endereco and endereco not in destinos:
            destinos.append(endereco)
    return destinos


def link_chat_teams(emails, mensagem: str = "", *, formato: str | None = None) -> str:
    """Return the deep link that opens the chat with the text ready.

    Com mais do que um endereço o Teams abre uma **conversa de grupo** com
    todos — é o que serve quando o mesmo problema é de duas pessoas.

    Sem endereço não há conversa para abrir: devolve string vazia para quem
    chama decidir o que dizer ao utilizador.
    """
    destinos = normalizar_destinos(emails)
    if not destinos:
        return ""

    url = f"{base_do_formato(formato)}?users={quote(','.join(destinos), safe='@,')}"
    texto = (mensagem or "").strip()
    if texto:
        cabe = texto_que_cabe(texto, len(url) + len("&message="))
        if cabe:
            url += f"&message={quote(cabe, safe='')}"
    return url


def formato_configurado(session) -> str:
    """Read the chosen link format from the system settings."""
    from app.services.system_setting_service import SystemSettingService

    valor = SystemSettingService(session).obter_valor(
        CHAVE_FORMATO_LINK, FORMATO_PADRAO
    )
    return (valor or FORMATO_PADRAO).strip().lower()


def encurtar(mensagem: str, limite: int = MAX_MENSAGEM) -> str:
    """Trim the message by character count.

    Continua aqui porque limita o tamanho do texto antes de mais nada; o corte
    que garante que o link funciona e' o do :func:`texto_que_cabe`.
    """
    texto = mensagem or ""
    if len(texto) <= limite:
        return texto
    return texto[: limite - 1].rstrip() + "…"


def texto_que_cabe(mensagem: str, ja_ocupado: int, limite: int = MAX_URL) -> str:
    """O maior pedaco da mensagem que ainda cabe no URL depois de codificado.

    ``ja_ocupado`` e' o comprimento do que o URL ja' tem (endereco base e
    destinatarios). Devolve texto vazio quando nem um pedaco util cabe -- ai' o
    Teams abre na conversa certa com a caixa vazia, que e' mau, mas menos mau
    do que um link cortado a meio que nao abre nada.
    """
    texto = encurtar(mensagem)
    if not texto:
        return ""

    def cabe(pedaco: str) -> bool:
        return ja_ocupado + len(quote(pedaco, safe="")) <= limite

    if cabe(texto):
        return texto

    # Procura binaria: o maior prefixo que ainda cabe. Fazer caractere a
    # caractere seria O(n) chamadas ao quote() para textos de milhares de
    # caracteres.
    baixo, alto = 0, len(texto)
    while baixo < alto:
        meio = (baixo + alto + 1) // 2
        if cabe(texto[:meio] + "…"):
            baixo = meio
        else:
            alto = meio - 1
    return texto[:baixo].rstrip() + "…" if baixo else ""


def caminhos_de_anexos(anexos) -> list[str]:
    """Existing files of a ticket — os que já não estão no disco não vão."""
    caminhos = []
    for anexo in anexos or ():
        caminho = _texto(getattr(anexo, "caminho", ""))
        if caminho and anexo_existe(caminho):
            caminhos.append(caminho)
    return caminhos


def abrir_chat_teams(emails, mensagem: str = "", *, formato: str | None = None) -> bool:
    """Open the Teams chat with the message ready; False if there is no address."""
    url = link_chat_teams(emails, mensagem, formato=formato)
    if not url:
        return False

    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    return bool(QDesktopServices.openUrl(QUrl(url)))


def _texto(valor) -> str:
    return str(valor or "").strip()
