"""Checks and operational steps that prepare one obra for production.

Porte da ideia do "Preparação" do Martelo V2: validar, numa só janela, o que
já está feito na pasta da obra (PDFs, Caderno de Encargos, programas CNC) e
deixar executar os passos que faltam. As validações de ficheiros são
escolhidas por utilizador — cada um marca as que quer ver; as dos programas
CNC são sempre obrigatórias.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import shutil
import tempfile
from typing import Iterable, Optional, Sequence

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.services.pdf_imagem_service import documento_pdf
from app.services.system_setting_service import SystemSettingService


logger = logging.getLogger(__name__)


#: Caminhos configuráveis em Configurações → Caminhos do Sistema (grupo CNC).
KEY_PASTA_ORIGEM_CNC = "pasta_origem_programas_cnc"
KEY_PASTA_DESTINO_CNC = "pasta_destino_programas_cnc"
DEFAULT_PASTA_ORIGEM_CNC = r"\\SERVER_LE\Homag_iX\_ProgramasCNC"
DEFAULT_PASTA_DESTINO_CNC = r"\\SERVER_LE\_Lanca_Encanto\Operador\FICHEIROS_MPR"

CONJ_PDF_NOME = "CONJ.pdf"
PROJETO_PRODUCAO_PDF_NOME = "2_Projeto_Producao.pdf"

ESTADO_OK = "ok"
ESTADO_PENDENTE = "pendente"
ESTADO_DESATUALIZADO = "desatualizado"
ESTADO_BLOQUEADO = "bloqueado"

ACAO_GERAR_PROJETO_PDF = "gerar_projeto_pdf"
ACAO_COPIAR_PROGRAMAS_OBRA = "copiar_programas_obra"
ACAO_ENVIAR_PROGRAMAS_CNC = "enviar_programas_cnc"

#: Páginas do CONJ.pdf aproveitadas para o 2_Projeto_Producao.pdf.
MAX_PAGINAS_PROJETO_PDF = 2


@dataclass(frozen=True)
class ValidacaoFicheiro:
    """One configurable file check inside the obra folder."""

    key: str
    label: str
    padrao: str
    padroes_origem: tuple[str, ...] = ()
    descricao: str = ""


VALIDACOES_FICHEIROS: tuple[ValidacaoFicheiro, ...] = (
    ValidacaoFicheiro(
        key="caderno_encargos",
        label="Caderno de Encargos (*.xlsm)",
        padrao="Caderno de Encargos_*.xlsm",
        descricao="Valida se existe o Excel Caderno de Encargos na pasta da obra.",
    ),
    ValidacaoFicheiro(
        key="lista_material_pdf",
        label="Lista_Material_*.pdf",
        padrao="Lista_Material_*.pdf",
        padroes_origem=("Lista_Material_*.xlsm", "Lista_Material_*.xlsx"),
        descricao="Valida se existe na pasta da obra o PDF da Lista de Material.",
    ),
    ValidacaoFicheiro(
        key="ferragens_a4_pdf",
        label="1_List_FerragensA4.pdf",
        padrao="1_List_FerragensA4.pdf",
        padroes_origem=("1_List_Ferragens.xlsx", "1_List_Ferragens.xlsm"),
        descricao="Valida se existe o PDF das ferragens na pasta da obra.",
    ),
    ValidacaoFicheiro(
        key="projeto_pdf",
        label=PROJETO_PRODUCAO_PDF_NOME,
        padrao=PROJETO_PRODUCAO_PDF_NOME,
        padroes_origem=(CONJ_PDF_NOME,),
        descricao=(
            "Valida se o 2_Projeto_Producao.pdf foi gerado a partir do CONJ.pdf "
            "em A4 horizontal."
        ),
    ),
    ValidacaoFicheiro(
        key="resumo_geral_pdf",
        label="3_Resumo_Geral_Encomenda.pdf",
        padrao="3_Resumo_Geral_Encomenda.pdf",
        padroes_origem=(
            "3_Resumo_Geral_Encomenda.xlsx",
            "3_Resumo_Geral_Encomenda.xlsm",
        ),
        descricao="Valida se existe o PDF do resumo geral da encomenda.",
    ),
    ValidacaoFicheiro(
        key="etiqueta_palete_pdf",
        label="5_Etiqueta_Palete.pdf",
        padrao="5_Etiqueta_Palete.pdf",
        padroes_origem=(
            "5_Etiqueta_Palete_PDF.xlsx",
            "5_Etiqueta_Palete.xlsx",
            "5_Etiqueta_Palete.xlsm",
        ),
        descricao="Valida se existe o PDF da etiqueta de palete.",
    ),
    ValidacaoFicheiro(
        key="resumo_ml_orlas_pdf",
        label="6_Resumo_ML_OrlasA4.pdf",
        padrao="6_Resumo_ML_OrlasA4.pdf",
        padroes_origem=(
            "6_Resumo_ML_OrlasA4.xlsx",
            "6_Resumo_ML_OrlasA4.xlsm",
            "6_List_Ferragens_Integrador.xlsx",
            "6_List_Ferragens_Integrador.xlsm",
        ),
        descricao="Valida se existe o PDF do resumo de ML de orlas.",
    ),
    ValidacaoFicheiro(
        key="cutrite_pdf",
        label="Plano CUT-RITE (*.pdf)",
        padrao="",
        descricao=(
            "Valida se o PDF do plano de corte já está na pasta da obra, com o "
            "nome do campo 'Nome Plano CUT-RITE'. Exporte-o no botão CUT-RITE → "
            "Exportar PDF CUT-RITE."
        ),
    ),
    ValidacaoFicheiro(
        key="conj_pdf",
        label=CONJ_PDF_NOME,
        padrao=CONJ_PDF_NOME,
        descricao="Valida se existe o CONJ.pdf (desenho de conjunto) na pasta da obra.",
    ),
)

KEYS_FICHEIROS = tuple(validacao.key for validacao in VALIDACOES_FICHEIROS)

#: Validações dos programas CNC: sempre visíveis e sempre obrigatórias.
KEYS_SEMPRE_OBRIGATORIAS = ("cnc_origem", "cnc_obra", "cnc_pasta_anual", "cnc_enviado")

DESCRICOES_CNC = {
    "cnc_origem": (
        "Valida se a pasta de programas CNC existe na origem IMOS e mostra "
        "quantos ficheiros tem."
    ),
    "cnc_obra": (
        "Valida se os programas CNC já foram copiados para a pasta da obra e "
        "se estão atualizados face à origem IMOS."
    ),
    "cnc_pasta_anual": (
        "Valida se a pasta anual de destino dos programas CNC está disponível "
        "na rede."
    ),
    "cnc_enviado": (
        "Valida se os programas CNC da obra já foram enviados para as máquinas "
        "e se estão atualizados face à pasta da obra."
    ),
}

DESCRICAO_OBRA_PRONTA = (
    "Resumo final: a obra fica pronta quando todas as validações obrigatórias "
    "estiverem OK."
)


@dataclass(frozen=True)
class PreparacaoContexto:
    """Everything the preparation panel needs to resolve one obra."""

    codigo_processo: str
    pasta_obra: Path
    nome_enc_imos: str
    nome_plano_cut_rite: str
    pasta_origem_cnc: Path
    pasta_origem_cnc_obra: Path
    pasta_programas_obra: Path
    pasta_destino_cnc: Path
    pasta_destino_cnc_ano: Path
    pasta_destino_cnc_obra: Path
    conj_pdf: Path
    projeto_pdf: Path


@dataclass(frozen=True)
class PreparacaoEstado:
    """State of one validation line shown in the preparation panel."""

    key: str
    label: str
    estado: str
    detalhe: str
    obrigatorio: bool = True
    descricao: str = ""
    acao: str = ""
    acao_label: str = ""

    @property
    def ok(self) -> bool:
        return self.estado == ESTADO_OK


@dataclass(frozen=True)
class SupervisaoProducao:
    """What the supervisor found when the obra was moving into production."""

    validou: bool
    motivo: str = ""
    estados: tuple[PreparacaoEstado, ...] = ()
    pendencias: tuple[PreparacaoEstado, ...] = ()

    @property
    def pronta(self) -> bool:
        """True when everything this user requires is already OK."""
        return self.validou and not self.pendencias


@dataclass(frozen=True)
class _Instantaneo:
    """Snapshot (file count + newest change) of one folder tree."""

    ficheiros: int
    ultima_alteracao: float

    @property
    def tem_ficheiros(self) -> bool:
        return self.ficheiros > 0


def chave_validacoes_utilizador(user_id: object) -> str:
    """Return the per-user system-setting key for the chosen validations."""
    return f"producao_preparacao_validacoes:{user_id or 'default'}"


def listar_validacoes_configuraveis() -> list[dict[str, str]]:
    """List the file validations each user can turn on or off."""
    return [
        {"key": validacao.key, "label": validacao.label}
        for validacao in VALIDACOES_FICHEIROS
    ]


def obter_validacoes_utilizador(session: Session, user_id: object) -> set[str]:
    """Return the file validations chosen by one user (all, by default)."""
    valor = SystemSettingService(session).obter_valor(
        chave_validacoes_utilizador(user_id), None
    )
    if not valor:
        return set(KEYS_FICHEIROS)

    try:
        guardadas = json.loads(valor)
    except (TypeError, ValueError):
        logger.warning("Preferências de Preparação ilegíveis para user_id=%s", user_id)
        return set(KEYS_FICHEIROS)

    if not isinstance(guardadas, list):
        return set(KEYS_FICHEIROS)
    return {str(key).strip() for key in guardadas if str(key).strip() in KEYS_FICHEIROS}


def guardar_validacoes_utilizador(
    session: Session, user_id: object, keys: Iterable[str]
) -> None:
    """Save the file validations chosen by one user."""
    limpas = sorted(
        {str(key).strip() for key in keys if str(key).strip() in KEYS_FICHEIROS}
    )
    SystemSettingService(session).guardar_valor(
        chave_validacoes_utilizador(user_id),
        json.dumps(limpas, ensure_ascii=False),
    )


def chave_email_projeto_utilizador(user_id: object) -> str:
    """Chave do 'avisar o cliente' de cada utilizador (é escolha pessoal)."""
    return f"producao_email_projeto:{user_id or 'default'}"


def obter_email_projeto_ativo(session: Session, user_id: object) -> bool:
    """True quando este utilizador quer preparar o email ao passar a Produção.

    Desligado por defeito: nem todos falam com o cliente, e ninguém deve ser
    surpreendido por uma janela de email que não pediu.
    """
    valor = SystemSettingService(session).obter_valor(
        chave_email_projeto_utilizador(user_id), ""
    )
    return str(valor or "").strip().upper() in {"ON", "1", "TRUE", "SIM"}


def guardar_email_projeto_ativo(
    session: Session, user_id: object, ativo: bool
) -> None:
    """Guardar a escolha deste utilizador."""
    SystemSettingService(session).guardar_valor(
        chave_email_projeto_utilizador(user_id), "ON" if ativo else "OFF"
    )


def obter_keys_obrigatorias(session: Session, user_id: object) -> set[str]:
    """Return every validation key required for this user."""
    keys = set(obter_validacoes_utilizador(session, user_id))
    keys.update(KEYS_SEMPRE_OBRIGATORIAS)
    return keys


def resolver_contexto(
    session: Session,
    *,
    codigo_processo: str,
    pasta_obra: str | Path,
    nome_enc_imos: str,
    nome_plano_cut_rite: str = "",
) -> PreparacaoContexto:
    """Build the preparation context for one obra version."""
    pasta_texto = str(pasta_obra or "").strip()
    if not pasta_texto:
        raise ValueError("Pasta da obra em falta no processo.")

    nome_enc = str(nome_enc_imos or "").strip()
    if not nome_enc:
        raise ValueError("Nome Enc IMOS IX em falta no processo.")

    settings = SystemSettingService(session)
    origem_cnc = Path(
        settings.obter_valor(KEY_PASTA_ORIGEM_CNC, "") or DEFAULT_PASTA_ORIGEM_CNC
    )
    destino_cnc = Path(
        settings.obter_valor(KEY_PASTA_DESTINO_CNC, "") or DEFAULT_PASTA_DESTINO_CNC
    )
    pasta = Path(pasta_texto)
    pasta_ano = destino_cnc / f"{datetime.now().year}_MPR"

    return PreparacaoContexto(
        codigo_processo=str(codigo_processo or "").strip(),
        pasta_obra=pasta,
        nome_enc_imos=nome_enc,
        nome_plano_cut_rite=str(nome_plano_cut_rite or "").strip(),
        pasta_origem_cnc=origem_cnc,
        pasta_origem_cnc_obra=origem_cnc / nome_enc,
        pasta_programas_obra=pasta / nome_enc,
        pasta_destino_cnc=destino_cnc,
        pasta_destino_cnc_ano=pasta_ano,
        pasta_destino_cnc_obra=pasta_ano / nome_enc,
        conj_pdf=pasta / CONJ_PDF_NOME,
        projeto_pdf=pasta / PROJETO_PRODUCAO_PDF_NOME,
    )


def recolher_estados(
    contexto: PreparacaoContexto,
    *,
    keys_obrigatorias: Optional[set[str]] = None,
) -> list[PreparacaoEstado]:
    """Check the obra folder and return one state per validation."""
    obrigatorias = set(
        keys_obrigatorias or set(KEYS_FICHEIROS) | set(KEYS_SEMPRE_OBRIGATORIAS)
    )
    estados = [
        _estado_ficheiro(contexto, validacao)
        for validacao in VALIDACOES_FICHEIROS
        if validacao.key in obrigatorias
    ]
    estados.extend(_estados_cnc(contexto, obrigatorias))
    estados.append(_estado_obra_pronta(estados, obrigatorias))
    return estados


def pendencias_estados(
    estados: Sequence[PreparacaoEstado],
) -> list[PreparacaoEstado]:
    """Return the required validations still not OK (the resumo line apart)."""
    return [
        estado
        for estado in estados
        if estado.key != "obra_pronta" and estado.obrigatorio and not estado.ok
    ]


def pendencias_obrigatorias(estados: Sequence[PreparacaoEstado]) -> list[str]:
    """Return the labels of the required validations still not OK."""
    return [estado.label for estado in pendencias_estados(estados)]


def supervisionar_para_producao(
    session: Session,
    *,
    codigo_processo: str,
    pasta_obra: str | Path,
    nome_enc_imos: str,
    nome_plano_cut_rite: str = "",
    user_id: object,
) -> SupervisaoProducao:
    """Check one obra against this user's preparation rules, before Produção.

    É o que o supervisor faz por trás do aviso de mudança de estado: usa
    exatamente as validações que **este** utilizador escolheu nas Preferências
    da Preparação (mais as do CNC, sempre obrigatórias). Nunca rebenta — quando
    não consegue validar (falta a pasta da obra ou o Nome Enc IMOS), devolve o
    motivo para o utilizador decidir com conhecimento de causa.
    """
    try:
        obrigatorias = obter_keys_obrigatorias(session, user_id)
        contexto = resolver_contexto(
            session,
            codigo_processo=codigo_processo,
            pasta_obra=pasta_obra,
            nome_enc_imos=nome_enc_imos,
            nome_plano_cut_rite=nome_plano_cut_rite,
        )
        estados = recolher_estados(contexto, keys_obrigatorias=obrigatorias)
    except (ValueError, OSError, SQLAlchemyError) as erro:
        logger.info("Supervisão da mudança para Produção não validou: %s", erro)
        return SupervisaoProducao(validou=False, motivo=str(erro))

    return SupervisaoProducao(
        validou=True,
        estados=tuple(estados),
        pendencias=tuple(pendencias_estados(estados)),
    )


def gerar_projeto_producao_pdf(contexto: PreparacaoContexto) -> Path:
    """Build 2_Projeto_Producao.pdf (A4 landscape) from the CONJ.pdf."""
    if not contexto.conj_pdf.exists():
        raise ValueError(f"CONJ.pdf em falta:\n{contexto.conj_pdf}")

    try:
        _gerar_projeto_pdf_vetorial(
            contexto.conj_pdf,
            contexto.projeto_pdf,
            max_paginas=MAX_PAGINAS_PROJETO_PDF,
        )
    except Exception as exc:  # pragma: no cover - depende do PDF de origem
        # PDFs que o pypdf não consegue transformar ainda saem como imagem.
        logger.warning("2_Projeto_Producao.pdf gerado por imagem: %s", exc)
        imagens = _imagens_do_conj(contexto.conj_pdf, MAX_PAGINAS_PROJETO_PDF)
        _imagens_para_pdf_a4(imagens, contexto.projeto_pdf)
    return contexto.projeto_pdf


def copiar_programas_para_obra(contexto: PreparacaoContexto) -> Path:
    """Copy the CNC programs from the IMOS source into the obra folder."""
    if not contexto.pasta_origem_cnc_obra.exists():
        raise ValueError(
            f"Pasta de origem IMOS em falta:\n{contexto.pasta_origem_cnc_obra}"
        )
    _substituir_pasta(contexto.pasta_origem_cnc_obra, contexto.pasta_programas_obra)
    return contexto.pasta_programas_obra


def enviar_programas_para_cnc(contexto: PreparacaoContexto) -> Path:
    """Send the obra CNC programs to the yearly machine folder."""
    if not contexto.pasta_programas_obra.exists():
        raise ValueError(
            f"Pasta de programas na obra em falta:\n{contexto.pasta_programas_obra}"
        )
    contexto.pasta_destino_cnc_ano.mkdir(parents=True, exist_ok=True)
    _substituir_pasta(contexto.pasta_programas_obra, contexto.pasta_destino_cnc_obra)
    return contexto.pasta_destino_cnc_obra


def _estado_ficheiro(
    contexto: PreparacaoContexto, validacao: ValidacaoFicheiro
) -> PreparacaoEstado:
    if validacao.key == "projeto_pdf":
        acao, acao_label = ACAO_GERAR_PROJETO_PDF, "Gerar"
    else:
        acao, acao_label = "", ""

    if validacao.key == "cutrite_pdf" and not contexto.nome_plano_cut_rite:
        return PreparacaoEstado(
            key=validacao.key,
            label=validacao.label,
            estado=ESTADO_BLOQUEADO,
            detalhe="Nome Plano CUT-RITE em falta no processo.",
            descricao=validacao.descricao,
        )

    caminho = _caminho_da_validacao(contexto, validacao)
    origens = _origens_da_validacao(contexto, validacao)

    if caminho is None or not caminho.exists():
        detalhe = _detalhe_em_falta(contexto, validacao)
        if origens:
            detalhe += "\nOrigem detetada: " + ", ".join(
                str(origem) for origem in origens[:3]
            )
        return PreparacaoEstado(
            key=validacao.key,
            label=validacao.label,
            estado=ESTADO_PENDENTE,
            detalhe=detalhe,
            descricao=validacao.descricao,
            acao=acao,
            acao_label=acao_label,
        )

    origem_mais_nova = _mais_recente(origens)
    if (
        origem_mais_nova is not None
        and _mtime(origem_mais_nova) > _mtime(caminho) + 1
        and validacao.key != "lista_material_pdf"
    ):
        return PreparacaoEstado(
            key=validacao.key,
            label=validacao.label,
            estado=ESTADO_DESATUALIZADO,
            detalhe=(
                f"{caminho}\nDesatualizado face a {origem_mais_nova.name} "
                f"({_data_hora(_mtime(origem_mais_nova))} > "
                f"{_data_hora(_mtime(caminho))})"
            ),
            descricao=validacao.descricao,
            acao=acao,
            acao_label=acao_label,
        )

    return PreparacaoEstado(
        key=validacao.key,
        label=validacao.label,
        estado=ESTADO_OK,
        detalhe=str(caminho),
        descricao=validacao.descricao,
        acao=acao,
        acao_label=acao_label,
    )


def _estados_cnc(
    contexto: PreparacaoContexto, obrigatorias: set[str]
) -> list[PreparacaoEstado]:
    origem = _instantaneo(contexto.pasta_origem_cnc_obra)
    obra = _instantaneo(contexto.pasta_programas_obra)
    maquinas = _instantaneo(contexto.pasta_destino_cnc_obra)

    estados = [
        PreparacaoEstado(
            key="cnc_origem",
            label="Programas CNC na origem IMOS",
            estado=ESTADO_OK if origem is not None else ESTADO_PENDENTE,
            detalhe=(
                _detalhe_pasta(contexto.pasta_origem_cnc_obra, origem)
                if origem is not None
                else f"{contexto.pasta_origem_cnc_obra} (em falta)"
            ),
            obrigatorio="cnc_origem" in obrigatorias,
            descricao=DESCRICOES_CNC["cnc_origem"],
        )
    ]

    if origem is None:
        estado_obra = ESTADO_BLOQUEADO
        detalhe_obra = f"Origem IMOS em falta:\n{contexto.pasta_origem_cnc_obra}"
    elif obra is None:
        estado_obra = ESTADO_PENDENTE
        detalhe_obra = (
            f"{contexto.pasta_programas_obra} (em falta)\n"
            "Origem encontrada mas ainda não copiada para a obra."
        )
    elif _esta_desatualizada(obra, origem):
        estado_obra = ESTADO_DESATUALIZADO
        detalhe_obra = (
            f"{_detalhe_pasta(contexto.pasta_programas_obra, obra)}\n"
            f"Desatualizada face a {contexto.pasta_origem_cnc_obra}"
        )
    else:
        estado_obra = ESTADO_OK
        detalhe_obra = _detalhe_pasta(contexto.pasta_programas_obra, obra)

    estados.append(
        PreparacaoEstado(
            key="cnc_obra",
            label="Programas CNC copiados para a obra",
            estado=estado_obra,
            detalhe=detalhe_obra,
            obrigatorio="cnc_obra" in obrigatorias,
            descricao=DESCRICOES_CNC["cnc_obra"],
            acao=ACAO_COPIAR_PROGRAMAS_OBRA,
            acao_label="Copiar",
        )
    )

    ano_ok = contexto.pasta_destino_cnc_ano.exists()
    estados.append(
        PreparacaoEstado(
            key="cnc_pasta_anual",
            label="Pasta anual dos programas CNC disponível",
            estado=ESTADO_OK if ano_ok else ESTADO_PENDENTE,
            detalhe=(
                str(contexto.pasta_destino_cnc_ano)
                if ano_ok
                else f"{contexto.pasta_destino_cnc_ano} (em falta)"
            ),
            obrigatorio="cnc_pasta_anual" in obrigatorias,
            descricao=DESCRICOES_CNC["cnc_pasta_anual"],
        )
    )

    if not ano_ok:
        estado_envio = ESTADO_BLOQUEADO
        detalhe_envio = f"Pasta anual em falta:\n{contexto.pasta_destino_cnc_ano}"
    elif obra is None:
        estado_envio = ESTADO_BLOQUEADO
        detalhe_envio = (
            f"Pasta de programas na obra em falta:\n{contexto.pasta_programas_obra}"
        )
    elif maquinas is None:
        estado_envio = ESTADO_PENDENTE
        detalhe_envio = (
            f"{contexto.pasta_destino_cnc_obra} (em falta)\n"
            "Programas na obra mas ainda não enviados para as máquinas."
        )
    elif _esta_desatualizada(maquinas, obra):
        estado_envio = ESTADO_DESATUALIZADO
        detalhe_envio = (
            f"{_detalhe_pasta(contexto.pasta_destino_cnc_obra, maquinas)}\n"
            f"Desatualizada face a {contexto.pasta_programas_obra}"
        )
    else:
        estado_envio = ESTADO_OK
        detalhe_envio = _detalhe_pasta(contexto.pasta_destino_cnc_obra, maquinas)

    estados.append(
        PreparacaoEstado(
            key="cnc_enviado",
            label="Programas CNC enviados para as máquinas",
            estado=estado_envio,
            detalhe=detalhe_envio,
            obrigatorio="cnc_enviado" in obrigatorias,
            descricao=DESCRICOES_CNC["cnc_enviado"],
            acao=ACAO_ENVIAR_PROGRAMAS_CNC,
            acao_label="Enviar",
        )
    )
    return estados


def _estado_obra_pronta(
    estados: Sequence[PreparacaoEstado], obrigatorias: set[str]
) -> PreparacaoEstado:
    em_falta = [
        estado for estado in estados if estado.key in obrigatorias and not estado.ok
    ]
    if not em_falta:
        return PreparacaoEstado(
            key="obra_pronta",
            label="Obra pronta para Produção",
            estado=ESTADO_OK,
            detalhe="Todos os passos obrigatórios desta preparação estão concluídos.",
            obrigatorio=False,
            descricao=DESCRICAO_OBRA_PRONTA,
        )

    detalhe = "Faltas/Bloqueios: " + ", ".join(
        estado.label for estado in em_falta[:6]
    )
    if len(em_falta) > 6:
        detalhe += ", ..."
    return PreparacaoEstado(
        key="obra_pronta",
        label="Obra pronta para Produção",
        estado=ESTADO_BLOQUEADO,
        detalhe=detalhe,
        obrigatorio=False,
        descricao=DESCRICAO_OBRA_PRONTA,
    )


def _caminho_da_validacao(
    contexto: PreparacaoContexto, validacao: ValidacaoFicheiro
) -> Optional[Path]:
    if validacao.key == "cutrite_pdf":
        return _caminho_pdf_cutrite(contexto)
    if validacao.key == "conj_pdf":
        return contexto.conj_pdf
    if validacao.key == "projeto_pdf":
        return contexto.projeto_pdf
    return _primeiro_ficheiro(contexto.pasta_obra, validacao.padrao)


def _origens_da_validacao(
    contexto: PreparacaoContexto, validacao: ValidacaoFicheiro
) -> list[Path]:
    if validacao.key == "cutrite_pdf":
        return []
    if validacao.key == "projeto_pdf":
        return [contexto.conj_pdf] if contexto.conj_pdf.exists() else []

    origens: list[Path] = []
    for padrao in validacao.padroes_origem:
        origens.extend(_listar_ficheiros(contexto.pasta_obra, padrao))
    return origens


def _detalhe_em_falta(
    contexto: PreparacaoContexto, validacao: ValidacaoFicheiro
) -> str:
    if validacao.key == "cutrite_pdf":
        destino = _caminho_pdf_cutrite(contexto)
        if destino is None:
            return "Nome Plano CUT-RITE em falta no processo."
        return (
            f"{destino} (em falta)\n"
            "Exporte-o no botão CUT-RITE → Exportar PDF CUT-RITE."
        )
    return f"{contexto.pasta_obra}\\{validacao.padrao} (em falta)"


def _caminho_pdf_cutrite(contexto: PreparacaoContexto) -> Optional[Path]:
    nome = contexto.nome_plano_cut_rite
    if not nome:
        return None
    ficheiro = nome if nome.casefold().endswith(".pdf") else f"{nome}.pdf"
    return contexto.pasta_obra / ficheiro


def _listar_ficheiros(pasta: Path, padrao: str) -> list[Path]:
    if not padrao:
        return []
    try:
        return sorted(caminho for caminho in pasta.glob(padrao) if caminho.is_file())
    except OSError:
        # Pasta inacessível (servidor em baixo) não pode rebentar o painel.
        return []


def _primeiro_ficheiro(pasta: Path, padrao: str) -> Optional[Path]:
    encontrados = _listar_ficheiros(pasta, padrao)
    return encontrados[0] if encontrados else None


def _mais_recente(caminhos: Iterable[Path]) -> Optional[Path]:
    existentes = [caminho for caminho in caminhos if caminho.exists()]
    if not existentes:
        return None
    return max(existentes, key=_mtime)


def _mtime(caminho: Path) -> float:
    try:
        return float(caminho.stat().st_mtime)
    except OSError:
        return 0.0


def _data_hora(valor: float) -> str:
    if not valor:
        return "-"
    return datetime.fromtimestamp(valor).strftime("%d-%m-%Y %H:%M")


def _instantaneo(pasta: Path) -> Optional[_Instantaneo]:
    try:
        if not pasta.is_dir():
            return None
        ficheiros = 0
        ultima = 0.0
        for caminho in pasta.rglob("*"):
            if not caminho.is_file():
                continue
            ficheiros += 1
            ultima = max(ultima, _mtime(caminho))
    except OSError:
        return None
    return _Instantaneo(ficheiros=ficheiros, ultima_alteracao=ultima)


def _esta_desatualizada(alvo: _Instantaneo, referencia: _Instantaneo) -> bool:
    if not alvo.tem_ficheiros:
        return True
    if referencia.ficheiros > alvo.ficheiros:
        return True
    return referencia.ultima_alteracao > alvo.ultima_alteracao + 1


def _detalhe_pasta(pasta: Path, instantaneo: _Instantaneo) -> str:
    return (
        f"{pasta} ({instantaneo.ficheiros} ficheiro(s); "
        f"atualização {_data_hora(instantaneo.ultima_alteracao)})"
    )


def _substituir_pasta(origem: Path, destino: Path) -> None:
    if destino.exists():
        shutil.rmtree(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(origem, destino)


def _gerar_projeto_pdf_vetorial(
    origem_pdf: Path, destino_pdf: Path, *, max_paginas: int
) -> None:
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter, Transformation
    from reportlab.lib.pagesizes import A4, landscape

    largura_a4, altura_a4 = landscape(A4)
    local = _pdf_local(origem_pdf)
    # Ler para memória: assim o PDF de origem não fica aberto (preso) enquanto
    # geramos o destino.
    leitor = PdfReader(BytesIO(local.read_bytes()))
    escritor = PdfWriter()

    total = min(max_paginas, len(leitor.pages))
    if total <= 0:
        raise RuntimeError(f"PDF sem páginas: {origem_pdf}")

    for indice in range(total):
        pagina_origem = leitor.pages[indice]
        largura = float(pagina_origem.mediabox.width)
        altura = float(pagina_origem.mediabox.height)
        if largura <= 0 or altura <= 0:
            continue

        escala = min(largura_a4 / largura, altura_a4 / altura)
        deslocar_x = (largura_a4 - largura * escala) / 2 - float(
            pagina_origem.mediabox.left
        ) * escala
        deslocar_y = (altura_a4 - altura * escala) / 2 - float(
            pagina_origem.mediabox.bottom
        ) * escala

        pagina = escritor.add_blank_page(largura_a4, altura_a4)
        pagina.merge_transformed_page(
            pagina_origem,
            Transformation().scale(escala).translate(deslocar_x, deslocar_y),
        )

    destino_pdf.parent.mkdir(parents=True, exist_ok=True)
    with destino_pdf.open("wb") as ficheiro:
        escritor.write(ficheiro)


def _imagens_do_conj(origem_pdf: Path, max_paginas: int) -> list:
    from PySide6.QtCore import QSize

    local = _pdf_local(origem_pdf)
    # Lido de memória para o PDF de origem não ficar preso (ver
    # app/services/pdf_imagem_service.py).
    with documento_pdf(local) as documento:
        if not _pdf_abriu(documento.error()):
            raise RuntimeError(f"Não foi possível abrir o PDF de origem: {origem_pdf}")

        paginas = min(max_paginas, documento.pageCount())
        if paginas <= 0:
            raise RuntimeError(f"PDF sem páginas disponíveis: {origem_pdf}")

        imagens = []
        for indice in range(paginas):
            tamanho = documento.pagePointSize(indice)
            alvo = QSize(
                max(1, int(tamanho.width() * 1.5)),
                max(1, int(tamanho.height() * 1.5)),
            )
            imagem = documento.render(indice, alvo)
            if imagem.isNull():
                raise RuntimeError(
                    f"Falha a desenhar a página {indice + 1} de {origem_pdf}"
                )
            imagens.append(imagem)
        return imagens


def _pdf_abriu(estado) -> bool:
    from PySide6 import QtPdf

    if estado == QtPdf.QPdfDocument.Error.None_:
        return True
    return str(getattr(estado, "name", "")).strip().casefold() in {"none_", "none", "ok"}


def _imagens_para_pdf_a4(imagens: Sequence, destino_pdf: Path) -> None:
    from io import BytesIO

    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    largura_a4, altura_a4 = landscape(A4)
    destino_pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(destino_pdf), pagesize=(largura_a4, altura_a4))
    for imagem in imagens:
        bytes_png = QByteArray()
        buffer = QBuffer(bytes_png)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        imagem.save(buffer, "PNG")
        leitor = ImageReader(BytesIO(bytes(bytes_png)))

        escala = min(largura_a4 / imagem.width(), altura_a4 / imagem.height())
        largura = imagem.width() * escala
        altura = imagem.height() * escala
        pdf.drawImage(
            leitor,
            (largura_a4 - largura) / 2,
            (altura_a4 - altura) / 2,
            largura,
            altura,
            preserveAspectRatio=True,
            mask="auto",
        )
        pdf.showPage()
    pdf.save()


def _pdf_local(origem_pdf: Path) -> Path:
    """Copy PDFs from the server to a temp folder before reading them."""
    caminho = Path(origem_pdf)
    if not caminho.exists():
        raise RuntimeError(f"Não foi possível abrir o PDF de origem: {origem_pdf}")
    if not str(caminho).startswith("\\\\"):
        return caminho
    temporaria = Path(tempfile.mkdtemp(prefix="martelo_preparacao_"))
    destino = temporaria / caminho.name
    shutil.copy2(caminho, destino)
    return destino
