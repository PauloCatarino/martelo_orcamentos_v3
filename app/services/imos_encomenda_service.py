"""Traduz uma obra da Produção numa encomenda do iMos.

Este serviço é a ponte entre o modelo do Martelo e as duas tabelas do iMos.
Faz duas coisas, deliberadamente separadas:

``preparar``
    Resolve o caminho ``LANCA_ENCANTO / ANO_XXXX / cliente / encomenda``,
    aplica o mapeamento de campos e devolve um plano com tudo o que vai ser
    criado, o que foi truncado e o que impede a criação. **Não escreve nada.**

``executar``
    Recebe esse plano e cria apenas o que falta, através de
    :mod:`app.services.imos_escrita`.

O plano é o que o diálogo mostra ao utilizador antes de confirmar: nada vai
para o iMos sem passar por ali.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.domain.datas import normalizar_data
from app.models.user import User
from app.models.cliente import Cliente
from app.services.imos_escrita import (
    COLUNAS_CONTACTO,
    COLUNAS_PROADMIN,
    NoCriado,
    NoParaCriar,
    criar_nos,
)
from app.services.imos_sql import (
    IMOS_DIR_ID_ORDER,
    IMOS_NOME_MAX,
    IMOS_TIPO_ENCOMENDA,
    IMOS_TIPO_PASTA,
    CaminhoImos,
    ImosConfig,
    caminho_do_no,
    carregar_pasta_raiz,
    nome_imos_valido,
    procurar_encomendas_por_nome,
    resolver_caminho_encomenda,
)
from app.services.producao_service import (
    _sanitize_nome_externo,  # a mesma normalização que gera os nomes externos
    gerar_nome_enc_imos_ix,
    gerar_nome_plano_cut_rite,
)

# MD5 de string vazia: é o que o iMos grava quando a encomenda ainda não tem
# especificação. Confirmado em 459 das 465 encomendas de 2026.
MD5_SEM_ESPECIFICACAO = "D41D8CD98F00B204E9800998ECF8427E"

# Colunas que o utilizador pode corrigir no diálogo antes de gravar. São as
# duas de texto livre: vêm da obra, mas muitas vezes estão vazias ou passam do
# que o iMos aceita. Editá-las aqui NÃO altera a obra no Martelo.
COLUNAS_EDITAVEIS = ("TEXT_SHORT", "TEXT_LONG")

# Valores constantes observados nas encomendas reais de 2026 do LANCA_ENCANTO.
CAMPOS_FIXOS_ENCOMENDA: dict[str, Any] = {
    "CNT": 1,
    "STATUS": 0,
    "REFSTAT": 0,
    "ORDERLOCK": 0,
    "EXPORTED": 0,
    "SOURCE": "IMOSADMIN",
    "CONTYPE": "STANDARD",
    "DESIGN": "FOLGAS_FRENTES_2022",
    "CMS_PROCESS": 0,
    "CMS_CALCULATION": 1,
    "CMS_PRICE": 0,
    "CMS_PRODUCTION": 0,
    "GLOBAL_SPEC_VERSION": MD5_SEM_ESPECIFICACAO,
    "DETAIL_SPEC_VERSION": MD5_SEM_ESPECIFICACAO,
}

# Uma pasta/projeto é bem mais simples: sem CONTYPE, DESIGN nem especificação.
CAMPOS_FIXOS_PASTA: dict[str, Any] = {
    "CNT": 1,
    "STATUS": 0,
    "REFSTAT": 0,
    "ORDERLOCK": 0,
    "EXPORTED": 0,
    "SOURCE": "IMOSADMIN",
    "CMS_PROCESS": 1,
    "CMS_CALCULATION": 0,
    "CMS_PRICE": 0,
    "CMS_PRODUCTION": 0,
}


@dataclass(frozen=True)
class CampoImos:
    """Um campo do Martelo já traduzido para uma coluna de dbo.PROADMIN."""

    coluna: str
    etiqueta: str
    origem: str
    valor: str
    valor_original: str
    limite: int

    @property
    def truncado(self) -> bool:
        return len(self.valor_original) > self.limite

    @property
    def vazio(self) -> bool:
        return not self.valor


@dataclass(frozen=True)
class PlanoCriacaoImos:
    """Tudo o que vai acontecer no iMos, para o utilizador confirmar."""

    caminho: CaminhoImos
    nome_encomenda: str
    nome_sugerido: str
    campos: tuple[CampoImos, ...]
    avisos: tuple[str, ...]
    bloqueios: tuple[str, ...]
    # Rasto de uma criação anterior desta obra, quando existe.
    ja_criada_em: datetime | None = None
    ja_criada_por: str = ""
    # Dados do cliente (dbo.CMSINCIDENTADRESS); vazio quando não há nada a gravar.
    contacto: tuple[CampoImos, ...] = ()

    @property
    def tem_contacto(self) -> bool:
        return any(not campo.vazio for campo in self.contacto)

    @property
    def pode_criar(self) -> bool:
        return not self.bloqueios

    @property
    def nome_truncado(self) -> bool:
        return len(self.nome_sugerido) > IMOS_NOME_MAX

    @property
    def campos_truncados(self) -> tuple[CampoImos, ...]:
        return tuple(campo for campo in self.campos if campo.truncado)

    @property
    def pastas_a_criar(self) -> tuple[str, ...]:
        return tuple(
            nivel.nome for nivel in self.caminho.pastas if not nivel.existe
        )


def _texto(valor) -> str:
    return str(valor or "").strip()


def _data_imos(valor) -> str:
    """O Martelo guarda ``dd-mm-aaaa``; o iMos usa ``dd/mm/aaaa``."""
    normalizada = normalizar_data(valor)
    return normalizada.replace("-", "/") if normalizada else ""


def _campo(
    coluna: str,
    etiqueta: str,
    origem: str,
    valor,
    *,
    colunas: dict[str, tuple[str, int]] | None = None,
) -> CampoImos:
    """Trunca o valor no limite real da coluna, guardando o original."""
    _, limite = (colunas or COLUNAS_PROADMIN)[coluna]
    original = _texto(valor).replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    original = " ".join(original.split())
    return CampoImos(
        coluna=coluna,
        etiqueta=etiqueta,
        origem=origem,
        valor=original[:limite],
        valor_original=original,
        limite=limite,
    )


def nome_pasta_cliente(processo) -> str:
    """Nome da pasta do cliente: sempre o cliente simplex, normalizado."""
    simplex = _texto(getattr(processo, "nome_cliente_simplex", ""))
    if not simplex:
        return ""
    return _sanitize_nome_externo(simplex)[:IMOS_NOME_MAX]


def nome_encomenda_sugerido(processo) -> str:
    """Nome iMos da obra, ainda sem truncar (para se poder avisar do corte)."""
    return gerar_nome_enc_imos_ix(
        getattr(processo, "ano", ""),
        getattr(processo, "num_enc_phc", ""),
        getattr(processo, "versao_obra", ""),
        nome_cliente_simplex=getattr(processo, "nome_cliente_simplex", None),
        nome_cliente=getattr(processo, "nome_cliente", None),
        ref_cliente=getattr(processo, "ref_cliente", None),
    )


def mapear_campos(
    processo,
    *,
    nome_encomenda: str,
    textos: Mapping[str, str] | None = None,
) -> tuple[CampoImos, ...]:
    """Mapeamento acordado com o utilizador entre a obra e dbo.PROADMIN.

    ``textos`` substitui as colunas de :data:`COLUNAS_EDITAVEIS` pelo que o
    utilizador escreveu no diálogo. A obra no Martelo fica intacta: a correção
    vale só para esta criação.
    """
    editados = {
        str(coluna).upper(): valor
        for coluna, valor in (textos or {}).items()
        if str(coluna).upper() in COLUNAS_EDITAVEIS
    }

    def _texto_livre(coluna: str, etiqueta: str, origem: str, valor) -> CampoImos:
        if coluna in editados:
            return _campo(coluna, etiqueta, "Editado aqui", editados[coluna])
        return _campo(coluna, etiqueta, origem, valor)

    nome_plano = gerar_nome_plano_cut_rite(
        getattr(processo, "ano", ""),
        getattr(processo, "num_enc_phc", ""),
        getattr(processo, "versao_obra", ""),
        getattr(processo, "versao_plano", ""),
        nome_cliente_simplex=getattr(processo, "nome_cliente_simplex", None),
        nome_cliente=getattr(processo, "nome_cliente", None),
        ref_cliente=getattr(processo, "ref_cliente", None),
    )
    return (
        _campo("PROGRAM", "Nome Enc IMOS IX", "Nome Enc IMOS IX", nome_encomenda),
        _campo("COMM", "Nº Enc PHC", "Nº Enc PHC", getattr(processo, "num_enc_phc", "")),
        _campo(
            "ARTICLENO", "Ref. Cliente", "Ref Cliente", getattr(processo, "ref_cliente", "")
        ),
        _campo(
            "CLIENT",
            "Cliente simplex",
            "Cliente simplex",
            getattr(processo, "nome_cliente_simplex", ""),
        ),
        _campo(
            "EMPLOYEE", "Responsável", "Responsável", getattr(processo, "responsavel", "")
        ),
        _texto_livre(
            "TEXT_SHORT",
            "Descrição produção",
            "Descrição produção",
            getattr(processo, "descricao_producao", ""),
        ),
        _texto_livre(
            "TEXT_LONG",
            "Matérias usados",
            "Matérias usados",
            getattr(processo, "materias_usados", ""),
        ),
        _campo(
            "DELIVERY_DATE",
            "Data entrega",
            "Data Entrega",
            _data_imos(getattr(processo, "data_entrega", "")),
        ),
        _campo(
            "STARTDATE",
            "Data início",
            "Data Início",
            _data_imos(getattr(processo, "data_inicio", "")),
        ),
        _campo("INFO1", "Nome Plano CUT-RITE", "Nome Plano CUT-RITE", nome_plano),
    )


def mapear_contacto(processo, cliente: Cliente | None) -> tuple[CampoImos, ...]:
    """Dados do cliente da encomenda (dbo.CMSINCIDENTADRESS).

    ``FIRMA`` e ``KDNR`` saem da própria obra; o telefone e o email só existem
    na ficha do cliente, por isso ficam vazios quando a obra não tem cliente
    associado.
    """

    def _contacto(coluna: str, etiqueta: str, origem: str, valor) -> CampoImos:
        return _campo(coluna, etiqueta, origem, valor, colunas=COLUNAS_CONTACTO)

    return (
        _contacto(
            "FIRMA", "Cliente", "Cliente", getattr(processo, "nome_cliente", "")
        ),
        _contacto(
            "KDNR",
            "Nº Cliente PHC",
            "Nº Cliente PHC",
            getattr(processo, "num_cliente_phc", ""),
        ),
        _contacto(
            "MOBILE",
            "Telefone",
            "Ficha do cliente",
            getattr(cliente, "telefone", "") if cliente else "",
        ),
        _contacto(
            "EMAIL1",
            "Email",
            "Ficha do cliente",
            getattr(cliente, "email", "") if cliente else "",
        ),
    )


def _cliente_da_obra(session: Session, processo) -> Cliente | None:
    """Ficha do cliente da obra, quando existe ligação."""
    cliente_id = getattr(processo, "cliente_id", None)
    if not cliente_id:
        return None
    return session.get(Cliente, cliente_id)


def preparar(
    session: Session,
    cfg: ImosConfig,
    processo,
    *,
    nome_encomenda: str | None = None,
    pasta_ano: str | None = None,
    textos: Mapping[str, str] | None = None,
) -> PlanoCriacaoImos:
    """Monta o plano de criação sem escrever nada no iMos.

    ``nome_encomenda`` e ``textos`` permitem refazer o plano com o que o
    utilizador corrigiu no diálogo, mantendo tudo o resto igual e sem alterar a
    obra no Martelo. ``pasta_ano`` desvia a criação para outra pasta que não a
    do ano da obra (usado em testes controlados).
    """
    pasta_raiz = carregar_pasta_raiz(session)
    sugerido = nome_encomenda_sugerido(processo)
    nome = _texto(nome_encomenda) if nome_encomenda is not None else sugerido[:IMOS_NOME_MAX]
    cliente = nome_pasta_cliente(processo)

    bloqueios: list[str] = []
    avisos: list[str] = []

    if not cliente:
        bloqueios.append(
            "A obra não tem Cliente simplex preenchido, e é esse o nome da pasta "
            "do cliente no iMos."
        )
    if not sugerido:
        bloqueios.append(
            "Não foi possível construir o nome da encomenda: confirme o Ano e o "
            "Nº Enc PHC da obra."
        )
    if nome and not nome_imos_valido(nome):
        bloqueios.append(
            f"O nome '{nome}' não é aceite pelo iMos: até {IMOS_NOME_MAX} "
            "caracteres em letras, algarismos, espaço e _ ( ) . -"
        )

    if bloqueios:
        # Sem nome ou sem cliente não vale a pena ir ao SQL resolver o caminho.
        return PlanoCriacaoImos(
            caminho=CaminhoImos(niveis=()),
            nome_encomenda=nome,
            nome_sugerido=sugerido,
            campos=(),
            avisos=(),
            bloqueios=tuple(bloqueios),
        )

    caminho = resolver_caminho_encomenda(
        cfg,
        ano=getattr(processo, "ano", ""),
        cliente_simplex=cliente,
        nome_encomenda=nome,
        pasta_raiz=pasta_raiz,
        pasta_ano=pasta_ano,
    )

    if pasta_ano:
        avisos.append(
            f"A encomenda vai para '{pasta_ano}' e não para a pasta do ano da obra."
        )

    if not caminho.niveis[0].existe:
        bloqueios.append(
            f"A pasta raiz '{pasta_raiz}' não existe no iMos. O Martelo não a "
            "cria: confirme a definição imos_pasta_raiz."
        )
    if caminho.encomenda_ja_existe:
        bloqueios.append(
            f"Já existe uma encomenda '{nome}' nesta pasta do iMos. "
            "O Martelo não duplica nem substitui encomendas."
        )
    else:
        # O nome tem de ser único em TODA a árvore, não só nesta pasta: os
        # dados do cliente são guardados por nome de encomenda, sem pasta.
        for outro in procurar_encomendas_por_nome(cfg, nome):
            onde = caminho_do_no(cfg, outro.dir_id) or "outra pasta"
            bloqueios.append(
                f"Já existe uma encomenda com o nome '{nome}' noutro sítio do "
                f"iMos: {onde}. Como os dados do cliente são guardados só pelo "
                "nome da encomenda, dois nomes iguais misturavam-nos. "
                "Altere o nome antes de criar."
            )

    # Rasto de uma criação anterior: é o que evita criar duas vezes por
    # engano, sem obrigar ninguém a ir ao iX Organizer confirmar.
    criada_em = getattr(processo, "imos_criado_em", None)
    criada_por = ""
    if criada_em:
        autor_id = getattr(processo, "imos_criado_por_id", None)
        autor = session.get(User, autor_id) if autor_id else None
        criada_por = getattr(autor, "nome", "") or getattr(autor, "username", "") or ""
        anterior = getattr(processo, "imos_nome_encomenda", "") or nome
        quem = f" por {criada_por}" if criada_por else ""
        avisos.append(
            f"Esta obra já criou a encomenda '{anterior}' no iMos em "
            f"{criada_em.strftime('%d-%m-%Y %H:%M')}{quem}. Confirme que não "
            "está a criar a mesma coisa outra vez."
        )

    campos = mapear_campos(processo, nome_encomenda=nome, textos=textos)
    cliente = _cliente_da_obra(session, processo)
    contacto = mapear_contacto(processo, cliente)

    if cliente is None:
        avisos.append(
            "A obra não está ligada a uma ficha de cliente, por isso o telefone "
            "e o email não vão para o iMos."
        )

    if len(sugerido) > IMOS_NOME_MAX:
        avisos.append(
            f"O nome sugerido tem {len(sugerido)} caracteres e o iMos só aceita "
            f"{IMOS_NOME_MAX}. Foi cortado — reveja-o antes de criar."
        )
    for campo in campos + contacto:
        if campo.truncado:
            avisos.append(
                f"{campo.etiqueta}: {len(campo.valor_original)} caracteres cortados "
                f"para {campo.limite} (coluna {campo.coluna} do iMos)."
            )
    pastas_novas = [nivel.nome for nivel in caminho.pastas if not nivel.existe]
    if pastas_novas:
        avisos.append("Vão ser criadas as pastas: " + ", ".join(pastas_novas) + ".")

    return PlanoCriacaoImos(
        caminho=caminho,
        nome_encomenda=nome,
        nome_sugerido=sugerido,
        campos=campos,
        avisos=tuple(avisos),
        bloqueios=tuple(bloqueios),
        contacto=contacto,
        ja_criada_em=criada_em,
        ja_criada_por=criada_por,
    )


def nos_para_criar(plano: PlanoCriacaoImos) -> list[NoParaCriar]:
    """Converte o plano na lista de nós, encadeando as pastas em falta.

    A primeira pasta em falta pendura-se na última que já existe; as seguintes
    apontam para a anterior pelo índice, porque só ganham DIR_ID durante a
    própria transação.
    """
    if not plano.pode_criar:
        raise RuntimeError(
            "Este plano não pode ser executado: " + " ".join(plano.bloqueios)
        )

    nos: list[NoParaCriar] = []
    ultimo_dir_id: int | None = IMOS_DIR_ID_ORDER
    ultimo_indice: int | None = None

    for nivel in plano.caminho.pastas:
        if nivel.existe:
            ultimo_dir_id = nivel.dir_id
            ultimo_indice = None
            continue
        nos.append(
            NoParaCriar(
                nome=nivel.nome,
                tipo=IMOS_TIPO_PASTA,
                parent_dir_id=ultimo_dir_id if ultimo_indice is None else None,
                parent_indice=ultimo_indice,
                campos=dict(CAMPOS_FIXOS_PASTA),
            )
        )
        ultimo_indice = len(nos) - 1
        ultimo_dir_id = None

    campos_encomenda: dict[str, Any] = dict(CAMPOS_FIXOS_ENCOMENDA)
    for campo in plano.campos:
        campos_encomenda[campo.coluna] = campo.valor

    nos.append(
        NoParaCriar(
            nome=plano.nome_encomenda,
            tipo=IMOS_TIPO_ENCOMENDA,
            parent_dir_id=ultimo_dir_id if ultimo_indice is None else None,
            parent_indice=ultimo_indice,
            campos=campos_encomenda,
            contacto={campo.coluna: campo.valor for campo in plano.contacto},
        )
    )
    return nos


def executar(
    session: Session,
    cfg: ImosConfig,
    plano: PlanoCriacaoImos,
    *,
    processo=None,
    user_id: int | None = None,
) -> list[NoCriado]:
    """Cria no iMos as pastas em falta e a encomenda, na mesma transação.

    Com ``processo``, guarda na obra o rasto do que foi criado. O rasto é
    gravado **depois** de o iMos confirmar: se a criação falhar, a obra fica
    como estava.
    """
    criados = criar_nos(session, cfg, nos_para_criar(plano))
    if processo is None:
        return criados

    encomenda = next(
        (no for no in criados if no.tipo == IMOS_TIPO_ENCOMENDA), None
    )
    if encomenda is not None:
        processo.imos_nome_encomenda = encomenda.nome
        processo.imos_dir_id = encomenda.dir_id
        processo.imos_criado_em = datetime.now()
        processo.imos_criado_por_id = user_id
        session.commit()

    return criados
