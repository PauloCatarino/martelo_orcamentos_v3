"""Escritório do Streamlit: o passo Desenho → Aprovisionamento visto do Martelo.

No Streamlit (Leitor_PHC3), cada modelo/versão de uma obra «com desenho» tem
uma etapa: ``DESENHO`` → ``APROVISIONAMENTO`` → ``LIBERTADA``. O primeiro passo
é do desenhador («Enviar para o Aprovisionamento»). Quando a obra passa a
Produção no Martelo, o Martelo dá esse passo por ele — e, ao contrário, quando
alguém o dá no Streamlit, o Martelo propõe pôr a obra em Produção.

Este módulo é só regras: sem Qt, sem SQL. Quem lê e escreve na base do
Streamlit são :mod:`app.services.escritorio_streamlit_service` (leitura) e
:mod:`app.services.escritorio_streamlit_escrita` (escrita).

As regras e os textos copiam os do próprio Streamlit
(``escritorio_service.enviar_para_aprovisionamento``) para que um avanço feito
no Martelo seja igual a um feito lá — com uma única diferença, de propósito: o
``detalhe`` do evento leva ``"via": "MARTELO"``.
"""

from __future__ import annotations

import json
import re
import unicodedata
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timezone, tzinfo

from app.domain.producao_estados import ESTADO_PRODUCAO, avanca_na_vida_da_obra

ETAPA_DESENHO = "DESENHO"
ETAPA_APROVISIONAMENTO = "APROVISIONAMENTO"
ETAPA_LIBERTADA = "LIBERTADA"

#: Etapas em que o modelo/versão já saiu das mãos do desenhador.
ETAPAS_AVANCADAS: tuple[str, ...] = (ETAPA_APROVISIONAMENTO, ETAPA_LIBERTADA)

OBRA_POR_DECIDIR = "POR_DECIDIR"
OBRA_COM_DESENHO = "COM_DESENHO"
OBRA_SEM_DESENHO = "SEM_DESENHO"
OBRA_ARQUIVADA = "ARQUIVADA"

#: O que distingue um avanço do Martelo dos do Streamlit (sem ``via``) e dos do
#: worker (``acionado_por: "worker"``).
VIA_MARTELO = "MARTELO"

#: ``libertada_por`` e utilizador do 2.º evento quando o material é só do
#: cliente. Tem significado próprio no Streamlit: não serve para mais nada.
UTILIZADOR_SISTEMA = "sistema"

#: ``operacao`` da linha de espelho no Histórico do Tempos de Produção.
OPERACAO_ESPELHO = "escritorio"

#: O «porquê» do avanço. Fixo, para o Gravar não ganhar mais um clique.
MOTIVO_AVANCAR = "Desenho concluído."
MOTIVO_LIBERTAR_AUTO = (
    "Placas e orla só do cliente: sem compras, não passa pelo Aprovisionamento."
)

ROTULO_AVANCAR = "Desenho → Aprovisionamento"
ROTULO_LIBERTAR_AUTO = "Libertada automaticamente"

#: Permissões do Streamlit que deixam enviar. ``Escritorio_Consulta`` só lê.
PERMISSOES_ESCRITA = frozenset({"Escritorio_ALL", "Escritorio_Desenhos"})

#: Só a versão 01 de cada modelo tem percurso; as seguintes são acréscimos.
VERSAO_COM_PERCURSO = "01"

#: Comprimentos das colunas do Streamlit onde o Martelo escreve.
LIMITE_BD_KEY = 60
LIMITE_NUMERO = 20
LIMITE_UTILIZADOR = 100
LIMITE_MOTIVO = 500
LIMITE_COMMAND_ID = 64
LIMITE_COMENTARIOS = 800

#: Recusas que não merecem caixa de mensagem: são o caso normal de muitas
#: obras (antigas, acréscimos, assistências) e vão só para a linha de estado.
RECUSAS_DISCRETAS = frozenset({"assistencia", "versao", "fora"})


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------
def sem_acentos(texto: object) -> str:
    """Comparar nomes sem ligar a acentos nem a maiúsculas."""
    normal = unicodedata.normalize("NFKD", str(texto or "").strip())
    return "".join(c for c in normal if not unicodedata.combining(c)).casefold()


def verdadeiro(valor: object) -> bool:
    """As colunas do material são BIT, mas aceita-se também o texto antigo."""
    if valor is None:
        return False
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return valor != 0
    return sem_acentos(valor) in {"1", "true", "sim", "s", "yes", "y", "on"}


