"""Quando é que o Martelo vai espreitar os clientes do PHC (regra pura).

A lista de clientes é feita no PHC e copiada para o Martelo. Enquanto alguém não
se lembrasse de carregar em «Atualizar PHC», um cliente novo simplesmente não
existia cá. Esta regra decide, sem Qt e sem base de dados, se já é hora de ir
ver — para poder ser testada sozinha.
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
