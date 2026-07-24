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
from app.domain.assistente_llm import (
    construir_mensagens,
    extrair_json,
    intencao_de_json,
)
from app.domain.assistente_obra import (
    DossierObra,
    VersaoObra,
    identificar_pedido,
    resumo_texto,
)
from app.domain.datas import normalizar_data
from app.domain.pesquisa_texto import normalizar
from app.domain.producao_estados import ESTADOS_PRODUCAO
from app.models.user import User
from app.services.ia_perfil_service import listar_entradas
from app.services.producao_service import (
    filtrar_processos,
    gerar_nome_enc_imos_ix,
    vocabulario_pesquisa,
)
from app.services.sinonimos_service import carregar_sinonimos
from app.services.system_setting_service import SystemSettingService

#: Separadores usados quando se escrevem várias formas na mesma célula.
_SEPARADORES = re.compile(r"[;,/|]")

#: Estados canónicos por forma normalizada, para ler o quadro «estado».
_ESTADO_POR_NORMA = {normalizar(estado): estado for estado in ESTADOS_PRODUCAO}


@dataclass(frozen=True)
class ResultadoIA:
    """Resposta do orquestrador: ou é uma pesquisa, ou uma ação sobre uma obra."""

    tipo: str  # "pesquisa" | "obra"
    # tipo == "pesquisa"
    intencao: Intencao | None = None
    recusa: str = ""
    # tipo == "obra"
    obra_id: int | None = None
    modo: str = ""       # "texto" | "pdf" | "email"
    texto: str = ""
    dossier: DossierObra | None = None
    aviso: str = ""


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


def _chave_versao(processo):
    """Ordena versões: por V. Obra, depois V. CUT-RITE, depois id."""
    def _n(valor):
        try:
            return int(re.sub(r"\D", "", str(valor or "")) or 0)
        except ValueError:
            return 0

    return (
        _n(getattr(processo, "versao_obra", "")),
        _n(getattr(processo, "versao_plano", "")),
        getattr(processo, "id", 0) or 0,
    )


