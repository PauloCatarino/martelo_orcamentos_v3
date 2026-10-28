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
    with pytest.raises(r.ErroRegistoHoras, match="As linhas 1 e 2 sobrepõem-se: das 13:00 às 14:00"):
        r.calcular_dia(
            r.DadosDia(tipo=r.TIPO_UTIL, entrada=480, saida=1020, entrada2=780, saida2=840)
        )


# ---- várias entradas e saídas (19-10-2026) ---------------------------------------
def _linhas(tipo: str, *periodos, **kw) -> r.CalculoDia:
    return r.calcular_dia(r.DadosDia(tipo=tipo, periodos=tuple(periodos), **kw))


def test_linhas_fora_de_ordem_sao_postas_pela_ordem_do_dia() -> None:
    calculo = _linhas(r.TIPO_UTIL, (780, 1020), (480, 600), (None, None), almoco=False)
    assert calculo.periodos == ((480, 600), (780, 1020))
    assert (calculo.trabalhado, calculo.saida, calculo.entrada2) == (360, 600, 780)


def test_linhas_que_se_sobrepoem_sao_recusadas() -> None:
    with pytest.raises(r.ErroRegistoHoras, match="das 11:00 às 12:00 estaria contado duas vezes"):
        _linhas(r.TIPO_TELETRABALHO, (480, 720), (660, 1020))


def test_linha_incompleta_diz_qual_e() -> None:
    with pytest.raises(r.ErroRegistoHoras, match="Na linha 2 indique a entrada e a saída"):
        _linhas(r.TIPO_UTIL, (480, 1020), (1200, None))


def test_no_maximo_seis_linhas() -> None:
    sete = [(h * 60, h * 60 + 30) for h in range(8, 15)]
    with pytest.raises(r.ErroRegistoHoras, match="No máximo 6"):
        _linhas(r.TIPO_UTIL, *sete, almoco=False)


def test_so_a_ultima_linha_passa_da_meia_noite() -> None:
    calculo = _linhas(r.TIPO_UTIL, (480, 1020), (1320, 60), almoco=True)
    assert calculo.periodos[-1] == (1320, 1500)
    with pytest.raises(r.ErroRegistoHoras, match="sobrepõem-se"):
        _linhas(r.TIPO_UTIL, (1320, 120), (1380, 1430))  # 22h–2h e 23h–23h50
    with pytest.raises(r.ErroRegistoHoras, match="24 horas"):
        _linhas(r.TIPO_UTIL, (60, 180), (1320, 120))


def test_fim_de_semana_feriado_e_ferias_com_linhas() -> None:
    sabado = _linhas(r.TIPO_FIM_SEMANA, (540, 720), (840, 1020), almoco=False)
    assert (sabado.trabalhado, sabado.normais, sabado.extra) == (360, 0, 360)
    uma_linha = _linhas(r.TIPO_FIM_SEMANA, (540, 1080), almoco=True)
    assert uma_linha.trabalhado == 480  # 9h menos o almoço
    # Linhas vazias = não trabalhou (o feriado e as férias aceitam; o sábado não).
    assert _linhas(r.TIPO_FERIADO, (None, None)).extra == 0
    with pytest.raises(r.ErroRegistoHoras, match="horas trabalhadas"):
        _linhas(r.TIPO_FIM_SEMANA, (None, None))


@pytest.mark.parametrize(
    ("periodos", "intervalo"),
    [
        (((480, 600), (780, 1020)), (600, 780)),  # consulta 10h–13h: já inclui o almoço
        (((480, 750), (810, 1020)), (750, 810)),  # 12h30–13h30
        (((480, 1020), (1200, 1380)), None),  # o caso do Pedro: o intervalo é à noite
        (((480, 680), (700, 1020)), None),  # 11h20–11h40: não é o almoço
        (((480, 1020),), None),
    ],
)
def test_intervalo_que_ja_e_o_almoco(periodos, intervalo) -> None:
    assert r.intervalo_almoco(periodos) == intervalo


