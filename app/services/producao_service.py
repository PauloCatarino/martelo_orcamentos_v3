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
from app.services.producao_pastas_service import (
    caminho_versao,
    caminho_versao_de_processo,
    criar_pasta_versao,
    eliminar_pasta_versao,
    listar_pastas_enc_arvore,
    sugerir_proxima_versao_obra,
    sugerir_proxima_versao_plano,
)

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


def listar_versoes_processo(
    session: Session,
    *,
    ano,
    num_enc_phc,
) -> set[tuple[str, str]]:
    """Return existing (versao_obra, versao_plano) pairs for an order."""
    enc_values = _enc_query_values(num_enc_phc)
    statement = select(Producao.versao_obra, Producao.versao_plano).where(
        Producao.ano == str(ano),
        Producao.num_enc_phc.in_(enc_values),
    )
    return {
        (_two_digit(versao_obra), _two_digit(versao_plano))
        for versao_obra, versao_plano in session.execute(statement).all()
        if versao_obra is not None and versao_plano is not None
    }


def preparar_nova_versao(
    session: Session,
    *,
    processo_id: int,
) -> dict:
    """Collect current process, existing versions and version suggestions."""
    processo = session.get(Producao, processo_id)
    if processo is None:
        raise ValueError("Processo de producao nao encontrado.")

    folder_root, folder_tree = listar_pastas_enc_arvore(
        session,
        ano=processo.ano,
        num_enc_phc=processo.num_enc_phc,
        tipo_pasta=processo.tipo_pasta,
    )
    existing_keys = listar_versoes_processo(
        session,
        ano=processo.ano,
        num_enc_phc=processo.num_enc_phc,
    )
    existing_keys |= _existing_keys_from_folder_tree(
        processo.num_enc_phc,
        folder_tree,
    )

    versao_obra_atual = _two_digit(processo.versao_obra)
    sug_cutrite = (
        versao_obra_atual,
        sugerir_proxima_versao_plano(
            session,
            ano=processo.ano,
            num_enc_phc=processo.num_enc_phc,
            versao_obra=versao_obra_atual,
            tipo_pasta=processo.tipo_pasta,
        ),
    )
    sug_cutrite = (
        sug_cutrite[0],
        _next_plano_from_keys(existing_keys, sug_cutrite[0], start=sug_cutrite[1]),
    )

    sug_obra = (
        sugerir_proxima_versao_obra(
            session,
            ano=processo.ano,
            num_enc_phc=processo.num_enc_phc,
            tipo_pasta=processo.tipo_pasta,
        ),
        "01",
    )
    sug_obra = (
        _next_obra_from_keys(existing_keys, start=sug_obra[0]),
        "01",
    )

    return {
        "processo_atual": processo,
        "existing_keys": existing_keys,
        "folder_root": folder_root,
        "folder_tree": folder_tree,
        "sug_cutrite": sug_cutrite,
        "sug_obra": sug_obra,
    }


