"""Quando é que o Martelo vai espreitar o PHC (regra pura, sem Qt nem base).

Há coisas que se decidem no PHC e o Martelo só copia: a lista de clientes, e o
estado das obras que já foram finalizadas ou arquivadas. Enquanto ninguém se
lembrasse de carregar num botão, essas mudanças simplesmente não chegavam cá.

Esta regra — dias úteis, a partir das 09h00, uma vez por dia — é partilhada
pelos analisadores diários que existem: o dos clientes
(``app/ui/helpers/verificacao_clientes_phc.py``) e o dos estados das obras
(``app/ui/helpers/verificacao_estados_phc.py``). Vive sozinha para poder ser
testada sozinha.
"""

from __future__ import annotations

from datetime import date, datetime, time

#: Hora a partir da qual a verificação do dia pode correr.
HORA_VERIFICACAO = time(9, 0)

#: Formato em que a data da última verificação fica guardada nas preferências.
FORMATO_DATA = "%Y-%m-%d"


def deve_verificar(
    agora: datetime,
    ultima_verificacao: date | None,
    *,
    hora: time = HORA_VERIFICACAO,
) -> bool:
    """Diz se falta fazer a verificação de hoje.

    Três condições, todas obrigatórias: é dia de semana (segunda a sexta), já
    passou da ``hora``, e ainda não se verificou hoje.

    Quem abrir o Martelo às 14h de uma terça em que ninguém o abriu de manhã é
    avisado nessa altura: a verificação do dia não se perde só porque a app
    estava fechada às 9h.
    """
    if agora.weekday() > 4:  # 5 = sábado, 6 = domingo
        return False
    if agora.time() < hora:
        return False
    return ultima_verificacao != agora.date()


def ler_data(valor: str | None) -> date | None:
    """Data guardada nas preferências; None quando falta ou está estragada."""
    if not valor:
        return None
    try:
        return datetime.strptime(valor.strip(), FORMATO_DATA).date()
    except ValueError:
        return None


def escrever_data(dia: date) -> str:
    """Texto a guardar nas preferências para ``dia``."""
    return dia.strftime(FORMATO_DATA)
