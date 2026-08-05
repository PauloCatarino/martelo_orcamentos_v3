"""Responder ao email com que o cliente pediu o orçamento.

As colegas do orçamento raramente escrevem um email novo: respondem ao pedido
que o cliente mandou, e esse email fica guardado como `.msg` na pasta da obra.
Este serviço encontra esse ficheiro e lê-lhe o cabeçalho, para o Martelo poder
propor a resposta já com o destinatário e o assunto certos.

Quem sabe mesmo responder é o Outlook: aberto o `.msg`, ele devolve uma
mensagem com o histórico citado e com o encadeamento da conversa — coisas que
não se imitam montando um email novo à mão. Por isso isto só funciona com o
método "outlook"; por SMTP não há resposta possível.

Nada aqui envia, grava ou altera seja o que for: só se lê o ficheiro.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import re
from types import SimpleNamespace
from typing import Callable, Sequence

from app.domain.pesquisa_texto import normalizar

logger = logging.getLogger(__name__)

#: Extensão dos emails guardados a partir do Outlook.
EXTENSAO_EMAIL = ".msg"

#: Palavras que denunciam um pedido de orçamento. Servem para adivinhar qual
#: dos emails guardados é o pedido, quando a pasta tem vários que nada têm a
#: ver com isso — e procuram-se **no nome do ficheiro**: ao arrastar um email
#: do Outlook para uma pasta, o nome que ele ganha é o próprio assunto. Assim
#: escolhe-se sem ter de abrir nenhum.
PALAVRAS_PEDIDO: tuple[str, ...] = (
    "orcamento",
    "cotacao",
    "preco",
    "proposta",
    "pedido",
    "consulta",
    "solicitacao",
)

#: Prefixos que já marcam uma resposta ou reencaminhamento.
_JA_E_RESPOSTA = re.compile(r"^\s*(re|res|rv|fw|fwd|enc)\s*:", re.IGNORECASE)


@dataclass(frozen=True)
class EmailDoCliente:
    """O pedido do cliente, lido do ficheiro guardado na pasta."""

    caminho: str
    assunto: str = ""
    de: str = ""
    recebido_em: datetime | None = None

    @property
    def nome_ficheiro(self) -> str:
        return Path(self.caminho).name

    @property
    def etiqueta(self) -> str:
        """O que se lê na janela: ``pedido.msg — de geral@seiva.pt (04-08-2026)``."""
        partes = [self.nome_ficheiro]
        if self.de:
            partes.append(f"de {self.de}")
        if self.recebido_em is not None:
            partes.append(f"({self.recebido_em.strftime('%d-%m-%Y')})")
        return " — ".join(partes[:2]) + (f" {partes[2]}" if len(partes) > 2 else "")


def pontuar_pedido(nome: object) -> int:
    """Quantas palavras de pedido de orçamento aparecem no nome do ficheiro."""
    texto = normalizar(Path(str(nome or "")).stem)
    return sum(1 for palavra in PALAVRAS_PEDIDO if palavra in texto)


def parece_pedido(nome: object) -> bool:
    """O nome sugere mesmo um pedido de orçamento?"""
    return pontuar_pedido(nome) > 0


def procurar_emails_do_cliente(*pastas: Path | str | None) -> tuple[Path, ...]:
    """Emails guardados nas pastas dadas, o mais provável primeiro.

    Procura por ordem: a primeira pasta que tiver emails ganha. Assim o email
    guardado na pasta da versão manda sobre um mais antigo na raiz da obra.

    A ordem põe à frente os que **parecem um pedido de orçamento** pelo
    assunto, e só depois desempata pela data: a pasta pode ter outros emails
    que nada têm a ver, e é ao primeiro da lista que o Martelo propõe
    responder.

    Nunca levanta — uma pasta do servidor pode simplesmente não responder.
    """
    for pasta in pastas:
        if not pasta:
            continue
        try:
            alvo = Path(pasta)
            encontrados = [
                ficheiro
                for ficheiro in alvo.iterdir()
                if ficheiro.is_file()
                and ficheiro.suffix.lower() == EXTENSAO_EMAIL
            ]
        except (OSError, ValueError) as erro:
            logger.debug("Não foi possível procurar emails em %s: %s", pasta, erro)
            continue
        if encontrados:
            return tuple(
                sorted(
                    encontrados,
                    key=lambda f: (-pontuar_pedido(f.name), -_modificado_em(f)),
                )
            )
    return ()


def _modificado_em(ficheiro: Path) -> float:
    try:
        return ficheiro.stat().st_mtime
    except OSError:
        return 0.0


def assunto_de_resposta(assunto_original: str) -> str:
    """``Pedido cotação`` → ``RE: Pedido cotação``; um ``RE:`` já lá não duplica."""
    texto = (assunto_original or "").strip()
    if not texto:
        return ""
    if _JA_E_RESPOSTA.match(texto):
        return texto
    return f"RE: {texto}"


def ler_email_do_cliente(
    caminho: Path | str,
    *,
    abrir: Callable[[str], object] | None = None,
) -> EmailDoCliente | None:
    """Ler o cabeçalho do `.msg`. Devolve None se não der — nunca levanta.

    ``abrir`` existe para os testes: por omissão é o Outlook que abre.
    """
    texto = str(caminho or "").strip()
    if not texto:
        return None

    abridor = abrir or _abrir_pelo_outlook
    try:
        mensagem = abridor(texto)
    except Exception as erro:  # noqa: BLE001 - sem Outlook ou ficheiro estranho
        logger.info("Não foi possível ler o email guardado %s: %s", texto, erro)
        return None
    if mensagem is None:
        return None

    return EmailDoCliente(
        caminho=texto,
        assunto=_texto(getattr(mensagem, "Subject", "")),
        de=_remetente(mensagem),
        recebido_em=_data(getattr(mensagem, "ReceivedTime", None)),
    )


def preparar_resposta(*pastas: Path | str | None) -> EmailDoCliente | None:
    """O email mais recente encontrado nas pastas, já lido. None se não houver."""
    encontrados = procurar_emails_do_cliente(*pastas)
    if not encontrados:
        return None
    return ler_email_do_cliente(encontrados[0])


# ---- peças ------------------------------------------------------------------
def _abrir_pelo_outlook(caminho: str):
    """Abrir o `.msg` pelo Outlook, só para leitura.

    Devolve uma cópia dos campos, não o objeto do Outlook: assim que o COM se
    fecha, esse objeto deixa de responder e todos os campos vinham vazios.
    """
    import pythoncom  # noqa: PLC0415 - só se precisa mesmo de ler
    import win32com.client as win32  # noqa: PLC0415

    pythoncom.CoInitialize()
    try:
        outlook = win32.Dispatch("Outlook.Application")
        mensagem = outlook.Session.OpenSharedItem(caminho)
        return SimpleNamespace(
            Subject=_texto(getattr(mensagem, "Subject", "")),
            SenderEmailAddress=_texto(getattr(mensagem, "SenderEmailAddress", "")),
            SenderName=_texto(getattr(mensagem, "SenderName", "")),
            ReceivedTime=_data_recebida(mensagem),
        )
    finally:
        pythoncom.CoUninitialize()


def _data_recebida(mensagem) -> datetime | None:
    """A data de recepção — e nunca ao preço de perder o email todo.

    Ler uma data de um objeto COM faz o pywin32 importar o ``win32timezone``
    por baixo. No executável empacotado esse módulo chegou a faltar e a
    exceção levava atrás o assunto e o remetente, que são o que realmente faz
    falta para responder. A data é a parte decorativa da etiqueta.
    """
    try:
        return _data(getattr(mensagem, "ReceivedTime", None))
    except Exception as erro:  # noqa: BLE001 - sem data, mas com email
        logger.info("Data do email guardado ilegível: %s", erro)
        return None


def _texto(valor: object) -> str:
    return str(valor or "").strip()


def _remetente(mensagem) -> str:
    """O endereço de quem enviou; o nome só serve se o endereço faltar."""
    endereco = _texto(getattr(mensagem, "SenderEmailAddress", ""))
    if endereco and "@" in endereco:
        return endereco
    return _texto(getattr(mensagem, "SenderName", "")) or endereco


def _data(valor: object) -> datetime | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None)
    try:
        return datetime.fromisoformat(str(valor))
    except (TypeError, ValueError):
        return None


def etiquetas(caminhos: Sequence[Path | str]) -> list[str]:
    """Só os nomes dos ficheiros — para a lista, sem custar uma leitura cada."""
    return [Path(str(caminho)).name for caminho in caminhos or ()]