# ---------------------------------------------------------------------------
# A chave do modelo/versão
# ---------------------------------------------------------------------------
def numero_canonico(numero: object) -> str:
    """Número da obra como o Streamlit o guarda.

    ``599`` → ``0599`` (encomendas do PHC: 4 algarismos), ``_58`` → ``_058``
    (as do Criar Encomendas), ``a7`` → ``A007`` (assistências).
    """
    texto = str(numero or "").strip()
    if re.fullmatch(r"\d+", texto):
        return f"{int(texto):04d}"
    especial = re.fullmatch(r"_(\d+)", texto)
    if especial:
        return f"_{int(especial.group(1)):03d}"
    assistencia = re.fullmatch(r"[Aa](\d+)", texto)
    if assistencia:
        return f"A{int(assistencia.group(1)):03d}"
    raise ValueError(f"Nº de encomenda inválido para o Escritório: {texto or '(vazio)'}.")


def _dois_algarismos(valor: object, nome: str) -> str:
    texto = str(valor or "").strip()
    if not re.fullmatch(r"\d{1,3}", texto) or not 1 <= int(texto) <= 99:
        raise ValueError(f"{nome} inválido para o Escritório: {texto or '(vazio)'}.")
    return f"{int(texto):02d}"


@dataclass(frozen=True)
class ChaveVersao:
    """Um modelo/versão de uma obra: a ``bd_key`` do Streamlit."""

    ano: int
    numero: str
    modelo: str
    versao: str

    @property
    def bd_key(self) -> str:
        return f"{self.ano}_{self.numero}_{self.modelo}_{self.versao}"

    @property
    def sufixo(self) -> str:
        """``_`` para as tabelas gémeas das obras ``_NNN``."""
        return "_" if self.numero.startswith("_") else ""

    @property
    def e_assistencia(self) -> bool:
        return self.numero.startswith("A")

    @property
    def descricao(self) -> str:
        return f"Modelo {self.modelo} · Versão {self.versao}"


def chave_versao(ano: object, numero: object, modelo: object, versao: object) -> ChaveVersao:
    """Montar a chave a partir dos campos da obra no Martelo (ano, Nº Enc,
    Modelo, Versão). Dá ``ValueError`` quando algum não serve."""
    texto_ano = str(ano or "").strip()
    if not re.fullmatch(r"\d{4}", texto_ano):
        raise ValueError(f"Ano inválido para o Escritório: {texto_ano or '(vazio)'}.")
    chave = ChaveVersao(
        ano=int(texto_ano),
        numero=numero_canonico(numero),
        modelo=_dois_algarismos(modelo, "Modelo"),
        versao=_dois_algarismos(versao, "Versão"),
    )
    if len(chave.bd_key) > LIMITE_BD_KEY or len(chave.numero) > LIMITE_NUMERO:
        raise ValueError("Nº de encomenda demasiado comprido para o Escritório.")
    return chave


def recusa_sem_ir_ao_streamlit(chave: ChaveVersao) -> str:
    """Recusas que se decidem só com a chave, sem gastar uma ida ao servidor."""
    if chave.e_assistencia:
        return "As assistências (A###) não passam pelo Escritório."
    if chave.versao != VERSAO_COM_PERCURSO:
        return (
            "Só a versão 01 de cada modelo segue para o Aprovisionamento; "
            "as seguintes são acréscimos do modelo."
        )
    return ""


# ---------------------------------------------------------------------------
# Material, avisos e datas
# ---------------------------------------------------------------------------
def material_so_do_cliente(ce: Mapping[str, object] | None) -> str:
    """Texto do material quando as placas e a orla são só do cliente; senão "".

    Igual ao botão do Streamlit: sem compras, o modelo/versão não passa pelo
    Aprovisionamento e fica logo libertado para a fábrica.
    """
    if not ce:
        return ""
    placas_cliente = (
        verdadeiro(ce.get("bd_placas_cl"))
        and not verdadeiro(ce.get("bd_placas_le"))
        and not verdadeiro(ce.get("bd_placas_ambos"))
    )
    orla_sem_compras = not verdadeiro(ce.get("bd_de_quem_orla_le")) and not verdadeiro(
        ce.get("bd_de_quem_orla_ambos")
    )
    if not (placas_cliente and orla_sem_compras):
        return ""
    orla = "Cliente" if verdadeiro(ce.get("bd_de_quem_orla_cl")) else "não indicada"
    return f"placas: Cliente · orla: {orla}"


