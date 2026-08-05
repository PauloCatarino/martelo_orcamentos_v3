"""Ler e gravar as preferências pessoais de cada utilizador.

O irmão do :mod:`app.services.system_setting_service`, para a outra metade das
definições. A regra para saber qual usar é uma pergunta só:

* é do **sistema** — caminhos do servidor, credenciais do PHC/iMos, tarifas?
  Vai para a ``system_settings``, e só um administrador a escreve.
* é do **utilizador** — que validações ver, a ordem de impressão, as colunas e
  as vistas que ele arranjou? Vai para aqui, e ele próprio grava.

Foi a confusão entre as duas que deixou os utilizadores normais sem gravar as
suas escolhas: estavam numa tabela trancada por causa das passwords que ela
guarda (``Error 1142``).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_pref import UserPref

#: Sem sessão iniciada as preferências ficam neste utilizador — o mesmo papel
#: que o sufixo "default" tinha nas chaves antigas.
UTILIZADOR_SEM_SESSAO = 0


class UserPrefService:
    """Preferências de um utilizador, por chave."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def obter_valor(
        self, user_id: object, chave: str, default: str | None = None
    ) -> str | None:
        """Valor guardado por este utilizador, ou ``default`` se não houver."""
        registo = self._registo(user_id, chave)
        if registo is None or registo.valor is None:
            return default
        return registo.valor

    def guardar_valor(self, user_id: object, chave: str, valor: str | None) -> None:
        """Gravar (ou atualizar) uma preferência deste utilizador."""
        normalizada = self._normalizar_chave(chave)
        registo = self._registo(user_id, normalizada)
        if registo is None:
            registo = UserPref(
                user_id=self._normalizar_user_id(user_id),
                chave=normalizada,
                valor=self._normalizar_valor(valor),
            )
            self.session.add(registo)
        else:
            registo.valor = self._normalizar_valor(valor)
        self.session.commit()

    # ---- peças --------------------------------------------------------------
    def _registo(self, user_id: object, chave: str) -> UserPref | None:
        return self.session.execute(
            select(UserPref).where(
                UserPref.user_id == self._normalizar_user_id(user_id),
                UserPref.chave == self._normalizar_chave(chave),
            )
        ).scalar_one_or_none()

    @staticmethod
    def _normalizar_user_id(user_id: object) -> int:
        """Sem utilizador (ou id estranho) → o utilizador sem sessão."""
        try:
            return int(user_id) if user_id else UTILIZADOR_SEM_SESSAO
        except (TypeError, ValueError):
            return UTILIZADOR_SEM_SESSAO

    @staticmethod
    def _normalizar_chave(chave: str) -> str:
        normalizada = (chave or "").strip()
        if not normalizada:
            raise ValueError("chave is required")
        return normalizada

    @staticmethod
    def _normalizar_valor(valor: str | None) -> str | None:
        if valor is None:
            return None
        return str(valor).strip()
