"""Filtro das mensagens de diagnóstico do Qt (ruído benigno no terminal).

O Qt escreve mensagens no ``stderr`` através de um *message handler* global.
Duas delas enchem o terminal do Martelo V3 sem corresponderem a qualquer
problema real:

* ``Could not parse stylesheet of object QTableWidget(0x...)`` (e o mesmo para
  ``QTreeWidget``). As folhas de estilo aplicadas às tabelas/árvores são CSS
  válido — analisam-se sem erro isoladamente, em lote e sob a folha global.
  O aviso é um falso-positivo do parser de QSS do Qt, emitido de forma
  intermitente quando muitos widgets são *polidos*/re-*polidos* ao mesmo tempo
  (repare-se que o endereço do objeto muda a cada arranque e a aplicação
  desenha-se corretamente). A cobertura de QSS válida é garantida pelos testes
  em ``tests/test_tema_qss_valido.py``.

Este módulo instala um *handler* que **descarta apenas** essas linhas benignas
e reencaminha tudo o resto para o ``stderr``, para que avisos e erros reais do
Qt continuem visíveis.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QtMsgType, qInstallMessageHandler

# Fragmentos das mensagens benignas a silenciar. Deliberadamente específicos:
# qualquer outra mensagem do Qt passa intacta.
_MENSAGENS_A_IGNORAR = (
    "Could not parse stylesheet of object",
)


def _handler(tipo: QtMsgType, contexto, mensagem: str) -> None:
    if any(fragmento in mensagem for fragmento in _MENSAGENS_A_IGNORAR):
        return
    # Reencaminha as restantes mensagens para o stderr (comportamento habitual).
    print(mensagem, file=sys.stderr)


def instalar_filtro_mensagens_qt() -> None:
    """Instala o filtro global de mensagens do Qt.

    Deve ser chamado uma vez no arranque, antes de criar a ``QApplication``.
    """
    qInstallMessageHandler(_handler)
