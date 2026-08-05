"""Production table column configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.domain.datas import normalizar_data
from app.services.user_pref_service import UserPrefService
from app.utils.formatters import format_currency


@dataclass(frozen=True)
class ColunaProducao:
    """Definition for one fixed production table column."""

    key: str
    titulo: str
    visivel_default: bool
    valor: Callable[[Any], str]


def _texto(valor: object) -> str:
    return "" if valor is None else str(valor)


def _data_criacao(processo: Any) -> str:
    valor = getattr(processo, "created_at", None)
    if valor is None:
        return ""
    try:
        return valor.strftime("%d-%m-%Y")
    except AttributeError:
        return ""


def _descricao_uma_linha(processo: Any) -> str:
    return _texto(getattr(processo, "descricao_producao", "")).replace("\n", " · ")


def _encomenda_imos(processo: Any) -> str:
    """Diz de relance se a obra já tem encomenda criada no iMos.

    Vazio quando não tem — inclui as obras cuja encomenda foi criada à mão no
    iX Organizer antes de o Martelo passar a criá-las, que o V3 não conhece.
    """
    criado_em = getattr(processo, "imos_criado_em", None)
    if criado_em is None:
        return ""
    try:
        return f"✓ {criado_em.strftime('%d-%m-%Y')}"
    except AttributeError:
        return "✓"


def _projeto_cliente(processo: Any) -> str:
    """Diz de relance se o cliente já foi avisado de que a obra entrou em produção."""
    enviado_em = getattr(processo, "projeto_cliente_enviado_em", None)
    if enviado_em is None:
        return ""
    try:
        return f"✉ {enviado_em.strftime('%d-%m-%Y')}"
    except AttributeError:
        return "✉"


COLUNAS_PRODUCAO: list[ColunaProducao] = [
    ColunaProducao("criada_em", "Criada em", True, _data_criacao),
    ColunaProducao("ano", "Ano", True, lambda p: _texto(getattr(p, "ano", ""))),
    ColunaProducao("estado", "Estado", True, lambda p: getattr(p, "estado", None) or ""),
    ColunaProducao(
        "responsavel",
        "Responsável",
        True,
        lambda p: getattr(p, "responsavel", None) or "",
    ),
    ColunaProducao(
        "processo",
        "Processo",
        True,
        lambda p: getattr(p, "codigo_processo", None) or "",
    ),
    ColunaProducao(
        "enc_phc",
        "Nº Enc PHC",
        True,
        lambda p: getattr(p, "num_enc_phc", None) or "",
    ),
    ColunaProducao(
        "versao_obra",
        "V. Obra",
        True,
        lambda p: getattr(p, "versao_obra", None) or "",
    ),
    ColunaProducao(
        "versao_cutrite",
        "V. CutRite",
        True,
        lambda p: getattr(p, "versao_plano", None) or "",
    ),
    ColunaProducao(
        "cliente",
        "Cliente",
        True,
        lambda p: getattr(p, "nome_cliente", None) or "",
    ),
    ColunaProducao(
        "ref_cliente",
        "Ref Cliente",
        True,
        lambda p: getattr(p, "ref_cliente", None) or "",
    ),
    ColunaProducao("obra", "Obra", True, lambda p: getattr(p, "obra", None) or ""),
    ColunaProducao(
        "data_inicio",
        "Data Início",
        True,
        lambda p: normalizar_data(getattr(p, "data_inicio", None)),
    ),
    ColunaProducao(
        "data_entrega",
        "Data Entrega",
        True,
        lambda p: normalizar_data(getattr(p, "data_entrega", None)),
    ),
    ColunaProducao(
        "qt_artigos",
        "Qt Artigos",
        True,
        lambda p: _texto(getattr(p, "qt_artigos", None)),
    ),
    ColunaProducao(
        "preco",
        "Preço",
        True,
        lambda p: format_currency(getattr(p, "preco_total", None)),
    ),
    ColunaProducao(
        "descricao_producao",
        "Descrição Produção",
        True,
        _descricao_uma_linha,
    ),
    ColunaProducao("imos", "Enc. iMos", True, _encomenda_imos),
    ColunaProducao("projeto_cliente", "Projeto Cliente", True, _projeto_cliente),
    ColunaProducao(
        "localizacao",
        "Localização",
        False,
        lambda p: getattr(p, "localizacao", None) or "",
    ),
    ColunaProducao(
        "tipo_pasta",
        "Tipo Pasta",
        False,
        lambda p: getattr(p, "tipo_pasta", None) or "",
    ),
]

_COLUNAS_POR_KEY = {coluna.key: coluna for coluna in COLUNAS_PRODUCAO}
_ORDEM_KEYS = [coluna.key for coluna in COLUNAS_PRODUCAO]
LARGURAS_DEFAULT_PRODUCAO: dict[str, int] = {
    "criada_em": 95,
    "ano": 60,
    "estado": 110,
    "responsavel": 120,
    "processo": 115,
    "enc_phc": 95,
    "versao_obra": 75,
    "versao_cutrite": 80,
    "cliente": 190,
    "ref_cliente": 110,
    "obra": 210,
    "data_inicio": 95,
    "data_entrega": 95,
    "qt_artigos": 85,
    "preco": 100,
    "descricao_producao": 220,
    "imos": 110,
    "projeto_cliente": 120,
    "localizacao": 150,
    "tipo_pasta": 170,
}


#: Chave da configuração de colunas de cada utilizador. O utilizador vai na sua
#: própria coluna das ``user_prefs`` (ver :mod:`app.services.user_pref_service`).
CHAVE_CONFIG_COLUNAS = "producao_colunas"


def _visiveis_default() -> list[str]:
    return [coluna.key for coluna in COLUNAS_PRODUCAO if coluna.visivel_default]


def _normalizar_visiveis(
    visiveis: object,
    known_keys: set[str] | None = None,
) -> list[str]:
    if not isinstance(visiveis, list):
        return _visiveis_default()

    configuradas = {str(key) for key in visiveis if str(key) in _COLUNAS_POR_KEY}
    for coluna in COLUNAS_PRODUCAO:
        if (
            known_keys is not None
            and coluna.key not in known_keys
            and coluna.visivel_default
        ):
            configuradas.add(coluna.key)

    normalizadas = [key for key in _ORDEM_KEYS if key in configuradas]
    return normalizadas or _visiveis_default()


def _normalizar_larguras(
    larguras: object,
    *,
    preencher_defaults: bool = False,
) -> dict[str, int]:
    normalizadas: dict[str, int] = (
        dict(LARGURAS_DEFAULT_PRODUCAO) if preencher_defaults else {}
    )
    if not isinstance(larguras, dict):
        return normalizadas

    for key, largura in larguras.items():
        key_texto = str(key)
        if key_texto not in _COLUNAS_POR_KEY:
            continue
        try:
            largura_int = int(largura)
        except (TypeError, ValueError):
            continue
        if largura_int > 0:
            normalizadas[key_texto] = largura_int

    return normalizadas


def serializar_config(visiveis: list[str], larguras: dict[str, int]) -> str:
    """Serialize a production-column configuration to JSON."""
    payload = {
        "visiveis": _normalizar_visiveis(visiveis, set(_ORDEM_KEYS)),
        "larguras": _normalizar_larguras(larguras, preencher_defaults=True),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def desserializar_config(texto: str | None) -> tuple[list[str], dict[str, int]]:
    """Deserialize production-column configuration, falling back to defaults."""
    if not texto:
        return _visiveis_default(), {}

    try:
        payload = json.loads(texto)
    except (TypeError, ValueError, json.JSONDecodeError):
        return _visiveis_default(), {}

    if not isinstance(payload, dict):
        return _visiveis_default(), {}

    raw_larguras = payload.get("larguras")
    known_keys: set[str] | None = None
    if isinstance(raw_larguras, dict):
        known_keys = {str(key) for key in raw_larguras if str(key) in _COLUNAS_POR_KEY}

    return (
        _normalizar_visiveis(payload.get("visiveis"), known_keys),
        _normalizar_larguras(raw_larguras),
    )


def carregar_config(session: Session, user_id: object) -> tuple[list[str], dict[str, int]]:
    """Load the production-column configuration for one user."""
    valor = UserPrefService(session).obter_valor(user_id, CHAVE_CONFIG_COLUNAS, None)
    return desserializar_config(valor)


def guardar_config(
    session: Session,
    user_id: object,
    visiveis: list[str],
    larguras: dict[str, int],
) -> None:
    """Save the production-column configuration for one user."""
    UserPrefService(session).guardar_valor(
        user_id, CHAVE_CONFIG_COLUNAS, serializar_config(visiveis, larguras)
    )
