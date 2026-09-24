"""Tempo ativo no iMos e na Lista Material, por obra (pedido do Paulo, 24-09-2026).

Nem o iMos nem o Excel guardam o tempo de trabalho: o Martelo mede-o pela
janela em primeiro plano, contando só com atividade nos últimos 5 minutos.
É uma métrica do tempo que a obra leva em desenho e na passagem à produção,
visível só para o administrador.
"""

from __future__ import annotations

import os
from datetime import date
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.core.janela_ativa import JanelaAtiva
from app.domain.tempo_programas import (
    PROGRAMA_EXCEL,
    PROGRAMA_IMOS,
    chave_encomenda,
    identificar_janela,
)
from app.models import ProducaoTempoAtividade
from app.models.user import User
from app.services.producao_tempo_atividade_service import (
    ProducaoTempoAtividadeService,
    TempoObra,
    chaves_da_obra,
)


# ----- que janelas contam -----


@pytest.mark.parametrize(
    ("processo", "titulo", "esperado"),
    [
        # Os títulos reais, vistos no PC do Paulo.
        ("imos.exe", "iX CAD 2025 - [0406_01_26_JF_VIVA.dwg]", ("imos", "0406_01_26_JF_VIVA")),
        ("excel.exe", "Lista_Material_1599_01_26_TEMPO_PLURAL.xlsm - Excel", ("excel", "1599_01_26_TEMPO_PLURAL")),
        # Obras "_" (Encomenda de Cliente Final).
        ("imos.exe", "iX CAD 2025 - [_263_01_26_RUI_CHANCELARIA.dwg]", ("imos", "_263_01_26_RUI_CHANCELARIA")),
        # Caminho inteiro no título, ficheiro só de leitura.
        ("imos.exe", r"iX CAD 2025 - [I:\Order\1599_01_26_TEMPO_PLURAL.dwg]", ("imos", "1599_01_26_TEMPO_PLURAL")),
        ("excel.exe", "Lista_Material_1599_01_26_TEMPO_PLURAL.xlsm  [Só de Leitura] - Excel", ("excel", "1599_01_26_TEMPO_PLURAL")),
        # O Windows não deixou ler o processo: decide o título.
        ("", "iX CAD 2025 - [0406_01_26_JF_VIVA.dwg]", ("imos", "0406_01_26_JF_VIVA")),
    ],
)
def test_janelas_que_contam(processo, titulo, esperado) -> None:
    assert tuple(identificar_janela(processo, titulo)) == esperado


@pytest.mark.parametrize(
    ("processo", "titulo"),
    [
        ("imos.exe", "iX CAD 2025"),  # sem desenho aberto
        ("imos.exe", "iX CAD 2025 - [Drawing1.dwg]"),  # desenho solto
        ("imos.exe", "iX CAD 2025 - [ORC_260881_2604023.dwg]"),  # orçamento: fora
        ("imos.exe", "iX Article Center"),
        ("organizer.exe", "iX Organizer"),  # decisão: o Organizer não conta
        ("excel.exe", "Orçamento 260961.xlsx - Excel"),  # outro Excel
        ("martelo_orcamentos_v3.exe", "Martelo Orçamentos V3"),
        ("explorer.exe", "Lista_Material_1599_01_26_TEMPO_PLURAL.xlsm"),
    ],
)
def test_janelas_que_nao_contam(processo, titulo) -> None:
    assert identificar_janela(processo, titulo) is None


# ----- o contador -----


class _Relogio:
    def __init__(self) -> None:
        self.agora = 1000.0

    def __call__(self) -> float:
        return self.agora


