from __future__ import annotations

import ssl
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import email_service


def test_extrair_imagens_inline_troca_file_por_cid(tmp_path) -> None:
    imagem = tmp_path / "obra.png"
    imagem.write_bytes(b"\x89PNG fake")
    corpo = f'<p>Olá</p><p><img src="{imagem.as_uri()}" width="480" /></p>'

    novo, inline = email_service._extrair_imagens_inline(corpo)

    assert len(inline) == 1
    cid, caminho = inline[0]
    assert f"cid:{cid}" in novo
    assert "file:" not in novo
    assert Path(caminho) == imagem


def test_extrair_imagens_inline_ignora_ficheiro_inexistente() -> None:
    corpo = '<img src="file:///C:/nao/existe/x.png" />'

    novo, inline = email_service._extrair_imagens_inline(corpo)

    assert inline == []
    assert novo == corpo  # fica como estava


class _FakeAnexos:
    def __init__(self) -> None:
        self.adicionados: list[str] = []

    def Add(self, caminho):  # noqa: N802 - assinatura do Outlook
        self.adicionados.append(str(caminho))
        return SimpleNamespace(
            PropertyAccessor=SimpleNamespace(SetProperty=lambda *_a: None)
        )


class _FakeMail:
    """Uma mensagem do Outlook, o suficiente para o serviço a preencher."""

    def __init__(self, html_inicial: str = "") -> None:
        self.To = ""
        self.CC = ""
        self.Subject = ""
        self.HTMLBody = html_inicial
        self.SendUsingAccount = None
        self.SentOnBehalfOfName = ""
        self.SaveSentMessageFolder = None
        self.Attachments = _FakeAnexos()
        self.enviado = False
        self.ultima_resposta: "_FakeMail | None" = None

    def Send(self):  # noqa: N802 - assinatura do Outlook
        self.enviado = True

    def Reply(self):  # noqa: N802 - assinatura do Outlook
        self.ultima_resposta = _FakeMail(self.HTMLBody)
        return self.ultima_resposta


class _FakeOutlook:
    """Outlook de mentira: guarda o que se lhe pediu, não envia nada."""

    def __init__(self, original: _FakeMail | None = None) -> None:
        self.novo = _FakeMail()
        self.original = original
        self.abertos: list[str] = []
        self.Session = SimpleNamespace(
            OpenSharedItem=self._abrir,
            GetDefaultFolder=lambda _n: "Enviados",
            Accounts=SimpleNamespace(Count=0),
        )

    def _abrir(self, caminho):
        self.abertos.append(str(caminho))
        if self.original is None:
            raise RuntimeError("nao ha' email guardado")
        return self.original

    def CreateItem(self, _tipo):  # noqa: N802 - assinatura do Outlook
        return self.novo


def _patch_outlook(monkeypatch, outlook: _FakeOutlook) -> None:
    monkeypatch.setattr(email_service, "_require_win32com_client", lambda: object())
    monkeypatch.setattr(email_service, "_ligar_outlook", lambda _c: outlook)


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
    assert config.smtp_verificar_certificado is True


def test_carregar_email_config_tamanho_max_por_defeito(monkeypatch) -> None:
    _patch_settings(monkeypatch, {})

    config = email_service.carregar_email_config(object())

    assert config.tamanho_max_mb == 18.0


def test_carregar_email_config_le_tamanho_max_com_virgula(monkeypatch) -> None:
    _patch_settings(monkeypatch, {"email_tamanho_max_mb": "12,5"})

    config = email_service.carregar_email_config(object())

    assert config.tamanho_max_mb == 12.5


def test_carregar_email_config_ignora_tamanho_max_invalido(monkeypatch) -> None:
    for valor in ("zero", "0", "-3"):
        _patch_settings(monkeypatch, {"email_tamanho_max_mb": valor})

        config = email_service.carregar_email_config(object())

        assert config.tamanho_max_mb == 18.0


def test_carregar_email_config_permite_desligar_verificacao(monkeypatch) -> None:
    _patch_settings(monkeypatch, {"smtp_verificar_certificado": "nao"})

    config = email_service.carregar_email_config(object())

    assert config.smtp_verificar_certificado is False


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


def _corpo(hora: int) -> str:
    return email_service.construir_corpo_email(
        SimpleNamespace(
            num_orcamento="260001", numero_versao=1, obra="", ref_cliente=""
        ),
        SimpleNamespace(nome="MÓVEIS J.F. VIVA"),
        Decimal("175"),
        momento=datetime(2026, 9, 3, hora, 0),
    )


@pytest.mark.parametrize(
    ("hora", "saudacao"),
    [(9, "Bom dia"), (15, "Boa tarde"), (21, "Boa noite")],
)
def test_o_email_comeca_por_cumprimentar_a_horas(hora, saudacao) -> None:
    corpo = _corpo(hora)

    assert corpo.index(saudacao) < corpo.index("Exmo(a)")


