"""Email sending service for budget reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
import html
import importlib
import logging
import os
from pathlib import Path
import re
import smtplib
import ssl
import sys
from typing import Any, Sequence

from app.domain.anexos_email import LIMITE_PADRAO_MB
from app.domain.assistente_obra import saudacao_por_hora
from app.domain.export_paths import subpasta_versao
from app.services.system_setting_service import SystemSettingService
from app.utils.formatters import format_currency, format_version

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailConfig:
    metodo: str = "outlook"
    copia: str = ""
    assinatura_html_path: str = ""
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_ssl: bool = False
    smtp_tls: bool = False
    #: Verificar o certificado do servidor de email. Desligar so' se o servidor
    #: interno tiver certificado proprio — ver ``_contexto_ssl``.
    smtp_verificar_certificado: bool = True
    #: Peso maximo dos anexos, em MB de ficheiro real. Ja' desconta a margem da
    #: codificacao (um anexo viaja ~1/3 mais pesado do que esta' no disco).
    tamanho_max_mb: float = LIMITE_PADRAO_MB


def carregar_email_config(session) -> EmailConfig:
    """Load optional email settings, defaulting to Outlook."""
    settings = SystemSettingService(session)

    def valor(chave: str, default: str = "") -> str:
        return (settings.obter_valor(chave, default=default) or "").strip()

    return EmailConfig(
        metodo=(valor("email_metodo", "outlook") or "outlook").lower(),
        copia=valor("email_copia"),
        assinatura_html_path=valor("email_assinatura_html"),
        smtp_host=valor("smtp_host", "localhost") or "localhost",
        smtp_port=_to_int(valor("smtp_port", "25"), 25),
        smtp_user=valor("smtp_user"),
        smtp_password=valor("smtp_password"),
        smtp_ssl=_to_bool(valor("smtp_ssl", "false"), False),
        smtp_tls=_to_bool(valor("smtp_tls", "false"), False),
        smtp_verificar_certificado=_to_bool(
            valor("smtp_verificar_certificado", "true"), True
        ),
        tamanho_max_mb=_to_float(
            valor("email_tamanho_max_mb", str(LIMITE_PADRAO_MB)), LIMITE_PADRAO_MB
        ),
    )


def get_email_log_path() -> Path:
    """Return a writable path for the email send log."""
    filename = "envio_emails.log"

    explicit = (os.getenv("MARTELO_EMAIL_LOG_PATH") or "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8"):
                pass
            return path
        except Exception:
            pass

    candidates: list[Path] = []
    programdata = (os.getenv("PROGRAMDATA") or "").strip()
    if programdata:
        candidates.append(Path(programdata) / "Martelo Orcamentos V3" / filename)
    localappdata = (os.getenv("LOCALAPPDATA") or "").strip()
    if localappdata:
        candidates.append(Path(localappdata) / "Martelo Orcamentos V3" / filename)
    candidates.append(Path.home() / "Martelo Orcamentos V3" / filename)

    for path in candidates:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8"):
                pass
            return path
        except Exception:
            continue

    return Path(filename).resolve()


def enviar_email(
    destino: str,
    assunto: str,
    corpo_html: str,
    anexos: Sequence[str] | None = None,
    *,
    config: EmailConfig,
    remetente_email: str | None = None,
    remetente_nome: str | None = None,
    cc: str | None = None,
    responder_a: str | None = None,
) -> None:
    """Send one HTML email through Outlook or SMTP.

    ``responder_a`` e' o caminho de um `.msg` guardado (o pedido do cliente):
    em vez de um email novo, sai uma RESPOSTA a esse — com o historico citado
    e no mesmo fio de conversa. So' pelo Outlook; por SMTP e' ignorado (nao ha'
    forma de continuar uma conversa que a aplicacao nunca viu).
    """
    destino = (destino or "").strip()
    assunto = assunto or "Orcamento"
    anexos = list(anexos or [])
    remetente_email = (remetente_email or "").strip()
    from_email = remetente_email or config.smtp_user

    cc_unique = _unique_recipients(
        [
            *_split_recipients(config.copia),
            *_split_recipients(remetente_email),
            *_split_recipients(cc or ""),
        ]
    )
    cc_outlook = ";".join(cc_unique)
    cc_rfc = ", ".join(cc_unique)
    log_dest = destino + (f";{cc_outlook}" if cc_outlook else "")
    corpo_html = (corpo_html or "").replace(
        "{{assinatura}}", _resolver_assinatura(config, remetente_nome)
    )
    # Imagens locais no corpo (file:...) passam a inline (cid:), para o
    # destinatário as ver — um caminho local só existiria no PC do remetente.
    corpo_html, imagens_inline = _extrair_imagens_inline(corpo_html)

    try:
        if (config.metodo or "outlook").lower() == "outlook":
            _enviar_outlook(
                destino,
                assunto,
                corpo_html,
                anexos,
                remetente_email=remetente_email,
                cc=cc_outlook,
                imagens_inline=imagens_inline,
                responder_a=responder_a or "",
            )
        else:
            if responder_a:
                _safe_log_result(
                    from_email,
                    log_dest,
                    assunto,
                    "AVISO: resposta pedida mas o metodo e' SMTP - foi email novo",
                    anexos,
                )
            _enviar_smtp(
                destino,
                assunto,
                corpo_html,
                anexos,
                config=config,
                from_email=from_email,
                cc=cc_rfc,
                imagens_inline=imagens_inline,
            )
    except Exception as exc:
        _safe_log_result(
            from_email or "<outlook>",
            log_dest,
            assunto,
            f"ERRO: {exc}",
            anexos,
        )
        raise

    _safe_log_result(from_email or "<outlook>", log_dest, assunto, "OK", anexos)


def construir_assunto_email(orcamento) -> str:
    """Build the default subject for a budget email."""
    num = getattr(orcamento, "num_orcamento", None) or ""
    versao = format_version(getattr(orcamento, "numero_versao", None))
    obra = getattr(orcamento, "obra", None) or ""
    return f"Orçamento {num}_{versao} - {obra}".strip(" -")


#: Vai a seguir ao total. O orçamento é sempre sem IVA, e sem esta linha havia
#: quem lesse o valor como o que ia pagar.
AVISO_IVA = "Acresce IVA à taxa em vigor"


def construir_corpo_email(
    orcamento,
    cliente,
    total,
    *,
    pdf_filename: str = "",
    momento: datetime | None = None,
) -> str:
    """Build the default HTML body for a budget email.

    ``momento`` só existe para os testes poderem fixar a hora: a saudação
    (Bom dia / Boa tarde / Boa noite) é a da altura em que o email é escrito.
    """
    agora = momento or datetime.now()
    saudacao = saudacao_por_hora(agora.hour)
    cliente_nome = html.escape(getattr(cliente, "nome", None) or "")
    num = html.escape(getattr(orcamento, "num_orcamento", None) or "")
    versao = html.escape(subpasta_versao(getattr(orcamento, "numero_versao", 1)))
    obra = html.escape(getattr(orcamento, "obra", None) or "")
    ref_cliente = html.escape(getattr(orcamento, "ref_cliente", None) or "")
    pdf_name = html.escape((pdf_filename or "").strip())

    pdf_part = f" (<b>{pdf_name}</b>)" if pdf_name else ""
    obra_ref = " | ".join(
        part
        for part in (
            f"Obra: {obra}" if obra else "",
            f"Ref.: {ref_cliente}" if ref_cliente else "",
        )
        if part
    )
    obra_ref_html = (
        f"<p style='margin:0 0 12px;'><b>{obra_ref}</b></p>" if obra_ref else ""
    )

    return (
        "<div style='font-family: Arial, sans-serif; color:#333;'>"
        f"<p style='margin:0 0 12px;'>{saudacao},</p>"
        f"<p style='margin:0 0 12px;'>Exmo(a). Sr(a). <b>{cliente_nome}</b>,</p>"
        "<p style='margin:0 0 12px;'>Segue em anexo o orçamento "
        f"{num}_{versao}{pdf_part} solicitado.</p>"
        f"{obra_ref_html}"
        "<p style='margin:0 0 12px;'><b>Total:</b> "
        f"<b style='font-size:18px;'>{format_currency(total)}</b>"
        # Os &nbsp; sao o que garante o espaco: o Qt, que desenha a
        # pre-visualizacao na janela de envio, ignora o margin-left num <span>
        # e colava o aviso ao valor ("2107,68 EURAcresce IVA..."). A margem
        # fica na mesma, para os clientes de email a sério.
        f"<span style='margin-left:12px;'>&nbsp;&nbsp;&nbsp;{AVISO_IVA}</span></p>"
        "<p style='margin:0 0 16px;'>Se tiver alguma dúvida ou necessitar de "
        "mais informação, não hesite em contactar-nos.</p>"
        "<p style='margin:0 0 4px;'>Com os melhores cumprimentos,</p>"
        "<p style='margin:0;'>{{assinatura}}</p>"
        "</div>"
    )


def escrever_relatorio_email(
    pasta,
    nome_base: str,
    *,
    remetente: str,
    destino: str,
    cc: str,
    assunto: str,
    corpo_html: str,
    anexos,
) -> Path | None:
    """Grava na pasta do orçamento um HTML com o registo do email enviado.

    Best-effort: nunca levanta (devolve None em erro).
    """
    try:
        agora = datetime.now()
        carimbo = agora.strftime("%Y%m%d_%H%M%S")
        destino_path = Path(pasta) / f"{nome_base}_{carimbo}.html"
        anexos_nomes = "<br>".join(
            html.escape(Path(str(anexo)).name) for anexo in (anexos or [])
        )
        conteudo = (
            "<!DOCTYPE html>"
            "<html><head><meta charset='utf-8'>"
            "<title>Orçamento enviado por email</title></head>"
            "<body style=\"font-family: Arial, sans-serif; color:#333;\">"
            "<h2>Orçamento enviado por email</h2>"
            f"<p><b>Data/hora:</b> "
            f"{html.escape(agora.strftime('%Y-%m-%d %H:%M:%S'))}</p>"
            f"<p><b>De:</b> {html.escape(remetente or '')}</p>"
            f"<p><b>Para:</b> {html.escape(destino or '')}</p>"
            f"<p><b>CC:</b> {html.escape(cc or '')}</p>"
            f"<p><b>Assunto:</b> {html.escape(assunto or '')}</p>"
            f"<p><b>Anexos:</b><br>{anexos_nomes}</p>"
            "<hr>"
            f"{corpo_html or ''}"
            "</body></html>"
        )
        destino_path.write_text(conteudo, encoding="utf-8")
        return destino_path
    except Exception:
        return None


#: <img src="file:...">, para trocar imagens locais por inline (cid:).
_RE_IMG_FILE = re.compile(r'src\s*=\s*"(file:[^"]+)"', re.IGNORECASE)


def _extrair_imagens_inline(corpo_html: str):
    """Troca imagens locais (file:) por referências inline (cid:).

    Devolve ``(corpo_html_novo, [(cid, caminho), ...])``. Só troca ficheiros que
    existem mesmo; os outros ficam como estão.
    """
    inline: list[tuple[str, str]] = []

    def _substituir(match: re.Match) -> str:
        url = match.group(1)
        caminho = _file_url_para_caminho(url)
        if not caminho or not os.path.exists(caminho):
            return match.group(0)
        cid = f"imgobra{len(inline)}"
        inline.append((cid, caminho))
        return match.group(0).replace(url, f"cid:{cid}")

    return _RE_IMG_FILE.sub(_substituir, corpo_html or ""), inline


def _file_url_para_caminho(url: str) -> str:
    """Converte uma URL file: no caminho local (trata drive e UNC)."""
    from urllib.parse import unquote, urlparse
    from urllib.request import url2pathname

    try:
        parsed = urlparse(url)
        caminho = url2pathname(unquote(parsed.path))
        if parsed.netloc:  # UNC: \\servidor\share\...
            caminho = f"\\\\{parsed.netloc}{caminho}"
        return caminho
    except Exception:  # noqa: BLE001 - URL inválida -> ignora
        return ""


def _subtipo_imagem(caminho: str) -> str:
    ext = os.path.splitext(caminho)[1].lower().lstrip(".")
    if ext in {"jpg", "jpeg"}:
        return "jpeg"
    return ext or "png"


def _enviar_outlook(
    destino: str,
    assunto: str,
    corpo_html: str,
    anexos: Sequence[str],
    *,
    remetente_email: str,
    cc: str,
    imagens_inline: Sequence[tuple[str, str]] = (),
    responder_a: str = "",
) -> None:
    win32_client = _require_win32com_client()
    try:
        import pythoncom
    except Exception as exc:
        raise RuntimeError(
            "O envio por Outlook requer o modulo 'pythoncom' do pacote pywin32."
        ) from exc

    pythoncom.CoInitialize()
    try:
        outlook = _ligar_outlook(win32_client)
        mail, historico = _criar_mensagem(outlook, responder_a)
        corpo_html = _juntar_ao_historico(corpo_html, historico)
        if remetente_email:
            account = _find_outlook_account(outlook.Session, remetente_email)
            if account is not None:
                mail.SendUsingAccount = account
            else:
                mail.SentOnBehalfOfName = remetente_email
        mail.To = destino
        if cc:
            mail.CC = cc
        mail.Subject = assunto
        mail.HTMLBody = corpo_html
        for cid, path in imagens_inline:
            if os.path.exists(path):
                anexo = mail.Attachments.Add(path)
                try:
                    # Content-ID + marcar como inline (referenciada por cid:).
                    anexo.PropertyAccessor.SetProperty(
                        "http://schemas.microsoft.com/mapi/proptag/0x3712001F", cid
                    )
                    anexo.PropertyAccessor.SetProperty(
                        "http://schemas.microsoft.com/mapi/proptag/0x37140003", 4
                    )
                except Exception:  # noqa: BLE001 - a imagem vai como anexo normal
                    pass
        for path in anexos:
            if os.path.exists(path):
                mail.Attachments.Add(path)
        mail.SaveSentMessageFolder = outlook.Session.GetDefaultFolder(5)
        mail.Send()
    finally:
        pythoncom.CoUninitialize()


def _criar_mensagem(outlook: Any, responder_a: str) -> tuple[Any, str]:
    """A mensagem a enviar e o historico que ja' traga.

    Sem ``responder_a`` e' um email novo, como sempre. Com ele, e' o Outlook a
    responder ao `.msg` guardado: fica com o encadeamento da conversa e com o
    email do cliente citado — e desse citado precisamos para o repor por baixo
    do nosso texto.
    """
    caminho = (responder_a or "").strip()
    if not caminho or not os.path.exists(caminho):
        if caminho:
            # Nao rebentar por causa disto: o email sai como novo.
            logger.warning("Email a responder nao encontrado: %s", caminho)
        return outlook.CreateItem(0), ""

    original = outlook.Session.OpenSharedItem(caminho)
    resposta = original.Reply()
    return resposta, str(getattr(resposta, "HTMLBody", "") or "")


def _juntar_ao_historico(corpo_html: str, historico: str) -> str:
    """Pôr o nosso texto POR CIMA do email citado, como numa resposta normal."""
    if not historico:
        return corpo_html

    # Entrar logo a seguir ao <body ...>, para nao deixar texto solto fora do
    # HTML; se a etiqueta nao existir, colar a' frente resolve na mesma.
    posicao = historico.lower().find("<body")
    fecho = historico.find(">", posicao) if posicao >= 0 else -1
    if fecho > 0:
        return historico[: fecho + 1] + corpo_html + historico[fecho + 1 :]
    return corpo_html + historico


def _contexto_ssl(verificar: bool = True) -> ssl.SSLContext:
    """Contexto TLS para o SMTP — com o certificado do servidor verificado.

    Sem ``context``, o ``smtplib`` usa um contexto interno do Python que **nao**
    valida o certificado nem o nome do servidor: a ligacao fica cifrada mas
    qualquer maquina no meio se pode fazer passar pelo servidor de email e ficar
    com a password. ``create_default_context`` e o oposto disso.

    ``verificar=False`` (definicao ``smtp_verificar_certificado``) existe para o
    caso de o servidor interno ter um certificado proprio, nao reconhecido pelo
    Windows. Nesse caso o melhor e instalar o certificado no PC; desligar a
    verificacao e a saida de recurso, e volta a deixar a ligacao a descoberto.
    """
    if verificar:
        return ssl.create_default_context()

    contexto = ssl.create_default_context()
    contexto.check_hostname = False
    contexto.verify_mode = ssl.CERT_NONE
    return contexto


def _enviar_smtp(
    destino: str,
    assunto: str,
    corpo_html: str,
    anexos: Sequence[str],
    *,
    config: EmailConfig,
    from_email: str,
    cc: str,
    imagens_inline: Sequence[tuple[str, str]] = (),
) -> None:
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = from_email
    msg["To"] = destino
    if cc:
        msg["Cc"] = cc
    msg.set_content("Este email requer visualizacao em HTML.")
    msg.add_alternative(corpo_html, subtype="html")

    html_part = msg.get_payload()[-1]
    for cid, path in imagens_inline:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "rb") as ficheiro:
                html_part.add_related(
                    ficheiro.read(),
                    maintype="image",
                    subtype=_subtipo_imagem(path),
                    cid=f"<{cid}>",
                )
        except Exception:  # noqa: BLE001 - inline é acessório no SMTP
            pass

    for path in anexos:
        if os.path.exists(path):
            with open(path, "rb") as file:
                msg.add_attachment(
                    file.read(),
                    maintype="application",
                    subtype="octet-stream",
                    filename=os.path.basename(path),
                )

    contexto = _contexto_ssl(config.smtp_verificar_certificado)

    if config.smtp_ssl:
        with smtplib.SMTP_SSL(
            config.smtp_host, config.smtp_port, context=contexto
        ) as smtp:
            if config.smtp_user:
                smtp.login(config.smtp_user, config.smtp_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(config.smtp_host, config.smtp_port) as smtp:
            if config.smtp_tls:
                smtp.starttls(context=contexto)
            elif config.smtp_user:
                raise RuntimeError(
                    "O envio por SMTP tem utilizador e password mas nao tem "
                    "cifra ligada: a password iria em claro pela rede. Ligue o "
                    "'smtp_tls' (porta 587) ou o 'smtp_ssl' (porta 465) em "
                    "Configuracoes > Definicoes do sistema."
                )
            if config.smtp_user:
                smtp.login(config.smtp_user, config.smtp_password)
            smtp.send_message(msg)


def _require_win32com_client() -> Any:
    try:
        return importlib.import_module("win32com.client")
    except Exception as exc:
        raise RuntimeError(
            "O envio por Outlook requer o pacote 'pywin32' instalado no Python/venv atual."
        ) from exc


def _is_elevated() -> bool:
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _caminho_do_executavel() -> str:
    """O .exe do Martelo (ou o python.exe, quando corre a partir do código)."""
    return str(Path(sys.executable).resolve())


def _marcado_para_abrir_como_administrador() -> bool:
    """Se alguém pôs o visto "Executar este programa como administrador".

    O Windows guarda esse visto no registo, e ele fica colado ao ficheiro: a
    partir daí o Martelo abre SEMPRE elevado, mesmo pelo atalho — e o Outlook
    deixa de responder para sempre, não só depois de instalar. Como o aviso
    antigo mandava "abrir pelo atalho", quem tinha este visto ficava a dar
    voltas sem nunca resolver.
    """
    alvo = _caminho_do_executavel().casefold()
    try:
        import winreg
    except ImportError:  # não é Windows
        return False

    chave = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
    for raiz in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(raiz, chave) as aberta:
                indice = 0
                while True:
                    try:
                        nome, valor, _tipo = winreg.EnumValue(aberta, indice)
                    except OSError:
                        break
                    indice += 1
                    if nome.casefold() == alvo and "RUNASADMIN" in str(valor).upper():
                        return True
        except OSError:
            continue

    return False


def _outlook_classico_instalado() -> bool:
    """Se existe um Outlook com automação (COM) registado nesta máquina.

    O "novo Outlook" do Windows não tem automação nenhuma: com ele instalado
    sozinho, nada disto funciona e não há visto nenhum para desmarcar.
    """
    try:
        import winreg
    except ImportError:
        return True  # não é Windows: não fazemos afirmações

    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Outlook.Application\CLSID"):
            return True
    except OSError:
        return False


def _ligar_outlook(win32_client: Any) -> Any:
    import time

    ultimo_erro = None
    for _tentativa in range(3):
        try:
            try:
                return win32_client.GetActiveObject("Outlook.Application")
            except Exception:
                return win32_client.Dispatch("Outlook.Application")
        except Exception as exc:
            ultimo_erro = exc
            time.sleep(1.0)

    raise RuntimeError(_explicar_falha_do_outlook(ultimo_erro))


def _explicar_falha_do_outlook(ultimo_erro: object) -> str:
    """Dizer a CAUSA concreta, e não uma lista de coisas a experimentar.

    Antes havia duas mensagens: "está elevado" e "erro do servidor COM". A
    primeira mandava fechar e abrir pelo atalho — o que não resolve nada quando
    o Martelo está marcado no Windows para abrir sempre como administrador, que
    foi o que aconteceu no PC da Andreia. Agora dizemos qual dos casos é.
    """
    if not _outlook_classico_instalado():
        return (
            "Não foi possível ligar ao Outlook: este computador não tem o "
            "Outlook clássico (o do Office).\n\n"
            "O 'novo Outlook' do Windows não deixa outros programas prepararem "
            "emails, por isso o Martelo não consegue lá chegar.\n\n"
            "SOLUÇÃO: instalar/abrir o Outlook do Office neste computador. Se "
            "só existir o 'novo Outlook', é preciso voltar ao clássico "
            "(no novo Outlook, desligar o separador 'Novo Outlook').\n\n"
            "Detalhe técnico: " + str(ultimo_erro)
        )

    if _is_elevated() and _marcado_para_abrir_como_administrador():
        return (
            "Não foi possível ligar ao Outlook. O Martelo está marcado no "
            "Windows para abrir SEMPRE como administrador, e o Outlook corre "
            "como utilizador normal — o Windows não os deixa falar entre si.\n\n"
            "SOLUÇÃO (é preciso fazê-la uma vez só):\n"
            f"1. Vá a {_caminho_do_executavel()}\n"
            "2. Clique com o botão direito → Propriedades → separador "
            "Compatibilidade\n"
            "3. DESMARQUE 'Executar este programa como administrador' e "
            "carregue em OK\n"
            "4. Feche o Martelo e volte a abri-lo\n\n"
            "Enquanto esse visto estiver marcado, fechar e abrir pelo atalho "
            "não resolve — ele abre elevado à mesma.\n\n"
            "Detalhe técnico: " + str(ultimo_erro)
        )

    if _is_elevated():
        return (
            "Não foi possível ligar ao Outlook. Esta janela do Martelo está a "
            "correr como ADMINISTRADOR e o Outlook corre como utilizador "
            "normal — o Windows não os deixa falar entre si.\n\n"
            "SOLUÇÃO: feche o Martelo e abra-o pelo atalho do menu Iniciar ou "
            "do Ambiente de Trabalho. Depois disso o email já sai.\n\n"
            "Acontece sobretudo quando se acabou de INSTALAR e se carregou em "
            "'Abrir' no fim do instalador: essa janela nasce como "
            "administrador. Basta fechá-la e voltar a abrir pelo atalho.\n\n"
            "Se voltar a acontecer depois de abrir pelo atalho, veja nas "
            "Propriedades do Martelo (separador Compatibilidade) se está "
            "marcado 'Executar este programa como administrador' — e desmarque.\n\n"
            "Detalhe técnico: " + str(ultimo_erro)
        )

    return (
        "Não foi possível ligar ao Outlook (erro do servidor COM).\n\n"
        "Verifique, por esta ordem: o Outlook está aberto e já acabou de "
        "arrancar; não está à espera de nenhuma janela (palavra-passe, perfil); "
        "experimente fechar o Outlook, abri-lo de novo e repetir. Se persistir, "
        "Reparar o Office.\n\n"
        "Detalhe técnico: " + str(ultimo_erro)
    )


def _find_outlook_account(session: Any, smtp_address: str) -> Any | None:
    wanted = (smtp_address or "").strip().lower()
    if not wanted:
        return None
    try:
        accounts = session.Accounts
        count = int(accounts.Count)
    except Exception:
        return None

    for index in range(1, count + 1):
        try:
            account = accounts.Item(index)
            addr = str(getattr(account, "SmtpAddress", "") or "").strip().lower()
        except Exception:
            continue
        if addr == wanted:
            return account
    return None


def _resolver_assinatura(config: EmailConfig, remetente_nome: str | None) -> str:
    nome = (remetente_nome or "").strip()
    if nome:
        return html.escape(nome)

    path = (config.assinatura_html_path or "").strip()
    if path and Path(path).exists():
        try:
            return Path(path).read_text(encoding="utf-8")
        except Exception:
            return ""
    return ""


def _split_recipients(value: str | None) -> list[str]:
    parts = re.split(r"[;,]+", str(value or ""))
    return [part.strip() for part in parts if part and part.strip()]


def _unique_recipients(recipients: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for addr in recipients:
        key = addr.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(addr)
    return result


def _safe_log_result(
    remetente: str,
    destino: str,
    assunto: str,
    status: str,
    anexos: Sequence[str] | None = None,
) -> None:
    try:
        log_path = get_email_log_path()
        linha = (
            f"{datetime.now().isoformat()} | {remetente} -> {destino} | "
            f"{assunto} | {status} | {list(anexos or [])}\n"
        )
        with log_path.open("a", encoding="utf-8") as log:
            log.write(linha)
    except Exception:
        pass


def _to_int(value: str, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _to_float(value: str, default: float) -> float:
    try:
        convertido = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return default
    return convertido if convertido > 0 else default


def _to_bool(value: str, default: bool) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return default
    if text in {"1", "true", "yes", "sim", "on"}:
        return True
    if text in {"0", "false", "no", "nao", "não", "off"}:
        return False
    return default
