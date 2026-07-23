"""IA Martelo na Produção (Fase 1): pergunta em linguagem natural -> obras.

Liga o cérebro determinístico (:mod:`app.domain.assistente_intencao`) aos dados
reais: carrega o vocabulário do «Assistente — o meu perfil», os clientes e
responsáveis existentes na lista, corre o filtro da Produção que já existe
(`filtrar_processos`) e devolve as obras — nunca escreve nada.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from sqlalchemy.orm import Session

from app.domain.assistente_intencao import (
    Intencao,
    PerfilVocabulario,
    frase_resposta,
    interpretar,
    sugestao_recrutamento,
)
from app.domain.pesquisa_texto import normalizar
from app.domain.producao_estados import ESTADOS_PRODUCAO
from app.models.user import User
from app.services.ia_perfil_service import listar_entradas
from app.services.producao_service import (
    filtrar_processos,
    vocabulario_pesquisa,
)
from app.services.sinonimos_service import carregar_sinonimos

#: Separadores usados quando se escrevem várias formas na mesma célula.
_SEPARADORES = re.compile(r"[;,/|]")

#: Estados canónicos por forma normalizada, para ler o quadro «estado».
_ESTADO_POR_NORMA = {normalizar(estado): estado for estado in ESTADOS_PRODUCAO}


@dataclass(frozen=True)
class RespostaAssistente:
    """Resultado de uma pergunta ao martelo (Fase 1)."""

    frase: str
    obras: list = field(default_factory=list)
    intencao: Intencao = field(default_factory=Intencao)
    #: «Não conheço «X» — quer ensiná-la?» (recrutamento por falha); "" se não.
    sugestao_perfil: str = ""

    @property
    def precisa_perguntar(self) -> bool:
        return self.intencao.precisa_perguntar


def _formas(valor: str | None) -> list[str]:
    """Separa uma célula em formas equivalentes («a Viva; a JF»)."""
    if not valor:
        return []
    return [parte.strip() for parte in _SEPARADORES.split(valor) if parte.strip()]


def _estado_canonico(significado: str | None) -> str | None:
    """Primeiro estado canónico mencionado no texto do quadro «estado»."""
    texto = normalizar(significado)
    if not texto:
        return None
    for norma, estado in _ESTADO_POR_NORMA.items():
        if f" {norma} " in f" {texto} ":
            return estado
    return None


def perfil_de_entradas(entradas) -> PerfilVocabulario:
    """Constrói o vocabulário a partir das linhas de «o meu perfil».

    Aceita objetos com ``tipo``/``expressao``/``significado`` (testável sem BD).
    """
    estados: dict[str, str] = {}
    clientes: dict[str, str] = {}
    pessoas: dict[str, str] = {}
    ambiguas: dict[str, str] = {}

    for entrada in entradas:
        tipo = (getattr(entrada, "tipo", "") or "").strip()
        expressao = getattr(entrada, "expressao", "") or ""
        significado = getattr(entrada, "significado", "") or ""

        if tipo == "estado":
            estado = _estado_canonico(significado)
            if estado:
                for forma in _formas(expressao) or [expressao]:
                    estados[forma] = estado
        elif tipo == "cliente":
            nome = significado.strip()
            if nome:
                for forma in _formas(expressao) or [expressao]:
                    clientes[forma] = nome
        elif tipo == "pessoa":
            nome = significado.strip()
            if nome:
                for forma in _formas(expressao) or [expressao]:
                    pessoas[forma] = nome
        elif tipo == "ambigua":
            questao = significado.strip() or f"«{expressao.strip()}» — a que se refere?"
            for forma in _formas(expressao) or [expressao]:
                ambiguas[forma] = questao

    return PerfilVocabulario(
        estados=estados,
        clientes=clientes,
        pessoas=pessoas,
        ambiguas=ambiguas,
    )


class AssistenteProducaoService:
    """Responde a perguntas de pesquisa no menu Produção (só leitura)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def interpretar_pergunta(
        self,
        pergunta: str,
        *,
        user_id: int | None,
        processos,
    ) -> Intencao:
        """Só a tradução pergunta -> filtros (usada pela UI para conduzir a lista).

        O nome do responsável é canonizado para o valor tal como aparece na
        lista, para os filtros/combos casarem exatamente.
        """
        perfil = self._perfil(user_id)
        clientes = self._distintos(processos, "nome_cliente")
        responsaveis = self._distintos(processos, "responsavel")
        intencao = interpretar(
            pergunta,
            clientes=clientes,
            responsaveis=responsaveis,
            perfil=perfil,
            utilizador_sessao=self._nome_sessao(user_id),
        )
        canonico = self._canonizar(intencao.responsavel, responsaveis)
        if canonico != intencao.responsavel:
            intencao = replace(intencao, responsavel=canonico)
        return intencao

    def responder(
        self,
        pergunta: str,
        *,
        user_id: int | None,
        processos=None,
    ) -> RespostaAssistente:
        """Traduz a pergunta em filtros e devolve as obras correspondentes."""
        if processos is None:
            from app.services.producao_service import ProducaoService

            processos = ProducaoService(self.session).listar_processos()

        sinonimos = carregar_sinonimos(self.session, user_id)
        intencao = self.interpretar_pergunta(
            pergunta, user_id=user_id, processos=processos
        )

        if intencao.precisa_perguntar:
            return RespostaAssistente(
                frase=" ".join(intencao.perguntas),
                obras=[],
                intencao=intencao,
            )

        obras = filtrar_processos(
            processos,
            texto=intencao.termos,
            estado=intencao.estado,
            cliente=intencao.cliente,
            responsavel=intencao.responsavel,
            so_atrasadas=intencao.so_atrasadas,
            sinonimos=sinonimos,
        )
        sugestao = sugestao_recrutamento(
            intencao, len(obras), vocabulario_pesquisa(processos)
        )
        return RespostaAssistente(
            frase=frase_resposta(intencao, len(obras)),
            obras=obras,
            intencao=intencao,
            sugestao_perfil=sugestao,
        )

    def _perfil(self, user_id: int | None) -> PerfilVocabulario:
        if not user_id:
            return PerfilVocabulario()
        return perfil_de_entradas(listar_entradas(self.session, user_id))

    def _nome_sessao(self, user_id: int | None) -> str | None:
        if not user_id:
            return None
        user = self.session.get(User, user_id)
        return getattr(user, "username", None) if user else None

    @staticmethod
    def _distintos(processos, atributo: str) -> list[str]:
        vistos: dict[str, str] = {}
        for processo in processos or []:
            valor = getattr(processo, atributo, None)
            texto = str(valor).strip() if valor is not None else ""
            if texto:
                vistos.setdefault(texto.lower(), texto)
        return list(vistos.values())

    @staticmethod
    def _canonizar(valor: str | None, valores: list[str]) -> str | None:
        """Devolve o valor tal como aparece na lista (casa sem distinguir maiúsculas)."""
        if not valor:
            return valor
        alvo = valor.strip().lower()
        for existente in valores:
            if existente.strip().lower() == alvo:
                return existente
        return valor