def envio_ok(status_envio: object) -> bool:
    """O plano de corte seguiu para a fábrica (``🟢 ENVIADO``)?"""
    texto = sem_acentos(status_envio).upper()
    return "ENVIADO" in texto and "NAO ENVIADO" not in texto


def avisos_do_envio(
    ce: Mapping[str, object] | None, tp: Mapping[str, object] | None
) -> tuple[str, ...]:
    """O que falta, como o Streamlit avisa. Não impede: pede confirmação."""
    tp = tp or {}
    avisos: list[str] = []
    plano = str(tp.get("bd_plano_corte") or "").strip()
    if not plano:
        avisos.append("sem plano de corte")
    elif not envio_ok(tp.get("bd_status_envio")):
        avisos.append("plano de corte não enviado")
    if not verdadeiro((ce or {}).get("tem_materias")):
        avisos.append("sem materiais calculados")
    return tuple(avisos)


def ler_data_utc(valor: object) -> datetime | None:
    """As datas chegam como texto ISO (``CONVERT(..., 126)``), em UTC."""
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        data = datetime.fromisoformat(texto[:19])
    except ValueError:
        return None
    return data.replace(tzinfo=timezone.utc)


def data_local(valor: object, *, fuso: tzinfo | None = None) -> str:
    """``28/10/2026 14:30`` na hora deste PC (os PCs estão na hora de Lisboa)."""
    data = ler_data_utc(valor)
    if data is None:
        return ""
    return data.astimezone(fuso).strftime("%d/%m/%Y %H:%M")


def etapa_legivel(etapa: object) -> str:
    return {
        ETAPA_DESENHO: "Em desenho",
        ETAPA_APROVISIONAMENTO: "No Aprovisionamento",
        ETAPA_LIBERTADA: "Libertado para a fábrica",
    }.get(str(etapa or "").strip().upper(), str(etapa or "").strip() or "—")


# ---------------------------------------------------------------------------
# Quem clica: o utilizador do Martelo visto no Streamlit
# ---------------------------------------------------------------------------
def lista_json(valor: object) -> frozenset[str]:
    """``permissoes``/``Permissoes`` são arrays JSON de texto."""
    if isinstance(valor, (list, tuple, set, frozenset)):
        itens = valor
    else:
        try:
            itens = json.loads(str(valor or "[]"))
        except (TypeError, ValueError):
            return frozenset()
    if not isinstance(itens, (list, tuple, set, frozenset)):
        return frozenset()
    return frozenset(str(item).strip() for item in itens if str(item or "").strip())


@dataclass(frozen=True)
class UtilizadorStreamlit:
    username: str
    nome: str
    is_admin: bool = False
    permissoes: frozenset[str] = field(default_factory=frozenset)

    @property
    def pode_enviar(self) -> bool:
        return self.is_admin or bool(self.permissoes & PERMISSOES_ESCRITA)


def utilizadores_streamlit(
    linhas: Iterable[Mapping[str, object]], locais: Iterable[Mapping[str, object]]
) -> list[UtilizadorStreamlit]:
    """Os utilizadores ativos, cada um com as permissões dele mais as do Local."""
    permissoes_do_local = {
        sem_acentos(local.get("Nome")): lista_json(local.get("Permissoes"))
        for local in locais
        if verdadeiro(local.get("Ativo"))
    }
    resultado = []
    for linha in linhas:
        if not verdadeiro(linha.get("ativo")):
            continue
        username = str(linha.get("username") or "").strip()
        if not username:
            continue
        permissoes = lista_json(linha.get("permissoes")) | permissoes_do_local.get(
            sem_acentos(linha.get("local_trabalho")), frozenset()
        )
        resultado.append(
            UtilizadorStreamlit(
                username=username,
                nome=str(linha.get("nome") or "").strip(),
                is_admin=verdadeiro(linha.get("is_admin")),
                permissoes=permissoes,
            )
        )
    return resultado


