from __future__ import annotations


def test_email_orcamento_dialog_imports() -> None:
    from app.ui.dialogs.email_orcamento_dialog import EmailOrcamentoDialog

    assert EmailOrcamentoDialog is not None
    for method in ("destinatario", "cc", "assunto", "corpo_html", "anexos"):
        assert hasattr(EmailOrcamentoDialog, method)


def test_o_aviso_do_iva_nao_cola_ao_valor() -> None:
    """O Qt ignora o margin-left num <span> e escrevia '2107,68 €Acresce IVA'."""
    from app.services.email_service import AVISO_IVA, construir_corpo_email
    from types import SimpleNamespace
    from decimal import Decimal

    corpo = construir_corpo_email(
        SimpleNamespace(num_orcamento="260881", numero_versao=1, obra="", ref_cliente=""),
        SimpleNamespace(nome="Cliente"),
        Decimal("2107.68"),
    )

    assert f"&nbsp;{AVISO_IVA}" in corpo
    # E o valor não fica encostado ao aviso em lado nenhum.
    assert f"€{AVISO_IVA}" not in corpo


def test_a_janela_do_email_abre_grande_com_o_corpo_a_mandar() -> None:
    import inspect

    from app.ui.dialogs.email_orcamento_dialog import EmailOrcamentoDialog

    init = inspect.getsource(EmailOrcamentoDialog.__init__)
    assert "CorpoEmailEdit()" in init
    # O corpo leva mais espaço do que a lista de anexos.
    assert "layout.addWidget(self.txt_corpo, 4)" in init
    assert "_dimensionar_ao_ecra()" in init

    dimensionar = inspect.getsource(EmailOrcamentoDialog._dimensionar_ao_ecra)
    assert "availableGeometry" in dimensionar