def test_o_nome_do_cliente_vai_a_negrito() -> None:
    assert "<b>MÓVEIS J.F. VIVA</b>" in _corpo(10)


def test_o_total_destaca_se_e_avisa_que_falta_o_iva() -> None:
    """O orçamento é sempre sem IVA; sem a linha havia quem lesse o total
    como o que ia pagar."""
    corpo = _corpo(10)

    assert "<b style='font-size:18px;'>175,00 €</b>" in corpo
    assert "Acresce IVA à taxa em vigor" in corpo
    # O aviso vem depois do valor, não antes.
    assert corpo.index("175,00 €") < corpo.index("Acresce IVA")


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


# ---- TLS do SMTP ------------------------------------------------------------
def test_contexto_ssl_verifica_certificado_e_nome_por_defeito() -> None:
    contexto = email_service._contexto_ssl()

    assert contexto.check_hostname is True
    assert contexto.verify_mode == ssl.CERT_REQUIRED


def test_contexto_ssl_desligado_deixa_de_verificar() -> None:
    contexto = email_service._contexto_ssl(False)

    assert contexto.check_hostname is False
    assert contexto.verify_mode == ssl.CERT_NONE


class _FakeSMTP:
    """SMTP de mentira: regista o que lhe foi pedido, sem tocar na rede."""

    def __init__(self, host, port, context=None) -> None:
        self.host = host
        self.port = port
        self.context = context
        self.starttls_context = "nunca chamado"
        self.login_args = None
        self.enviou = False

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> bool:
        return False

    def starttls(self, context=None) -> None:
        self.starttls_context = context

    def login(self, user, password) -> None:
        self.login_args = (user, password)

    def send_message(self, _msg) -> None:
        self.enviou = True


def _cfg_smtp(**overrides) -> email_service.EmailConfig:
    base = {
        "metodo": "smtp",
        "smtp_host": "smtp.example.test",
        "smtp_port": 587,
        "smtp_user": "user@example.test",
        "smtp_password": "secret",
        "smtp_tls": True,
    }
    base.update(overrides)
    return email_service.EmailConfig(**base)


def _capturar_smtp(monkeypatch, atributo: str) -> list[_FakeSMTP]:
    criados: list[_FakeSMTP] = []

    def _fabrica(*args, **kwargs):
        fake = _FakeSMTP(*args, **kwargs)
        criados.append(fake)
        return fake

    monkeypatch.setattr(email_service.smtplib, atributo, _fabrica)
    return criados


def _enviar(config) -> None:
    email_service._enviar_smtp(
        "dest@example.test",
        "Assunto",
        "<p>corpo</p>",
        [],
        config=config,
        from_email="rem@example.test",
        cc="",
    )


def test_enviar_smtp_starttls_recebe_contexto_que_verifica(monkeypatch) -> None:
    criados = _capturar_smtp(monkeypatch, "SMTP")

    _enviar(_cfg_smtp())

    contexto = criados[0].starttls_context
    assert isinstance(contexto, ssl.SSLContext)
    assert contexto.check_hostname is True
    assert contexto.verify_mode == ssl.CERT_REQUIRED
    assert criados[0].login_args == ("user@example.test", "secret")
    assert criados[0].enviou is True


def test_enviar_smtp_ssl_recebe_contexto_que_verifica(monkeypatch) -> None:
    criados = _capturar_smtp(monkeypatch, "SMTP_SSL")

    _enviar(_cfg_smtp(smtp_tls=False, smtp_ssl=True, smtp_port=465))

    contexto = criados[0].context
    assert isinstance(contexto, ssl.SSLContext)
    assert contexto.check_hostname is True
    assert contexto.verify_mode == ssl.CERT_REQUIRED


def test_enviar_smtp_respeita_verificacao_desligada(monkeypatch) -> None:
    criados = _capturar_smtp(monkeypatch, "SMTP")

    _enviar(_cfg_smtp(smtp_verificar_certificado=False))

    assert criados[0].starttls_context.verify_mode == ssl.CERT_NONE


def test_enviar_smtp_recusa_password_em_claro(monkeypatch) -> None:
    """Com utilizador mas sem TLS nem SSL, a password iria a descoberto."""
    criados = _capturar_smtp(monkeypatch, "SMTP")

    with pytest.raises(RuntimeError, match="em claro"):
        _enviar(_cfg_smtp(smtp_tls=False, smtp_ssl=False))

    assert criados[0].login_args is None
    assert criados[0].enviou is False


def test_enviar_smtp_sem_credenciais_continua_a_funcionar_sem_cifra(monkeypatch) -> None:
    """Relay interno anonimo (o caso do 'localhost:25') nao e' bloqueado."""
    criados = _capturar_smtp(monkeypatch, "SMTP")

    _enviar(_cfg_smtp(smtp_tls=False, smtp_ssl=False, smtp_user="", smtp_password=""))

    assert criados[0].login_args is None
    assert criados[0].enviou is True