def ler_mapa_utilizadores(texto: object) -> dict[str, str]:
    """``paulo=paulo_catarino; Ana=ana.felix`` → {"paulo": "paulo_catarino", ...}.

    É a correção à mão, em Configurações › Caminhos do Sistema
    (``streamlit_mapa_utilizadores``), para quando a ligação automática pelo
    nome não chega.
    """
    mapa: dict[str, str] = {}
    for par in re.split(r"[;,\n]+", str(texto or "")):
        if "=" not in par:
            continue
        martelo, streamlit = (parte.strip() for parte in par.split("=", 1))
        if martelo and streamlit:
            mapa[sem_acentos(martelo)] = streamlit
    return mapa


def _primeiro_nome(texto: object) -> str:
    partes = sem_acentos(texto).split()
    return partes[0] if partes else ""


def resolver_utilizador(
    martelo_username: object,
    martelo_nome: object,
    utilizadores: list[UtilizadorStreamlit],
    mapa_manual: Mapping[str, str] | None = None,
) -> tuple[UtilizadorStreamlit | None, str]:
    """Quem é, no Streamlit, a pessoa que está no Martelo.

    Os nomes de utilizador não coincidem (no Martelo «Ana», no Streamlit
    «ana.felix»), por isso vai-se pelo nome da pessoa: primeiro o nome
    completo, depois o primeiro nome. Nunca pelo username sozinho — o «admin»
    do Martelo não é o «admin» do Streamlit.
    Devolve ``(utilizador, "")`` ou ``(None, mensagem)``.
    """
    por_username = {sem_acentos(u.username): u for u in utilizadores}
    quem = str(martelo_username or "").strip() or str(martelo_nome or "").strip()

    manual = (mapa_manual or {}).get(sem_acentos(martelo_username))
    if manual:
        utilizador = por_username.get(sem_acentos(manual))
        if utilizador is None:
            return None, (
                f"O nome «{manual}» indicado para «{quem}» em "
                "streamlit_mapa_utilizadores não existe (ou está inativo) no Streamlit."
            )
        return utilizador, ""

    nome = sem_acentos(martelo_nome)
    if nome:
        iguais = [u for u in utilizadores if sem_acentos(u.nome) == nome]
        if len(iguais) == 1:
            return iguais[0], ""

    primeiro = _primeiro_nome(martelo_nome) or _primeiro_nome(martelo_username)
    candidatos = [u for u in utilizadores if primeiro and _primeiro_nome(u.nome) == primeiro]
    if len(candidatos) > 1:
        # Entre duas pessoas com o mesmo primeiro nome, ganha quem desenha.
        candidatos = [u for u in candidatos if u.pode_enviar] or candidatos
    if len(candidatos) == 1:
        return candidatos[0], ""
    if len(candidatos) > 1:
        return None, (
            f"Há mais do que uma pessoa no Streamlit que pode ser «{quem}». "
            "Indique qual em Configurações › Caminhos do Sistema › "
            "streamlit_mapa_utilizadores (ex.: paulo=paulo_catarino)."
        )
    return None, (
        f"Não encontrei «{quem}» entre os utilizadores do Streamlit. Indique o nome "
        "em Configurações › Caminhos do Sistema › streamlit_mapa_utilizadores "
        "(ex.: paulo=paulo_catarino)."
    )


# ---------------------------------------------------------------------------
# A decisão: pode avançar?
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DadosEscritorio:
    """O que se leu do Streamlit para decidir (linhas cruas, ou None)."""

    obra: Mapping[str, object] | None = None
    versao: Mapping[str, object] | None = None
    ultimo_avanco: Mapping[str, object] | None = None
    ce: Mapping[str, object] | None = None
    tp: Mapping[str, object] | None = None
    utilizadores: tuple[UtilizadorStreamlit, ...] = ()


PRONTO = "pronto"
RECUSADO = "recusado"
JA_ENVIADO = "ja_enviado"


@dataclass(frozen=True)
class Avaliacao:
    """Resposta à pergunta «este modelo/versão pode seguir para o Aprovisionamento?»"""

    chave: ChaveVersao
    resultado: str
    mensagem: str
    #: Porque recusou, quando recusou: ``assistencia``, ``versao``, ``fora``,
    #: ``obra``, ``utilizador``, ``dono``, ``ce``.
    motivo_recusa: str = ""
    utilizador: str = ""
    desenhador: str | None = None
    em_nome_de: str = ""
    avisos: tuple[str, ...] = ()
    material_cliente: str = ""
    ce: Mapping[str, object] = field(default_factory=dict)
    plano_corte: str = ""

    @property
    def pronto(self) -> bool:
        return self.resultado == PRONTO

    @property
    def discreta(self) -> bool:
        """Recusa normal (obra antiga, acréscimo…): basta a linha de estado."""
        return self.resultado != PRONTO and (
            self.resultado == JA_ENVIADO or self.motivo_recusa in RECUSAS_DISCRETAS
        )


