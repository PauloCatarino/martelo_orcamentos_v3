"""Versão do Martelo, para o diário de bordo e o relatório de problema.

Serve para saber, quando alguém reporta um erro, se estava a correr a versão
que já tem a correção. Subir aqui a cada entrega para os utilizadores.
"""

from __future__ import annotations

#: 3.2.0 -- cada pessoa passa a entrar com a sua conta na base de dados. E' a
#: versao a partir da qual o .env deixa de levar credenciais; se alguem
#: reportar "nao consigo entrar", e' a primeira coisa a confirmar.
VERSAO_APLICACAO = "3.2.0"
