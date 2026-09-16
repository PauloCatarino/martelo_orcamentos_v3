"""Corretor ortográfico: o do Windows (pt-PT) + o dicionário da casa.

Usa a API de verificação ortográfica que o Windows 8+ traz (a mesma do Edge e
do Outlook), através de ``comtypes`` — que já vai no instalador. Não há
dicionários para descarregar nem para pôr no servidor.

**Nunca bloqueia nada.** Sem Windows em português, sem ``comtypes`` ou sem a
tabela do dicionário, o corretor simplesmente não sublinha: é uma ajuda, não
uma validação.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Iterable, Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain.ortografia import (
    acertar_caixa,
    chave_dicionario,
    deve_verificar,
    formas_a_tentar,
    sem_acentos,
    sigla_curta,
)

logger = logging.getLogger(__name__)

LINGUA = "pt-PT"
MAX_SUGESTOES = 6
#: De quanto em quanto tempo se volta a ler o dicionário da casa, para apanhar
#: as palavras que os colegas acrescentaram entretanto.
RECARREGAR_DICIONARIO_S = 300


class Verificador(Protocol):
    def correta(self, palavra: str) -> bool: ...

    def sugestoes(self, palavra: str) -> list[str]: ...


# ---- Windows ------------------------------------------------------------------
def _criar_verificador_windows(lingua: str = LINGUA) -> Verificador | None:
    """O corretor do Windows, ou ``None`` quando não existe neste PC."""
    try:
        from ctypes import HRESULT, POINTER, c_int, c_ulong, c_wchar_p

        import comtypes
        import comtypes.client
        from comtypes import COMMETHOD, GUID, IUnknown
    except Exception:  # noqa: BLE001 - fora do Windows ou sem comtypes
        return None

    class IEnumString(IUnknown):
        _iid_ = GUID("{00000101-0000-0000-C000-000000000046}")
        _methods_ = [
            COMMETHOD(
                [], HRESULT, "Next",
                (["in"], c_ulong),
                (["out"], POINTER(c_wchar_p)),
                (["out"], POINTER(c_ulong)),
            )
        ]

    class ISpellingError(IUnknown):
        _iid_ = GUID("{B7C82D61-FBE8-4B47-9B27-6C0D2E0DE0A3}")
        _methods_ = [
            COMMETHOD([], HRESULT, "get_StartIndex", (["out"], POINTER(c_ulong))),
        ]

    class IEnumSpellingError(IUnknown):
        _iid_ = GUID("{803E3BD4-2828-4410-8290-418D1D73C762}")
        _methods_ = [
            COMMETHOD(
                [], HRESULT, "Next", (["out"], POINTER(POINTER(ISpellingError)))
            )
        ]

    class ISpellChecker(IUnknown):
        _iid_ = GUID("{B6FD0B71-E2BC-4653-8D05-F197E412770B}")
        _methods_ = [
            COMMETHOD([], HRESULT, "get_LanguageTag", (["out"], POINTER(c_wchar_p))),
            COMMETHOD(
                [], HRESULT, "Check",
                (["in"], c_wchar_p),
                (["out"], POINTER(POINTER(IEnumSpellingError))),
            ),
            COMMETHOD(
                [], HRESULT, "Suggest",
                (["in"], c_wchar_p),
                (["out"], POINTER(POINTER(IEnumString))),
            ),
        ]

    class ISpellCheckerFactory(IUnknown):
        _iid_ = GUID("{8E018A9D-2415-4677-BF08-794EA61F94BB}")
        _methods_ = [
            COMMETHOD(
                [], HRESULT, "get_SupportedLanguages",
                (["out"], POINTER(POINTER(IEnumString))),
            ),
            COMMETHOD(
                [], HRESULT, "IsSupported",
                (["in"], c_wchar_p),
                (["out"], POINTER(c_int)),
            ),
            COMMETHOD(
                [], HRESULT, "CreateSpellChecker",
                (["in"], c_wchar_p),
                (["out"], POINTER(POINTER(ISpellChecker))),
            ),
        ]

    try:
        comtypes.CoInitialize()
    except OSError:
        pass  # a thread já tinha o COM iniciado (o Qt faz isso)

    try:
        fabrica = comtypes.client.CreateObject(
            GUID("{7AB36653-1796-484B-BDFA-E74F1DB7C1DC}"),
            interface=ISpellCheckerFactory,
        )
        if not fabrica.IsSupported(lingua):
            logger.info("Corretor: o Windows não tem a língua %s", lingua)
            return None
        verificador = fabrica.CreateSpellChecker(lingua)
    except Exception:  # noqa: BLE001 - Windows antigo, serviço desligado…
        logger.info("Corretor ortográfico do Windows indisponível", exc_info=True)
        return None

    class _VerificadorWindows:
        def correta(self, palavra: str) -> bool:
            erros = verificador.Check(palavra)
            try:
                return not bool(erros.Next())
            except Exception:  # noqa: BLE001 - S_FALSE: não há erros
                return True

        def sugestoes(self, palavra: str) -> list[str]:
            lista: list[str] = []
            enumeracao = verificador.Suggest(palavra)
            while len(lista) < MAX_SUGESTOES:
                try:
                    texto, lidos = enumeracao.Next(1)
                except Exception:  # noqa: BLE001 - fim da lista
                    break
                if not lidos or not texto:
                    break
                lista.append(texto)
            return lista

    return _VerificadorWindows()


# ---- corretor -----------------------------------------------------------------
class Corretor:
    """Diz se uma palavra está bem escrita, e o que sugerir se não estiver."""

    def __init__(
        self,
        verificador: Verificador | None,
        *,
        carregar_dicionario: Callable[[], Iterable[str]] | None = None,
        gravar_palavra: Callable[[str, object], None] | None = None,
    ) -> None:
        self._verificador = verificador
        self._carregar_dicionario = carregar_dicionario or _ler_dicionario_da_base
        self._gravar_palavra = gravar_palavra or _gravar_palavra_na_base
        self._dicionario: set[str] = set()
        self._lido_em: float | None = None
        self._cache: dict[str, bool] = {}
        self._lock = threading.Lock()

    @property
    def disponivel(self) -> bool:
        return self._verificador is not None

    # -- dicionário da casa --
    def recarregar_dicionario(self, *, forcar: bool = False) -> bool:
        """Ler o dicionário da casa. Devolve True se mudou alguma coisa."""
        agora = time.monotonic()
        if (
            not forcar
            and self._lido_em is not None
            and agora - self._lido_em < RECARREGAR_DICIONARIO_S
        ):
            return False
        self._lido_em = agora
        try:
            palavras = {chave_dicionario(p) for p in self._carregar_dicionario()}
        except Exception:  # noqa: BLE001 - sem base / sem tabela: segue sem ele
            logger.info("Dicionário da casa indisponível", exc_info=True)
            return False
        palavras.discard("")
        if palavras == self._dicionario:
            return False
        self._dicionario = palavras
        return True

    def no_dicionario(self, palavra: str) -> bool:
        return chave_dicionario(palavra) in self._dicionario

    def adicionar(self, palavra: str, user_id: object = None) -> None:
        """Acrescentar ao dicionário da casa (para todos). Levanta se falhar."""
        chave = chave_dicionario(palavra)
        if not chave:
            return
        self._gravar_palavra(chave, user_id)
        self._dicionario.add(chave)

    # -- verificação --
    def correta(self, palavra: str) -> bool:
        if not self.disponivel or not deve_verificar(palavra):
            return True
        if self.no_dicionario(palavra):
            return True
        with self._lock:
            if palavra in self._cache:
                return self._cache[palavra]
            try:
                resultado = any(
                    self._verificador.correta(forma)  # type: ignore[union-attr]
                    for forma in formas_a_tentar(palavra)
                )
                if not resultado and sigla_curta(palavra):
                    resultado = not self._so_falta_acento(palavra)
            except Exception:  # noqa: BLE001 - nunca sublinhar por avaria
                resultado = True
            self._cache[palavra] = resultado
            return resultado

    def _so_falta_acento(self, palavra: str) -> bool:
        """NAO → NÃO sim; MLM, AGL, PUX (siglas) não."""
        alvo = palavra.upper()
        return any(
            sugestao.upper() != alvo and sem_acentos(sugestao).upper() == alvo
            for sugestao in self._verificador.sugestoes(  # type: ignore[union-attr]
                palavra.lower()
            )
        )

    def sugestoes(self, palavra: str) -> list[str]:
        if not self.disponivel:
            return []
        try:
            brutas = self._verificador.sugestoes(  # type: ignore[union-attr]
                formas_a_tentar(palavra)[0]
            )
        except Exception:  # noqa: BLE001
            return []
        finais: list[str] = []
        for sugestao in brutas:
            final = acertar_caixa(sugestao, palavra)
            if final not in finais and final != palavra:
                finais.append(final)
        return finais


# ---- base de dados --------------------------------------------------------------
def _ler_dicionario_da_base() -> list[str]:
    from app.db.session import SessionLocal
    from app.models.dicionario_palavra import DicionarioPalavra

    with SessionLocal() as session:
        return list(session.scalars(select(DicionarioPalavra.palavra)))


def _gravar_palavra_na_base(chave: str, user_id: object) -> None:
    from app.db.session import SessionLocal
    from app.models.dicionario_palavra import DicionarioPalavra

    with SessionLocal() as session:
        existe = session.scalar(
            select(DicionarioPalavra.id).where(DicionarioPalavra.palavra == chave)
        )
        if existe:
            return
        try:
            session.add(
                DicionarioPalavra(
                    palavra=chave[:80],
                    criado_por_id=int(user_id) if user_id else None,
                )
            )
            session.commit()
        except IntegrityError:
            session.rollback()  # um colega acrescentou-a no mesmo instante


# ---- instância única -------------------------------------------------------------
_corretor: Corretor | None = None


def corretor() -> Corretor:
    """O corretor da aplicação (criado à primeira utilização)."""
    global _corretor
    if _corretor is None:
        _corretor = Corretor(_criar_verificador_windows())
    return _corretor


def definir_corretor(novo: Corretor | None) -> None:
    """Trocar o corretor (usado pelos testes)."""
    global _corretor
    _corretor = novo
