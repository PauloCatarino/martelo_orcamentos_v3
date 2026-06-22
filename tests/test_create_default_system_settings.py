"""Tests for the default system settings seed script."""

from __future__ import annotations

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.repositories.system_setting_repository import SystemSettingRepository
from app.services.system_setting_service import SystemSettingService
from scripts.create_default_system_settings import (
    DEFAULT_SYSTEM_SETTINGS,
    PASTA_EMBEDDINGS_IA_DEFAULT,
    PASTA_IMAGENS_MODULOS_CHAVE,
    PASTA_IMAGENS_MODULOS_DEFAULT,
    PASTA_PESQUISA_PROFUNDA_IA_DEFAULT,
    DefaultSystemSettingsResult,
    ensure_default_system_settings,
)


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_default_system_settings_constants_import() -> None:
    settings_by_key = {seed.chave: seed for seed in DEFAULT_SYSTEM_SETTINGS}

    assert "pasta_base_orcamentos" in settings_by_key
    assert "pasta_materias_primas" in settings_by_key
    assert "preencher_comp_larg_automaticamente" in settings_by_key
    assert settings_by_key["provedor_resposta_ia"].valor == "local"
    assert settings_by_key["modelo_openai_texto"].valor == "gpt-4o-mini"
    assert (
        settings_by_key["modelo_embeddings_ia"].valor
        == "paraphrase-multilingual-MiniLM-L12-v2"
    )
    assert settings_by_key["modelo_local_ia"].valor == ""
    assert settings_by_key["preencher_comp_larg_automaticamente"].valor == "ON"
    assert settings_by_key["pasta_base_orcamentos"].tipo == "pasta"
    assert settings_by_key["ficheiro_imos_msg"].tipo == "ficheiro"
    assert settings_by_key["phc_sql_server"].valor == r"Server_le\phc"
    assert settings_by_key["phc_sql_server"].grupo == "PHC"
    assert settings_by_key["phc_sql_database"].valor == "lancaencanto"
    assert settings_by_key["phc_sql_user"].valor == "adriano.silva"
    assert settings_by_key["phc_sql_password"].valor == ""
    assert settings_by_key["phc_sql_trusted"].valor == "OFF"
    assert settings_by_key["phc_sql_trust_server_certificate"].valor == "ON"
    assert (
        settings_by_key["pasta_pesquisa_profunda_ia"].valor
        == PASTA_PESQUISA_PROFUNDA_IA_DEFAULT
    )
    assert settings_by_key["pasta_embeddings_ia"].valor == PASTA_EMBEDDINGS_IA_DEFAULT
    # Phase 8U.4: module images folder (default = V2 network path), browsable.
    imagens = settings_by_key[PASTA_IMAGENS_MODULOS_CHAVE]
    assert imagens.tipo == "pasta"
    assert imagens.grupo == "Modulos"
    assert imagens.valor == PASTA_IMAGENS_MODULOS_DEFAULT
    assert imagens.valor == (
        r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos"
        r"\Base_Dados_Orcamento\Imagens_Modulos"
    )


def test_seed_cria_pasta_imagens_modulos_e_e_listada(session) -> None:
    ensure_default_system_settings(session)

    setting = SystemSettingRepository(session).get_by_key(PASTA_IMAGENS_MODULOS_CHAVE)
    assert setting is not None
    assert setting.tipo == "pasta"  # -> "Procurar..." enabled on the page
    assert setting.valor == PASTA_IMAGENS_MODULOS_DEFAULT

    # The Caminhos do Sistema page loads exactly this list, so the row shows up.
    listadas = SystemSettingService(session).listar_configuracoes()
    chaves = {s.chave for s in listadas}
    assert PASTA_IMAGENS_MODULOS_CHAVE in chaves


def test_seed_idempotente_nao_duplica_nem_recria(session) -> None:
    primeira = ensure_default_system_settings(session)
    segunda = ensure_default_system_settings(session)

    repo = SystemSettingRepository(session)
    ocorrencias = [
        s for s in repo.list_all() if s.chave == PASTA_IMAGENS_MODULOS_CHAVE
    ]
    assert len(ocorrencias) == 1  # not duplicated
    assert ocorrencias[0].valor == PASTA_IMAGENS_MODULOS_DEFAULT

    # First run creates the keys; the second run only reuses them.
    assert primeira.criadas > 0
    assert segunda.criadas == 0
    assert segunda.reutilizadas == primeira.criadas + primeira.reutilizadas


def test_seed_nao_sobrepoe_valor_definido_pelo_utilizador(session) -> None:
    repo = SystemSettingRepository(session)
    repo.upsert_setting(
        chave=PASTA_IMAGENS_MODULOS_CHAVE,
        valor="D:/minhas_imagens_modulos",
        descricao="Pasta de Imagens de Modulos",
        tipo="pasta",
        grupo="Modulos",
    )
    session.commit()

    ensure_default_system_settings(session)

    setting = repo.get_by_key(PASTA_IMAGENS_MODULOS_CHAVE)
    assert setting.valor == "D:/minhas_imagens_modulos"  # user value preserved


def test_default_system_settings_result_dataclass() -> None:
    result = DefaultSystemSettingsResult(criadas=2, reutilizadas=18)

    assert result.criadas == 2
    assert result.reutilizadas == 18
