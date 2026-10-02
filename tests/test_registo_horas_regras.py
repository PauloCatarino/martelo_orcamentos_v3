"""Regras da folha de horas: as mesmas contas da app PHP antiga, e a agenda."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.domain import registo_horas as r


def _util(entrada: str, saida: str, **kw) -> r.CalculoDia:
    dados = r.DadosDia(
        tipo=r.TIPO_UTIL, entrada=r.ler_hora(entrada), saida=r.ler_hora(saida), **kw
    )
    return r.calcular_dia(dados)


# ---- feriados ---------------------------------------------------------------
def test_pascoa_e_feriados_moveis() -> None:
    assert r.domingo_de_pascoa(2025) == date(2025, 4, 20)
    assert r.domingo_de_pascoa(2026) == date(2026, 4, 5)
    assert r.feriado(date(2025, 4, 18)) == "Sexta-feira Santa"
    assert r.feriado(date(2026, 6, 4)) == "Corpo de Deus"
    assert r.feriado(date(2026, 10, 5)) == "Implantação da República"
    assert r.feriado(date(2026, 10, 6)) == ""


def test_tipo_por_defeito() -> None:
    assert r.tipo_por_defeito(date(2026, 10, 2)) == r.TIPO_UTIL  # sexta
    assert r.tipo_por_defeito(date(2026, 10, 3)) == r.TIPO_FIM_SEMANA  # sábado
    assert r.tipo_por_defeito(date(2026, 10, 5)) == r.TIPO_FERIADO


# ---- contas de um dia (iguais às da app antiga) ------------------------------
def test_dia_util_com_extra_8_mais_3() -> None:
    calculo = _util("8:00", "20:00", almoco=True)
    assert (calculo.trabalhado, calculo.normais, calculo.extra) == (660, 480, 180)
    assert r.horas_como_na_folha(r.TIPO_UTIL, 480, 180, 660) == "8 + 3"


def test_dia_util_com_menos_de_8_horas_desconta() -> None:
    calculo = _util("8:00", "13:00", almoco=False)
    assert (calculo.normais, calculo.extra) == (300, -180)
    assert r.horas_como_na_folha(r.TIPO_UTIL, 300, -180, 300) == f"5 {r.MENOS} 3"


def test_saida_a_meia_noite_e_depois_da_meia_noite() -> None:
    meia_noite = _util("8:00", "0:00", almoco=True)
    assert meia_noite.saida == 1440
    assert meia_noite.trabalhado == 900
    noite = _util("22:00", "6:00", almoco=False)
    assert noite.trabalhado == 480 and noite.saida == 30 * 60
    assert r.formatar_hora(noite.saida) == "6h (+1)"


def test_jantar_e_acerto() -> None:
    calculo = _util("8:00", "22:00", almoco=True, jantar=True, acerto=90)
    assert calculo.trabalhado == 14 * 60 - 120 + 90


def test_segundo_periodo_em_casa_a_noite() -> None:
    """O caso do Pedro: empresa das 8h às 17h e mais umas horas em casa."""
    calculo = r.calcular_dia(
        r.DadosDia(
            tipo=r.TIPO_UTIL, entrada=480, saida=1020, entrada2=1200, saida2=1380, almoco=True
        )
    )
    assert (calculo.trabalhado, calculo.normais, calculo.extra) == (660, 480, 180)
    assert (calculo.entrada2, calculo.saida2) == (1200, 1380)


def test_segundo_periodo_que_passa_a_meia_noite() -> None:
    calculo = r.calcular_dia(
        r.DadosDia(tipo=r.TIPO_UTIL, entrada=480, saida=1020, entrada2=1320, saida2=60)
    )
    assert calculo.saida2 == 1500
    assert calculo.extra == 540 + 180 - 60 - 480


def test_segundo_periodo_sobreposto_e_recusado() -> None:
    with pytest.raises(r.ErroRegistoHoras, match="2.º período"):
        r.calcular_dia(
            r.DadosDia(tipo=r.TIPO_UTIL, entrada=480, saida=1020, entrada2=780, saida2=840)
        )


def test_segundo_periodo_incompleto_e_recusado() -> None:
    with pytest.raises(r.ErroRegistoHoras):
        r.calcular_dia(r.DadosDia(tipo=r.TIPO_UTIL, entrada=480, saida=1020, entrada2=1200))


@pytest.mark.parametrize(
    ("dados", "mensagem"),
    [
        (r.DadosDia(tipo=r.TIPO_UTIL, saida=1020), "entrada"),
        (r.DadosDia(tipo=r.TIPO_UTIL, entrada=480), "saída"),
        (r.DadosDia(tipo=r.TIPO_UTIL, entrada=480, saida=510, almoco=True), "descontos"),
        (r.DadosDia(tipo=r.TIPO_UTIL, entrada=480, saida=1020, acerto=13 * 60), "acerto"),
        (r.DadosDia(tipo=r.TIPO_FIM_SEMANA, horas=0), "horas trabalhadas"),
        (r.DadosDia(tipo=r.TIPO_FOLGA, horas=0), "descontar"),
        (r.DadosDia(tipo=r.TIPO_FERIAS, horas=25 * 60), "entre 0 e 24"),
        (r.DadosDia(tipo="outro"), "Tipo"),
    ],
)
def test_dias_invalidos(dados, mensagem) -> None:
    with pytest.raises(r.ErroRegistoHoras, match=mensagem):
        r.calcular_dia(dados)


def test_fim_de_semana_feriado_ferias_e_folga() -> None:
    assert r.calcular_dia(r.DadosDia(tipo=r.TIPO_FIM_SEMANA, horas=180)).extra == 180
    assert r.calcular_dia(r.DadosDia(tipo=r.TIPO_FERIADO, horas=0)).extra == 0
    ferias = r.calcular_dia(r.DadosDia(tipo=r.TIPO_FERIAS, horas=120))
    assert (ferias.normais, ferias.extra) == (0, 120)
    folga = r.calcular_dia(r.DadosDia(tipo=r.TIPO_FOLGA, horas=480))
    assert (folga.trabalhado, folga.extra) == (0, -480)
    assert r.horas_como_na_folha(r.TIPO_FOLGA, 0, -480, 0) == f"{r.MENOS}8"


def test_horas_normais_por_pessoa() -> None:
    calculo = r.calcular_dia(
        r.DadosDia(tipo=r.TIPO_UTIL, entrada=480, saida=1020, almoco=True), horas_normais=420
    )
    assert (calculo.normais, calculo.extra) == (420, 60)


# ---- escrita -----------------------------------------------------------------
def test_formatos() -> None:
    assert r.formatar_horas(150) == "2h30"
    assert r.formatar_horas(-180) == "3"
    assert r.formatar_total(61 * 60) == "61h"
    assert r.formatar_total(-180) == f"{r.MENOS}3h"
    assert r.formatar_total(120, com_mais=True) == "+2h"
    assert r.formatar_hora(1050) == "17h30"
    assert r.formatar_hora(1440) == "24h"
    assert r.formatar_hora(1530) == "1h30 (+1)"
    assert r.hora_texto(1530) == "01:30"


@pytest.mark.parametrize(
    ("texto", "minutos"),
    [("8", 480), ("8:30", 510), ("08h30", 510), ("17h", 1020), ("24:00", 1440), ("", None), ("25:00", None), ("abc", None)],
)
def test_ler_hora(texto, minutos) -> None:
    assert r.ler_hora(texto) == minutos


def test_nome_do_ficheiro_como_as_folhas_digitalizadas() -> None:
    assert r.nome_ficheiro_folha("Paulo Catarino", 2026, 3) == "HORAS_PAULO_CATARINO_MARCO_2026.pdf"


def test_observacoes_da_folha() -> None:
    sabado = r.LinhaDia(data=date(2026, 9, 26), tipo=r.TIPO_FIM_SEMANA, trabalhado=180, extra=180)
    assert sabado.observacoes_folha() == "Sábado"
    util = r.LinhaDia(
        data=date(2026, 9, 29), tipo=r.TIPO_UTIL, entrada=480, saida=1080, acerto=120,
        jantar=True, observacoes="Feira",
    )
    assert util.observacoes_folha() == "Acerto +2h – Desc. jantar – Feira"
    assert util.horario == "8h – 18h"


# ---- o mês -------------------------------------------------------------------
def test_resumo_separa_extra_por_tipo_de_dia() -> None:
    dias = [
        r.LinhaDia(data=date(2026, 9, 1), tipo=r.TIPO_UTIL, normais=480, extra=120, trabalhado=600),
        r.LinhaDia(data=date(2026, 9, 2), tipo=r.TIPO_UTIL, normais=300, extra=-180, trabalhado=300),
        r.LinhaDia(data=date(2026, 9, 5), tipo=r.TIPO_FIM_SEMANA, extra=180, trabalhado=180),
        r.LinhaDia(data=date(2026, 9, 6), tipo=r.TIPO_FIM_SEMANA, extra=60, trabalhado=60),
        r.LinhaDia(data=date(2026, 9, 8), tipo=r.TIPO_FERIADO, extra=240, trabalhado=240),
        r.LinhaDia(data=date(2026, 9, 9), tipo=r.TIPO_FERIAS),
        r.LinhaDia(data=date(2026, 9, 10), tipo=r.TIPO_FOLGA, extra=-480),
    ]
    resumo = r.resumir_mes(dias)
    assert resumo.normais == 780
    assert (resumo.extra_uteis, resumo.extra_sabados, resumo.extra_domingos) == (120, 180, 60)
    assert resumo.extra_feriados == 240
    assert resumo.descontos == -660
    assert resumo.total_extra == 120 + 180 + 60 + 240 - 660
    assert (resumo.dias_registados, resumo.dias_uteis, resumo.dias_ferias) == (7, 2, 1)
    assert (resumo.dias_feriado, resumo.dias_folga) == (1, 1)
    assert resumo.linhas()[-1] == ("Total de horas extra", r.formatar_total(resumo.total_extra))


def test_dias_em_falta_salta_fins_de_semana_e_feriados() -> None:
    falta = r.dias_em_falta(
        {date(2026, 10, 1)}, desde=date(2026, 10, 1), ate=date(2026, 10, 8)
    )
    # 2 (sex), 6 e 7; 3-4 fim de semana; 5 é feriado.
    assert falta == [date(2026, 10, 2), date(2026, 10, 6), date(2026, 10, 7)]
    assert r.lista_de_dias(falta) == "sexta 02/10, terça 06/10 e quarta 07/10"


# ---- agenda --------------------------------------------------------------------
def test_momento_do_envio_e_dia_2_as_9h20() -> None:
    assert r.momento_envio(2026, 10) == datetime(2026, 11, 2, 9, 20)
    assert r.momento_envio(2026, 12) == datetime(2027, 1, 2, 9, 20)


def test_meses_por_enviar() -> None:
    inicio = date(2026, 10, 1)
    com = [(2026, 9), (2026, 10), (2026, 11)]
    antes = r.meses_por_enviar(
        datetime(2026, 11, 2, 9, 19), inicio_registo=inicio, enviados=[], com_registos=com
    )
    assert antes == []
    na_hora = r.meses_por_enviar(
        datetime(2026, 11, 2, 9, 20), inicio_registo=inicio, enviados=[], com_registos=com
    )
    assert na_hora == [(2026, 10)]  # setembro é histórico: nunca segue
    enviado = r.meses_por_enviar(
        datetime(2026, 11, 20), inicio_registo=inicio, enviados=[(2026, 10)], com_registos=com
    )
    assert enviado == []
    atrasado = r.meses_por_enviar(
        datetime(2026, 12, 5), inicio_registo=inicio, enviados=[], com_registos=com
    )
    assert atrasado == [(2026, 10), (2026, 11)]
    sem_dias = r.meses_por_enviar(
        datetime(2026, 12, 5), inicio_registo=inicio, enviados=[], com_registos=[(2026, 11)]
    )
    assert sem_dias == [(2026, 11)]


def test_lembrete_uma_vez_por_dia() -> None:
    assert r.deve_lembrar_hoje(date(2026, 10, 2), None)
    assert not r.deve_lembrar_hoje(date(2026, 10, 2), date(2026, 10, 2))
    assert r.deve_lembrar_hoje(date(2026, 10, 3), date(2026, 10, 2))


def test_email_leva_o_resumo() -> None:
    resumo = r.ResumoMes(normais=176 * 60, extra_uteis=37 * 60)
    corpo = r.corpo_email("Paulo Catarino", 2026, 9, resumo)
    assert "setembro de 2026" in corpo
    assert "• Horas normais: 176h" in corpo
    assert r.assunto_email("Paulo Catarino", 2026, 9) == (
        "Registo de horas — Paulo Catarino — setembro de 2026"
    )


# ---- definições --------------------------------------------------------------
def test_config_ida_e_volta_e_valores_estragados() -> None:
    config = r.ConfigHoras(nome_folha="Pedro Silva", saida_habitual=19 * 60, lembrete_diario=False,
                           inicio_registo=date(2026, 11, 1))
    assert r.ConfigHoras.de_json(config.para_json()) == config
    estragada = r.ConfigHoras.de_json('{"saida_habitual": "x", "envio_mensal": 0, "outra": 1}')
    assert estragada.saida_habitual == 17 * 60
    assert estragada.envio_mensal is False
    assert r.ConfigHoras.de_json("não é json") == r.ConfigHoras()
    assert r.ConfigHoras.de_json(None).inicio_registo == r.INICIO_REGISTO_PADRAO