def criar_nova_versao(
    session: Session,
    *,
    processo_id: int,
    versao_obra,
    versao_plano,
    criar_pasta: bool = True,
    current_user_id: int | None = None,
) -> Producao:
    """Create a new production process version, optionally creating its folder."""
    origem = session.get(Producao, processo_id)
    if origem is None:
        raise ValueError("Processo de producao nao encontrado.")

    ver_obra = _two_digit(versao_obra)
    ver_plano = _two_digit(versao_plano)
    if (ver_obra, ver_plano) in listar_versoes_processo(
        session,
        ano=origem.ano,
        num_enc_phc=origem.num_enc_phc,
    ):
        raise ValueError("Ja existe um processo com esta versao.")

    codigo_processo = gerar_codigo_processo(
        origem.ano,
        origem.num_enc_phc,
        ver_obra,
        ver_plano,
    )
    duplicado_codigo = session.scalar(
        select(Producao).where(Producao.codigo_processo == codigo_processo)
    )
    if duplicado_codigo is not None:
        raise ValueError(f"Ja existe o processo {duplicado_codigo.codigo_processo}.")

    novo = Producao(
        estado="Desenho",
        versao_obra=ver_obra,
        versao_plano=ver_plano,
        codigo_processo=codigo_processo,
        ano=origem.ano,
        num_enc_phc=origem.num_enc_phc,
        cliente_id=origem.cliente_id,
        nome_cliente=origem.nome_cliente,
        nome_cliente_simplex=origem.nome_cliente_simplex,
        num_cliente_phc=origem.num_cliente_phc,
        ref_cliente=origem.ref_cliente,
        orcamento_id=origem.orcamento_id,
        num_orcamento=origem.num_orcamento,
        versao_orc=origem.versao_orc,
        obra=origem.obra,
        localizacao=origem.localizacao,
        descricao_orcamento=origem.descricao_orcamento,
        descricao_artigos=origem.descricao_artigos,
        materias_usados=origem.materias_usados,
        descricao_producao=origem.descricao_producao,
        notas1=origem.notas1,
        notas2=origem.notas2,
        notas3=origem.notas3,
        preco_total=origem.preco_total,
        qt_artigos=origem.qt_artigos,
        responsavel=origem.responsavel,
        tipo_pasta=origem.tipo_pasta,
        created_by_id=current_user_id,
    )

    if criar_pasta:
        caminho = caminho_versao(
            session,
            ano=novo.ano,
            tipo_pasta=novo.tipo_pasta,
            num_enc_phc=novo.num_enc_phc,
            versao_obra=novo.versao_obra,
            versao_plano=novo.versao_plano,
            nome_simplex=novo.nome_cliente_simplex,
            nome_cliente=novo.nome_cliente,
            ref_cliente=novo.ref_cliente,
        )
        criar_pasta_versao(caminho)
        novo.pasta_servidor = str(caminho)

    session.add(novo)
    session.commit()
    session.refresh(novo)
    return novo


def eliminar_processo(session: Session, proc_id: int) -> None:
    """Delete one production process record without committing."""
    processo = session.get(Producao, proc_id)
    if processo is None:
        raise ValueError("Processo de producao nao encontrado.")
    session.delete(processo)


def eliminar_processo_completo(
    session: Session,
    *,
    processo_id: int,
    apagar_registo: bool,
    apagar_pasta: bool,
) -> None:
    """Delete the selected production process folder and/or database record."""
    if not apagar_registo and not apagar_pasta:
        raise ValueError("Escolha o registo, a pasta, ou ambos para eliminar.")

    processo = session.get(Producao, processo_id)
    if processo is None:
        raise ValueError("Processo de producao nao encontrado.")

    if apagar_pasta:
        caminho = caminho_versao_de_processo(session, processo)
        eliminar_pasta_versao(session, caminho, nome_esperado=caminho.name)

    if apagar_registo:
        eliminar_processo(session, processo_id)

    session.commit()


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


def _enc_query_values(valor) -> set[str]:
    raw = str(valor or "").strip()
    norm = _num_enc_norm(raw)
    return {value for value in (raw, norm) if value}


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


def _existing_keys_from_folder_tree(
    num_enc_phc,
    folder_tree: dict[str, dict[str, list[str]]],
) -> set[tuple[str, str]]:
    enc = _num_enc_norm(num_enc_phc)
    if not enc:
        return set()

    pattern = re.compile(
        rf"^{re.escape(enc)}(?:_|-| )(?P<vv>\d{{2}})(?:_|-| )(?P<pp>\d{{2}})(?:_|-| |$)",
        re.IGNORECASE,
    )
    keys: set[tuple[str, str]] = set()
    for versoes_obra in (folder_tree or {}).values():
        for versoes_plano in versoes_obra.values():
            for nome_pasta in versoes_plano:
                match = pattern.match(str(nome_pasta or ""))
                if match:
                    keys.add(
                        (
                            _two_digit(match.group("vv")),
                            _two_digit(match.group("pp")),
                        )
                    )
    return keys


def _next_plano_from_keys(
    keys: set[tuple[str, str]],
    versao_obra,
    *,
    start,
) -> str:
    vv = _two_digit(versao_obra)
    candidate = max(1, _as_positive_int(start))
    used = {pp for key_vv, pp in keys if key_vv == vv}
    while _two_digit(candidate) in used:
        candidate += 1
    return _two_digit(candidate)


def _next_obra_from_keys(keys: set[tuple[str, str]], *, start) -> str:
    candidate = max(1, _as_positive_int(start))
    used = {vv for vv, _pp in keys}
    while _two_digit(candidate) in used:
        candidate += 1
    return _two_digit(candidate)


def _as_positive_int(value) -> int:
    try:
        return max(1, int(str(value).strip()))
    except (TypeError, ValueError):
        return 1


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
