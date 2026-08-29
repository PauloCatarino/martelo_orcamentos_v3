"""Carregar o `dateutil`/`six` ANTES do shiboken, dentro do executável.

Sem isto os gráficos dos Dashboards dos relatórios não abrem no `.exe` — só em
desenvolvimento — e a página limita-se a dizer "Instale matplotlib", que é
mentira: o matplotlib está lá.

O que acontece: o PySide6 instala um gancho (`shibokensupport.feature`) que, a
cada módulo importado, lê o código-fonte desse módulo para ver se usa PySide.
O `dateutil` (que o `matplotlib.dates` importa) passa pelo `six`, e os módulos
do `six` não vêm de um ficheiro. Ler o código-fonte de um módulo desses rebenta
com

    AttributeError: '_SixMetaPathImporter' object has no attribute '_path'

e leva à frente o `matplotlib.figure` inteiro.

O `app/main.py` já tenta evitar isto pré-carregando o matplotlib antes do
PySide6. Em desenvolvimento resulta; **dentro do executável não**, porque o
shiboken já está carregado antes de a primeira linha do programa correr
(verificado: `shiboken carregado? True` logo à entrada). Um runtime hook é o
único sítio que corre mais cedo do que ele.

Importado o `dateutil` aqui, o gancho do shiboken nunca chega a vê-lo, e daí
para a frente está tudo carregado.
"""

import sys


def _pre_carregar() -> None:
    try:
        import six  # noqa: F401
        import dateutil.rrule  # noqa: F401
        import dateutil.tz  # noqa: F401
    except Exception:  # noqa: BLE001
        # Sem gráficos a aplicação funciona na mesma; não vale a pena impedir
        # o arranque por causa disto.
        pass


if getattr(sys, "frozen", False):
    _pre_carregar()
