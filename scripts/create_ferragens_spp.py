"""Criar os perfis SPP (medidos ao ML) e as ferragens que os acompanham.

Um perfil SPP e' uma ferragem comprada que se corta a medida e se paga ao metro
linear: entra no custeio como o varao de roupeiro (leva comprimento, por defeito
o do modulo). Cada perfil tem depois os seus acessorios, contados por regra:

* ``PERFIL_LL`` (perfil lava-louça) + 2 terminais por perfil;
* ``RODAPE_PVC/ALUM`` + 2 grampas por cada 650 mm de rodape;
* ``PUX_GOLA_C`` e ``PUX_GOLA_J`` + 2 esquadros L por cada 650 mm de gola.

Ficam tambem no catalogo, soltas, as ferragens que se aplicam a mao: terminais,
grampas, canto de rodape e esquadro L.

O seed e idempotente: cria so' o que falta (chaves, regras, peças e associados)
e nunca apaga nem altera o que ja existe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.domain.associado_types import COMP, GERAL, TOTAL  # noqa: E402
from app.domain.componente_types import PECA  # noqa: E402
from app.domain.peca_funcao_types import FERRAGEM as FUNCAO_FERRAGEM  # noqa: E402
from app.domain.peca_natureza_types import (  # noqa: E402
    CONJUNTO,
    FERRAGEM as NATUREZA_FERRAGEM,
    MATERIAL,
    NEUTRA,
)
from app.domain.peca_subgrupo_types import GRUPO_FERRAGENS  # noqa: E402
from app.domain.peca_types import COMPOSTA, SIMPLES  # noqa: E402
from app.domain.regra_quantidade_types import FIXA  # noqa: E402
from app.domain.regras_quantidade_expr import (  # noqa: E402
    CONTEXTO_EXEMPLO,
    avaliar_regra_quantidade,
)
from app.models import (  # noqa: E402
    DefPeca,
    DefPecaComponente,
    DefPecaUserPref,
    DefRegraQuantidade,
    DefValuesetChave,
)


SUBFAMILIA_COZINHAS = "COZINHAS"
SUBFAMILIA_PUXADORES = "PUXADORES"


@dataclass(frozen=True)
class ChaveSeed:
    """Uma chave de ferragem no ValueSet."""

    codigo: str
    nome: str
    descricao: str


@dataclass(frozen=True)
class RegraSeed:
    """Uma regra de quantidade."""

    codigo: str
    nome: str
    expressao: str
    descricao: str


@dataclass(frozen=True)
class PecaSeed:
    """Uma ferragem do catalogo.

    ``ao_metro`` marca os perfis SPP: sao peças fisicas porque levam
    comprimento e pagam-se ao metro linear. As restantes sao ferragens
    contadas a` unidade, sem medidas.
    """

    codigo: str
    nome: str
    descricao: str
    chave: str
    subfamilia: str
    nome_biblioteca: str | None = None
    ao_metro: bool = False


@dataclass(frozen=True)
class ComponenteSeed:
    """Um associado de um conjunto."""

    codigo_peca: str
    descricao: str
    ordem: int
    quantidade: Decimal
    codigo_regra: str | None = None
    formula_comp: str | None = None


@dataclass(frozen=True)
class ConjuntoSeed:
    """Um conjunto perfil + acessorios."""

    codigo: str
    nome: str
    descricao: str
    subfamilia: str
    componentes: tuple[ComponenteSeed, ...] = field(default_factory=tuple)
    nome_biblioteca: str | None = None


CHAVES: tuple[ChaveSeed, ...] = (
    ChaveSeed(
        "FERRAGEM_PERFIL_LL",
        "Perfil Lava Louça",
        "Perfil de lava-louça comprado ao metro (SPP).",
    ),
    ChaveSeed(
        "FERRAGEM_TERMINAIS_PERFIL_LL",
        "Terminais Perfil Lava Louça",
        "Terminais de fecho do perfil de lava-louça.",
    ),
    ChaveSeed(
        "FERRAGEM_RODAPE_PVC_ALUM",
        "Rodapé PVC/Alumínio",
        "Rodapé de PVC ou alumínio comprado ao metro (SPP).",
    ),
    ChaveSeed(
        "FERRAGEM_GRAMPAS_RODAPE",
        "Grampas Rodapé",
        "Grampas de fixação do rodapé aos pés.",
    ),
    ChaveSeed(
        "FERRAGEM_CANTO_RODAPE_PVC",
        "Canto Rodapé PVC/Alumínio",
        "Canto de ligação entre dois rodapés.",
    ),
    ChaveSeed(
        "FERRAGEM_PUX_GOLA_C",
        "Puxador Gola C",
        "Puxador de gola perfil C, comprado ao metro (SPP).",
    ),
    ChaveSeed(
        "FERRAGEM_PUX_GOLA_J",
        "Puxador Gola J",
        "Puxador de gola perfil J, comprado ao metro (SPP).",
    ),
    ChaveSeed(
        "FERRAGEM_ESQUADRO_L_PUX_GOLA",
        "Esquadro L Puxador Gola",
        "Esquadro de canto em L para fixar o puxador de gola.",
    ),
)

REGRA_TERMINAIS = "TERMINAIS_PERFIL_LL"
REGRA_GRAMPAS = "GRAMPAS_RODAPE_650"
REGRA_ESQUADROS = "ESQUADROS_PUX_GOLA_650"

REGRAS: tuple[RegraSeed, ...] = (
    RegraSeed(
        codigo=REGRA_TERMINAIS,
        nome="Terminais do perfil lava-louça",
        expressao="2",
        descricao="2 terminais por perfil de lava-louça (um em cada ponta).",
    ),
    RegraSeed(
        codigo=REGRA_GRAMPAS,
        nome="Grampas de rodapé (2 por 650 mm)",
        expressao="2 * CEIL(COMP / 650)",
        descricao="2 grampas por cada 650 mm de rodapé (ou fração).",
    ),
    RegraSeed(
        codigo=REGRA_ESQUADROS,
        nome="Esquadros L do puxador de gola (2 por 650 mm)",
        expressao="2 * CEIL(COMP / 650)",
        descricao="2 esquadros L por cada 650 mm de puxador de gola (ou fração).",
    ),
)

PECAS: tuple[PecaSeed, ...] = (
    PecaSeed(
        codigo="PERFIL_LL",
        nome="Perfil Lava Louça",
        descricao="Perfil de lava-louça ao metro linear.",
        chave="FERRAGEM_PERFIL_LL",
        subfamilia=SUBFAMILIA_COZINHAS,
        nome_biblioteca="Perfil Lava Louça {SPP}",
        ao_metro=True,
    ),
    PecaSeed(
        codigo="TERMINAIS_PERFIL_LL",
        nome="Terminais Perfil Lava Louça",
        descricao="Terminal de fecho do perfil de lava-louça.",
        chave="FERRAGEM_TERMINAIS_PERFIL_LL",
        subfamilia=SUBFAMILIA_COZINHAS,
    ),
    PecaSeed(
        codigo="RODAPE_PVC/ALUM",
        nome="Rodapé PVC/Alumínio",
        descricao="Rodapé de PVC ou alumínio ao metro linear.",
        chave="FERRAGEM_RODAPE_PVC_ALUM",
        subfamilia=SUBFAMILIA_COZINHAS,
        nome_biblioteca="Rodapé PVC/Alum {SPP}",
        ao_metro=True,
    ),
    PecaSeed(
        codigo="GRAMPAS_RDP",
        nome="Grampas Rodapé",
        descricao="Grampa de fixação do rodapé.",
        chave="FERRAGEM_GRAMPAS_RODAPE",
        subfamilia=SUBFAMILIA_COZINHAS,
    ),
    PecaSeed(
        codigo="CANTO_RDP_PVC",
        nome="Canto Rodapé PVC/Alumínio",
        descricao="Canto de ligação entre dois rodapés.",
        chave="FERRAGEM_CANTO_RODAPE_PVC",
        subfamilia=SUBFAMILIA_COZINHAS,
    ),
    PecaSeed(
        codigo="PUX_GOLA_C",
        nome="Puxador Gola C",
        descricao="Puxador de gola perfil C ao metro linear.",
        chave="FERRAGEM_PUX_GOLA_C",
        subfamilia=SUBFAMILIA_PUXADORES,
        nome_biblioteca="Pux Gola C {SPP}",
        ao_metro=True,
    ),
    PecaSeed(
        codigo="PUX_GOLA_J",
        nome="Puxador Gola J",
        descricao="Puxador de gola perfil J ao metro linear.",
        chave="FERRAGEM_PUX_GOLA_J",
        subfamilia=SUBFAMILIA_PUXADORES,
        nome_biblioteca="Pux Gola J {SPP}",
        ao_metro=True,
    ),
    PecaSeed(
        codigo="ESQUADRO_L_PUX_GOLA",
        nome="Esquadro L Puxador Gola",
        descricao="Esquadro de canto em L do puxador de gola.",
        chave="FERRAGEM_ESQUADRO_L_PUX_GOLA",
        subfamilia=SUBFAMILIA_PUXADORES,
    ),
)


def _perfil(codigo: str, descricao: str) -> ComponenteSeed:
    """O perfil do conjunto: 1 unidade ao comprimento do modulo."""
    return ComponenteSeed(
        codigo_peca=codigo,
        descricao=descricao,
        ordem=1,
        quantidade=Decimal("1.000"),
        formula_comp="LM",
    )


CONJUNTOS: tuple[ConjuntoSeed, ...] = (
    ConjuntoSeed(
        codigo="PERFIL_LL+TERMINAIS",
        nome="Perfil Lava Louça + Terminais",
        descricao="Perfil de lava-louça ao comprimento do módulo + 2 terminais.",
        subfamilia=SUBFAMILIA_COZINHAS,
        nome_biblioteca="Perfil Lava Louça {SPP}+Terminais",
        componentes=(
            _perfil("PERFIL_LL", "Perfil lava-louça ao comprimento do modulo"),
            ComponenteSeed(
                codigo_peca="TERMINAIS_PERFIL_LL",
                descricao="Terminais (2 por perfil)",
                ordem=2,
                quantidade=Decimal("2.000"),
                codigo_regra=REGRA_TERMINAIS,
            ),
        ),
    ),
    ConjuntoSeed(
        codigo="RODAPE_PVC/ALUM+GRAMPAS",
        nome="Rodapé PVC/Alumínio + Grampas",
        descricao="Rodapé ao comprimento do módulo + 2 grampas por cada 650 mm.",
        subfamilia=SUBFAMILIA_COZINHAS,
        nome_biblioteca="Rodapé PVC/Alum {SPP}+Grampas",
        componentes=(
            _perfil("RODAPE_PVC/ALUM", "Rodape ao comprimento do modulo"),
            ComponenteSeed(
                codigo_peca="GRAMPAS_RDP",
                descricao="Grampas (2 por cada 650 mm de rodape)",
                ordem=2,
                quantidade=Decimal("2.000"),
                codigo_regra=REGRA_GRAMPAS,
            ),
        ),
    ),
    ConjuntoSeed(
        codigo="PUX_GOLA_C+L",
        nome="Puxador Gola C + Esquadros L",
        descricao="Gola C ao comprimento do módulo + 2 esquadros por cada 650 mm.",
        subfamilia=SUBFAMILIA_PUXADORES,
        nome_biblioteca="Pux Gola C {SPP}+L",
        componentes=(
            _perfil("PUX_GOLA_C", "Puxador gola C ao comprimento do modulo"),
            ComponenteSeed(
                codigo_peca="ESQUADRO_L_PUX_GOLA",
                descricao="Esquadros L (2 por cada 650 mm de gola)",
                ordem=2,
                quantidade=Decimal("2.000"),
                codigo_regra=REGRA_ESQUADROS,
            ),
        ),
    ),
    ConjuntoSeed(
        codigo="PUX_GOLA_J+L",
        nome="Puxador Gola J + Esquadros L",
        descricao="Gola J ao comprimento do módulo + 2 esquadros por cada 650 mm.",
        subfamilia=SUBFAMILIA_PUXADORES,
        nome_biblioteca="Pux Gola J {SPP}+L",
        componentes=(
            _perfil("PUX_GOLA_J", "Puxador gola J ao comprimento do modulo"),
            ComponenteSeed(
                codigo_peca="ESQUADRO_L_PUX_GOLA",
                descricao="Esquadros L (2 por cada 650 mm de gola)",
                ordem=2,
                quantidade=Decimal("2.000"),
                codigo_regra=REGRA_ESQUADROS,
            ),
        ),
    ),
)


@dataclass(frozen=True)
class FerragensSppResult:
    """Resumo do seed dos perfis SPP."""

    chaves_criadas: int
    regras_criadas: int
    pecas_criadas: int
    conjuntos_criados: int
    componentes_criados: int
    reutilizados: int
    prefs_criadas: int


def get_peca(session: Session, codigo: str) -> DefPeca | None:
    """Devolver uma peca do catalogo pelo codigo."""
    return session.execute(
        select(DefPeca).where(DefPeca.codigo == codigo)
    ).scalar_one_or_none()


def criar_chaves(session: Session) -> int:
    """Criar as chaves de ferragem em falta. Devolve quantas criou."""
    criadas = 0
    for seed in CHAVES:
        existente = session.execute(
            select(DefValuesetChave).where(DefValuesetChave.codigo == seed.codigo)
        ).scalar_one_or_none()
        if existente is not None:
            print(f"Chave {seed.codigo} ja existe, mantida")
            continue

        ordem_maxima = session.execute(
            select(func.max(DefValuesetChave.ordem)).where(
                DefValuesetChave.grupo == "FERRAGENS"
            )
        ).scalar_one()
        session.add(
            DefValuesetChave(
                codigo=seed.codigo,
                nome=seed.nome,
                descricao=seed.descricao,
                tipo="FERRAGEM",
                grupo="FERRAGENS",
                sistema=True,
                ativo=True,
                ordem=(ordem_maxima or 0) + 1,
            )
        )
        session.flush()
        criadas += 1
        print(f"Chave {seed.codigo} criada")

    return criadas


def criar_regras(session: Session) -> int:
    """Criar as regras de quantidade em falta. Devolve quantas criou."""
    criadas = 0
    for seed in REGRAS:
        existente = session.execute(
            select(DefRegraQuantidade).where(DefRegraQuantidade.codigo == seed.codigo)
        ).scalar_one_or_none()
        if existente is not None:
            print(f"Regra {seed.codigo} ja existe, mantida")
            continue

        quantidade, motivo = avaliar_regra_quantidade(seed.expressao, CONTEXTO_EXEMPLO)
        if motivo is not None:
            raise ValueError(f"Regra {seed.codigo} invalida: {motivo}")

        session.add(
            DefRegraQuantidade(
                codigo=seed.codigo,
                nome=seed.nome,
                expressao=seed.expressao,
                descricao=seed.descricao,
                ativo=True,
            )
        )
        session.flush()
        criadas += 1
        print(f"Regra {seed.codigo} criada (exemplo: {quantidade})")

    return criadas


def get_regra_id(session: Session, codigo: str) -> int:
    """Devolver o id de uma regra de quantidade, com erro claro quando falta."""
    regra = session.execute(
        select(DefRegraQuantidade).where(DefRegraQuantidade.codigo == codigo)
    ).scalar_one_or_none()
    if regra is None:
        raise ValueError(f"Regra de quantidade {codigo} nao existe nesta base")
    return regra.id


def criar_pecas(session: Session) -> tuple[int, int]:
    """Criar as ferragens em falta. Devolve (criadas, reutilizadas)."""
    criadas = 0
    reutilizadas = 0

    for seed in PECAS:
        if get_peca(session, seed.codigo) is not None:
            reutilizadas += 1
            print(f"Peca {seed.codigo} ja existe, mantida")
            continue

        session.add(
            DefPeca(
                codigo=seed.codigo,
                nome=seed.nome,
                nome_biblioteca=seed.nome_biblioteca,
                descricao=seed.descricao,
                grupo=GRUPO_FERRAGENS,
                subgrupo=seed.subfamilia,
                tipo_peca=SIMPLES,
                # Um perfil ao metro leva comprimento e paga-se ao ML: entra
                # como peça fisica, tal como o varao. As ferragens contadas a`
                # unidade nao tem medidas.
                natureza=MATERIAL if seed.ao_metro else NATUREZA_FERRAGEM,
                orientacao=NEUTRA,
                funcao=FUNCAO_FERRAGEM,
                chave_valueset_material=seed.chave,
                permite_acabamento=False,
                sem_material=False,
                ativo=True,
            )
        )
        session.flush()
        criadas += 1
        print(f"Peca {seed.codigo} criada ({GRUPO_FERRAGENS} > {seed.subfamilia})")

    return criadas, reutilizadas


