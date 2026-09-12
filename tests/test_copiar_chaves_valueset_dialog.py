"""O diálogo de copiar chaves não deixa marcar o que não pode ser mexido."""

from __future__ import annotations

import sys

import pytest
from PySide6.QtCore import Qt

from app.services.def_valueset_chave_copia_service import (
    ACRESCENTAR_E_ATUALIZAR,
    SO_ACRESCENTAR,
    ChaveDisponivel,
    ContextoCopiaChaves,
    DestinoCopiaChaves,
    PrevisaoChaveDestino,
)

VARAO = "FERRAGEM_VARAO"
SUPORTE = "FERRAGEM_SUPORTE_LATERAL_VARAO"


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


CHAVES = (
    ChaveDisponivel(chave=VARAO, nome="Varão", grupo="Ferragens", opcoes=3),
    ChaveDisponivel(chave=SUPORTE, nome="Suporte lateral", grupo="Ferragens", opcoes=2),
)


def _destino(id, codigo, *, criar=0, atualizar=0, permitido=True, motivo=None):
    return DestinoCopiaChaves(
        modelo_id=id,
        modelo_codigo=codigo,
        modelo_nome=codigo,
        tipo="ROUPEIRO",
        ambito="Meu utilizador" if permitido else "Outro utilizador",
        proprietario="paulo" if permitido else "ana",
        modelo_ativo=True,
        permitido=permitido,
        motivo_bloqueio=motivo,
        previsoes=(
            PrevisaoChaveDestino(
                chave=VARAO, a_criar=criar, a_atualizar=atualizar,
                iguais=1, so_no_destino=2,
            ),
        ),
    )


def _contexto(modo=SO_ACRESCENTAR):
    return ContextoCopiaChaves(
        modelo_origem_id=1,
        modelo_origem_codigo="ORIGEM",
        chaves=(VARAO,),
        modo=modo,
        destinos=(
            _destino(2, "MEU", criar=4),
            _destino(3, "DELA", criar=4, permitido=False, motivo="Sem permissão."),
            _destino(4, "IGUAL"),  # nada a fazer
        ),
    )


def _abrir(_app, chaves_iniciais=None):
    from app.ui.dialogs.copiar_chaves_valueset_dialog import (
        CopiarChavesValuesetDialog,
    )

    chamadas: list = []

    def recalcular(chaves, modo):
        chamadas.append((list(chaves), modo))
        return _contexto(modo)

    dialog = CopiarChavesValuesetDialog(
        "ORIGEM", CHAVES, recalcular, chaves_iniciais=chaves_iniciais or [VARAO]
    )
    return dialog, chamadas


def test_a_chave_que_estava_filtrada_ja_vem_marcada(_app) -> None:
    dialog, _chamadas = _abrir(_app, chaves_iniciais=[SUPORTE])

    assert dialog.chaves_escolhidas == [SUPORTE]


def test_destino_bloqueado_nao_se_consegue_marcar(_app) -> None:
    dialog, _chamadas = _abrir(_app)

    bloqueado = dialog.destinos_table.item(1, 0)
    assert bloqueado.flags() == Qt.ItemFlag.NoItemFlags
    assert "Sem permissão" in bloqueado.toolTip()

    permitido = dialog.destinos_table.item(0, 0)
    assert permitido.flags() & Qt.ItemFlag.ItemIsUserCheckable


def test_destino_sem_nada_a_fazer_tambem_nao_se_marca(_app) -> None:
    dialog, _chamadas = _abrir(_app)

    sem_efeito = dialog.destinos_table.item(2, 0)
    assert sem_efeito.flags() == Qt.ItemFlag.NoItemFlags
    assert "nada a criar" in sem_efeito.toolTip()


def test_o_botao_so_liga_quando_ha_mesmo_o_que_copiar(_app) -> None:
    dialog, _chamadas = _abrir(_app)

    assert dialog.botao_copiar.isEnabled() is False
    assert "Marque os modelos" in dialog.status_label.text()

    dialog.destinos_table.item(0, 0).setCheckState(Qt.CheckState.Checked)

    assert dialog.destinos_escolhidos == [2]
    assert dialog.botao_copiar.isEnabled() is True
    assert "4 linha(s) a criar" in dialog.status_label.text()
    assert "Nada é apagado" in dialog.status_label.text()


def test_sem_chaves_nao_ha_destinos_nem_botao(_app) -> None:
    dialog, _chamadas = _abrir(_app)

    dialog.chaves_table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)

    assert dialog.chaves_escolhidas == []
    assert dialog.destinos_table.rowCount() == 0
    assert dialog.botao_copiar.isEnabled() is False
    assert "pelo menos uma chave" in dialog.status_label.text()


def test_mudar_o_modo_refaz_a_conta(_app) -> None:
    dialog, chamadas = _abrir(_app)
    antes = len(chamadas)

    dialog.modo_atualizar.setChecked(True)

    assert dialog.modo == ACRESCENTAR_E_ATUALIZAR
    assert len(chamadas) > antes
    assert chamadas[-1][1] == ACRESCENTAR_E_ATUALIZAR


def test_marcar_outra_chave_refaz_a_conta(_app) -> None:
    dialog, chamadas = _abrir(_app)

    dialog.chaves_table.item(1, 0).setCheckState(Qt.CheckState.Checked)

    assert dialog.chaves_escolhidas == [VARAO, SUPORTE]
    assert chamadas[-1][0] == [VARAO, SUPORTE]


def test_o_modo_de_partida_e_o_menos_destrutivo(_app) -> None:
    dialog, _chamadas = _abrir(_app)

    assert dialog.modo == SO_ACRESCENTAR
    assert dialog.modo_acrescentar.isChecked() is True