def _recusa(chave: ChaveVersao, motivo: str, mensagem: str) -> Avaliacao:
    return Avaliacao(chave=chave, resultado=RECUSADO, mensagem=mensagem, motivo_recusa=motivo)


def _via_do_detalhe(detalhe: object) -> str:
    try:
        dados = json.loads(str(detalhe or "{}"))
    except (TypeError, ValueError):
        dados = {}
    if not isinstance(dados, dict):
        return "Streamlit"
    if dados.get("via"):
        return str(dados["via"])
    if dados.get("acionado_por") == "worker":
        return "Worker"
    return "Streamlit"


def _ja_enviado(chave: ChaveVersao, dados: DadosEscritorio) -> Avaliacao:
    versao = dados.versao or {}
    etapa = str(versao.get("etapa") or "").strip().upper()
    if etapa == ETAPA_LIBERTADA:
        mensagem = "Este modelo/versão já foi libertado para a fábrica."
    else:
        avanco = dados.ultimo_avanco or {}
        quem = str(versao.get("desenho_concluido_por") or "").strip() or str(
            avanco.get("utilizador") or ""
        ).strip() or "—"
        quando = data_local(versao.get("desenho_concluido_em")) or data_local(
            avanco.get("criado_em")
        ) or "—"
        via = _via_do_detalhe(avanco.get("detalhe")) if avanco else "Streamlit"
        mensagem = (
            f"Este modelo/versão já foi enviado em {quando} por {quem} (via {via})."
        )
    return Avaliacao(chave=chave, resultado=JA_ENVIADO, mensagem=mensagem)


def avaliar_envio(
    chave: ChaveVersao,
    dados: DadosEscritorio,
    utilizador: UtilizadorStreamlit | None,
    mensagem_utilizador: str = "",
) -> Avaliacao:
    """As validações do Streamlit, pela mesma ordem: a primeira que falha decide."""
    local = recusa_sem_ir_ao_streamlit(chave)
    if local:
        return _recusa(chave, "assistencia" if chave.e_assistencia else "versao", local)

    tp = dados.tp or {}
    if verdadeiro(tp.get("bd_assistencia")):
        return _recusa(
            chave,
            "assistencia",
            "Este modelo/versão está marcado como assistência no Tempos de "
            "Produção: as assistências não passam pelo Escritório.",
        )

    obra = dados.obra
    estado_obra = str((obra or {}).get("estado_obra") or "").strip().upper()
    if obra is None or estado_obra == OBRA_POR_DECIDIR:
        return _recusa(
            chave,
            "fora",
            "Esta obra ainda não está no Escritório (Orçamentos ainda não a encaminhou).",
        )
    if estado_obra == OBRA_SEM_DESENHO:
        return _recusa(
            chave,
            "fora",
            "Obra decidida sem desenho: não passa pelo Desenho/Aprovisionamento.",
        )
    if estado_obra == OBRA_ARQUIVADA:
        return _recusa(chave, "obra", "Obra retirada do Escritório.")
    if estado_obra != OBRA_COM_DESENHO:
        return _recusa(
            chave, "obra", f"Estado da obra no Escritório desconhecido: {estado_obra or '—'}."
        )
    desenhador = str(obra.get("desenhador_username") or "").strip() or None
    if desenhador is None:
        return _recusa(
            chave, "obra", "Obra sem desenhador atribuído (foi devolvida a Orçamentos)."
        )

    if utilizador is None:
        return _recusa(chave, "utilizador", mensagem_utilizador or "Utilizador desconhecido no Streamlit.")
    if not utilizador.pode_enviar:
        return _recusa(
            chave,
            "utilizador",
            f"No Streamlit, «{utilizador.username}» não tem a permissão de enviar "
            "do Desenho para o Aprovisionamento (Escritorio_Desenhos).",
        )
    dono = utilizador.username == desenhador
    if not dono and not utilizador.is_admin:
        nomes = {u.username: u.nome for u in dados.utilizadores}
        return _recusa(
            chave,
            "dono",
            f"Esta obra está atribuída a {nomes.get(desenhador) or desenhador}. "
            "Peça a Orçamentos para a reatribuir.",
        )

    if dados.ce is None:
        return _recusa(
            chave,
            "ce",
            "Falta criar o Caderno de Encargos desta versão (no Streamlit) antes de a enviar.",
        )

    etapa = str((dados.versao or {}).get("etapa") or ETAPA_DESENHO).strip().upper()
    if etapa != ETAPA_DESENHO:
        return _ja_enviado(chave, dados)

    return Avaliacao(
        chave=chave,
        resultado=PRONTO,
        mensagem=f"{chave.descricao} pronto a seguir para o Aprovisionamento.",
        utilizador=utilizador.username,
        desenhador=desenhador,
        em_nome_de="" if dono else desenhador,
        avisos=avisos_do_envio(dados.ce, tp),
        material_cliente=material_so_do_cliente(dados.ce),
        ce=dict(dados.ce),
        plano_corte=str(tp.get("bd_plano_corte") or "").strip(),
    )


