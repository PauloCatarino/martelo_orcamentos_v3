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
        contacto=(
            CampoImos(
                "FIRMA", "Cliente", "Cliente", "LINHAS DIREITAS, LDA", "LINHAS DIREITAS, LDA", 150
            ),
            CampoImos("MOBILE", "Telefone", "Ficha do cliente", "", "", 50),
        ),
    )


def _plano_com_textos() -> PlanoCriacaoImos:
    """Plano com as duas colunas editáveis: uma preenchida, outra vazia."""
    return PlanoCriacaoImos(
        caminho=CaminhoImos(
            niveis=(
                NivelCaminho("LANCA_ENCANTO", IMOS_TIPO_PASTA, 180),
                NivelCaminho("ANO_2026", IMOS_TIPO_PASTA, 6624),
                NivelCaminho("LINHAS_DIREITAS", IMOS_TIPO_PASTA, 6641),
                NivelCaminho("1260_01_26_LD", IMOS_TIPO_ENCOMENDA, None),
            )
        ),
        nome_encomenda="1260_01_26_LD",
        nome_sugerido="1260_01_26_LD",
        campos=(
            CampoImos("COMM", "Nº Enc PHC", "Nº Enc PHC", "1260", "1260", 80),
            CampoImos(
                "TEXT_SHORT",
                "Descrição produção",
                "Descrição produção",
                "roupeiro 4 portas",
                "roupeiro 4 portas",
                255,
            ),
            CampoImos(
                "TEXT_LONG", "Matérias usados", "Matérias usados", "", "", 255
            ),
        ),
        avisos=(),
        bloqueios=(),
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

    # 3 campos da encomenda + 2 dos dados do cliente
    assert dlg.campos_table.rowCount() == 5
    assert dlg.nome_input.text() == "1260_01_26_LINHAS_DIREITAS"
    assert dlg.contador_label.text() == "26/30"
    assert dlg.criar_button.isEnabled() is True


def test_dialogo_marca_a_pasta_que_falta(dialogo) -> None:
    dlg = dialogo(_plano(cliente_dir_id=None))

    assert dlg.caminho_table.item(2, 2).text() == "vai ser criada (não existe)"


def test_dialogo_mostra_o_campo_cortado_e_o_valor_original_na_dica(dialogo) -> None:
    dlg = dialogo(_plano())

    assert dlg.campos_table.item(1, 3).text() == "cortado de 400 para 255"
    # TEXT_SHORT é editável: a dica junta o valor original e o convite a corrigir.
    dica = dlg.campos_table.item(1, 2).toolTip()
    assert dica.startswith("A" * 400)
    assert "Duplo clique para corrigir" in dica
    assert dlg.campos_table.item(2, 3).text() == "vazio na obra"


def test_dialogo_distingue_os_dados_do_cliente_dos_da_encomenda(dialogo) -> None:
    dlg = dialogo(_plano())

    # As 3 primeiras linhas sao da encomenda; as 2 ultimas do cliente.
    assert dlg.campos_table.item(0, 1).text() == "COMM"
    assert dlg.campos_table.item(3, 1).text() == "FIRMA (dados do cliente)"
    assert dlg.campos_table.item(3, 2).text() == "LINHAS DIREITAS, LDA"
    assert dlg.campos_table.item(4, 1).text() == "MOBILE (dados do cliente)"
    assert dlg.campos_table.item(4, 3).text() == "vazio na obra"


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


def test_ensaio_ano_teste_foi_removido(dialogo) -> None:
    dlg = dialogo(_plano())

    assert not hasattr(dlg, "ensaio_check")
    assert "ANO_TESTE" not in inspect.getsource(ImosEncomendaDialog)


def test_aviso_ao_atingir_o_limite_de_30_caracteres(dialogo) -> None:
    dlg = dialogo(_plano())

    dlg.nome_input.setText("X" * 30)
    assert "máximo de 30 caracteres" in dlg.nome_limite_label.text()

    dlg.nome_input.setText("X" * 20)
    assert dlg.nome_limite_label.text() == ""


def test_larguras_das_colunas_ficam_guardadas_por_utilizador() -> None:
    source = inspect.getsource(ImosEncomendaDialog)

    assert source.count("ligar_persistencia_larguras(") == 2
    assert "dialog_imos_encomenda_caminho" in source
    assert "dialog_imos_encomenda_campos" in source


def test_so_a_descricao_e_as_materias_sao_editaveis(dialogo) -> None:
    from PySide6.QtCore import Qt

    dlg = dialogo(_plano_com_textos())

    editaveis = [
        dlg.campos_table.item(linha, 2).data(Qt.ItemDataRole.UserRole)
        for linha in range(dlg.campos_table.rowCount())
    ]
    assert editaveis == [None, "TEXT_SHORT", "TEXT_LONG"]

    def _e_editavel(linha: int) -> bool:
        flags = dlg.campos_table.item(linha, 2).flags()
        return bool(flags & Qt.ItemFlag.ItemIsEditable)

    assert _e_editavel(0) is False
    assert _e_editavel(1) is True
    assert _e_editavel(2) is True


def test_editar_a_descricao_guarda_a_correcao_sem_tocar_na_obra(dialogo) -> None:
    dlg = dialogo(_plano_com_textos())

    dlg.campos_table.item(1, 2).setText("ROUPEIRO CORRIGIDO")

    assert dlg._textos == {"TEXT_SHORT": "ROUPEIRO CORRIGIDO"}


def test_texto_editado_grande_demais_avisa_e_corta(dialogo, monkeypatch) -> None:
    avisos: list = []
    monkeypatch.setattr(
        imos_encomenda_dialog.QMessageBox,
        "warning",
        lambda *args, **_k: avisos.append(args[2]),
    )
    dlg = dialogo(_plano_com_textos())

    dlg.campos_table.item(1, 2).setText("Z" * 300)

    assert len(dlg._textos["TEXT_SHORT"]) == 255
    assert avisos and "só aceita 255 caracteres" in avisos[0]


def test_linhas_editaveis_dizem_que_o_sao(dialogo) -> None:
    dlg = dialogo(_plano_com_textos())

    assert dlg.campos_table.item(1, 3).text() == "editável"
    assert dlg.campos_table.item(2, 3).text() == "vazio na obra — pode escrever"
    assert "não é alterada" in dlg.campos_table.item(1, 2).toolTip()


def test_ligacao_imos_tem_interruptor_de_escrita() -> None:
    from app.ui.pages.imos_ligacao_page import ImosLigacaoPage

    source = inspect.getsource(ImosLigacaoPage)
    assert "Permitir que o Martelo crie encomendas no iMos" in source
    assert "KEY_IMOS_ESCRITA_ATIVA" in source
    # Gravar o interruptor é o que cria a definição numa base já existente.
    assert "guardar_valor(" in source
    assert "O iMos não tem desfazer" in source


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
