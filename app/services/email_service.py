"""Email sending service for budget reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
import html
import importlib
import os
from pathlib import Path
import re
import smtplib
from typing import Any, Sequence

from app.domain.export_paths import subpasta_versao
from app.services.system_setting_service import SystemSettingService
from app.utils.formatters import format_currency, format_version


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
) -> None:
    """Send one HTML email through Outlook or SMTP."""
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

    try:
        if (config.metodo or "outlook").lower() == "outlook":
            _enviar_outlook(
                destino,
                assunto,
                corpo_html,
                anexos,
                remetente_email=remetente_email,
                cc=cc_outlook,
            )
        else:
            _enviar_smtp(
                destino,
                assunto,
                corpo_html,
                anexos,
                config=config,
                from_email=from_email,
                cc=cc_rfc,
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


def construir_corpo_email(
    orcamento,
    cliente,
    total,
    *,
    pdf_filename: str = "",
) -> str:
    """Build the default HTML body for a budget email."""
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
        f"<p style='margin:0 0 12px;'>Exmo(a). Sr(a). {cliente_nome},</p>"
        "<p style='margin:0 0 12px;'>Segue em anexo o orçamento "
        f"{num}_{versao}{pdf_part} solicitado.</p>"
        f"{obra_ref_html}"
        f"<p style='margin:0 0 12px;'><b>Total:</b> {format_currency(total)}</p>"
        "<p style='margin:0 0 16px;'>Se tiver alguma dúvida ou necessitar de "
        "mais informação, não hesite em contactar-nos.</p>"
        "<p style='margin:0 0 4px;'>Com os melhores cumprimentos,</p>"
        "<p style='margin:0;'>{{assinatura}}</p>"
        "</div>"
    )


def _enviar_outlook(
    destino: str,
    assunto: str,
    corpo_html: str,
    anexos: Sequence[str],
    *,
    remetente_email: str,
    cc: str,
) -> None:
    win32_client = _require_win32com_client()
    outlook = win32_client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)
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
    for path in anexos:
        if os.path.exists(path):
            mail.Attachments.Add(path)
    mail.SaveSentMessageFolder = outlook.Session.GetDefaultFolder(5)
    mail.Send()


def _enviar_smtp(
    destino: str,
    assunto: str,
    corpo_html: str,
    anexos: Sequence[str],
    *,
    config: EmailConfig,
    from_email: str,
    cc: str,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = from_email
    msg["To"] = destino
    if cc:
        msg["Cc"] = cc
    msg.set_content("Este email requer visualizacao em HTML.")
    msg.add_alternative(corpo_html, subtype="html")

    for path in anexos:
        if os.path.exists(path):
            with open(path, "rb") as file:
                msg.add_attachment(
                    file.read(),
                    maintype="application",
                    subtype="octet-stream",
                    filename=os.path.basename(path),
                )

    if config.smtp_ssl:
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) as smtp:
            if config.smtp_user:
                smtp.login(config.smtp_user, config.smtp_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(config.smtp_host, config.smtp_port) as smtp:
            if config.smtp_tls:
                smtp.starttls()
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


def _to_bool(value: str, default: bool) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return default
    if text in {"1", "true", "yes", "sim", "on"}:
        return True
    if text in {"0", "false", "no", "nao", "não", "off"}:
        return False
    return default
