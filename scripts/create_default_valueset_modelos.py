"""Create the default (base) ValueSet models/libraries.

This seed is idempotent: it creates the model if missing and reuses it
otherwise, and creates each model line only when the (chave, codigo_opcao)
pair does not exist yet. Existing lines are kept, unless ``--force`` is passed.
Nothing is deleted or duplicated.

Materia-prima links are left empty in this phase (conceptual options): each
line stores codigo_opcao, nome_opcao and valor_texto, with materia_prima_id
as None.
"""

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
from app.models import DefValuesetModelo, DefValuesetModeloLinha  # noqa: E402


@dataclass(frozen=True)
class ModeloLinhaSeed:
    """One default line inside a ValueSet model."""

    chave: str
    codigo_opcao: str
    nome_opcao: str
    padrao: bool
    ordem: int


@dataclass(frozen=True)
class ValuesetModeloSeed:
    """One default ValueSet model and its lines."""

    codigo: str
    nome: str
    descricao: str
    tipo: str
    linhas: tuple[ModeloLinhaSeed, ...]


@dataclass(frozen=True)
class DefaultValuesetModelosResult:
    """Summary of the ValueSet models seed."""

    modelos_criados: int
    modelos_reutilizados: int
    linhas_criadas: int
    linhas_reutilizadas: int
    linhas_atualizadas: int


_AGL = ("AGL_19_STANDARD", "Aglomerado 19mm standard")
_MDF = ("MDF_19_STANDARD", "MDF 19mm standard")

ROUPEIRO_STANDARD_LINHAS: tuple[ModeloLinhaSeed, ...] = (
    ModeloLinhaSeed("MATERIAL_LATERAIS", _AGL[0], _AGL[1], True, 1),
    ModeloLinhaSeed("MATERIAL_TAMPOS", _AGL[0], _AGL[1], True, 2),
    ModeloLinhaSeed("MATERIAL_PORTAS", _MDF[0], _MDF[1], True, 3),
    ModeloLinhaSeed("MATERIAL_COSTAS", "COSTA_12_STANDARD", "Costa 12mm standard", True, 4),
    ModeloLinhaSeed("MATERIAL_FUNDOS", "FUNDO_19_STANDARD", "Fundo 19mm standard", True, 5),
    ModeloLinhaSeed("MATERIAL_PRATELEIRAS", _AGL[0], _AGL[1], True, 6),
    ModeloLinhaSeed("MATERIAL_FRENTES", _MDF[0], _MDF[1], True, 7),
    ModeloLinhaSeed("MATERIAL_GAVETAS", _AGL[0], _AGL[1], True, 8),
    ModeloLinhaSeed("FERRAGEM_DOBRADICA", "DOBRADICA_STANDARD", "Dobradiça standard", True, 10),
    ModeloLinhaSeed("FERRAGEM_CORREDICA", "CORREDICA_STANDARD", "Corrediça standard", True, 11),
    ModeloLinhaSeed("FERRAGEM_PUXADOR", "PUXADOR_STANDARD", "Puxador standard", True, 12),
    ModeloLinhaSeed("FERRAGEM_VARAO", "VARAO_STANDARD", "Varão standard", True, 13),
    ModeloLinhaSeed(
        "FERRAGEM_SUPORTE_VARAO", "SUPORTE_VARAO_STANDARD", "Suporte varão standard", True, 14
    ),
    ModeloLinhaSeed(
        "FERRAGEM_PE_NIVELADOR", "PE_NIVELADOR_STANDARD", "Pé nivelador standard", True, 15
    ),
    ModeloLinhaSeed("ORLA_FINA", "ORLA_FINA_STANDARD", "Orla fina standard", True, 20),
    ModeloLinhaSeed("ORLA_GROSSA", "ORLA_GROSSA_STANDARD", "Orla grossa standard", True, 21),
    ModeloLinhaSeed("ACABAMENTO_FACE_SUP", "SEM_ACABAMENTO", "Sem acabamento", True, 30),
    ModeloLinhaSeed("ACABAMENTO_FACE_INF", "SEM_ACABAMENTO", "Sem acabamento", True, 31),
)


DEFAULT_VALUESET_MODELOS: tuple[ValuesetModeloSeed, ...] = (
    ValuesetModeloSeed(
        codigo="ROUPEIRO_STANDARD",
        nome="Roupeiro standard",
        descricao="Modelo base para roupeiros standard",
        tipo="ROUPEIRO",
        linhas=ROUPEIRO_STANDARD_LINHAS,
    ),
)


