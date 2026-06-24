"""Service helpers for production processes."""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.orcamento import Orcamento
from app.models.orcamento_versao import OrcamentoVersao
from app.models.producao import Producao

CAMPOS_EDITAVEIS_PRODUCAO = (
    "estado",
    "responsavel",
    "ref_cliente",
    "obra",
    "localizacao",
    "data_inicio",
    "data_entrega",
    "tipo_pasta",
    "descricao_artigos",
    "materias_usados",
    "descricao_producao",
    "notas1",
    "notas2",
    "notas3",
    "imagem_path",
)

_CAMPOS_PESQUISA = (
    "codigo_processo",
    "num_enc_phc",
    "nome_cliente",
    "nome_cliente_simplex",
    "ref_cliente",
    "obra",
    "localizacao",
    "num_orcamento",
    "responsavel",
    "descricao_producao",
)


class ProducaoService:
    """Application service for production workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def listar_processos(self) -> list[Producao]:
        """List production processes ordered for the production page."""
        statement = select(Producao).order_by(
            Producao.created_at.desc(),
            Producao.ano.desc(),
            Producao.num_enc_phc.desc(),
        )
        return list(self.session.scalars(statement).all())

    def obter_processo(self, proc_id: int) -> Producao | None:
        """Return one production process by id."""
        return self.session.get(Producao, proc_id)

    def atualizar_processo(
        self,
        proc_id: int,
        data: dict,
        *,
        updated_by_id: int | None,
    ) -> Producao:
        """Update only editable production fields and commit the change."""
        processo = self.obter_processo(proc_id)
        if processo is None:
            raise ValueError("Processo de producao nao encontrado.")

        for campo, valor in campos_editaveis(data).items():
            setattr(processo, campo, valor)
        processo.updated_by_id = updated_by_id

        self.session.commit()
        self.session.refresh(processo)
        return processo


def gerar_codigo_processo(
    ano,
    num_enc_phc,
    versao_obra,
    versao_plano,
) -> str:
    """Build the production process code AA.NNNN_VV_PP."""
    ano_text = re.sub(r"\D+", "", str(ano or ""))
    aa = (ano_text[-2:] if ano_text else "00").zfill(2)
    nnnn = _format_digits(num_enc_phc, 4)
    vv = _format_digits(versao_obra, 2)
    pp = _format_digits(versao_plano, 2)
    return f"{aa}.{nnnn}_{vv}_{pp}"


def gerar_nome_plano_cut_rite(
    ano,
    num_enc_phc,
    versao_obra,
    versao_plano,
    *,
    nome_cliente_simplex=None,
    nome_cliente=None,
    ref_cliente=None,
) -> str:
    """Build the external CUT-RITE plan name for one production process."""
    nnnn = _num_enc_norm(num_enc_phc)
    aa = _ano_two_digits(ano)
    if not nnnn or not aa:
        return ""

    cliente = _sanitize_nome_externo(
        nome_cliente_simplex or nome_cliente or ref_cliente
    )
    return (
        f"{nnnn}_{_two_digit(versao_obra)}_{_two_digit(versao_plano)}"
        f"_{aa}_{cliente}"
    )


def gerar_nome_enc_imos_ix(
    ano,
    num_enc_phc,
    versao_obra,
    *,
    nome_cliente_simplex=None,
    nome_cliente=None,
    ref_cliente=None,
) -> str:
    """Build the external IMOS iX order name for one production process."""
    nnnn = _num_enc_norm(num_enc_phc)
    aa = _ano_two_digits(ano)
    if not nnnn or not aa:
        return ""

    cliente = _sanitize_nome_externo(
        nome_cliente_simplex or nome_cliente or ref_cliente
    )
    return f"{nnnn}_{_two_digit(versao_obra)}_{aa}_{cliente}"


def listar_orcamentos_convertiveis(session: Session) -> list[dict]:
    """Return adjudicated budget versions with their budget and customer data."""
    statement = (
        select(Orcamento, OrcamentoVersao, Cliente)
        .join(OrcamentoVersao, OrcamentoVersao.orcamento_id == Orcamento.id)
        .join(Cliente, Cliente.id == Orcamento.cliente_id)
        .order_by(
            Orcamento.ano.asc(),
            Orcamento.num_orcamento.asc(),
            OrcamentoVersao.numero_versao.asc(),
        )
    )

    rows = session.execute(statement).all()
    resultado = []
    for orcamento, versao, cliente in rows:
        if _normalizar_texto(versao.estado) != "adjudicado":
            continue
        resultado.append(
            {
                "orcamento_id": orcamento.id,
                "versao_id": versao.id,
                "ano": orcamento.ano,
                "num_orcamento": orcamento.num_orcamento,
                "numero_versao": versao.numero_versao,
                "cliente_nome": cliente.nome,
                "enc_phc": versao.enc_phc,
                "preco_total": versao.preco_total,
                "is_temporary": cliente.is_temporary,
                "source_system": cliente.source_system,
                "num_cliente_phc": cliente.num_cliente_phc,
            }
        )
    return resultado


def validar_conversao(
    *,
    estado,
    is_temporary,
    source_system,
    num_cliente_phc,
    enc_phc,
) -> list[str]:
    """Return validation errors for budget-to-production conversion."""
    erros = []
    if _normalizar_texto(estado) != "adjudicado":
        erros.append("O orçamento tem de estar Adjudicado.")
    if is_temporary:
        erros.append("O cliente ainda é temporário.")
    if _normalizar_texto(source_system) != "phc":
        erros.append("O cliente tem de ser do PHC.")
    if not _tem_texto(num_cliente_phc):
        erros.append("O cliente não tem Nº Cliente PHC.")
    if not _tem_texto(enc_phc):
        erros.append("O orçamento não tem Nº Enc PHC.")
    return erros


def converter_orcamento(
    session: Session,
    *,
    orcamento_id: int,
    versao_id: int,
    created_by_id: int | None,
) -> Producao:
    """Convert one adjudicated budget version into a production process."""
    statement = (
        select(Orcamento, OrcamentoVersao, Cliente)
        .join(OrcamentoVersao, OrcamentoVersao.orcamento_id == Orcamento.id)
        .join(Cliente, Cliente.id == Orcamento.cliente_id)
        .where(Orcamento.id == orcamento_id, OrcamentoVersao.id == versao_id)
    )
    row = session.execute(statement).one_or_none()
    if row is None:
        raise ValueError("Orçamento não encontrado.")

    orcamento, versao, cliente = row
    erros = validar_conversao(
        estado=versao.estado,
        is_temporary=cliente.is_temporary,
        source_system=cliente.source_system,
        num_cliente_phc=cliente.num_cliente_phc,
        enc_phc=versao.enc_phc,
    )
    if erros:
        raise ValueError("\n".join(erros))

    versao_obra = "01"
    versao_plano = "01"
    codigo_processo = gerar_codigo_processo(
        orcamento.ano,
        versao.enc_phc,
        versao_obra,
        versao_plano,
    )
    duplicado = session.scalar(
        select(Producao).where(
            Producao.ano == str(orcamento.ano),
            Producao.num_enc_phc == str(versao.enc_phc).strip(),
            Producao.versao_obra == versao_obra,
            Producao.versao_plano == versao_plano,
        )
    )
    if duplicado is not None:
        raise ValueError(f"Já existe o processo {duplicado.codigo_processo}.")

    processo = Producao(
        estado="Desenho",
        tipo_pasta="Encomenda de Cliente",
        versao_obra=versao_obra,
        versao_plano=versao_plano,
        codigo_processo=codigo_processo,
        ano=str(orcamento.ano),
        num_enc_phc=str(versao.enc_phc).strip(),
        orcamento_id=orcamento.id,
        cliente_id=cliente.id,
        nome_cliente=cliente.nome,
        nome_cliente_simplex=cliente.nome_simplex,
        num_cliente_phc=cliente.num_cliente_phc,
        ref_cliente=orcamento.ref_cliente,
        num_orcamento=orcamento.num_orcamento,
        versao_orc=f"{int(versao.numero_versao):02d}",
        obra=orcamento.obra,
        localizacao=orcamento.localizacao,
        descricao_orcamento=orcamento.descricao,
        preco_total=versao.preco_total,
        created_by_id=created_by_id,
    )
    session.add(processo)
    session.commit()
    session.refresh(processo)
    return processo


def campos_editaveis(data: dict) -> dict:
    """Return only fields that are editable in the production detail form."""
    return {
        campo: data[campo]
        for campo in CAMPOS_EDITAVEIS_PRODUCAO
        if campo in data
    }


def _normalizar_texto(valor) -> str:
    texto = "" if valor is None else str(valor).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(char for char in texto if not unicodedata.combining(char))


def _tem_texto(valor) -> bool:
    return bool(str(valor or "").strip())


def _format_digits(valor, width: int) -> str:
    digits = re.sub(r"\D+", "", str(valor or ""))
    if not digits:
        return "0".zfill(width)
    return str(int(digits)).zfill(width)


def _num_enc_norm(valor) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return ""
    if texto.startswith("_"):
        digits = re.sub(r"\D+", "", texto[1:])
        return f"_{digits.zfill(3)}" if digits else ""
    digits = re.sub(r"\D+", "", texto)
    return digits.zfill(4) if digits else ""


def _two_digit(valor) -> str:
    return _format_digits(valor, 2)


def _ano_two_digits(valor) -> str:
    digits = re.sub(r"\D+", "", str(valor or ""))
    if not digits:
        return ""
    return digits[-2:].zfill(2)


def _sanitize_nome_externo(valor) -> str:
    texto = str(valor or "").strip() or "CLIENTE"
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    texto = re.sub(r"\s+", "_", texto.upper())
    texto = re.sub(r"[^A-Z0-9_-]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto or "CLIENTE"


def filtrar_processos(
    todos,
    *,
    texto="",
    estado=None,
    cliente=None,
    responsavel=None,
) -> list[Producao]:
    """Filter production processes in memory, case-insensitively."""
    termos = [
        termo
        for termo in re.split(r"[\s%]+", (texto or "").strip().lower())
        if termo
    ]
    estado_norm = _normalizar_filtro(estado)
    cliente_norm = _normalizar_filtro(cliente)
    responsavel_norm = _normalizar_filtro(responsavel)

    resultado = []
    for processo in todos or []:
        if estado_norm and _texto(getattr(processo, "estado", None)) != estado_norm:
            continue
        if (
            cliente_norm
            and _texto(getattr(processo, "nome_cliente", None)) != cliente_norm
        ):
            continue
        if (
            responsavel_norm
            and _texto(getattr(processo, "responsavel", None)) != responsavel_norm
        ):
            continue

        haystack = " ".join(
            _texto(getattr(processo, campo, None)) for campo in _CAMPOS_PESQUISA
        )
        if all(termo in haystack for termo in termos):
            resultado.append(processo)

    return resultado


def _normalizar_filtro(valor) -> str | None:
    texto = _texto(valor)
    if not texto or texto == "todos":
        return None
    return texto


def _texto(valor) -> str:
    return "" if valor is None else str(valor).strip().lower()
