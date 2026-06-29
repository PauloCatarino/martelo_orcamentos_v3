from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.services import email_service


class _FakeSystemSettingService:
    values: dict[str, str | None] = {}

    def __init__(self, _session) -> None:
        pass

    def obter_valor(self, chave: str, default: str | None = None) -> str | None:
        return self.values.get(chave, default)


def _patch_settings(monkeypatch, values: dict[str, str | None]):
    _FakeSystemSettingService.values = values
    monkeypatch.setattr(email_service, "SystemSettingService", _FakeSystemSettingService)


def test_carregar_email_config_defaults_outlook(monkeypatch) -> None:
    _patch_settings(monkeypatch, {})

    config = email_service.carregar_email_config(object())

    assert config.metodo == "outlook"
    assert config.copia == ""
    assert config.smtp_host == "localhost"
    assert config.smtp_port == 25
    assert config.smtp_ssl is False
    assert config.smtp_tls is False


def test_carregar_email_config_le_e_converte(monkeypatch) -> None:
    _patch_settings(
        monkeypatch,
        {
            "email_metodo": "SMTP",
            "email_copia": "comercial@example.test",
            "email_assinatura_html": "C:/assinatura.html",
            "smtp_host": "smtp.example.test",
            "smtp_port": "587",
            "smtp_user": "user@example.test",
            "smtp_password": "secret",
            "smtp_ssl": "0",
            "smtp_tls": "sim",
        },
    )

    config = email_service.carregar_email_config(object())

    assert config.metodo == "smtp"
    assert config.copia == "comercial@example.test"
    assert config.assinatura_html_path == "C:/assinatura.html"
    assert config.smtp_host == "smtp.example.test"
    assert config.smtp_port == 587
    assert config.smtp_user == "user@example.test"
    assert config.smtp_password == "secret"
    assert config.smtp_ssl is False
    assert config.smtp_tls is True


def test_construir_assunto_email() -> None:
    orcamento = SimpleNamespace(
        num_orcamento="260001",
        numero_versao=2,
        obra="Cozinha",
    )

    assert email_service.construir_assunto_email(orcamento) == (
        "Orçamento 260001_02 - Cozinha"
    )


def test_construir_corpo_email_escapa_campos_e_inclui_total() -> None:
    orcamento = SimpleNamespace(
        num_orcamento="260001",
        numero_versao=2,
        obra="Cozinha & Sala <A>",
        ref_cliente="REF & <9>",
    )
    cliente = SimpleNamespace(nome="JF & Filhos <Lda>")

    corpo = email_service.construir_corpo_email(
        orcamento,
        cliente,
        Decimal("1234.50"),
        pdf_filename="orcamento & teste.pdf",
    )

    assert "JF &amp; Filhos &lt;Lda&gt;" in corpo
    assert "260001_02" in corpo
    assert "orcamento &amp; teste.pdf" in corpo
    assert "Cozinha &amp; Sala &lt;A&gt;" in corpo
    assert "REF &amp; &lt;9&gt;" in corpo
    assert "1234,50 €" in corpo
    assert "{{assinatura}}" in corpo


def test_get_email_log_path_usa_env_explicit_e_cria_pasta(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "logs" / "envio_emails.log"
    monkeypatch.setenv("MARTELO_EMAIL_LOG_PATH", str(log_path))

    result = email_service.get_email_log_path()

    assert result == log_path
    assert result.parent.exists()
    assert result.exists()


def test_escrever_relatorio_email_grava_html_com_campos(tmp_path) -> None:
    resultado = email_service.escrever_relatorio_email(
        tmp_path,
        "Email_Enviado_260001_02",
        remetente="João <joao@example.test>",
        destino="cliente@example.test",
        cc="comercial@example.test",
        assunto="Orçamento 260001_02 - Cozinha",
        corpo_html="<p>Segue em anexo o orçamento.</p>",
        anexos=[r"C:\obras\orcamento.pdf", "lista.xlsx"],
    )

    assert resultado is not None
    assert resultado.parent == tmp_path
    assert resultado.name.startswith("Email_Enviado_260001_02_")
    assert resultado.suffix == ".html"
    assert resultado.exists()

    texto = resultado.read_text(encoding="utf-8")
    assert "Orçamento enviado por email" in texto
    assert "joao@example.test" in texto
    assert "cliente@example.test" in texto
    assert "comercial@example.test" in texto
    assert "Orçamento 260001_02 - Cozinha" in texto
    # Anexos: apenas os nomes dos ficheiros (sem caminho).
    assert "orcamento.pdf" in texto
    assert "lista.xlsx" in texto
    assert "C:\\obras" not in texto
    # Corpo HTML incluído tal e qual.
    assert "<p>Segue em anexo o orçamento.</p>" in texto


def test_escrever_relatorio_email_pasta_invalida_devolve_none() -> None:
    resultado = email_service.escrever_relatorio_email(
        "Z:/pasta/que/nao/existe/de/certeza",
        "Email_Enviado_260001_02",
        remetente="rem@example.test",
        destino="dest@example.test",
        cc="",
        assunto="Assunto",
        corpo_html="<p>corpo</p>",
        anexos=[],
    )

    assert resultado is None


def test_safe_log_result_nao_rebenta_e_escreve_linha(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "envio_emails.log"
    monkeypatch.setenv("MARTELO_EMAIL_LOG_PATH", str(log_path))

    email_service._safe_log_result(
        "rem@example.test",
        "dest@example.test",
        "Assunto",
        "OK",
        ["a.pdf"],
    )

    text = log_path.read_text(encoding="utf-8")
    assert "rem@example.test -> dest@example.test" in text
    assert "Assunto | OK | ['a.pdf']" in text
