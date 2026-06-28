from __future__ import annotations


def test_email_orcamento_dialog_imports() -> None:
    from app.ui.dialogs.email_orcamento_dialog import EmailOrcamentoDialog

    assert EmailOrcamentoDialog is not None
    for method in ("destinatario", "cc", "assunto", "corpo_html", "anexos"):
        assert hasattr(EmailOrcamentoDialog, method)