def _get_modelo(session: Session, codigo: str) -> DefValuesetModelo | None:
    return session.execute(
        select(DefValuesetModelo).where(DefValuesetModelo.codigo == codigo)
    ).scalar_one_or_none()


def _get_linha(
    session: Session, modelo_id: int, chave: str, codigo_opcao: str
) -> DefValuesetModeloLinha | None:
    return session.execute(
        select(DefValuesetModeloLinha).where(
            DefValuesetModeloLinha.def_valueset_modelo_id == modelo_id,
            DefValuesetModeloLinha.chave == chave,
            DefValuesetModeloLinha.codigo_opcao == codigo_opcao,
        )
    ).scalar_one_or_none()


def ensure_default_valueset_modelos(
    session: Session, force: bool = False
) -> DefaultValuesetModelosResult:
    """Create or reuse the default ValueSet models and their lines."""
    modelos_criados = 0
    modelos_reutilizados = 0
    linhas_criadas = 0
    linhas_reutilizadas = 0
    linhas_atualizadas = 0

    for modelo_seed in DEFAULT_VALUESET_MODELOS:
        modelo = _get_modelo(session, modelo_seed.codigo)
        if modelo is None:
            modelo = DefValuesetModelo(
                codigo=modelo_seed.codigo,
                nome=modelo_seed.nome,
                descricao=modelo_seed.descricao,
                tipo=modelo_seed.tipo,
                ativo=True,
            )
            session.add(modelo)
            session.flush()
            modelos_criados += 1
            print(f"Modelo {modelo_seed.codigo} criado")
        else:
            modelos_reutilizados += 1
            print(f"Modelo {modelo_seed.codigo} ja existe, reutilizado")

        for linha_seed in modelo_seed.linhas:
            existing = _get_linha(
                session, modelo.id, linha_seed.chave, linha_seed.codigo_opcao
            )
            if existing is not None:
                if force:
                    existing.nome_opcao = linha_seed.nome_opcao
                    existing.padrao = linha_seed.padrao
                    existing.ordem = linha_seed.ordem
                    existing.valor_texto = linha_seed.nome_opcao
                    session.flush()
                    linhas_atualizadas += 1
                    print(
                        f"Linha {modelo_seed.codigo} {linha_seed.chave}/"
                        f"{linha_seed.codigo_opcao} atualizada (--force)"
                    )
                else:
                    linhas_reutilizadas += 1
                    print(
                        f"Linha {modelo_seed.codigo} {linha_seed.chave}/"
                        f"{linha_seed.codigo_opcao} reutilizada"
                    )
                continue

            linha = DefValuesetModeloLinha(
                def_valueset_modelo_id=modelo.id,
                chave=linha_seed.chave,
                codigo_opcao=linha_seed.codigo_opcao,
                nome_opcao=linha_seed.nome_opcao,
                padrao=linha_seed.padrao,
                ordem=linha_seed.ordem,
                materia_prima_id=None,
                ref_materia_prima=None,
                descricao_materia_prima=None,
                valor_texto=linha_seed.nome_opcao,
                ativo=True,
            )
            session.add(linha)
            session.flush()
            linhas_criadas += 1
            print(
                f"Linha {modelo_seed.codigo} {linha_seed.chave}/"
                f"{linha_seed.codigo_opcao} criada"
            )

    session.commit()

    return DefaultValuesetModelosResult(
        modelos_criados=modelos_criados,
        modelos_reutilizados=modelos_reutilizados,
        linhas_criadas=linhas_criadas,
        linhas_reutilizadas=linhas_reutilizadas,
        linhas_atualizadas=linhas_atualizadas,
    )


def print_summary(result: DefaultValuesetModelosResult) -> None:
    """Print the final user-facing summary."""
    print("Resumo final")
    print(f"Modelos criados: {result.modelos_criados}")
    print(f"Modelos reutilizados: {result.modelos_reutilizados}")
    print(f"Linhas criadas: {result.linhas_criadas}")
    print(f"Linhas reutilizadas: {result.linhas_reutilizadas}")
    print(f"Linhas atualizadas (--force): {result.linhas_atualizadas}")
    print("Nota: materias-primas nao foram associadas (opcoes conceptuais).")


def main(argv: list[str] | None = None) -> int:
    """Create or reuse the default ValueSet models in the configured database."""
    args = list(sys.argv[1:] if argv is None else argv)
    force = "--force" in args

    _ = settings.database_url

    with SessionLocal() as session:
        result = ensure_default_valueset_modelos(session, force=force)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
