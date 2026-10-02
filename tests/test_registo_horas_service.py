"""Registo de horas na base de dados: dias, envios, definições e importação."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.domain import registo_horas as r
from app.models import SystemSetting, User, UserPermission
from app.models.registo_horas import RegistoHorasDia
from app.services import registo_horas_importacao as imp
from app.services.registo_horas_pdf import gerar_folha_pdf
from app.services.registo_horas_service import RegistoHorasService


def _user(session, user_id: int, nome: str, role: str = "user") -> User:
    user = User(
        id=user_id, username=nome.split()[0].lower(), nome=nome,
        email=f"{user_id}@x.pt", password_hash="x", role=role,
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture()
def servico(session) -> RegistoHorasService:
    _user(session, 1, "Administrador Martelo", "admin")
    _user(session, 2, "Paulo Catarino")
    _user(session, 11, "Pedro")
    _user(session, 4, "Andreia")
    return RegistoHorasService(session)


UTIL = r.DadosDia(tipo=r.TIPO_UTIL, entrada=480, saida=1140, almoco=True)


def test_guardar_ler_e_substituir_um_dia(servico) -> None:
    linha = servico.guardar_dia(2, date(2026, 10, 1), UTIL, observacoes="  Feira  ")
    assert (linha.trabalhado, linha.normais, linha.extra) == (600, 480, 120)
    assert linha.observacoes == "Feira"

    servico.guardar_dia(2, date(2026, 10, 1), r.DadosDia(tipo=r.TIPO_FERIAS))
    dias = servico.listar_mes(2, 2026, 10)
    assert len(dias) == 1
    assert dias[0].tipo == r.TIPO_FERIAS and dias[0].entrada is None and dias[0].extra == 0


def test_cada_pessoa_tem_a_sua_folha(servico) -> None:
    servico.guardar_dia(2, date(2026, 10, 1), UTIL)
    servico.guardar_dia(11, date(2026, 10, 1), r.DadosDia(tipo=r.TIPO_UTIL, entrada=480, saida=1020,
                                                          entrada2=1200, saida2=1380, almoco=True))
    assert servico.listar_mes(2, 2026, 10)[0].extra == 120
    pedro = servico.listar_mes(11, 2026, 10)[0]
    assert (pedro.entrada2, pedro.saida2, pedro.extra) == (1200, 1380, 180)


def test_as_contas_ficam_com_as_horas_normais_de_quando_se_gravou(servico, session) -> None:
    config = r.ConfigHoras(horas_normais_dia=420)
    servico.guardar_config(2, config)
    servico.guardar_dia(2, date(2026, 10, 1), UTIL)
    registo = session.query(RegistoHorasDia).one()
    assert (registo.normais_min, registo.extra_min, registo.horas_normais_dia_min) == (420, 180, 420)


def test_dia_invalido_nao_grava(servico, session) -> None:
    with pytest.raises(r.ErroRegistoHoras):
        servico.guardar_dia(2, date(2026, 10, 1), r.DadosDia(tipo=r.TIPO_FIM_SEMANA))
    with pytest.raises(r.ErroRegistoHoras, match="255"):
        servico.guardar_dia(2, date(2026, 10, 1), UTIL, observacoes="x" * 256)
    assert session.query(RegistoHorasDia).count() == 0


def test_apagar_um_dia(servico) -> None:
    servico.guardar_dia(2, date(2026, 10, 1), UTIL)
    assert servico.apagar_dia(11, date(2026, 10, 1)) is False  # não é dele
    assert servico.apagar_dia(2, date(2026, 10, 1)) is True
    assert servico.listar_mes(2, 2026, 10) == []


def test_dias_em_falta_desde_o_inicio_do_registo(servico) -> None:
    config = r.ConfigHoras(inicio_registo=date(2026, 10, 1))
    servico.guardar_dia(2, date(2026, 10, 1), UTIL)
    falta = servico.dias_em_falta(2, date(2026, 10, 8), config)
    assert falta == [date(2026, 10, 2), date(2026, 10, 6), date(2026, 10, 7)]
    # Antes do início é histórico: nunca falta nada.
    assert servico.dias_em_falta(2, date(2026, 9, 30), config) == []


def test_totais_por_mes(servico) -> None:
    servico.guardar_dia(2, date(2026, 9, 30), UTIL)
    servico.guardar_dia(2, date(2026, 10, 1), UTIL)
    servico.guardar_dia(2, date(2026, 10, 3), r.DadosDia(tipo=r.TIPO_FIM_SEMANA, horas=180))
    totais = servico.totais_por_mes(2)
    assert [(a, m, res.total_extra) for a, m, res in totais] == [(2026, 9, 120), (2026, 10, 300)]
    assert servico.meses_com_registos(2) == [(2026, 9), (2026, 10)]


def test_envios_e_meses_por_enviar(servico) -> None:
    config = r.ConfigHoras(inicio_registo=date(2026, 10, 1))
    servico.guardar_dia(2, date(2026, 10, 1), UTIL)
    agora = datetime(2026, 11, 2, 9, 30)
    assert servico.meses_por_enviar(2, agora, config) == [(2026, 10)]

    resumo = r.resumir_mes(servico.listar_mes(2, 2026, 10))
    servico.registar_envio(2, 2026, 10, destinatario="financeiro@lancaencanto.pt", resumo=resumo,
                           quando=datetime(2026, 11, 2, 9, 31))
    servico.registar_envio(2, 2026, 10, destinatario="outro@x.pt", resumo=resumo,
                           quando=datetime(2026, 11, 3, 10, 0))
    assert servico.meses_por_enviar(2, agora, config) == []
    envio = servico.ultimo_envio(2, 2026, 10)
    assert envio.destinatario == "outro@x.pt" and envio.extra == 120
    assert servico.ultimo_envio(11, 2026, 10) is None


def test_definicoes_e_lembretes_ficam_nas_preferencias_de_cada_um(servico) -> None:
    servico.guardar_config(11, r.ConfigHoras(nome_folha="Pedro Silva", lembrete_diario=False))
    assert servico.config(11).nome_folha == "Pedro Silva"
    assert servico.config(2) == r.ConfigHoras()
    servico.marcar_lembrete(2, date(2026, 10, 2))
    servico.adiar_envio(2, date(2026, 11, 2))
    assert servico.ultimo_lembrete(2) == date(2026, 10, 2)
    assert servico.envio_adiado(2) == date(2026, 11, 2)
    assert servico.ultimo_lembrete(11) is None


def test_email_da_contabilidade(servico, session) -> None:
    assert servico.email_contabilidade() == "financeiro@lancaencanto.pt"
    servico.guardar_email_contabilidade("contas@lancaencanto.pt")
    assert servico.email_contabilidade() == "contas@lancaencanto.pt"
    assert session.query(SystemSetting).filter_by(chave="registo_horas_email_contabilidade").one()


def test_colaboradores_para_o_admin(servico, session) -> None:
    session.add(UserPermission(user_id=11, permission_key="menu.registo_horas", enabled=True))
    session.add(UserPermission(user_id=4, permission_key="menu.registo_horas", enabled=False))
    session.commit()
    servico.guardar_dia(2, date(2026, 10, 1), UTIL)
    nomes = [c.nome for c in servico.colaboradores()]
    assert nomes == ["Paulo Catarino", "Pedro"]


def test_importar_nao_substitui_o_que_ja_existe(servico) -> None:
    servico.guardar_dia(2, date(2026, 10, 1), UTIL)
    antigos = [
        r.LinhaDia(data=date(2026, 9, 30), tipo=r.TIPO_UTIL, entrada=600, saida=1140, almoco=True,
                   trabalhado=480, normais=480),
        r.LinhaDia(data=date(2026, 10, 1), tipo=r.TIPO_UTIL, entrada=480, saida=1080, trabalhado=540,
                   normais=480, extra=60),
    ]
    entraram, ja = servico.importar_dias(2, antigos)
    assert (entraram, ja) == (1, [date(2026, 10, 1)])
    dias = {d.data: d for d in servico.listar_periodo(2, date(2026, 9, 1), date(2026, 10, 31))}
    assert dias[date(2026, 9, 30)].origem == "app_antiga"
    assert dias[date(2026, 10, 1)].extra == 120  # o do Martelo ficou


# ---- app antiga ------------------------------------------------------------------
def test_ler_instalacao_da_app_antiga(tmp_path: Path) -> None:
    (tmp_path / "includes").mkdir()
    (tmp_path / "includes" / "instalacao.php").write_text(
        "<?php\nconst NOME_COLABORADOR = 'Pedro Silva';\nconst INICIO_REGISTO = '2026-10';\n"
        "const BD_PORTA = 3308;\nconst BD_NOME = 'horas_pedro';\n",
        encoding="utf-8",
    )
    instalacao = imp.ler_instalacao(tmp_path)
    assert (instalacao.nome, instalacao.porta, instalacao.base) == ("Pedro Silva", 3308, "horas_pedro")
    assert imp.ler_instalacao(tmp_path / "nada") is None


def test_linhas_da_app_antiga() -> None:
    linhas = [
        {"data": date(2025, 4, 28), "tipo": "util", "hora_entrada": timedelta(hours=8),
         "hora_saida": timedelta(hours=25, minutes=30), "desconto_almoco": 1, "desconto_jantar": 0,
         "acerto_min": 120, "trabalhado_min": 990, "normais_min": 480, "extra_min": 510,
         "observacoes": "Apagão geral"},
        {"data": date(2025, 4, 26), "tipo": "fim_semana", "hora_entrada": None, "hora_saida": None,
         "desconto_almoco": 0, "desconto_jantar": 0, "acerto_min": 0, "trabalhado_min": 420,
         "normais_min": 0, "extra_min": 420, "observacoes": ""},
        {"data": date(2025, 4, 27), "tipo": "folga", "trabalhado_min": 0, "normais_min": 0,
         "extra_min": -480},
        {"data": "estragado", "tipo": "util"},
        {"data": date(2025, 4, 29), "tipo": "desconhecido"},
    ]
    dias = imp.converter(linhas)
    assert [d.data.day for d in dias] == [26, 27, 28]
    util = dias[2]
    assert (util.entrada, util.saida, util.acerto, util.extra) == (480, 1530, 120, 510)
    assert util.almoco is True and util.origem == "app_antiga"
    assert dias[0].horas == 420
    assert dias[1].horas == 480 and dias[1].extra == -480


class _Cursor:
    def __init__(self, linhas):
        self.linhas = linhas
        self.sql = []

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def execute(self, sql):
        self.sql.append(sql)

    def fetchall(self):
        return self.linhas


class _Ligacao:
    def __init__(self, linhas):
        self.cursor_ = _Cursor(linhas)
        self.fechada = False

    def cursor(self):
        return self.cursor_

    def close(self):
        self.fechada = True


def test_ler_dias_so_faz_select() -> None:
    ligacao = _Ligacao([{"data": date(2026, 10, 1), "tipo": "util", "hora_entrada": "08:00:00",
                         "hora_saida": "19:00:00", "desconto_almoco": 1, "trabalhado_min": 600,
                         "normais_min": 480, "extra_min": 120}])
    dias = imp.ler_dias(imp.InstalacaoAntiga(pasta=Path(".")), ligar=lambda _i: ligacao)
    assert dias[0].saida == 1140
    assert ligacao.fechada
    assert all(sql.lstrip().upper().startswith("SELECT") for sql in ligacao.cursor_.sql)


def test_mysql_do_xampp_desligado_explica_o_que_fazer() -> None:
    def _falha(_i):
        raise ConnectionRefusedError("recusada")

    with pytest.raises(imp.ErroImportacao, match="XAMPP Control Panel"):
        imp.ler_dias(imp.InstalacaoAntiga(pasta=Path(".")), ligar=_falha)


def test_importacao_nunca_escreve_na_app_antiga() -> None:
    import re

    fonte = Path(imp.__file__).read_text(encoding="utf-8")
    escrita = re.compile(
        r"\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+(TABLE|DATABASE)"
        r"|TRUNCATE\s|ALTER\s+TABLE|REPLACE\s+INTO)\b",
        re.IGNORECASE,
    )
    assert escrita.search(fonte) is None
    assert imp._SELECT.startswith("SELECT ")


# ---- PDF ---------------------------------------------------------------------------
def test_folha_em_pdf(tmp_path: Path) -> None:
    dias = [
        r.LinhaDia(data=date(2026, 9, 1), tipo=r.TIPO_UTIL, entrada=480, saida=1140, almoco=True,
                   trabalhado=600, normais=480, extra=120),
        r.LinhaDia(data=date(2026, 9, 3), tipo=r.TIPO_UTIL, entrada=480, saida=1020, entrada2=1200,
                   saida2=1380, almoco=True, trabalhado=660, normais=480, extra=180,
                   observacoes="Em casa"),
        r.LinhaDia(data=date(2026, 9, 4), tipo=r.TIPO_FOLGA, horas=480, extra=-480),
        r.LinhaDia(data=date(2026, 9, 5), tipo=r.TIPO_FIM_SEMANA, horas=180, trabalhado=180, extra=180),
    ]
    caminho = gerar_folha_pdf(
        tmp_path / "sub" / "folha.pdf", nome="Paulo Catarino", ano=2026, mes=9, dias=dias,
        em_falta=[date(2026, 9, 2)], logo=tmp_path / "nao_existe.png",
    )
    texto = "".join(p.extract_text() for p in PdfReader(str(caminho)).pages)
    assert "Paulo Catarino" in texto and "Setembro" in texto
    assert "20H" in texto and "23H" in texto
    assert "Total de horas extra" in texto
    assert "Por registar" in texto and "Dias úteis sem registo: 2" in texto
    assert "-8" in texto  # o «−» tipográfico não existe no Helvetica
