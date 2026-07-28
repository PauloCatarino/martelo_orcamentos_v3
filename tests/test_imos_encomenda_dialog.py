"""Verificações do diálogo de criação da encomenda no iMos."""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from app.services.imos_encomenda_service import CampoImos, PlanoCriacaoImos
from app.services.imos_sql import (
    IMOS_TIPO_ENCOMENDA,
    IMOS_TIPO_PASTA,
    CaminhoImos,
    NivelCaminho,
)
from app.ui.dialogs import imos_encomenda_dialog
from app.ui.dialogs.imos_encomenda_dialog import ImosEncomendaDialog

_app = QApplication.instance() or QApplication([])


class _SessaoFalsa:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def get(self, _modelo, _id):
        return SimpleNamespace(codigo_processo="26.1260_01_01")


def _plano(
    *,
    cliente_dir_id: int | None = 6641,
    encomenda_dir_id: int | None = None,
    avisos: tuple[str, ...] = (),
    bloqueios: tuple[str, ...] = (),
    nome: str = "1260_01_26_LINHAS_DIREITAS",
    nome_sugerido: str | None = None,
) -> PlanoCriacaoImos:
    return PlanoCriacaoImos(
        caminho=CaminhoImos(
            niveis=(
                NivelCaminho("LANCA_ENCANTO", IMOS_TIPO_PASTA, 180),
                NivelCaminho("ANO_2026", IMOS_TIPO_PASTA, 6624),
                NivelCaminho("LINHAS_DIREITAS", IMOS_TIPO_PASTA, cliente_dir_id),
                NivelCaminho(nome, IMOS_TIPO_ENCOMENDA, encomenda_dir_id),
            )
        ),
        nome_encomenda=nome,
        nome_sugerido=nome_sugerido or nome,
        campos=(
            CampoImos("COMM", "Nº Enc PHC", "Nº Enc PHC", "1260", "1260", 80),
            CampoImos(
                "TEXT_SHORT",
                "Descrição produção",
                "Descrição produção",
                "A" * 255,
                "A" * 400,
                255,
            ),
            CampoImos("ARTICLENO", "Ref. Cliente", "Ref Cliente", "", "", 30),
        ),
        avisos=avisos,
        bloqueios=bloqueios,
    )


@pytest.fixture()
def dialogo(monkeypatch):
    """Constrói o diálogo real, com o iMos e a base substituídos."""

    def _montar(plano: PlanoCriacaoImos, *, escrita_ativa: bool = True):
        monkeypatch.setattr(
            imos_encomenda_dialog, "SessionLocal", lambda: _SessaoFalsa()
        )
        monkeypatch.setattr(
            imos_encomenda_dialog, "load_imos_config", lambda _s: {}
        )
        monkeypatch.setattr(
            imos_encomenda_dialog, "carregar_escrita_ativa", lambda _s: escrita_ativa
        )
        monkeypatch.setattr(
            imos_encomenda_dialog, "preparar", lambda *_a, **_k: plano
        )
        return ImosEncomendaDialog(processo_id=1)

    return _montar


def test_dialogo_constroi_e_preenche_as_tabelas(dialogo) -> None:
    dlg = dialogo(_plano())

    assert dlg.caminho_table.rowCount() == 4
    assert dlg.caminho_table.item(0, 1).text() == "LANCA_ENCANTO"
    assert "já existe (DIR_ID 180)" in dlg.caminho_table.item(0, 2).text()
    assert dlg.caminho_table.item(3, 2).text() == "vai ser criada agora"

    assert dlg.campos_table.rowCount() == 3
    assert dlg.nome_input.text() == "1260_01_26_LINHAS_DIREITAS"
    assert dlg.contador_label.text() == "26/30"
    assert dlg.criar_button.isEnabled() is True


def test_dialogo_marca_a_pasta_que_falta(dialogo) -> None:
    dlg = dialogo(_plano(cliente_dir_id=None))

    assert dlg.caminho_table.item(2, 2).text() == "vai ser criada (não existe)"


def test_dialogo_mostra_o_campo_cortado_e_o_valor_original_na_dica(dialogo) -> None:
    dlg = dialogo(_plano())

    assert dlg.campos_table.item(1, 3).text() == "cortado de 400 para 255"
    assert dlg.campos_table.item(1, 2).toolTip() == "A" * 400
    assert dlg.campos_table.item(2, 3).text() == "vazio na obra"


