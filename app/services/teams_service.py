"""Mandar um ticket para o chat do Microsoft Teams.

O objetivo não é "integrar o Teams" — é a pessoa responsável ser avisada e
ficar prova disso no ticket, em vez do copiar-e-colar manual de hoje.

Usa um *deep link*: uma ligação que o Teams instalado sabe abrir na conversa
certa, já com a mensagem escrita. A pessoa que está a enviar só tem de carregar
em Enter. Não precisa de API, de registo de aplicação nem de autorização de
administrador — funciona com Teams de trabalho e com Teams gratuito.

As fotos não cabem num link. Vão pela área de transferência: o programa copia
os ficheiros do ticket e, no Teams, um Ctrl+V anexa-os à mensagem.
"""

from __future__ import annotations

from urllib.parse import quote

from app.domain import ocorrencia_tipos as tipos
from app.domain.ocorrencia_anexos import existe as anexo_existe


#: Deep link oficial de conversa 1:1 do Teams.
BASE_CHAT = "https://teams.microsoft.com/l/chat/0/0"

#: Acima disto o Windows corta o URL. O texto completo fica sempre no ticket.
MAX_MENSAGEM = 1500


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
        plural = "fotos" if len(caminhos) > 1 else "foto"
        linhas.append(f"({len(caminhos)} {plural} em anexo)")

    autor = _texto(getattr(ocorrencia, "autor", ""))
    if autor:
        linhas.append("")
        linhas.append(f"— {autor}")

    return "\n".join(linhas).strip()


def link_chat_teams(email: str | None, mensagem: str = "") -> str:
    """Return the deep link that opens the 1:1 chat with the text ready.

    Sem email não há conversa para abrir — devolve string vazia para quem chama
    decidir o que dizer ao utilizador.
    """
    destino = (email or "").strip()
    if not destino:
        return ""

    url = f"{BASE_CHAT}?users={quote(destino, safe='@')}"
    texto = (mensagem or "").strip()
    if texto:
        url += f"&message={quote(encurtar(texto), safe='')}"
    return url


def encurtar(mensagem: str, limite: int = MAX_MENSAGEM) -> str:
    """Trim the message so the deep link survives the Windows URL limit."""
    texto = mensagem or ""
    if len(texto) <= limite:
        return texto
    return texto[: limite - 1].rstrip() + "…"


def caminhos_de_anexos(anexos) -> list[str]:
    """Existing files of a ticket — os que já não estão no disco não vão."""
    caminhos = []
    for anexo in anexos or ():
        caminho = _texto(getattr(anexo, "caminho", ""))
        if caminho and anexo_existe(caminho):
            caminhos.append(caminho)
    return caminhos


def abrir_chat_teams(email: str | None, mensagem: str = "") -> bool:
    """Open the Teams chat with the message ready; False if there is no email."""
    url = link_chat_teams(email, mensagem)
    if not url:
        return False

    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    return bool(QDesktopServices.openUrl(QUrl(url)))


def _texto(valor) -> str:
    return str(valor or "").strip()