# ---- teletrabalho (28-10-2026): o horário está no ponto da empresa ----------------------
def _tele(*periodos, **kw) -> r.CalculoDia:
    return _linhas(r.TIPO_TELETRABALHO, *periodos, **kw)


@pytest.mark.parametrize(
    ("periodos", "extra", "no_ponto", "folha"),
    [
        (((1140, 1260),), 120, 0, "ponto + 2"),  # o exemplo do Paulo: 19h–21h = 2h extra
        (((1020, 1140),), 120, 0, "ponto + 2"),  # só a parte de casa, 17h–19h
        (((480, 1140),), 120, 540, "ponto + 2"),  # o dia todo, 08h–19h: dá o mesmo
        (((480, 1020), (1200, 1380)), 180, 540, "ponto + 3"),  # o caso do Pedro
        (((420, 540), (1080, 1200)), 180, 60, "ponto + 3"),  # 07h–09h e 18h–20h
        (((390, 480), (1320, 90)), 300, 0, "ponto + 5"),  # 06h30–08h e 22h–01h30
        (((480, 1020),), 0, 540, "ponto"),  # só o horário: nada conta
    ],
)
def test_teletrabalho_so_conta_fora_do_horario(periodos, extra, no_ponto, folha) -> None:
    calculo = _tele(*periodos)
    assert (calculo.trabalhado, calculo.normais, calculo.extra) == (extra, 0, extra)
    assert calculo.no_ponto == no_ponto
    assert r.horas_como_na_folha(r.TIPO_TELETRABALHO, 0, calculo.extra, calculo.trabalhado) == folha


def test_teletrabalho_sem_linhas_guarda_o_dia_vazio() -> None:
    calculo = _tele((None, None))
    assert (calculo.extra, calculo.periodos, calculo.saida) == (0, (), None)
    assert r.calcular_dia(r.DadosDia(tipo=r.TIPO_TELETRABALHO)).extra == 0
    with pytest.raises(r.ErroRegistoHoras, match="Indique a hora de saída"):
        _tele((1140, None))


def test_teletrabalho_sem_almoco_com_jantar_e_acerto() -> None:
    # O almoço é dentro do horário (no ponto): mesmo marcado, não tira nada.
    assert _tele((480, 1140), almoco=True).extra == 120
    assert _tele((1140, 1380), jantar=True).extra == 180  # 19h–23h menos o jantar
    assert _tele((1140, 1260), acerto=60).extra == 180
    assert _tele((None, None), acerto=90).extra == 90
    with pytest.raises(r.ErroRegistoHoras, match="excedem as horas feitas fora do horário"):
        _tele((1140, 1170), jantar=True)


def test_teletrabalho_usa_o_horario_da_pessoa() -> None:
    dados = r.DadosDia(tipo=r.TIPO_TELETRABALHO, periodos=((480, 1020),))
    nove_as_seis = r.calcular_dia(dados, horario=(540, 1080))
    assert (nove_as_seis.extra, nove_as_seis.no_ponto) == (60, 480)  # das 8 às 9 é antes


def test_partes_no_horario() -> None:
    periodos = [(420, 540), (720, 780), (1080, 1200)]
    assert r.partes_no_horario(periodos, (480, 1020)) == [(480, 540), (720, 780)]
    assert r.partes_no_horario([(1320, 1530)], (480, 1020)) == []