def criar_componentes(
    session: Session, conjunto: DefPeca, seed: ConjuntoSeed
) -> int:
    """Criar os associados de um conjunto. Devolve quantos criou."""
    criados = 0
    for componente in seed.componentes:
        peca = get_peca(session, componente.codigo_peca)
        if peca is None:
            raise ValueError(
                f"Peca {componente.codigo_peca} nao existe; "
                f"nao e possivel montar {seed.codigo}"
            )

        session.add(
            DefPecaComponente(
                def_peca_pai_id=conjunto.id,
                tipo_componente=PECA,
                def_peca_componente_id=peca.id,
                descricao=componente.descricao,
                ordem=componente.ordem,
                quantidade=componente.quantidade,
                regra_quantidade=FIXA,
                def_regra_quantidade_id=(
                    get_regra_id(session, componente.codigo_regra)
                    if componente.codigo_regra
                    else None
                ),
                obrigatorio=True,
                ativo=True,
                zona_aplicacao=GERAL,
                dimensao_referencia=COMP,
                numero_topos=0,
                modo_quantidade=TOTAL,
                prioridade_valueset=1,
                formula_comp=componente.formula_comp,
            )
        )
        criados += 1
    session.flush()

    return criados


def criar_conjuntos(session: Session) -> tuple[int, int, int]:
    """Criar os conjuntos em falta. Devolve (criados, reutilizados, componentes)."""
    criados = 0
    reutilizados = 0
    componentes = 0

    for seed in CONJUNTOS:
        if get_peca(session, seed.codigo) is not None:
            reutilizados += 1
            print(f"Conjunto {seed.codigo} ja existe, mantido")
            continue

        conjunto = DefPeca(
            codigo=seed.codigo,
            nome=seed.nome,
            nome_biblioteca=seed.nome_biblioteca,
            descricao=seed.descricao,
            grupo=GRUPO_FERRAGENS,
            subgrupo=seed.subfamilia,
            tipo_peca=COMPOSTA,
            natureza=CONJUNTO,
            orientacao=NEUTRA,
            funcao=FUNCAO_FERRAGEM,
            permite_acabamento=False,
            sem_material=True,
            ativo=True,
        )
        session.add(conjunto)
        session.flush()

        componentes += criar_componentes(session, conjunto, seed)
        criados += 1
        print(f"Conjunto {seed.codigo} criado ({seed.nome})")

    return criados, reutilizados, componentes


