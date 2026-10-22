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
                 instalacao=INSTALACAO, elevado=False, respostas=(), copiado=True,
                 erro_preparar=None):
        self.estados: list[str] = []
        self.avisos: list[str] = []
        self.perguntas: list[str] = []
        self.enviados: list[str] = []
        self.preparados: list[tuple[str, str]] = []
        self.arranques = 0
        self.frente = 0
        self.canal = canal
        self.abertos: frozenset[str] = frozenset()
        self.ativo = ""
        self.gravado: float | None = 1.0
        respostas = list(respostas)

        def _preparar_desenho(pasta, nome, _modelo):
            if erro_preparar is not None:
                raise erro_preparar
            self.preparados.append((pasta, nome))
            return copiado

        monkeypatch.setattr(svc, "preparar_desenho_novo", _preparar_desenho)
        monkeypatch.setattr(svc, "modelo_desenho", lambda _inst: Path("IMOS.dwt"))
        monkeypatch.setattr(svc, "desenho_ativo", lambda: self.ativo)
        monkeypatch.setattr(svc, "momento_gravacao", lambda _d: self.gravado)
        monkeypatch.setattr(svc, "PAUSA_DEPOIS_SEM_AVISO_S", 0)

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
        monkeypatch.setattr(
            svc, "enviar_comando", lambda comando, **_k: self.enviados.append(comando)
        )
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

    def abrir_obra_nova(self) -> None:
        self.abridor.abrir_obra_nova(
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


# --------------------------------------------------------------------------
# Obra nova (fase E3): preparar o desenho, abrir e gravar
# --------------------------------------------------------------------------


def _ate_gravar(c: _Cenario, monkeypatch) -> None:
    """Obra nova pedida, aberta no iX CAD e já no separador ativo."""
    c.abrir_obra_nova()
    c.abertos = frozenset({f"{NOME}.DWG"})
    c.tique()  # apareceu: passa a «gravar»
    monkeypatch.setattr(helper, "ESPERA_ANTES_DE_GRAVAR_S", 0)
    c.ativo = f"{NOME}.DWG"


def test_obra_nova_prepara_abre_sem_aviso_e_grava(monkeypatch) -> None:
    c = _Cenario(monkeypatch)

    c.abrir_obra_nova()

    assert c.preparados == [(r"I:\Factory\Imorder", NOME)]
    # Como o LoadOrderInAcad do Organizer: primeiro sem o aviso de carregamento.
    assert c.enviados == [svc.COMANDO_SEM_AVISO_CARREGAR, _plano().comando]

    c.abertos = frozenset({f"{NOME}.DWG"})
    c.tique()
    assert "a seguir é gravada" in c.estados[-1]
    assert c.abridor.ocupado

    monkeypatch.setattr(helper, "ESPERA_ANTES_DE_GRAVAR_S", 0)
    c.ativo = f"{NOME}.DWG"
    c.tique()
    assert c.enviados[-1] == svc.COMANDO_GRAVAR
    assert c.estados[-1] == f"A gravar a obra {NOME} no iX CAD…"

    c.tique()  # a data do desenho ainda não mudou
    assert c.abridor.ocupado

    c.gravado = 2.0
    c.tique()
    assert c.estados[-1] == f"Obra {NOME} aberta e gravada no iX CAD: pode desenhar."
    assert not c.abridor._temporizador.isActive()
    assert c.enviados.count(svc.COMANDO_GRAVAR) == 1


def test_obra_nova_que_ja_tinha_desenho_so_abre(monkeypatch) -> None:
    c = _Cenario(monkeypatch, copiado=False)

    c.abrir_obra_nova()
    c.abertos = frozenset({f"{NOME}.DWG"})
    c.tique()

    assert c.enviados == [_plano().comando]
    assert c.estados[-1] == f"Obra {NOME} aberta no iX CAD."


def test_obra_nova_nao_grava_se_o_separador_ativo_for_outro(monkeypatch) -> None:
    c = _Cenario(monkeypatch)
    _ate_gravar(c, monkeypatch)
    c.ativo = "APAGAR_05.DWG"

    c.tique()  # dá tempo ao iX CAD para mudar de separador
    assert svc.COMANDO_GRAVAR not in c.enviados

    monkeypatch.setattr(helper, "ESPERA_SEPARADOR_ATIVO_S", -1)
    c.tique()
    assert svc.COMANDO_GRAVAR not in c.enviados
    assert "não foi gravada" in c.estados[-1]
    assert not c.abridor._temporizador.isActive()


def test_obra_nova_sem_pasta_dos_desenhos_nao_toca_no_ix_cad(monkeypatch) -> None:
    c = _Cenario(monkeypatch, erro_preparar=svc.ErroIxCad("A pasta dos desenhos do iMos não está acessível neste PC:\nI:"))

    c.abrir_obra_nova()

    assert "não está acessível" in c.avisos[0]
    assert c.enviados == [] and c.arranques == 0
    assert "\n" not in c.estados[-1]


def test_obra_nova_sem_ix_cad_instalado_nao_prepara_nada(monkeypatch) -> None:
    c = _Cenario(monkeypatch, instalacao=None)

    c.abrir_obra_nova()

    assert c.avisos == ["O iX CAD não está instalado neste PC."]
    assert c.preparados == []


def test_gravacao_que_nao_acontece_explica(monkeypatch) -> None:
    c = _Cenario(monkeypatch)
    _ate_gravar(c, monkeypatch)
    c.tique()  # pede a gravação

    monkeypatch.setattr(helper, "GRAVACAO_S", -1)
    c.tique()

    assert "ainda não foi gravado" in c.estados[-1]
    assert not c.abridor._temporizador.isActive()


def test_pedido_de_gravar_recusado_pelo_canal(monkeypatch) -> None:
    c = _Cenario(monkeypatch)
    _ate_gravar(c, monkeypatch)

    def _recusa(comando, **_k):
        raise svc.ErroIxCad("O iX CAD ainda não leu o pedido anterior.\nEspere.")

    monkeypatch.setattr(svc, "enviar_comando", _recusa)
    c.tique()

    assert "não foi possível pedir a gravação" in c.estados[-1]
    assert "Grave-a no iX CAD" in c.estados[-1]


def test_segundo_pedido_durante_a_gravacao_nao_mexe_em_nada(monkeypatch) -> None:
    c = _Cenario(monkeypatch)
    _ate_gravar(c, monkeypatch)
    c.tique()
    enviados = list(c.enviados)

    c.abrir()

    assert "ainda está a gravar" in c.estados[-1]
    assert c.enviados == enviados


def test_obra_nova_com_ix_cad_fechado_arranca_e_depois_grava(monkeypatch) -> None:
    c = _Cenario(monkeypatch, canal=svc.ESTADO_CANAL_FECHADO, respostas=[True])
    monkeypatch.setattr(svc, "ESPERA_DEPOIS_DO_CANAL_S", 0)

    c.abrir_obra_nova()
    assert c.arranques == 1 and c.enviados == []

    c.canal = svc.ESTADO_CANAL_ATIVO
    c.tique()  # o canal apareceu
    c.tique()  # pede a obra
    assert c.enviados == [svc.COMANDO_SEM_AVISO_CARREGAR, _plano().comando]

    c.abertos = frozenset({f"{NOME}.DWG"})
    c.tique()
    assert "a seguir é gravada" in c.estados[-1]


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


def test_producao_abre_e_grava_a_encomenda_acabada_de_criar() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    criar = inspect.getsource(ProducaoPage._abrir_criar_encomenda_imos)
    assert "dialog.abrir_a_seguir" in criar
    assert "encomenda.nome, encomenda.dir_id" in criar
    nova = inspect.getsource(ProducaoPage._abrir_encomenda_nova_no_ix_cad)
    assert ".abrir_obra_nova(" in nova and "load_imos_config" in nova