def test_teletrabalho_na_folha_e_no_resumo() -> None:
    novo = r.LinhaDia(data=date(2026, 10, 27), tipo=r.TIPO_TELETRABALHO, periodos=((1140, 1260),),
                      trabalhado=120, extra=120)
    assert (novo.horas_folha, novo.extra_partes, novo.desconto) == ("ponto + 2", (120,), 0)
    assert novo.observacoes_folha() == "Teletrabalho" and novo.subsidio == 0
    assert not novo.teletrabalho_regra_antiga
    vazio = r.LinhaDia(data=date(2026, 10, 28), tipo=r.TIPO_TELETRABALHO)
    assert (vazio.horas_folha, vazio.horario, vazio.extra_partes) == ("ponto", "", ())
    # Os dias da regra de 19-10 mostram-se como foram gravados.
    antigo = r.LinhaDia(
        data=date(2026, 10, 20), tipo=r.TIPO_TELETRABALHO, periodos=((480, 600), (780, 1020), (1200, 1380)),
        trabalhado=540, normais=360, extra=60, falta=120, observacoes="Consulta",
    )
    assert antigo.teletrabalho_regra_antiga
    assert (antigo.horas_folha, antigo.extra_partes) == ("6 + 3", (180, -120))
    assert antigo.observacoes_folha() == "Teletrabalho – Consulta"
    com_ausencia = r.LinhaDia(data=date(2026, 10, 21), tipo=r.TIPO_TELETRABALHO,
                              normais=480, extra=180, ausencia=120)
    assert com_ausencia.observacoes_folha() == "Teletrabalho – Ausência justificada 2h"
    assert com_ausencia.teletrabalho_regra_antiga

    resumo = r.resumir_mes([
        novo, vazio, r.LinhaDia(data=date(2026, 10, 22), tipo=r.TIPO_UTIL, normais=480, extra=60),
    ])
    assert (resumo.normais, resumo.extra_uteis, resumo.descontos) == (480, 180, 0)
    assert (resumo.dias_uteis, resumo.dias_teletrabalho) == (3, 2)
    assert resumo.linha_teletrabalho() == ("Dias em teletrabalho (horário no ponto da empresa)", "2")
    relatorio = resumo.linhas_relatorio()
    assert relatorio[-1] == resumo.linha_teletrabalho()
    assert relatorio[-2] == resumo.linha_subsidio()
    corpo = r.corpo_email("Paulo Catarino", 2026, 10, resumo)
    assert "• Dias em teletrabalho (horário no ponto da empresa): 2" in corpo
    assert r.ResumoMes().linha_teletrabalho() is None


def test_dados_do_dia_gravado_para_refazer_as_contas() -> None:
    antigo = r.LinhaDia(data=date(2026, 10, 20), tipo=r.TIPO_TELETRABALHO, entrada=480, saida=1260,
                        almoco=True, jantar=True, acerto=30, normais=480, extra=120)
    dados = antigo.dados()
    assert (dados.tipo, dados.periodos, dados.jantar, dados.acerto) == (
        r.TIPO_TELETRABALHO, ((480, 1260),), True, 30,
    )
    assert r.calcular_dia(dados).extra == 240 - 60 + 30


def test_dias_antigos_e_so_o_total() -> None:
    antigo = r.LinhaDia(data=date(2026, 10, 6), tipo=r.TIPO_UTIL, entrada=480, saida=1020,
                        entrada2=1200, saida2=1380)
    assert antigo.lista_periodos == ((480, 1020), (1200, 1380))
    assert antigo.horario == "8h – 17h · 20h – 23h"
    domingo = r.LinhaDia(data=date(2026, 10, 4), tipo=r.TIPO_FIM_SEMANA, horas=180, trabalhado=180,
                         extra=180)
    assert domingo.so_total and domingo.horario == ""
    folga = r.LinhaDia(data=date(2026, 10, 7), tipo=r.TIPO_FOLGA, horas=480, extra=-480)
    assert not folga.so_total and folga.desconto == -480 and folga.extra_partes == (-480,)


def test_tipo_habitual_das_definicoes() -> None:
    assert r.tipo_por_defeito(date(2026, 10, 20), r.TIPO_TELETRABALHO) == r.TIPO_TELETRABALHO
    assert r.tipo_por_defeito(date(2026, 10, 24), r.TIPO_TELETRABALHO) == r.TIPO_FIM_SEMANA
    assert r.tipo_por_defeito(date(2026, 10, 5), r.TIPO_TELETRABALHO) == r.TIPO_FERIADO
    assert r.tipo_por_defeito(date(2026, 10, 20), r.TIPO_FOLGA) == r.TIPO_UTIL
    config = r.ConfigHoras(tipo_habitual=r.TIPO_TELETRABALHO)
    assert r.ConfigHoras.de_json(config.para_json()).tipo_habitual == r.TIPO_TELETRABALHO
    assert r.ConfigHoras.de_json('{"tipo_habitual": "folga"}').tipo_habitual == r.TIPO_UTIL


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


