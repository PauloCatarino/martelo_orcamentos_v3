"""O aviso do supervisor: o que o utilizador vê e o que pode decidir."""

from __future__ import annotations

import inspect

import pytest
from PySide6.QtWidgets import QApplication

from app.services import producao_preparacao_service as svc
from app.ui.dialogs.producao_supervisao_dialog import SupervisaoProducaoDialog


@pytest.fixture(scope="module", autouse=True)
def _app():
    yield QApplication.instance() or QApplication([])


def _pendencia(key: str, label: str) -> svc.PreparacaoEstado:
    return svc.PreparacaoEstado(
        key=key,
        label=label,
        estado=svc.ESTADO_PENDENTE,
        detalhe=f"\\\\SERVER_LE\\obra\\{label} (em falta)",
        descricao=f"Valida se existe {label}.",
    )


def _dialogo() -> SupervisaoProducaoDialog:
    return SupervisaoProducaoDialog(
        codigo_processo="26.1349_01_01_NEXT_LEVEL",
        pasta_obra="\\\\SERVER_LE\\obra",
        nome_enc_imos="1349_01_26_NEXT_LEVEL",
        nome_plano_cut_rite="1349_01_01_26_NEXT_LEVEL",
        user_id=7,
        estado_anterior="Desenho",
    )


def test_pendencias_aparecem_na_tabela_com_o_que_falta() -> None:
    dialogo = _dialogo()
    pendencias = (_pendencia("conj_pdf", "CONJ.pdf"), _pendencia("cnc_obra", "CNC"))

    validas = (_pendencia("cutrite_pdf", "Plano CUT-RITE"),)
    dialogo.mostrar(
        svc.SupervisaoProducao(
            validou=True,
            estados=pendencias + validas + (_pendencia("obra_pronta", "Pronta"),),
            pendencias=pendencias,
        )
    )

    assert dialogo.tabela.rowCount() == 2
    assert dialogo.tabela.item(0, 0).text() == "CONJ.pdf"
    assert "em falta" in dialogo.tabela.item(0, 2).text()
    # A linha "obra pronta" é o resumo, não conta como validação.
    assert "2 de 3" in dialogo.resumo_label.text()
    assert dialogo.continuar_button.text() == "Passar a Produção mesmo assim"
    # Enquanto não decidir, nada segue para gravação.
    assert dialogo.continuar is False


def test_tudo_validado_deixa_seguir_sem_confirmacao() -> None:
    dialogo = _dialogo()

    dialogo.mostrar(svc.SupervisaoProducao(validou=True))
    dialogo._continuar()

    assert dialogo.continuar_button.text() == "Passar a Produção"
    assert "tudo validado" in dialogo.resumo_label.text().lower()
    assert dialogo.tabela.rowCount() == 0
    assert dialogo.continuar is True


def test_quando_nao_da_para_validar_explica_porque() -> None:
    dialogo = _dialogo()

    dialogo.mostrar(
        svc.SupervisaoProducao(validou=False, motivo="Nome Enc IMOS IX em falta.")
    )

    assert "Nome Enc IMOS IX em falta." in dialogo.resumo_label.text()
    assert dialogo.continuar is False
    # Continuar sem validação continua a ser possível — é um aviso, não um muro.
    assert dialogo.continuar_button.isEnabled()


def test_continuar_com_pendencias_pede_confirmacao() -> None:
    """A confirmação extra evita que o aviso passe por engano num clique."""
    fonte = inspect.getsource(SupervisaoProducaoDialog._continuar)

    assert "_confirmar_com_pendencias" in fonte
    assert "self.continuar = True" in fonte
    assert "QMessageBox.StandardButton.No" in inspect.getsource(
        SupervisaoProducaoDialog._confirmar_com_pendencias
    )


def test_resolver_na_preparacao_volta_a_verificar() -> None:
    fonte = inspect.getsource(SupervisaoProducaoDialog._abrir_preparacao)

    assert "ProducaoPreparacaoDialog" in fonte
    assert "self.verificar()" in fonte
    # Mudar as preferências também tem de refazer a verificação.
    assert "self.verificar()" in inspect.getsource(
        SupervisaoProducaoDialog._abrir_preferencias
    )