@pytest.fixture
def contador(monkeypatch):
    from PySide6.QtWidgets import QApplication

    from app.ui import tempo_programas_tracker as mod

    QApplication.instance() or QApplication([])
    gravado: list[tuple] = []
    diario: list[tuple] = []

    class _ServicoFalso:
        def __init__(self, _session) -> None:
            pass

        def adicionar_segundos(self, user_id, programa, nome, dia, segundos):
            gravado.append((user_id, programa, nome, dia, segundos))

    class _Sessao:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def commit(self):
            pass

    monkeypatch.setattr(mod, "ProducaoTempoAtividadeService", _ServicoFalso)
    monkeypatch.setattr(mod, "SessionLocal", _Sessao)
    monkeypatch.setattr(mod.diario_bordo, "registar_acao", lambda *a: diario.append(a))

    relogio = _Relogio()
    janela = {"atual": None}

    def _nova(user_id=7):
        tracker = mod.TempoProgramasTracker(
            None,
            user_id=user_id,
            leitor=lambda: janela["atual"],
            relogio=relogio,
            hoje=lambda: date(2026, 9, 24),
            iniciar=False,
        )
        return tracker

    def _passar(tracker, segundos, *, processo, titulo, parado=0.0):
        janela["atual"] = JanelaAtiva(processo, titulo, parado)
        for _ in range(int(segundos // 5)):
            relogio.agora += 5
            tracker._tick()

    return SimpleNamespace(nova=_nova, passar=_passar, gravado=gravado, diario=diario)


IMOS_0406 = dict(processo="imos.exe", titulo="iX CAD 2025 - [0406_01_26_JF_VIVA.dwg]")
EXCEL_1599 = dict(processo="excel.exe", titulo="Lista_Material_1599_01_26_TEMPO_PLURAL.xlsm - Excel")


def _total(gravado, programa, nome):
    return sum(s for _u, p, n, _d, s in gravado if p == programa and n == nome)


def test_conta_o_desenho_e_grava_de_minuto_a_minuto(contador) -> None:
    tracker = contador.nova()

    contador.passar(tracker, 60, **IMOS_0406)

    assert contador.gravado == [(7, "imos", "0406_01_26_JF_VIVA", date(2026, 9, 24), 60)]


def test_parado_mais_de_5_minutos_nao_conta(contador) -> None:
    tracker = contador.nova()

    contador.passar(tracker, 120, parado=301, **IMOS_0406)
    tracker.encerrar()

    assert contador.gravado == []


def test_a_olhar_para_o_desenho_sem_mexer_ainda_conta(contador) -> None:
    tracker = contador.nova()

    contador.passar(tracker, 60, parado=240, **IMOS_0406)

    assert _total(contador.gravado, "imos", "0406_01_26_JF_VIVA") == 60


def test_cada_obra_e_programa_leva_o_seu_tempo(contador) -> None:
    tracker = contador.nova()

    contador.passar(tracker, 30, **IMOS_0406)
    contador.passar(tracker, 20, **EXCEL_1599)
    contador.passar(tracker, 10, processo="martelo.exe", titulo="Martelo")  # não conta
    tracker.encerrar()

    assert _total(contador.gravado, "imos", "0406_01_26_JF_VIVA") == 30
    assert _total(contador.gravado, "excel", "1599_01_26_TEMPO_PLURAL") == 20
    assert sum(s for *_r, s in contador.gravado) == 50


def test_ao_fechar_grava_o_que_falta(contador) -> None:
    tracker = contador.nova()

    contador.passar(tracker, 25, **IMOS_0406)
    assert contador.gravado == []
    tracker.encerrar()

    assert _total(contador.gravado, "imos", "0406_01_26_JF_VIVA") == 25


def test_pc_suspenso_nao_vira_horas_de_trabalho(contador) -> None:
    tracker = contador.nova()
    contador.passar(tracker, 5, **IMOS_0406)

    tracker._relogio.agora += 3600  # uma hora de PC suspenso
    tracker._tick()
    tracker.encerrar()

    assert _total(contador.gravado, "imos", "0406_01_26_JF_VIVA") <= 5 + 20


def test_sem_utilizador_nao_mede(contador) -> None:
    tracker = contador.nova(user_id=None)

    contador.passar(tracker, 60, **IMOS_0406)
    tracker.encerrar()

    assert contador.gravado == []


def test_windows_a_falhar_nao_parte_nada(contador) -> None:
    tracker = contador.nova()

    def _rebenta():
        raise OSError("sem acesso")

    tracker._leitor = _rebenta
    tracker._tick()
    tracker.encerrar()

    assert contador.gravado == []


def test_desenho_do_imos_sem_obra_fica_no_diario_uma_vez(contador) -> None:
    """Se uma versão nova do iMos mudar o título, dá-se por isso no diário."""
    tracker = contador.nova()

    contador.passar(tracker, 30, processo="imos.exe", titulo="iX CAD 2026 · 0406-01-26.dwg")

    assert len(contador.diario) == 1
    assert "0406-01-26.dwg" in contador.diario[0][1]


# ----- gravar e ligar às obras -----


def _utilizador(session, uid, nome):
    session.add(
        User(
            id=uid,
            username=nome.lower(),
            nome=nome,
            email=f"{nome.lower()}@exemplo.pt",
            password_hash="-",
            role="user",
            is_active=True,
        )
    )
    session.flush()


def _obra(pid, codigo, *, num="1211", versao="01", plano="01", cliente="STHINK", imos_nome=None):
    return SimpleNamespace(
        id=pid,
        codigo_processo=codigo,
        ano="2026",
        num_enc_phc=num,
        versao_obra=versao,
        versao_plano=plano,
        nome_cliente_simplex=cliente,
        nome_cliente=cliente,
        ref_cliente=None,
        imos_nome_encomenda=imos_nome,
    )


def test_soma_no_mesmo_dia_e_separa_os_dias(session) -> None:
    _utilizador(session, 5, "Pedro")
    servico = ProducaoTempoAtividadeService(session)

    servico.adicionar_segundos(5, PROGRAMA_IMOS, "1599_01_26_TEMPO_PLURAL", date(2026, 9, 24), 60)
    servico.adicionar_segundos(5, PROGRAMA_IMOS, "1599_01_26_TEMPO_PLURAL", date(2026, 9, 24), 45)
    servico.adicionar_segundos(5, PROGRAMA_IMOS, "1599_01_26_TEMPO_PLURAL", date(2026, 9, 25), 30)
    session.commit()

    linhas = session.query(ProducaoTempoAtividade).order_by(ProducaoTempoAtividade.dia).all()
    assert [(l.dia.day, l.segundos) for l in linhas] == [(24, 105), (25, 30)]


def test_liga_o_tempo_a_obra_pelo_nome_do_imos(session) -> None:
    _utilizador(session, 5, "Pedro")
    _utilizador(session, 6, "Paulo")
    servico = ProducaoTempoAtividadeService(session)
    dia = date(2026, 9, 24)
    servico.adicionar_segundos(5, PROGRAMA_IMOS, "1599_01_26_TEMPO_PLURAL", dia, 3600)
    servico.adicionar_segundos(6, PROGRAMA_IMOS, "1599_01_26_TEMPO_PLURAL", dia, 600)
    servico.adicionar_segundos(5, PROGRAMA_EXCEL, "1599_01_26_TEMPO_PLURAL", dia, 900)
    servico.adicionar_segundos(5, PROGRAMA_IMOS, "9999_01_26_OUTRA", dia, 999)  # sem obra
    session.commit()
    obra = _obra(1, "26.1599_01_01_TEMPO_PLURAL", num="1599", cliente="TEMPO_PLURAL")

    tempos = servico.tempos_por_obra([obra])

    tempo = tempos[1]
    assert (tempo.desenho, tempo.excel) == (4200, 900)
    assert tempo.por_pessoa == {"Pedro": [3600, 900], "Paulo": [600, 0]}
    assert tempo.partilhado_com == ()


def test_planos_da_mesma_encomenda_mostram_o_mesmo_tempo_com_aviso(session) -> None:
    _utilizador(session, 5, "Pedro")
    servico = ProducaoTempoAtividadeService(session)
    servico.adicionar_segundos(5, PROGRAMA_IMOS, "1211_01_26_STHINK", date(2026, 9, 24), 1200)
    session.commit()
    plano1 = _obra(1, "26.1211_01_01_STHINK")
    plano2 = _obra(2, "26.1211_01_02_STHINK", plano="02")
    outra = _obra(3, "26.1212_01_01_STHINK", num="1212")

    tempos = servico.tempos_por_obra([plano1, plano2, outra])

    assert tempos[1].desenho == tempos[2].desenho == 1200
    assert tempos[1].partilhado_com == ("26.1211_01_02_STHINK",)
    assert tempos[2].partilhado_com == ("26.1211_01_01_STHINK",)
    assert 3 not in tempos


def test_nome_comprido_cortado_aos_30_do_imos_tambem_liga(session) -> None:
    cliente = "CLIENTE_COM_UM_NOME_MUITO_COMPRIDO"
    obra = _obra(1, "26.1600_01_01_X", num="1600", cliente=cliente)
    nome_completo = f"1600_01_26_{cliente}"
    assert chave_encomenda(nome_completo[:30]) in chaves_da_obra(obra)
    assert chave_encomenda(nome_completo) in chaves_da_obra(obra)


def test_nome_guardado_pelo_martelo_ao_criar_no_imos_liga(session) -> None:
    obra = _obra(1, "26.1601_01_01_X", num="1601", imos_nome="1601_01_26_NOME_A_MAO")
    assert chave_encomenda("1601_01_26_nome_a_mao") in chaves_da_obra(obra)


# ----- o que se vê na Produção -----


def test_texto_ordenacao_e_dica_das_colunas(monkeypatch) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from app.ui.helpers.colunas_producao import COLUNAS_PRODUCAO
    from app.ui.helpers.modelo_producao import ProducaoTableModel

    QApplication.instance() or QApplication([])
    modelo = ProducaoTableModel()
    obra = _obra(1, "26.1211_01_01_STHINK")
    sem_tempo = _obra(2, "26.1300_01_01_X", num="1300")
    modelo.definir_processos([obra, sem_tempo])
    modelo.definir_tempos(
        {1: TempoObra(desenho=3900, excel=600, por_pessoa={"Pedro": [3300, 600], "Paulo": [600, 0]},
                      partilhado_com=("26.1211_01_02_STHINK",))}
    )
    col = next(i for i, c in enumerate(COLUNAS_PRODUCAO) if c.key == "tempo_desenho")
    col_excel = next(i for i, c in enumerate(COLUNAS_PRODUCAO) if c.key == "tempo_excel")

    assert modelo.index(0, col).data() == "1 h 05 min ⚠"
    assert modelo.index(0, col_excel).data() == "10 min ⚠"
    assert modelo.index(1, col).data() == ""
    assert modelo.index(0, col).data(ProducaoTableModel.ROLE_ORDENACAO) == 3900

    # Uns segundos não aparecem como "0 min" (visto no teste do Paulo).
    modelo.definir_tempos({2: TempoObra(excel=20, por_pessoa={"Admin": [0, 20]})})
    assert modelo.index(1, col_excel).data() == "< 1 min"
    dica = modelo.index(0, col).data(Qt.ItemDataRole.ToolTipRole)
    assert "Pedro: 55 min" in dica and "Paulo: 10 min" in dica
    assert "Partilhado com 26.1211_01_02_STHINK" in dica
    assert "Só visível para administradores" in modelo.headerData(
        col, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole
    )


def test_colunas_de_tempo_sao_so_do_admin() -> None:
    from app.ui.helpers.colunas_producao import COLUNAS_PRODUCAO

    tempo = [c for c in COLUNAS_PRODUCAO if c.key in ("tempo_desenho", "tempo_excel")]
    assert len(tempo) == 2 and all(c.so_admin for c in tempo)
    assert not any(c.so_admin for c in COLUNAS_PRODUCAO if c not in tempo)


def test_quem_nao_e_admin_nem_le_os_tempos_da_base(monkeypatch) -> None:
    from app.core.session import app_session
    from app.ui.pages.producao_page import ProducaoPage

    monkeypatch.setattr(app_session, "current_user", SimpleNamespace(id=5, role="user"))
    pagina = SimpleNamespace(_e_admin=ProducaoPage._e_admin)

    def _nao_devia(*_a, **_k):
        raise AssertionError("não devia abrir a base")

    monkeypatch.setattr("app.ui.pages.producao_page.SessionLocal", _nao_devia)

    assert ProducaoPage._ler_tempos_ativos(pagina, [_obra(1, "x")]) == {}


def test_esconde_as_colunas_e_tira_as_do_menu_a_quem_nao_e_admin() -> None:
    import inspect

    from app.ui.pages.producao_page import ProducaoPage

    aplicar = inspect.getsource(ProducaoPage._aplicar_config_colunas)
    menu = inspect.getsource(ProducaoPage._abrir_menu_colunas)
    assert "coluna.so_admin and not admin" in aplicar
    assert "coluna.so_admin and not admin" in menu


def test_o_contador_arranca_com_a_janela_principal_e_grava_ao_fechar() -> None:
    import inspect

    from app.ui.main_window import MainWindow

    fonte = inspect.getsource(MainWindow)
    assert "TempoProgramasTracker(" in fonte
    fecho = inspect.getsource(MainWindow.closeEvent)
    assert "_tempo_programas_tracker" in fecho