# ---- subsídio de alimentação (regra do Paulo, 10-10-2026) ---------------------------
@pytest.mark.parametrize(
    ("tipo", "trabalhado", "centimos"),
    [
        (r.TIPO_FIM_SEMANA, 4 * 60, 500),  # sábado com 4h: 4 × 1,25 €
        (r.TIPO_FIM_SEMANA, 8 * 60, 1000),  # 8h = o máximo
        (r.TIPO_FIM_SEMANA, 9 * 60, 1000),  # mais de 8h não passa dos 10 €
        (r.TIPO_FIM_SEMANA, 150, 250),  # 2h30: só as horas inteiras contam
        (r.TIPO_FIM_SEMANA, 59, 0),  # menos de uma hora inteira
        (r.TIPO_FERIADO, 3 * 60, 375),  # feriado trabalhado, mesmo a meio da semana
        (r.TIPO_FERIAS, 2 * 60, 250),  # dia de férias trabalhado
        (r.TIPO_FERIADO, 0, 0),  # feriado sem trabalhar
        (r.TIPO_UTIL, 11 * 60, 0),  # dia útil com 3h extra: não conta
        (r.TIPO_TELETRABALHO, 11 * 60, 0),  # teletrabalho é um dia útil: não conta
        (r.TIPO_FOLGA, 0, 0),
    ],
)
def test_subsidio_alimentacao_por_dia(tipo, trabalhado, centimos) -> None:
    assert r.subsidio_alimentacao(tipo, trabalhado) == centimos


def test_subsidio_na_linha_e_no_resumo_do_mes() -> None:
    dias = [
        r.LinhaDia(data=date(2026, 10, 2), tipo=r.TIPO_UTIL, normais=480, extra=180, trabalhado=660),
        r.LinhaDia(data=date(2026, 10, 3), tipo=r.TIPO_FIM_SEMANA, extra=240, trabalhado=240),
        r.LinhaDia(data=date(2026, 10, 4), tipo=r.TIPO_FIM_SEMANA, extra=540, trabalhado=540),
        r.LinhaDia(data=date(2026, 10, 5), tipo=r.TIPO_FERIADO, extra=180, trabalhado=180),
        r.LinhaDia(data=date(2026, 10, 6), tipo=r.TIPO_FERIAS, extra=150, trabalhado=150),
        r.LinhaDia(data=date(2026, 10, 7), tipo=r.TIPO_FOLGA, extra=-480),
    ]
    assert [d.subsidio_folha for d in dias] == ["", "5,00 €", "10,00 €", "3,75 €", "2,50 €", ""]
    resumo = r.resumir_mes(dias)
    assert resumo.subsidio == 500 + 1000 + 375 + 250
    assert resumo.linha_subsidio() == ("Subsídio de alimentação", "21,25 €")
    # As horas continuam a fechar com o total; o subsídio vem à parte, no fim.
    assert resumo.linhas()[-1][0] == "Total de horas extra"
    assert resumo.linhas_relatorio()[-1] == resumo.linha_subsidio()


def test_formatar_euros() -> None:
    assert r.formatar_euros(0) == "0,00 €"
    assert r.formatar_euros(2188) == "21,88 €"
    assert r.formatar_euros(125050) == "1.250,50 €"


def test_email_leva_o_subsidio() -> None:
    resumo = r.ResumoMes(normais=176 * 60, subsidio=1375)
    corpo = r.corpo_email("Paulo Catarino", 2026, 10, resumo)
    assert "• Subsídio de alimentação: 13,75 €" in corpo
