"""Assisted migration report for the phased evolution (phase 7).

Reads the database and reports, phase by phase, how the legacy data was
migrated and whether anything needs attention. ``aplicar_correcoes`` fixes
the two deterministic gaps in place:

- versions that still only have the legacy ``enc_phc`` value get their child
  PHC-order record (phase 5);
- the module-category table is seeded/completed with any code still used by
  modules (phase 6).

Nothing here recalculates budgets, prices or margins.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, inspect as sa_inspect, select, text
from sqlalchemy.orm import Session

from app.models import (
    DefMargemPadrao,
    DefModulo,
    DefModuloCategoria,
    OrcamentoItem,
    OrcamentoItemCusteioLinha,
    OrcamentoVersao,
    OrcamentoVersaoEncomendaPhc,
)
from app.services.def_modulo_categoria_service import DefModuloCategoriaService


REVISAO_ESPERADA = "20260729_68"


@dataclass(frozen=True)
class LinhaRelatorio:
    """One line of the integration report."""

    fase: str
    descricao: str
    valor: str
    atencao: bool = False


@dataclass(frozen=True)
class RelatorioIntegracao:
    """Full integration report of the phased evolution."""

    linhas: list[LinhaRelatorio] = field(default_factory=list)

    @property
    def ocorrencias(self) -> list[LinhaRelatorio]:
        return [linha for linha in self.linhas if linha.atencao]


@dataclass(frozen=True)
class ResultadoCorrecoes:
    """What aplicar_correcoes changed."""

    encomendas_materializadas: int
    categorias_criadas: int


class IntegracaoFasesService:
    """Application service for the phase-7 integration report."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ----- report -----

    def gerar_relatorio(self) -> RelatorioIntegracao:
        linhas: list[LinhaRelatorio] = []
        linhas.append(self._linha_revisao())
        linhas.extend(self._linhas_fase_2_orlas())
        linhas.extend(self._linhas_fase_3_simplificado())
        linhas.extend(self._linhas_fase_4_margens())
        linhas.extend(self._linhas_fase_5_encomendas())
        linhas.extend(self._linhas_fase_6_categorias())
        return RelatorioIntegracao(linhas=linhas)

    def _linha_revisao(self) -> LinhaRelatorio:
        versao = self._revisao_alembic()
        if versao is None:
            return LinhaRelatorio(
                fase="Base",
                descricao="Revisão alembic",
                valor="tabela alembic_version não encontrada",
                atencao=True,
            )
        return LinhaRelatorio(
            fase="Base",
            descricao="Revisão alembic",
            valor=versao,
            atencao=versao != REVISAO_ESPERADA,
        )

    def _revisao_alembic(self) -> str | None:
        # Inspect through the session's OWN connection: a fresh engine-level
        # connection would roll back uncommitted session state on sqlite.
        inspector = sa_inspect(self.session.connection())
        if not inspector.has_table("alembic_version"):
            return None
        return self.session.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()

    def _linhas_fase_2_orlas(self) -> list[LinhaRelatorio]:
        total = self._contar(select(func.count(OrcamentoItemCusteioLinha.id)))
        com_snapshot = self._contar(
            select(func.count(OrcamentoItemCusteioLinha.id)).where(
                (OrcamentoItemCusteioLinha.preco_orla_0_4_m2.is_not(None))
                | (OrcamentoItemCusteioLinha.preco_orla_1_0_m2.is_not(None))
            )
        )
        return [
            LinhaRelatorio(
                fase="Fase 2",
                descricao="Linhas de custeio com preço de orla local (€/m²)",
                valor=f"{com_snapshot} de {total} "
                "(as restantes usam o fallback da matéria-prima)",
            )
        ]

    def _linhas_fase_3_simplificado(self) -> list[LinhaRelatorio]:
        por_modalidade = dict(
            self.session.execute(
                select(
                    OrcamentoItem.modalidade_custeio,
                    func.count(OrcamentoItem.id),
                ).group_by(OrcamentoItem.modalidade_custeio)
            ).all()
        )
        standard = int(por_modalidade.get("STANDARD", 0))
        simplificado = int(por_modalidade.get("SIMPLIFICADO", 0))
        outros = sum(
            int(quantidade)
            for modalidade, quantidade in por_modalidade.items()
            if modalidade not in ("STANDARD", "SIMPLIFICADO")
        )
        linhas = [
            LinhaRelatorio(
                fase="Fase 3",
                descricao="Items por modalidade de custeio",
                valor=f"Standard: {standard} · Simplificado: {simplificado}",
            )
        ]
        if outros:
            linhas.append(
                LinhaRelatorio(
                    fase="Fase 3",
                    descricao="Items com modalidade desconhecida",
                    valor=str(outros),
                    atencao=True,
                )
            )
        return linhas

    def _linhas_fase_4_margens(self) -> list[LinhaRelatorio]:
        por_perfil = dict(
            self.session.execute(
                select(
                    OrcamentoVersao.perfil_margens,
                    func.count(OrcamentoVersao.id),
                ).group_by(OrcamentoVersao.perfil_margens)
            ).all()
        )
        resumo = " · ".join(
            f"{perfil}: {quantidade}"
            for perfil, quantidade in sorted(por_perfil.items())
        )
        legadas = self._contar(
            select(func.count(DefMargemPadrao.id)).where(
                DefMargemPadrao.ambito == "UTILIZADOR"
            )
        )
        return [
            LinhaRelatorio(
                fase="Fase 4",
                descricao="Versões por perfil de margens",
                valor=resumo or "sem versões",
            ),
            LinhaRelatorio(
                fase="Fase 4",
                descricao="Margens UTILIZADOR antigas preservadas (histórico)",
                valor=str(legadas),
            ),
        ]

    def _linhas_fase_5_encomendas(self) -> list[LinhaRelatorio]:
        com_enc = self._contar(
            select(func.count(OrcamentoVersao.id)).where(
                OrcamentoVersao.enc_phc.is_not(None),
                func.trim(OrcamentoVersao.enc_phc) != "",
            )
        )
        registos = self._contar(
            select(func.count(OrcamentoVersaoEncomendaPhc.id))
        )
        legadas = len(self._versoes_enc_phc_sem_filhos())
        espelho_errado = len(self._versoes_espelho_divergente())
        linhas = [
            LinhaRelatorio(
                fase="Fase 5",
                descricao="Versões com Nº Enc PHC / registos de encomendas",
                valor=f"{com_enc} versões · {registos} encomendas registadas",
            )
        ]
        if legadas:
            linhas.append(
                LinhaRelatorio(
                    fase="Fase 5",
                    descricao=(
                        "Versões antigas só com enc_phc (sem registo filho; "
                        "use --corrigir para materializar)"
                    ),
                    valor=str(legadas),
                    atencao=True,
                )
            )
        if espelho_errado:
            linhas.append(
                LinhaRelatorio(
                    fase="Fase 5",
                    descricao="Versões cujo enc_phc difere da encomenda principal",
                    valor=str(espelho_errado),
                    atencao=True,
                )
            )
        return linhas

    def _versoes_enc_phc_sem_filhos(self) -> list[int]:
        subquery = select(OrcamentoVersaoEncomendaPhc.orcamento_versao_id)
        return list(
            self.session.execute(
                select(OrcamentoVersao.id).where(
                    OrcamentoVersao.enc_phc.is_not(None),
                    func.trim(OrcamentoVersao.enc_phc) != "",
                    OrcamentoVersao.id.not_in(subquery),
                )
            ).scalars()
        )

    def _versoes_espelho_divergente(self) -> list[int]:
        principais = dict(
            self.session.execute(
                select(
                    OrcamentoVersaoEncomendaPhc.orcamento_versao_id,
                    OrcamentoVersaoEncomendaPhc.numero,
                ).where(OrcamentoVersaoEncomendaPhc.is_principal.is_(True))
            ).all()
        )
        if not principais:
            return []
        divergentes = []
        rows = self.session.execute(
            select(OrcamentoVersao.id, OrcamentoVersao.enc_phc).where(
                OrcamentoVersao.id.in_(principais.keys())
            )
        ).all()
        for versao_id, enc_phc in rows:
            if (enc_phc or "").strip() != principais[versao_id].strip():
                divergentes.append(versao_id)
        return divergentes

    def _linhas_fase_6_categorias(self) -> list[LinhaRelatorio]:
        total = self._contar(select(func.count(DefModuloCategoria.id)))
        ativas = self._contar(
            select(func.count(DefModuloCategoria.id)).where(
                DefModuloCategoria.ativo.is_(True)
            )
        )
        orfas = len(self._categorias_de_modulos_sem_registo())
        linhas = [
            LinhaRelatorio(
                fase="Fase 6",
                descricao="Categorias de módulos (ativas/total)",
                valor=f"{ativas}/{total}",
                atencao=total == 0,
            )
        ]
        if orfas:
            linhas.append(
                LinhaRelatorio(
                    fase="Fase 6",
                    descricao=(
                        "Códigos de categoria usados por módulos sem registo "
                        "(use --corrigir para importar)"
                    ),
                    valor=str(orfas),
                    atencao=True,
                )
            )
        return linhas

    def _categorias_de_modulos_sem_registo(self) -> list[str]:
        registadas = set(
            self.session.execute(select(DefModuloCategoria.codigo)).scalars()
        )
        usadas = set(
            self.session.execute(select(DefModulo.categoria).distinct()).scalars()
        )
        return sorted(
            codigo
            for codigo in usadas
            if codigo and codigo.strip() and codigo not in registadas
        )

    # ----- assisted fixes -----

    def aplicar_correcoes(self) -> ResultadoCorrecoes:
        """Apply the deterministic fixes (idempotent); commits."""
        encomendas = 0
        for versao_id in self._versoes_enc_phc_sem_filhos():
            versao = self.session.get(OrcamentoVersao, versao_id)
            self.session.add(
                OrcamentoVersaoEncomendaPhc(
                    orcamento_versao_id=versao_id,
                    numero=versao.enc_phc.strip(),
                    is_principal=True,
                )
            )
            encomendas += 1
        self.session.flush()

        antes = self._contar(select(func.count(DefModuloCategoria.id)))
        DefModuloCategoriaService(self.session).garantir_seed()
        depois = self._contar(select(func.count(DefModuloCategoria.id)))

        self.session.commit()
        return ResultadoCorrecoes(
            encomendas_materializadas=encomendas,
            categorias_criadas=depois - antes,
        )

    # ----- helpers -----

    def _contar(self, statement) -> int:
        return int(self.session.execute(statement).scalar_one())


def formatar_relatorio(relatorio: RelatorioIntegracao) -> str:
    """Render the report as aligned text for the console/log."""
    linhas_texto = ["Relatório de integração das fases (V3)", "=" * 46]
    for linha in relatorio.linhas:
        marcador = "[ATENÇÃO] " if linha.atencao else ""
        linhas_texto.append(
            f"{linha.fase:8} | {marcador}{linha.descricao}: {linha.valor}"
        )
    ocorrencias = relatorio.ocorrencias
    linhas_texto.append("-" * 46)
    if ocorrencias:
        linhas_texto.append(
            f"{len(ocorrencias)} ocorrência(s) a rever — ver linhas [ATENÇÃO]."
        )
    else:
        linhas_texto.append("Sem ocorrências: dados antigos íntegros.")
    return "\n".join(linhas_texto)
