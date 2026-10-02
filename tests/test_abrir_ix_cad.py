"""O «Abrir no iX CAD» da Produção: perguntas, linha de estado e arranque."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.services import imos_cad_service as svc
from app.services.imos_sql import NoImos
from app.ui.helpers import abrir_ix_cad as helper
from app.ui.helpers.abrir_ix_cad import AbridorIxCad

_app = QApplication.instance() or QApplication([])

NOME = "1702_01_26_JF_VIVA"
INSTALACAO = svc.InstalacaoIxCad(
    17, Path("imos.exe"), Path("BIN"), r"I:\Factory\Imorder"
)


def _plano(*, tipo: int = 173, ja_aberta: bool = False, existe: bool = True) -> svc.PlanoAbertura:
    return svc.PlanoAbertura(
        encomenda=NoImos(dir_id=7727, nome=NOME, tipo=tipo, parent_id=6626),
        desenho=svc.caminho_desenho(r"I:\Factory\Imorder", NOME),
        desenho_existe=existe,
        ja_aberta_neste_pc=ja_aberta,
    )


class _Cenario:
    """Substitui o iMos/Windows e regista o que o Martelo fez."""

    def __init__(self, monkeypatch, *, plano=None, erro=None, canal=svc.ESTADO_CANAL_ATIVO,
                 instalacao=INSTALACAO, elevado=False, respostas=()):
        self.estados: list[str] = []
        self.avisos: list[str] = []
        self.perguntas: list[str] = []
        self.enviados: list[str] = []
        self.arranques = 0
        self.frente = 0
        self.canal = canal
        self.abertos: frozenset[str] = frozenset()
        respostas = list(respostas)

        def _preparar(*_a, **_k):
            if erro is not None:
                raise erro
            return plano or _plano()

        def _arrancar(_inst):
            self.arranques += 1

        def _frente():
            self.frente += 1
            return True

        monkeypatch.setattr(svc, "localizar_instalacao", lambda: instalacao)
        monkeypatch.setattr(svc, "preparar_abertura", _preparar)
        monkeypatch.setattr(svc, "estado_canal", lambda: self.canal)
        monkeypatch.setattr(svc, "enviar_comando", self.enviados.append)
        monkeypatch.setattr(svc, "arrancar_ix_cad", _arrancar)
        monkeypatch.setattr(svc, "trazer_para_frente", _frente)
        monkeypatch.setattr(svc, "martelo_elevado", lambda: elevado)
        monkeypatch.setattr(svc, "desenhos_abertos", lambda: self.abertos)
        monkeypatch.setattr(helper.diario_bordo, "registar_acao", lambda *_a, **_k: None)
        monkeypatch.setattr(
            QMessageBox, "warning", lambda _p, _t, texto, *_a: self.avisos.append(texto)
        )

        def _pergunta(_p, _t, texto, *_a):
            self.perguntas.append(texto)
            resposta = respostas.pop(0) if respostas else False
            return QMessageBox.StandardButton.Yes if resposta else QMessageBox.StandardButton.No

        monkeypatch.setattr(QMessageBox, "question", _pergunta)
        self.janela = QWidget()
        self.abridor = AbridorIxCad(self.janela, self.estados.append)

    def abrir(self) -> None:
        self.abridor.abrir(
            nome=NOME, dir_id=7727, cfg={"server": "s", "database": "d"},  # type: ignore[arg-type]
            pasta_imorder_martelo="",
        )

    def tique(self) -> None:
        self.abridor._tique()


def test_com_o_ix_cad_aberto_envia_o_imosopendwg_e_confirma(monkeypatch) -> None:
    c = _Cenario(monkeypatch)

    c.abrir()

    assert c.enviados == [_plano().comando]
    assert c.frente == 1
    assert c.estados[-1].startswith("Pedido enviado ao iX CAD")
    c.abertos = frozenset({f"{NOME}.DWG"})
    c.tique()
    assert c.estados[-1] == f"Obra {NOME} aberta no iX CAD."
    assert not c.abridor._temporizador.isActive()


def test_encomenda_inexistente_avisa_e_nao_toca_no_ix_cad(monkeypatch) -> None:
    c = _Cenario(monkeypatch, erro=svc.ErroIxCad(f"A encomenda «{NOME}» não existe no iX Organizer, por isso…\n\nCrie-a"))

    c.abrir()

    assert "não existe no iX Organizer" in c.avisos[0]
    assert c.enviados == [] and c.arranques == 0
    assert "\n" not in c.estados[-1]


def test_falha_a_ler_o_imos_nao_abre_as_cegas(monkeypatch) -> None:
    c = _Cenario(monkeypatch, erro=RuntimeError("network-related error"))

    c.abrir()

    assert "Não foi possível confirmar no iMos" in c.avisos[0]
    assert c.enviados == []


def test_imos_que_nao_responde_a_tempo(monkeypatch) -> None:
    import subprocess

    c = _Cenario(monkeypatch, erro=subprocess.TimeoutExpired("powershell", 60))

    c.abrir()

    assert "Não foi possível confirmar no iMos" in c.avisos[0]
    assert c.enviados == []


def test_nome_invalido_mostra_a_razao_verdadeira(monkeypatch) -> None:
    c = _Cenario(monkeypatch, erro=ValueError("Nome inválido para o iMos: 'X'"))

    c.abrir()

    assert "Nome inválido para o iMos" in c.avisos[0]
    assert c.enviados == []


def test_sem_ix_cad_instalado(monkeypatch) -> None:
    c = _Cenario(monkeypatch, instalacao=None)

    c.abrir()

    assert c.avisos == ["O iX CAD não está instalado neste PC."]


def test_obra_ja_aberta_so_passa_o_ix_cad_para_a_frente(monkeypatch) -> None:
    c = _Cenario(monkeypatch, plano=_plano(ja_aberta=True))

    c.abrir()

    assert c.enviados == []
    assert c.frente == 1
    assert "já está aberta" in c.estados[-1]


def test_avisos_do_organizer_pedem_confirmacao(monkeypatch) -> None:
    c = _Cenario(monkeypatch, plano=_plano(tipo=999987), respostas=[False])

    c.abrir()

    assert "em produção" in c.perguntas[0]
    assert c.enviados == []
    assert "não foi aberta" in c.estados[-1]


def test_avisos_aceites_abre(monkeypatch) -> None:
    c = _Cenario(monkeypatch, plano=_plano(tipo=673), respostas=[True])

    c.abrir()

    assert c.enviados == [_plano().comando]


def test_martelo_elevado_sem_acesso_ao_canal(monkeypatch) -> None:
    c = _Cenario(monkeypatch, canal=svc.ESTADO_CANAL_SEM_ACESSO)

    c.abrir()

    assert c.avisos == [svc.MENSAGEM_ELEVADO]
    assert c.enviados == [] and c.arranques == 0


def test_martelo_elevado_nao_arranca_o_ix_cad(monkeypatch) -> None:
    c = _Cenario(monkeypatch, canal=svc.ESTADO_CANAL_FECHADO, elevado=True)

    c.abrir()

    assert c.avisos == [svc.MENSAGEM_ELEVADO]
    assert c.arranques == 0 and c.perguntas == []


def test_ix_cad_fechado_pergunta_antes_de_o_abrir(monkeypatch) -> None:
    c = _Cenario(monkeypatch, canal=svc.ESTADO_CANAL_FECHADO, respostas=[False])

    c.abrir()

    assert "não está aberto" in c.perguntas[0]
    assert c.arranques == 0 and c.enviados == []


def test_ix_cad_fechado_arranca_espera_pelo_canal_e_pede_a_obra(monkeypatch) -> None:
    c = _Cenario(monkeypatch, canal=svc.ESTADO_CANAL_FECHADO, respostas=[True])

    c.abrir()
    assert c.arranques == 1
    assert c.abridor.ocupado
    assert c.estados[-1].startswith("A abrir o iX CAD")

    # Segundo clique durante o arranque: não arranca outro iX CAD.
    c.abrir()
    assert c.arranques == 1
    assert "ainda está a arrancar" in c.estados[-1]

    c.tique()  # ainda a carregar
    assert c.enviados == []

    c.canal = svc.ESTADO_CANAL_ATIVO
    c.tique()  # canal acabou de aparecer: espera um pouco, como o Organizer
    assert c.enviados == []
    assert "quase pronto" in c.estados[-1]

    monkeypatch.setattr(svc, "ESPERA_DEPOIS_DO_CANAL_S", 0)
    c.tique()
    assert c.enviados == [_plano().comando]
    assert c.estados[-1].startswith("Pedido enviado ao iX CAD")


def test_ix_cad_que_nunca_fica_pronto(monkeypatch) -> None:
    c = _Cenario(monkeypatch, canal=svc.ESTADO_CANAL_FECHADO, respostas=[True])
    c.abrir()

    monkeypatch.setattr(svc, "ESPERA_ARRANQUE_S", -1)
    c.tique()

    assert "não ficou pronto" in c.estados[-1]
    assert not c.abridor._temporizador.isActive()
    assert c.enviados == []


def test_pedido_que_nao_aparece_no_ix_cad(monkeypatch) -> None:
    c = _Cenario(monkeypatch)
    c.abrir()

    monkeypatch.setattr(helper, "CONFIRMACAO_S", -1)
    c.tique()

    assert "ainda não apareceu" in c.estados[-1]


@pytest.mark.parametrize("onde", ["menu", "campo"])
def test_producao_tem_a_opcao_no_menu_funcoes_e_no_campo(onde) -> None:
    from app.ui.pages.producao_page import ProducaoPage

    fonte = inspect.getsource(ProducaoPage)
    if onde == "menu":
        assert "self.funcoes_menu.addAction(self.abrir_ix_cad_action)" in fonte
    else:
        assert "self.nome_enc_imos_ix_input.addAction(" in fonte
    abrir = inspect.getsource(ProducaoPage._abrir_no_ix_cad)
    assert "imos_dir_id" in abrir and "load_imos_config" in abrir
