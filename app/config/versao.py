"""Versão do Martelo — o número, um só, para tudo.

Havia dois: este (que ia no diário de bordo e no "Reportar problema") e o do
`version.py` da raiz (que ia no instalador). Andavam dessincronizados — o
registo dizia `3.2.0` enquanto o instalador ia na `0.9.6-beta` — e isso tirava
o valor ao relatório de problema: pelo número não se sabia que versão a pessoa
tinha à frente.

Agora é um só, e vive aqui, dentro do pacote da aplicação: assim o executável
encontra-o pelo caminho da app, sem depender de um módulo de nome genérico na
raiz. O `version.py` da raiz continua a existir — o empacotamento procura-o lá
desde o início — mas limita-se a reexportar isto.

**Subir aqui a cada entrega para os utilizadores.**
"""

from __future__ import annotations

#: 1.0.0 = a primeira versao oficial, a que vai para os PCs de toda a gente a
#: 31 de agosto de 2026. Ate' aqui o Martelo andou em beta, numa base de dados
#: de testes; a partir daqui e' o programa da casa, com dados a serio.
APP_VERSION = "1.0.5"

#: Vazio quer dizer versao oficial. Enquanto tiver texto ("beta", "rc"), esse
#: texto aparece no numero da versao E o rotulo do ambiente aparece na janela.
APP_STAGE = ""


def version_completa() -> str:
    """Ex.: ``0.9.7-beta`` (ou ``0.9.7`` se ``APP_STAGE`` ficar vazio)."""
    return f"{APP_VERSION}-{APP_STAGE}" if APP_STAGE else APP_VERSION


#: O que o diário de bordo e o "Reportar problema" mostram. Marco histórico:
#: foi na 3.2.0 (numeração antiga) que cada pessoa passou a entrar com a sua
#: conta na base de dados — se alguém reportar "não consigo entrar", é a
#: primeira coisa a confirmar.
VERSAO_APLICACAO = version_completa()