def _sem_filtros_estruturados(intencao: Intencao) -> bool:
    """True quando só há (quando muito) texto livre, sem estado/cliente/etc.

    Se o utilizador deu um filtro concreto, é uma pesquisa válida e uma recusa
    do modelo pequeno é ignorada; se é só texto solto, confia-se no juízo do
    modelo sobre se o tema é do trabalho.
    """
    return not (
        intencao.estado
        or intencao.cliente
        or intencao.responsavel
        or intencao.so_atrasadas
    )


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

    def responder_ia(
        self,
        pergunta: str,
        *,
        user_id: int | None,
        processos,
    ) -> ResultadoIA:
        """Decide: ação sobre UMA obra («relatório da obra 1134») ou pesquisa.

        Corre na thread de fundo da UI (pode tocar no Streamlit para as fases).
        """
        pedido = identificar_pedido(pergunta)
        if pedido is not None:
            versoes = self._encontrar_obras(processos, pedido.numero)
            if not versoes:
                return ResultadoIA(
                    tipo="obra",
                    modo=pedido.modo,
                    aviso=f"Não encontrei a obra {pedido.numero} na lista.",
                )
            dossier = self.montar_dossier(versoes)
            principal = versoes[-1]  # versão mais recente
            return ResultadoIA(
                tipo="obra",
                obra_id=getattr(principal, "id", None),
                modo=pedido.modo,
                texto=resumo_texto(dossier),
                dossier=dossier,
            )

        intencao, recusa = self.interpretar_pergunta_llm(
            pergunta, user_id=user_id, processos=processos
        )
        return ResultadoIA(tipo="pesquisa", intencao=intencao, recusa=recusa)

    def montar_dossier(self, versoes_processo, *, carregar_estados=None) -> DossierObra:
        """Junta os dados da obra + as versões (obra/CUT-RITE) e as suas fases.

        ``versoes_processo`` são todos os processos da mesma obra (nº encomenda),
        já ordenados da versão mais antiga para a mais recente. O cabeçalho usa
        a versão mais recente (a que está a trabalhar-se).
        """
        versoes_processo = list(versoes_processo or [])
        principal = versoes_processo[-1]
        estados = (carregar_estados or self._estados_producao)(versoes_processo)

        versoes: list[VersaoObra] = []
        for processo in versoes_processo:
            fases, etiqueta, encontrado = estados.get(
                getattr(processo, "id", None), ((), "", False)
            )
            versoes.append(
                VersaoObra(
                    versao_obra=str(getattr(processo, "versao_obra", "") or "").strip(),
                    versao_plano=str(getattr(processo, "versao_plano", "") or "").strip(),
                    codigo=str(getattr(processo, "codigo_processo", "") or "").strip(),
                    estado_local=str(getattr(processo, "estado", "") or "").strip(),
                    fases=fases,
                    estado_global=etiqueta,
                    encontrado_streamlit=encontrado,
                )
            )

        fases, estado_global, encontrado = estados.get(
            getattr(principal, "id", None), ((), "", False)
        )
        return DossierObra(
            codigo=str(getattr(principal, "codigo_processo", "") or "").strip(),
            enc=str(getattr(principal, "num_enc_phc", "") or "").strip(),
            cliente=str(getattr(principal, "nome_cliente", "") or "").strip(),
            obra=str(getattr(principal, "obra", "") or "").strip(),
            ref_cliente=str(getattr(principal, "ref_cliente", "") or "").strip(),
            localizacao=str(getattr(principal, "localizacao", "") or "").strip(),
            pasta=str(getattr(principal, "pasta_servidor", "") or "").strip(),
            responsavel=str(getattr(principal, "responsavel", "") or "").strip(),
            estado_local=str(getattr(principal, "estado", "") or "").strip(),
            data_inicio=normalizar_data(getattr(principal, "data_inicio", None)) or "",
            data_entrega=normalizar_data(getattr(principal, "data_entrega", None)) or "",
            descricao_producao=str(
                getattr(principal, "descricao_producao", "") or ""
            ).strip(),
            notas=self._juntar_notas(principal),
            imagem_path=self._imagem_imos(principal),
            email_cliente=self._email_cliente(principal),
            fases=fases,
            estado_global=estado_global,
            encontrado_streamlit=encontrado,
            versoes=tuple(versoes),
        )

    def _email_cliente(self, processo) -> str:
        """Email do cliente da obra, pelo nº de cliente PHC (dados do cliente)."""
        num = str(getattr(processo, "num_cliente_phc", "") or "").strip()
        if not num or self.session is None:
            return ""
        try:
            from sqlalchemy import select

            from app.models.cliente import Cliente

            email = self.session.execute(
                select(Cliente.email).where(Cliente.num_cliente_phc == num)
            ).scalars().first()
            return (email or "").strip()
        except Exception:  # noqa: BLE001 - email é acessório
            return ""

    def _imagem_imos(self, processo) -> str:
        """Caminho da imagem IMOS da obra (mesma lógica do detalhe da Produção)."""
        try:
            nome_enc = gerar_nome_enc_imos_ix(
                getattr(processo, "ano", None),
                getattr(processo, "num_enc_phc", None),
                getattr(processo, "versao_obra", None),
                nome_cliente_simplex=getattr(processo, "nome_cliente_simplex", None),
                nome_cliente=getattr(processo, "nome_cliente", None),
                ref_cliente=getattr(processo, "ref_cliente", None),
            )
            if not nome_enc:
                return ""
            from app.services.imos_imagem_service import resolver_imagem_imos

            caminho = resolver_imagem_imos(self.session, nome_enc_imos=nome_enc)
            return str(caminho) if caminho else ""
        except Exception:  # noqa: BLE001 - imagem é acessória
            return ""

    def _estados_producao(self, processos) -> dict:
        """Fases por processo (Streamlit); id -> (fases, etiqueta, encontrado)."""
        try:
            from app.services.estado_producao_service import (
                estado_producao_por_processo,
            )

            resultados = estado_producao_por_processo(self.session, list(processos))
        except Exception:  # noqa: BLE001 - fonte externa pode falhar
            return {}
        estados: dict = {}
        for obra in resultados:
            fases = tuple(
                (setor.nome, setor.media_pct, setor.concluido)
                for setor in obra.estado.setores
            )
            estados[obra.id] = (fases, obra.estado.etiqueta, bool(obra.encontrado))
        return estados

    @staticmethod
    def _encontrar_obras(processos, numero: str) -> list:
        """Todas as versões da obra (mesmo nº encomenda), da mais antiga à recente."""
        alvo = re.sub(r"\D", "", numero or "")
        if not alvo:
            return []
        alvo_int = int(alvo)
        encontradas = []
        for processo in processos or []:
            bruto = re.sub(r"\D", "", str(getattr(processo, "num_enc_phc", "") or ""))
            if bruto and (bruto == alvo or int(bruto) == alvo_int):
                encontradas.append(processo)
        return sorted(encontradas, key=_chave_versao)

    @staticmethod
    def _juntar_notas(processo) -> str:
        partes = [
            str(getattr(processo, campo, "") or "").strip()
            for campo in ("notas1", "notas2", "notas3")
        ]
        return " · ".join(parte for parte in partes if parte)

    def interpretar_pergunta_llm(
        self,
        pergunta: str,
        *,
        user_id: int | None,
        processos,
        chamar_modelo=None,
    ) -> tuple[Intencao, str]:
        """Interpreta com o LLM local; cai no determinístico se falhar.

        Devolve ``(Intencao, recusa)``. O modelo só propõe; os valores são
        validados contra os que existem mesmo, por isso não pode inventar dados.
        ``chamar_modelo`` é injetável (testes); por omissão fala com o Ollama.
        """
        # As regras são a base fiável; o modelo pequeno só ENRIQUECE o que
        # elas não apanharam. Assim o resultado nunca fica pior que o
        # determinístico, mesmo quando o LLM erra ou inventa perguntas.
        base = self.interpretar_pergunta(
            pergunta, user_id=user_id, processos=processos
        )
        clientes = self._distintos(processos, "nome_cliente")
        responsaveis = self._distintos(processos, "responsavel")
        chamar = chamar_modelo or self._chamar_ollama

        try:
            system, user = construir_mensagens(
                pergunta, self._perfil_texto(self._perfil(user_id))
            )
            dados = extrair_json(chamar(system, user))
            llm, recusa = intencao_de_json(
                dados, clientes=clientes, responsaveis=responsaveis
            )
        except Exception:  # noqa: BLE001 - qualquer falha do modelo -> só regras
            return base, ""

        # Só se recusa quando não há filtros estruturados, para o modelo pequeno
        # não bloquear pesquisas válidas com falsos positivos.
        if recusa and _sem_filtros_estruturados(base):
            return Intencao(), recusa

        return self._combinar(base, llm), ""

    @staticmethod
    def _combinar(base: Intencao, llm: Intencao | None) -> Intencao:
        """Junta as regras (base fiável) com o LLM, sem o deixar poluir.

        Teste real (llama3.2 e llama3.1): os modelos locais ALUCINAM o estado
        e repetem nomes no texto livre. Por isso o LLM só contribui com
        **cliente/responsável validados** (não pode inventar nomes que não
        existam); estado, texto livre, atrasadas e ambiguidade vêm só das regras.
        """
        if llm is None:
            return base
        return replace(
            base,
            cliente=base.cliente or llm.cliente,
            responsavel=base.responsavel or llm.responsavel,
        )

    def _chamar_ollama(self, system: str, user: str) -> str:
        """Fala com o Ollama local (modelo de ``modelo_local_ia``)."""
        modelo = (
            SystemSettingService(self.session).obter_valor("modelo_local_ia", "")
            or ""
        ).strip()
        if not modelo:
            raise RuntimeError("Sem modelo local definido.")

        import json
        import urllib.request

        payload = {
            "model": modelo,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            dados = json.loads(resp.read().decode("utf-8"))
        return (dados.get("message", {}).get("content") or "").strip()

    @staticmethod
    def _perfil_texto(perfil: PerfilVocabulario) -> str:
        """Rendering compacto do vocabulário para dar contexto ao modelo."""
        linhas: list[str] = []
        for forma, nome in perfil.clientes.items():
            linhas.append(f"«{forma}» = cliente {nome}")
        for forma, nome in perfil.pessoas.items():
            linhas.append(f"«{forma}» = responsável {nome}")
        for forma, questao in perfil.ambiguas.items():
            linhas.append(f"«{forma}» é ambíguo — perguntar: {questao}")
        return "\n".join(linhas)

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