def test_dialogo_bloqueado_desativa_o_botao_criar(dialogo) -> None:
    dlg = dialogo(_plano(bloqueios=("Já existe uma encomenda 'X' nesta pasta.",)))

    assert dlg.criar_button.isEnabled() is False
    assert "Já existe uma encomenda" in dlg.avisos_label.text()
    assert "Resolva os pontos a vermelho" in dlg.status_label.text()


def test_escrita_desligada_desativa_o_botao_mesmo_sem_bloqueios(dialogo) -> None:
    dlg = dialogo(_plano(), escrita_ativa=False)

    assert dlg.criar_button.isEnabled() is False
    assert "imos_escrita_ativa" in dlg.avisos_label.text()
    assert "escrita no iMos está desligada" in dlg.status_label.text()


def test_nome_cortado_explica_qual_era_o_nome_completo(dialogo) -> None:
    dlg = dialogo(
        _plano(
            nome="1260_01_26_VIRGILIO_PEREIRA_LO",
            nome_sugerido="1260_01_26_VIRGILIO_PEREIRA_LOPES",
        )
    )

    assert "1260_01_26_VIRGILIO_PEREIRA_LOPES" in dlg.nome_original_label.text()
    assert "33 caracteres" in dlg.nome_original_label.text()
    assert dlg.contador_label.text() == "30/30"


def test_contador_acompanha_a_edicao_do_nome(dialogo) -> None:
    dlg = dialogo(_plano())

    dlg.nome_input.setText("1260_01_26_LD")

    assert dlg.contador_label.text() == "13/30"


def test_nome_nao_pode_ultrapassar_o_limite_do_imos(dialogo) -> None:
    dlg = dialogo(_plano())

    dlg.nome_input.setText("X" * 60)

    assert len(dlg.nome_input.text()) == 30


def test_dialogo_comeca_sem_nada_criado(dialogo) -> None:
    assert dialogo(_plano()).criada is False


def test_dialogo_mostra_caminho_nome_e_campos() -> None:
    source = inspect.getsource(ImosEncomendaDialog)

    assert "Onde vai ser criada" in source
    assert "Nome da encomenda" in source
    assert "O que vai ser gravado na encomenda" in source
    assert "já existe (DIR_ID" in source


def test_dialogo_avisa_que_o_imos_nao_tem_desfazer() -> None:
    source = inspect.getsource(ImosEncomendaDialog)

    assert "não tem desfazer" in source
    assert "O iMos não tem desfazer." in source


def test_botao_criar_nasce_desativado_e_confirma_antes_de_gravar() -> None:
    source = inspect.getsource(ImosEncomendaDialog)

    assert "self.criar_button.setEnabled(False)" in source
    assert "QMessageBox.question" in source
    assert "StandardButton.No," in source  # a resposta pré-selecionada é Não


def test_criar_recalcula_o_plano_antes_de_escrever() -> None:
    """O nome pode ter sido editado: o plano tem de ser refeito antes de gravar."""
    source = inspect.getsource(ImosEncomendaDialog._criar)

    assert source.index("self._recarregar()") < source.index("QMessageBox.question")
    assert "if not plano.pode_criar or not self._escrita_ativa:" in source


def test_dialogo_respeita_o_interruptor_de_escrita() -> None:
    source = inspect.getsource(ImosEncomendaDialog)

    assert "carregar_escrita_ativa" in source
    assert "KEY_IMOS_ESCRITA_ATIVA" in source
    assert "pode = plano.pode_criar and self._escrita_ativa" in source


def test_contador_do_nome_usa_o_limite_do_imos() -> None:
    source = inspect.getsource(ImosEncomendaDialog)

    assert "setMaxLength(IMOS_NOME_MAX)" in source
    assert 'f"{usados}/{IMOS_NOME_MAX}"' in source


def test_enter_nao_dispara_a_criacao() -> None:
    assert "keyPressEvent" in inspect.getsource(ImosEncomendaDialog)


def test_producao_liga_a_acao_ao_menu_funcoes() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    source = inspect.getsource(ProducaoPage)
    assert "Criar Encomenda IMOS…" in source
    assert "self.funcoes_menu.addAction(self.criar_encomenda_imos_action)" in source
    assert "_abrir_criar_encomenda_imos" in source


def test_producao_exige_obra_selecionada() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    source = inspect.getsource(ProducaoPage._abrir_criar_encomenda_imos)
    assert "Selecione uma obra" in source
    assert "processo_id=processo.id" in source