# ---------------------------------------------------------------------------
# O que fica gravado
# ---------------------------------------------------------------------------
def novo_command_id() -> str:
    """Um por clique: o índice único do Streamlit não deixa gravar duas vezes."""
    return str(uuid.uuid4())


def id_filho(command_id: str, bd_key: str) -> str:
    """``command_id`` do 2.º evento (``LIBERTAR_AUTO``), sempre o mesmo para o
    mesmo clique — como o ``_id_filho`` do Streamlit."""
    return str(uuid.uuid5(uuid.UUID(str(command_id)), "libertar_auto:" + bd_key))


def detalhe_avancar(
    chave: ChaveVersao,
    *,
    versao_programa: str = "",
    posto: str = "",
    em_nome_de: str = "",
    avisos_aceites: Iterable[str] = (),
    pasta: str = "",
) -> dict[str, object]:
    """O ``detalhe`` (JSON) do evento ``AVANCAR``: ``mensagem`` e ``via`` sempre."""
    detalhe: dict[str, object] = {
        "mensagem": (
            f"Obra {chave.numero}: 1 modelo/versão enviado(s) para o "
            f"Aprovisionamento pelo {VIA_MARTELO}."
        ),
        "via": VIA_MARTELO,
    }
    if versao_programa:
        detalhe["versao_programa"] = versao_programa
    if posto:
        detalhe["posto"] = posto
    if em_nome_de:
        detalhe["em_nome_de"] = em_nome_de
    avisos = [str(aviso) for aviso in avisos_aceites if str(aviso or "").strip()]
    if avisos:
        detalhe["avisos_aceites"] = avisos
    if pasta:
        detalhe["pasta"] = pasta
    return detalhe


def detalhe_libertar_auto(
    chave: ChaveVersao, *, material: str, acionado_por: str
) -> dict[str, object]:
    """O ``detalhe`` do 2.º evento, quando o material é só do cliente."""
    return {
        "mensagem": (
            f"Versão {chave.modelo}/{chave.versao} libertada automaticamente "
            "(material só do cliente)."
        ),
        "automatico": True,
        "regra": "material só do cliente",
        "material": material,
        "acionado_por": acionado_por,
        "via": VIA_MARTELO,
    }


def json_detalhe(detalhe: Mapping[str, object]) -> str:
    """JSON válido e com os acentos tal e qual (a coluna é NVARCHAR)."""
    return json.dumps(dict(detalhe), ensure_ascii=False)


def texto_espelho(rotulo: str, *, via: str = "", motivo: str = "") -> str:
    """``comentarios`` do Histórico do Tempos de Produção.

    Formato combinado com o Streamlit (``descrever_evento``):
    ``rótulo · via <VIA> · motivo: <motivo>``, cada parte só se existir.
    """
    partes = [rotulo]
    if via:
        partes.append(f"via {via}")
    if motivo:
        partes.append(f"motivo: {motivo}")
    return " · ".join(partes)[:LIMITE_COMENTARIOS]


def mensagem_sucesso(chave: ChaveVersao) -> str:
    return f"✔ {chave.descricao} enviado para o Aprovisionamento."


MENSAGEM_LIBERTADA = (
    "Material só do cliente: este modelo/versão não passa pelo Aprovisionamento "
    "e ficou logo libertado para a fábrica."
)