def adicionar_as_bibliotecas(session: Session) -> int:
    """Mostrar as peças novas a quem tem biblioteca personalizada."""
    codigos = [seed.codigo for seed in PECAS] + [seed.codigo for seed in CONJUNTOS]
    pecas_ids = [
        peca.id
        for peca in (get_peca(session, codigo) for codigo in codigos)
        if peca is not None
    ]
    if not pecas_ids:
        return 0

    users_com_biblioteca = session.execute(
        select(DefPecaUserPref.user_id).distinct()
    ).scalars().all()

    criadas = 0
    for user_id in users_com_biblioteca:
        for peca_id in pecas_ids:
            existente = session.execute(
                select(DefPecaUserPref).where(
                    DefPecaUserPref.user_id == user_id,
                    DefPecaUserPref.def_peca_id == peca_id,
                )
            ).scalar_one_or_none()
            if existente is not None:
                continue

            session.add(
                DefPecaUserPref(user_id=user_id, def_peca_id=peca_id, favorito=False)
            )
            criadas += 1

    session.flush()
    return criadas


def seed_ferragens_spp(session: Session) -> FerragensSppResult:
    """Criar chaves, regras, ferragens e conjuntos em falta (idempotente)."""
    chaves = criar_chaves(session)
    regras = criar_regras(session)
    pecas, pecas_reutilizadas = criar_pecas(session)
    conjuntos, conjuntos_reutilizados, componentes = criar_conjuntos(session)
    prefs = adicionar_as_bibliotecas(session)

    session.commit()

    return FerragensSppResult(
        chaves_criadas=chaves,
        regras_criadas=regras,
        pecas_criadas=pecas,
        conjuntos_criados=conjuntos,
        componentes_criados=componentes,
        reutilizados=pecas_reutilizadas + conjuntos_reutilizados,
        prefs_criadas=prefs,
    )


def print_summary(result: FerragensSppResult) -> None:
    """Escrever o resumo final para o utilizador."""
    print("Resumo final")
    print(f"Chaves de ferragem criadas: {result.chaves_criadas}")
    print(f"Regras de quantidade criadas: {result.regras_criadas}")
    print(f"Ferragens criadas: {result.pecas_criadas}")
    print(f"Conjuntos criados: {result.conjuntos_criados}")
    print(f"Associados criados: {result.componentes_criados}")
    print(f"Pecas mantidas (ja existiam): {result.reutilizados}")
    print(f"Linhas de biblioteca de utilizador criadas: {result.prefs_criadas}")
    print(
        "Nota: nos modelos ValueSet em uso, acrescente uma linha por cada chave "
        "nova com o artigo comprado, senao as ferragens ficam sem preço."
    )


def main() -> int:
    """Criar as ferragens SPP na base de dados configurada."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = seed_ferragens_spp(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
