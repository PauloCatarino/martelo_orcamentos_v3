"""Tests for the raw-materials Excel verification dialog."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.materias_primas_validacao import (
    AVISO,
    CRITICO,
    INFO,
    AvisoExcel,
    RelatorioExcel,
)
from app.ui.dialogs.verificar_excel_materias_primas_dialog import (
    VerificarExcelMateriasPrimasDialog,
)

_app = QApplication.instance() or QApplication([])


def _relatorio() -> RelatorioExcel:
    return RelatorioExcel(
        avisos=(
            AvisoExcel(
                severidade=AVISO,
                categoria="preco_desatualizado",
                mensagem="Preço com 13 meses — deve ser revisto.",
                linha=20,
                ref_le="FER0001",
            ),
            AvisoExcel(
                severidade=CRITICO,
                categoria="preco_em_falta",
                mensagem="Preço líquido a zero.",
                linha=14,
                ref_le="PLC0009",
                descricao="AGL FOL ALD. FAIA BRANCA",
                detalhe="Preencha o PRECO_TABELA.",
            ),
            AvisoExcel(
                severidade=INFO,
                categoria="preco_alterado",
                mensagem="Preço de tabela alterado: 20 € → 24 €.",
                linha=6,
                ref_le="PLC0001",
            ),
        ),
        total_linhas=332,
    )


def test_dialogo_mostra_criticos_primeiro() -> None:
    dialogo = VerificarExcelMateriasPrimasDialog(_relatorio(), "C:/TAB.xlsm")

    # Informativos começam desligados, por isso ficam 2 linhas visíveis.
    assert dialogo.table.rowCount() == 2
    assert dialogo.table.item(0, 0).text() == CRITICO
    assert dialogo.table.item(0, 2).text() == "PLC0009"
    assert dialogo.table.item(1, 0).text() == AVISO


def test_filtros_escondem_e_mostram_severidades() -> None:
    dialogo = VerificarExcelMateriasPrimasDialog(_relatorio())

    dialogo.filtro_informativos.setChecked(True)
    assert dialogo.table.rowCount() == 3

    dialogo.filtro_criticos.setChecked(False)
    dialogo.filtro_avisos.setChecked(False)
    assert dialogo.table.rowCount() == 1
    assert dialogo.table.item(0, 0).text() == INFO


def test_linha_do_supervisor_avisa_quando_ha_criticos() -> None:
    dialogo = VerificarExcelMateriasPrimasDialog(_relatorio())

    assert "críticos" in dialogo.status_label.text()

    sem_criticos = RelatorioExcel(avisos=(), total_linhas=10)
    limpo = VerificarExcelMateriasPrimasDialog(sem_criticos)

    assert "pode importar" in limpo.status_label.text()


def test_texto_para_copiar_leva_cabecalho_e_linhas_visiveis() -> None:
    dialogo = VerificarExcelMateriasPrimasDialog(_relatorio())

    linhas = dialogo.texto_para_copiar().splitlines()

    assert linhas[0].startswith("Gravidade\tLinha\tRef LE")
    assert len(linhas) == 3  # cabeçalho + 2 avisos visíveis
    assert "PLC0009" in linhas[1]


def test_dialogo_nao_grava_nada() -> None:
    """O diálogo é só de leitura: não conhece serviços nem sessões."""
    import inspect

    from app.ui.dialogs import verificar_excel_materias_primas_dialog as modulo

    fonte = inspect.getsource(modulo)

    assert "SessionLocal" not in fonte
    assert "Service" not in fonte
    assert "commit" not in fonte