# ---------------------------------------------------------------------------
# No sentido contrário: o Streamlit avançou, o Martelo ainda diz Desenho
# ---------------------------------------------------------------------------
def marca_sugestao(bd_key: str, etapa: str) -> str:
    """Identifica uma sugestão: muda quando a etapa muda (e volta a avisar)."""
    return f"{bd_key}|{str(etapa or '').strip().upper()}"


def o_que_diz_o_escritorio(versao: Mapping[str, object], *, fuso: tzinfo | None = None) -> str:
    """Texto da coluna «O que diz lá fora»."""
    etapa = str(versao.get("etapa") or "").strip().upper()
    if etapa == ETAPA_LIBERTADA:
        quando = data_local(versao.get("libertada_em"), fuso=fuso)
        quem = str(versao.get("libertada_por") or "").strip()
        texto = "Libertado para a fábrica"
    else:
        quando = data_local(versao.get("desenho_concluido_em"), fuso=fuso)
        quem = str(versao.get("desenho_concluido_por") or "").strip()
        texto = "No Aprovisionamento"
    if quando:
        texto += f" desde {quando}"
    if quem:
        texto += f" ({quem})"
    return texto


def sugestoes_de_producao(
    processos: Iterable[object],
    versoes: Mapping[str, Mapping[str, object]],
    *,
    fuso: tzinfo | None = None,
) -> list[dict[str, object]]:
    """Obras em Desenho no Martelo cujo modelo/versão o Escritório já avançou.

    ``versoes`` é ``{bd_key: linha de Escritorio_Versoes}`` (só as avançadas).
    Devolve linhas no formato da caixa do analisador de estados, com mais
    ``bd_key`` e ``marca``. Nunca propõe recuar: uma obra que já está em
    Produção (ou à frente) fica como está.
    """
    sugestoes = []
    for processo in processos:
        atual = str(getattr(processo, "estado", "") or "").strip()
        if not avanca_na_vida_da_obra(atual, ESTADO_PRODUCAO):
            continue
        try:
            chave = chave_versao(
                getattr(processo, "ano", ""),
                getattr(processo, "num_enc_phc", ""),
                getattr(processo, "versao_obra", ""),
                getattr(processo, "versao_plano", ""),
            )
        except ValueError:
            continue
        versao = versoes.get(chave.bd_key)
        if not versao:
            continue
        etapa = str(versao.get("etapa") or "").strip().upper()
        if etapa not in ETAPAS_AVANCADAS:
            continue
        sugestoes.append(
            {
                "id": getattr(processo, "id", None),
                "codigo": str(getattr(processo, "codigo_processo", "") or "").strip(),
                "num_enc_phc": str(getattr(processo, "num_enc_phc", "") or "").strip(),
                "cliente": str(getattr(processo, "nome_cliente", "") or "").strip(),
                "estado_martelo": atual or "(sem estado)",
                "estado_sugerido": ESTADO_PRODUCAO,
                "estado_phc_raw": o_que_diz_o_escritorio(versao, fuso=fuso),
                "fonte": "Escritório",
                "responsavel": str(getattr(processo, "responsavel", "") or "").strip(),
                "data_entrega": str(getattr(processo, "data_entrega", "") or "").strip(),
                "ref_cliente": str(getattr(processo, "ref_cliente", "") or "").strip(),
                "bd_key": chave.bd_key,
                "marca": marca_sugestao(chave.bd_key, etapa),
            }
        )
    sugestoes.sort(key=lambda s: str(s["codigo"]).casefold())
    return sugestoes


#: Valor guardado para uma sugestão recusada de vez (desmarcada e confirmada).
VISTO_DE_VEZ = "sempre"


def por_mostrar(
    sugestoes: Iterable[Mapping[str, object]], vistos: Mapping[str, str], hoje: date
) -> list[Mapping[str, object]]:
    """Tira as que a pessoa já recusou e as que adiou para outro dia.

    ``vistos``: ``{marca: "sempre" | "aaaa-mm-dd"}``. «Ver depois» guarda o
    dia de hoje: volta a aparecer amanhã. Desmarcar e confirmar guarda
    «sempre»: só volta se a etapa mudar (a marca muda com ela).
    """
    resultado = []
    for sugestao in sugestoes:
        visto = vistos.get(str(sugestao.get("marca") or ""))
        if visto == VISTO_DE_VEZ or visto == hoje.isoformat():
            continue
        resultado.append(sugestao)
    return resultado
