"""O diálogo do email mostra o peso dos anexos e avisa antes de enviar."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _ficheiro(tmp_path: Path, nome: str, megabytes: float) -> str:
    caminho = tmp_path / nome
    caminho.write_bytes(b"0" * int(megabytes * 1024 * 1024))
    return str(caminho)


def _dialogo(anexos, *, limite: float = 18.0):
    from app.ui.dialogs.email_orcamento_dialog import EmailOrcamentoDialog

    return EmailOrcamentoDialog(anexos=anexos, tamanho_max_mb=limite)


def test_anexos_devolve_os_caminhos_e_nao_o_que_se_ve(_app, tmp_path: Path) -> None:
    # A lista mostra "nome — tamanho", mas quem envia precisa do caminho.
    caminho = _ficheiro(tmp_path, "2_Projeto_Producao.pdf", 1)
    dialogo = _dialogo([caminho])

    assert dialogo.anexos() == [caminho]
    assert "2_Projeto_Producao.pdf — 1,0 MB" in dialogo.list_anexos.item(0).text()


def test_barra_soma_todos_os_anexos(_app, tmp_path: Path) -> None:
    anexos = [_ficheiro(tmp_path, f"anexo_{i}.pdf", 3) for i in range(3)]

    dialogo = _dialogo(anexos)

    assert "3 anexos" in dialogo.lbl_tamanho.text()
    assert "9,0 MB de 18 MB" in dialogo.lbl_tamanho.text()


def test_acima_do_limite_a_barra_avisa(_app, tmp_path: Path) -> None:
    dialogo = _dialogo([_ficheiro(tmp_path, "pesado.pdf", 23)])

    assert "demasiado grande" in dialogo.lbl_tamanho.text()
    assert dialogo._resumo_anexos().excede


def test_remover_anexo_refresca_a_barra(_app, tmp_path: Path) -> None:
    dialogo = _dialogo(
        [_ficheiro(tmp_path, "pesado.pdf", 23), _ficheiro(tmp_path, "leve.pdf", 1)]
    )
    assert dialogo._resumo_anexos().excede

    dialogo.list_anexos.item(0).setSelected(True)
    dialogo._remover_anexos_selecionados()

    assert not dialogo._resumo_anexos().excede
    assert "demasiado grande" not in dialogo.lbl_tamanho.text()


def test_dentro_do_limite_envia_sem_perguntar(_app, tmp_path: Path) -> None:
    dialogo = _dialogo([_ficheiro(tmp_path, "leve.pdf", 2)])

    assert dialogo._confirmar_tamanho()


def test_limite_vem_das_definicoes(_app, tmp_path: Path) -> None:
    anexos = [_ficheiro(tmp_path, "medio.pdf", 10)]

    assert not _dialogo(anexos, limite=18)._resumo_anexos().excede
    assert _dialogo(anexos, limite=5)._resumo_anexos().excede


# ---- responder ao pedido do cliente -----------------------------------------
def _msg(tmp_path: Path, nome: str) -> str:
    caminho = tmp_path / nome
    caminho.write_bytes(b"outlook")
    return str(caminho)


def _fingir_leitura(monkeypatch, *, assunto="Pedido cotação Projeto CMM",
                    de="geral@seiva.pt", falha=False):
    """Substituir a leitura do .msg — nos testes não há Outlook."""
    from datetime import datetime

    from app.services import email_resposta_service as svc

    def _ler(caminho, **_kwargs):
        if falha:
            return None
        return svc.EmailDoCliente(
            caminho=str(caminho),
            assunto=assunto,
            de=de,
            recebido_em=datetime(2026, 8, 4, 11, 31),
        )

    monkeypatch.setattr(svc, "ler_email_do_cliente", _ler)


def _dialogo_resposta(anexos, emails, **kwargs):
    from app.ui.dialogs.email_orcamento_dialog import EmailOrcamentoDialog

    base = {
        "destinatario": "compras@seiva.pt",
        "assunto": "Orçamento 260836_01 - Projeto CMM",
        "anexos": anexos,
        "emails_do_cliente": emails,
    }
    base.update(kwargs)
    return EmailOrcamentoDialog(**base)


def test_sem_msg_na_pasta_nada_muda(_app, tmp_path: Path) -> None:
    dialogo = _dialogo_resposta([_ficheiro(tmp_path, "orc.pdf", 1)], [])

    assert dialogo.check_responder is None
    assert dialogo.responder_a() == ""
    assert dialogo.destinatario() == "compras@seiva.pt"
    assert dialogo.assunto() == "Orçamento 260836_01 - Projeto CMM"


def test_com_msg_propoe_responder_e_enche_os_campos(
    _app, monkeypatch, tmp_path: Path
) -> None:
    _fingir_leitura(monkeypatch)
    guardado = _msg(tmp_path, "Pedido cotação Projeto CMM.msg")

    dialogo = _dialogo_resposta([_ficheiro(tmp_path, "orc.pdf", 1)], [guardado])

    assert dialogo.check_responder.isChecked()
    assert dialogo.responder_a() == guardado
    # Destinatário e assunto passam a ser os do email do cliente.
    assert dialogo.destinatario() == "geral@seiva.pt"
    assert dialogo.assunto() == "RE: Pedido cotação Projeto CMM"
    assert "geral@seiva.pt" in dialogo.lbl_resposta.text()


def test_desligar_o_visto_repoe_o_email_novo(_app, monkeypatch, tmp_path: Path) -> None:
    _fingir_leitura(monkeypatch)
    guardado = _msg(tmp_path, "pedido.msg")
    dialogo = _dialogo_resposta([_ficheiro(tmp_path, "orc.pdf", 1)], [guardado])

    dialogo.check_responder.setChecked(False)

    assert dialogo.responder_a() == ""
    assert dialogo.destinatario() == "compras@seiva.pt"
    assert dialogo.assunto() == "Orçamento 260836_01 - Projeto CMM"


def test_escolher_outro_email_da_lista(_app, monkeypatch, tmp_path: Path) -> None:
    _fingir_leitura(monkeypatch)
    primeiro = _msg(tmp_path, "recente.msg")
    segundo = _msg(tmp_path, "antigo.msg")

    dialogo = _dialogo_resposta([], [primeiro, segundo])
    assert dialogo.responder_a() == primeiro

    dialogo.combo_resposta.setCurrentIndex(1)

    assert dialogo.responder_a() == segundo


def test_outlook_em_baixo_desliga_o_visto_e_avisa(
    _app, monkeypatch, tmp_path: Path
) -> None:
    _fingir_leitura(monkeypatch, falha=True)
    guardado = _msg(tmp_path, "pedido.msg")

    dialogo = _dialogo_resposta([], [guardado])

    # Sem conseguir ler, nao se bloqueia ninguem: vai um email novo.
    assert not dialogo.check_responder.isChecked()
    assert dialogo.responder_a() == ""
    assert "email novo" in dialogo.lbl_resposta.text()
    assert dialogo.destinatario() == "compras@seiva.pt"