# ---- responder ao pedido do cliente -----------------------------------------
def _config_outlook() -> email_service.EmailConfig:
    return email_service.EmailConfig(metodo="outlook", copia="")


def test_sem_responder_a_sai_um_email_novo(monkeypatch, tmp_path) -> None:
    outlook = _FakeOutlook()
    _patch_outlook(monkeypatch, outlook)
    monkeypatch.setattr(email_service, "get_email_log_path", lambda: tmp_path / "l.log")

    email_service.enviar_email(
        "cliente@example.test",
        "Orçamento 260836_01",
        "<p>Segue o orçamento.</p>",
        [],
        config=_config_outlook(),
    )

    assert outlook.abertos == []
    assert outlook.novo.enviado is True
    assert outlook.novo.Subject == "Orçamento 260836_01"
    assert outlook.novo.HTMLBody == "<p>Segue o orçamento.</p>"


def test_responder_abre_o_msg_e_mantem_o_historico(monkeypatch, tmp_path) -> None:
    guardado = tmp_path / "Pedido cotação.msg"
    guardado.write_bytes(b"outlook")
    original = _FakeMail("<html><body><p>Pedido do cliente</p></body></html>")
    outlook = _FakeOutlook(original=original)
    _patch_outlook(monkeypatch, outlook)
    monkeypatch.setattr(email_service, "get_email_log_path", lambda: tmp_path / "l.log")

    email_service.enviar_email(
        "geral@seiva.pt",
        "RE: Pedido cotação",
        "<p>Segue o orçamento.</p>",
        [],
        config=_config_outlook(),
        responder_a=str(guardado),
    )

    assert outlook.abertos == [str(guardado)]
    # O email novo do Outlook nao foi usado: saiu mesmo uma resposta.
    assert outlook.novo.enviado is False
    enviada = original.ultima_resposta
    assert enviada.enviado is True
    assert enviada.To == "geral@seiva.pt"
    assert enviada.Subject == "RE: Pedido cotação"
    # O nosso texto por cima, o do cliente por baixo, dentro do <body>.
    assert enviada.HTMLBody == (
        "<html><body><p>Segue o orçamento.</p><p>Pedido do cliente</p></body></html>"
    )


def test_responder_a_ficheiro_que_sumiu_envia_email_novo(monkeypatch, tmp_path) -> None:
    outlook = _FakeOutlook()
    _patch_outlook(monkeypatch, outlook)
    monkeypatch.setattr(email_service, "get_email_log_path", lambda: tmp_path / "l.log")

    # Alguem apagou o .msg entretanto: nao se perde o email por causa disso.
    email_service.enviar_email(
        "cliente@example.test",
        "Orçamento",
        "<p>Corpo</p>",
        [],
        config=_config_outlook(),
        responder_a=str(tmp_path / "sumiu.msg"),
    )

    assert outlook.abertos == []
    assert outlook.novo.enviado is True


def test_juntar_ao_historico_sem_etiqueta_body() -> None:
    junto = email_service._juntar_ao_historico("<p>novo</p>", "texto antigo solto")

    assert junto == "<p>novo</p>texto antigo solto"


def test_juntar_ao_historico_sem_historico_nao_mexe() -> None:
    assert email_service._juntar_ao_historico("<p>novo</p>", "") == "<p>novo</p>"


# ---- ligar ao Outlook: a armadilha da janela elevada -------------------------
def _outlook_indisponivel(monkeypatch):
    """win32 que nunca liga, e sem esperas entre tentativas."""
    import time as _time

    monkeypatch.setattr(_time, "sleep", lambda _s: None)

    class _Win32:
        def GetActiveObject(self, _nome):  # noqa: N802 - assinatura do pywin32
            raise OSError("(-2146959355, 'A execução no servidor falhou', None, None)")

        def Dispatch(self, _nome):  # noqa: N802 - assinatura do pywin32
            raise OSError("(-2146959355, 'A execução no servidor falhou', None, None)")

    return _Win32()


def test_erro_de_janela_elevada_explica_o_instalador(monkeypatch) -> None:
    monkeypatch.setattr(email_service, "_is_elevated", lambda: True)

    with pytest.raises(RuntimeError) as erro:
        email_service._ligar_outlook(_outlook_indisponivel(monkeypatch))

    mensagem = str(erro.value)
    # A saida imediata tem de estar la': fechar e abrir pelo atalho.
    assert "atalho" in mensagem
    # E a causa mais comum: ter carregado em "Abrir" no fim do instalador.
    assert "INSTALAR" in mensagem
    assert "ADMINISTRADOR" in mensagem


def test_erro_sem_elevacao_aponta_para_o_office(monkeypatch) -> None:
    monkeypatch.setattr(email_service, "_is_elevated", lambda: False)

    with pytest.raises(RuntimeError) as erro:
        email_service._ligar_outlook(_outlook_indisponivel(monkeypatch))

    mensagem = str(erro.value)
    assert "Reparar o Office" in mensagem
    assert "ADMINISTRADOR" not in mensagem
