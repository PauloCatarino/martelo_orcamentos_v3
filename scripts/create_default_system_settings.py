"""Create default system settings for Martelo V3."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import SystemSetting  # noqa: E402


@dataclass(frozen=True)
class SystemSettingSeed:
    """Definition data for one default system setting."""

    chave: str
    descricao: str
    tipo: str = "texto"
    grupo: str | None = None
    valor: str | None = ""
    ativo: bool = True


@dataclass(frozen=True)
class EntityResult:
    """Result for one seeded setting."""

    status: str
    entity: SystemSetting


@dataclass(frozen=True)
class DefaultSystemSettingsResult:
    """Summary of the default system settings seed."""

    criadas: int
    reutilizadas: int


# Key + default folder for the module images (phase 8U.4). The copy of a module
# image (guardar/editar módulo) reads this key; the Caminhos do Sistema page
# lists it (tipo "pasta" -> "Procurar..." enabled) so the user can change it.
PASTA_IMAGENS_MODULOS_CHAVE = "pasta_imagens_modulos"
PASTA_IMAGENS_MODULOS_DEFAULT = (
    r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos"
    r"\Base_Dados_Orcamento\Imagens_Modulos"
)

# Caminhos por defeito da exportação de orçamentos (fase 8W.4.0). A seed só
# preenche valores vazios (não sobrepõe os já definidos pelo utilizador).
PASTA_BASE_ORCAMENTOS_DEFAULT = (
    r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos"
)
PASTA_BASE_DADOS_ORCAMENTO_DEFAULT = (
    r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos"
    r"\Base_Dados_Orcamento"
)
PASTA_PESQUISA_PROFUNDA_IA_DEFAULT = (
    r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Compras"
    r"\Tabela e Catalogos_Fornecedores\Tabelas Preços\Pesquisa_Profunda_IA"
)
PASTA_EMBEDDINGS_IA_DEFAULT = (
    r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos"
    r"\Base_Dados_Orcamento\Pesquisa_IA_Martelo"
)
PRODUCAO_BASE_PATH_CHAVE = "producao_base_path"
PRODUCAO_BASE_PATH_DEFAULT = (
    r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep_Producao"
)
PRODUCAO_BASE_PATH_DEFAULT_ANTIGO = (
    r"\\SERVER_LE\Lanca_Encanto\LancaEncanto\Dep_Producao"
)
PRODUCAO_BASE_PATH_DEFAULT_HOST_ANTIGO = (
    r"\\SERVER_LE_Lanca_Encanto\LancaEncanto\Dep_Producao"
)
PRODUCAO_BASE_PATH_CHAVE_LEGACY = "pasta_base_producao"

DEFAULT_SYSTEM_SETTINGS: tuple[SystemSettingSeed, ...] = (
    SystemSettingSeed(
        "pasta_base_orcamentos",
        "Pasta base dos Orcamentos",
        "pasta",
        "Orcamentos",
        PASTA_BASE_ORCAMENTOS_DEFAULT,
    ),
    SystemSettingSeed("pasta_materias_primas", "Pasta Materias Primas", "pasta", "Materias-Primas"),
    SystemSettingSeed(
        PASTA_IMAGENS_MODULOS_CHAVE,
        "Pasta de Imagens de Modulos",
        "pasta",
        "Modulos",
        PASTA_IMAGENS_MODULOS_DEFAULT,
    ),
    SystemSettingSeed(
        "pasta_base_dados_orcamento",
        "Pasta Base Dados Orcamento",
        "pasta",
        "Orcamentos",
        PASTA_BASE_DADOS_ORCAMENTO_DEFAULT,
    ),
    SystemSettingSeed(
        "phc_sql_server",
        "PHC SQL - Servidor",
        "texto",
        "PHC",
        r"Server_le\phc",
    ),
    SystemSettingSeed(
        "phc_sql_database",
        "PHC SQL - Base de Dados",
        "texto",
        "PHC",
        "lancaencanto",
    ),
    SystemSettingSeed(
        "phc_sql_user",
        "PHC SQL - Utilizador",
        "texto",
        "PHC",
        "adriano.silva",
    ),
    SystemSettingSeed(
        "phc_sql_password",
        "PHC SQL - Password",
        "texto",
        "PHC",
        "",
    ),
    SystemSettingSeed(
        "phc_sql_trusted",
        "PHC SQL - Integrated Security (ON/OFF)",
        "opcao",
        "PHC",
        "OFF",
    ),
    SystemSettingSeed(
        "phc_sql_trust_server_certificate",
        "PHC SQL - TrustServerCertificate (ON/OFF)",
        "opcao",
        "PHC",
        "ON",
    ),
    SystemSettingSeed(
        PRODUCAO_BASE_PATH_CHAVE,
        "Pasta base Producao",
        "pasta",
        "Producao",
        PRODUCAO_BASE_PATH_DEFAULT,
    ),
    SystemSettingSeed("pasta_base_imorder", "Pasta Base Imorder / imos iX", "pasta", "IMOS"),
    SystemSettingSeed("ficheiro_imos_msg", "Ficheiro imos.msg", "ficheiro", "IMOS"),
    SystemSettingSeed("excel_traducoes_imos", "Excel traducoes IMOS", "ficheiro", "IMOS"),
    SystemSettingSeed("executavel_cut_rite", "Executavel CUT-RITE", "ficheiro", "CUT-RITE"),
    SystemSettingSeed("pasta_trabalho_cut_rite", "Pasta Trabalho CUT-RITE", "pasta", "CUT-RITE"),
    SystemSettingSeed("pasta_dados_cut_rite", "Pasta Dados CUT-RITE", "pasta", "CUT-RITE"),
    SystemSettingSeed("pasta_origem_programas_cnc", "Pasta Origem Programas CNC", "pasta", "CNC"),
    SystemSettingSeed("pasta_destino_programas_cnc", "Pasta Destino Programas CNC", "pasta", "CNC"),
    SystemSettingSeed(
        "pasta_auditoria_lista_material",
        "Pasta Auditoria Lista Material",
        "pasta",
        "Producao",
    ),
    SystemSettingSeed(
        "pasta_pesquisa_profunda_ia",
        "Pasta Pesquisa Profunda IA (catalogos Excel/PDF de fornecedores)",
        "pasta",
        "IA",
        PASTA_PESQUISA_PROFUNDA_IA_DEFAULT,
    ),
    SystemSettingSeed(
        "pasta_embeddings_ia",
        "Pasta Embeddings IA (indice da pesquisa)",
        "pasta",
        "IA",
        PASTA_EMBEDDINGS_IA_DEFAULT,
    ),
    SystemSettingSeed("pasta_modelo_ia_texto", "Pasta Modelo IA texto", "pasta", "IA"),
    SystemSettingSeed("ficheiro_log", "Ficheiro de log", "ficheiro", "Geral"),
    SystemSettingSeed(
        "provedor_resposta_ia",
        "Provedor resposta IA (local / openai / claude)",
        "texto",
        "IA",
        "local",
    ),
    SystemSettingSeed(
        "modelo_embeddings_ia",
        "Modelo de embeddings IA (sentence-transformers)",
        "texto",
        "IA",
        "paraphrase-multilingual-MiniLM-L12-v2",
    ),
    SystemSettingSeed(
        "modelo_local_ia",
        "Modelo local IA para resposta (ex. Ollama: llama3.1)",
        "texto",
        "IA",
        "",
    ),
    SystemSettingSeed("modelo_openai_texto", "Modelo OpenAI texto", "texto", "IA", "gpt-4o-mini"),
    SystemSettingSeed(
        "modelo_claude_ia",
        "Modelo Claude (Anthropic) para resposta",
        "texto",
        "IA",
        "claude-opus-4-8",
    ),
    SystemSettingSeed(
        "preencher_comp_larg_automaticamente",
        "Preencher COMP/LARG automaticamente",
        "opcao",
        "Geral",
        "ON",
    ),
)


def get_setting_by_key(session: Session, chave: str) -> SystemSetting | None:
    """Find one system setting by key."""
    return session.execute(select(SystemSetting).where(SystemSetting.chave == chave)).scalar_one_or_none()


def get_or_create_setting(session: Session, seed: SystemSettingSeed) -> EntityResult:
    """Create or reuse one default system setting."""
    setting = get_setting_by_key(session, seed.chave)

    if setting is not None:
        if (setting.valor is None or setting.valor == "") and seed.valor:
            setting.valor = seed.valor
        elif (
            seed.chave == PRODUCAO_BASE_PATH_CHAVE
            and setting.valor
            in {
                PRODUCAO_BASE_PATH_DEFAULT_ANTIGO,
                PRODUCAO_BASE_PATH_DEFAULT_HOST_ANTIGO,
            }
        ):
            setting.valor = PRODUCAO_BASE_PATH_DEFAULT
        setting.descricao = seed.descricao
        setting.tipo = seed.tipo
        setting.grupo = seed.grupo
        setting.ativo = seed.ativo
        session.flush()
        return EntityResult(status="reutilizada", entity=setting)

    setting = SystemSetting(
        chave=seed.chave,
        valor=seed.valor,
        descricao=seed.descricao,
        tipo=seed.tipo,
        grupo=seed.grupo,
        ativo=seed.ativo,
    )
    session.add(setting)
    session.flush()

    return EntityResult(status="criada", entity=setting)


def migrar_pasta_base_producao_legacy(session: Session) -> None:
    """Move the old production base-path setting into the canonical key."""
    legacy = get_setting_by_key(session, PRODUCAO_BASE_PATH_CHAVE_LEGACY)
    if legacy is None:
        return

    valor_legacy = (legacy.valor or "").strip()
    if valor_legacy:
        target = get_setting_by_key(session, PRODUCAO_BASE_PATH_CHAVE)
        if target is None:
            target = SystemSetting(
                chave=PRODUCAO_BASE_PATH_CHAVE,
                valor=valor_legacy,
                descricao="Pasta base Producao",
                tipo="pasta",
                grupo="Producao",
                ativo=True,
            )
            session.add(target)
        else:
            target.valor = valor_legacy

    session.delete(legacy)
    session.flush()


def ensure_default_system_settings(session: Session) -> DefaultSystemSettingsResult:
    """Create or reuse all default system settings."""
    criadas = 0
    reutilizadas = 0

    migrar_pasta_base_producao_legacy(session)

    for seed in DEFAULT_SYSTEM_SETTINGS:
        result = get_or_create_setting(session, seed)
        print(f"Configuracao {seed.chave} {result.status}")
        if result.status == "criada":
            criadas += 1
        else:
            reutilizadas += 1

    session.commit()

    return DefaultSystemSettingsResult(criadas=criadas, reutilizadas=reutilizadas)


def print_summary(result: DefaultSystemSettingsResult) -> None:
    """Print the final user-facing seed summary."""
    print("Resumo final")
    print(f"Configuracoes criadas: {result.criadas}")
    print(f"Configuracoes reutilizadas: {result.reutilizadas}")


def main() -> int:
    """Create or reuse default system settings in the configured database."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = ensure_default_system_settings(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
