"""Corrigir a hierarquia porta -> dobradicas/puxador.

Uma porta dupla estava catalogada com PORTA_SIMPLES x 2, DOBRADICA e PUXADOR
como tres irmaos.  O motor de quantidades, corretamente, so multiplica pelos
ancestrais; por isso uma dobradica por porta ficava com 5 em vez de 2 x 5.

A definicao passa a reutilizar o conjunto de uma porta duas vezes.  Os snapshots
ja existentes no custeio e nos modulos sao apenas reparentados: nao se apagam
linhas, materiais, ferragens ou escolhas locais.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260816_86"
down_revision: str | Sequence[str] | None = "20260815_85"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PORTA_SIMPLES = "PORTA_SIMPLES"
PORTA_COM_DOBRADICA = "PORTA_SIMPLES+DOBRADICA"
PORTA_COM_DOBRADICA_PUXADOR = "PORTA_SIMPLES+DOBRADICA+PUXADOR"
PORTA_DUPLA = "PORTA_DUPLA+DOBRADICA+PUXADOR"
FERRAGENS_POR_PORTA = ("DOBRADICA", "PUXADOR")


def upgrade() -> None:
    ligacao = op.get_bind()
    _normalizar_catalogo(ligacao)
    _reparentear_linhas_custeio(ligacao)
    _reparentear_linhas_modulos(ligacao)


def _peca_id(ligacao, codigo: str) -> int | None:
    return ligacao.execute(
        sa.text("SELECT id FROM def_pecas WHERE codigo = :codigo LIMIT 1"),
        {"codigo": codigo},
    ).scalar_one_or_none()


def _normalizar_catalogo(ligacao) -> None:
    porta_simples_id = _peca_id(ligacao, PORTA_SIMPLES)
    porta_sem_puxador_id = _peca_id(ligacao, PORTA_COM_DOBRADICA)
    porta_com_puxador_id = _peca_id(ligacao, PORTA_COM_DOBRADICA_PUXADOR)
    porta_dupla_id = _peca_id(ligacao, PORTA_DUPLA)

    # Cada conjunto passa a ter dimensoes proprias. Os filhos leem sempre o
    # pai imediato, permitindo reutilizar o conjunto simples dentro do duplo.
    for peca_id in (
        porta_sem_puxador_id,
        porta_com_puxador_id,
        porta_dupla_id,
    ):
        if peca_id is None:
            continue
        ligacao.execute(
            sa.text(
                "UPDATE def_pecas "
                "SET formula_comp = 'HM', formula_larg = 'LM' "
                "WHERE id = :id"
            ),
            {"id": peca_id},
        )

    for conjunto_id in (porta_sem_puxador_id, porta_com_puxador_id):
        if conjunto_id is None or porta_simples_id is None:
            continue
        ligacao.execute(
            sa.text(
                "UPDATE def_peca_componentes "
                "SET formula_comp = 'PAI_COMP', formula_larg = 'PAI_LARG' "
                "WHERE def_peca_pai_id = :pai_id "
                "AND def_peca_componente_id = :filho_id AND ativo = 1"
            ),
            {"pai_id": conjunto_id, "filho_id": porta_simples_id},
        )

    if porta_dupla_id is None or porta_com_puxador_id is None:
        return

    # O primeiro associado da porta dupla deixa de ser apenas a chapa da porta:
    # passa a ser o conjunto completo de uma porta, usado duas vezes.
    if porta_simples_id is not None:
        ligacao.execute(
            sa.text(
                "UPDATE def_peca_componentes "
                "SET def_peca_componente_id = :novo_filho_id, "
                "referencia_componente = :novo_codigo, quantidade = 2, "
                "formula_comp = 'PAI_COMP', formula_larg = 'PAI_LARG/2' "
                "WHERE def_peca_pai_id = :pai_id "
                "AND def_peca_componente_id = :filho_antigo_id AND ativo = 1"
            ),
            {
                "novo_filho_id": porta_com_puxador_id,
                "novo_codigo": PORTA_COM_DOBRADICA_PUXADOR,
                "pai_id": porta_dupla_id,
                "filho_antigo_id": porta_simples_id,
            },
        )

    # As ferragens ja vivem dentro do conjunto simples. Mantem-se o historico
    # das associacoes antigas, apenas inativo, para nao criar duplicados.
    ligacao.execute(
        sa.text(
            "UPDATE def_peca_componentes c "
            "JOIN def_pecas f ON f.id = c.def_peca_componente_id "
            "SET c.ativo = 0 "
            "WHERE c.def_peca_pai_id = :pai_id "
            "AND f.codigo IN ('DOBRADICA', 'PUXADOR') AND c.ativo = 1"
        ),
        {"pai_id": porta_dupla_id},
    )


def _reparentear_linhas_custeio(ligacao) -> None:
    cabecalhos = ligacao.execute(
        sa.text(
            "SELECT id FROM orcamento_item_custeio_linhas "
            "WHERE ativo = 1 AND (def_peca_codigo = :codigo OR codigo = :codigo)"
        ),
        {"codigo": PORTA_DUPLA},
    ).scalars().all()

    for cabecalho_id in cabecalhos:
        porta = ligacao.execute(
            sa.text(
                "SELECT id, nivel FROM orcamento_item_custeio_linhas "
                "WHERE ativo = 1 AND linha_pai_id = :pai_id "
                "AND (def_peca_codigo = :codigo OR codigo = :codigo) "
                "ORDER BY ordem, id LIMIT 1"
            ),
            {"pai_id": cabecalho_id, "codigo": PORTA_SIMPLES},
        ).mappings().first()
        if porta is None:
            continue

        ligacao.execute(
            sa.text(
                "UPDATE orcamento_item_custeio_linhas "
                "SET linha_pai_id = :porta_id, nivel = :nivel "
                "WHERE ativo = 1 AND linha_pai_id = :cabecalho_id "
                "AND (def_peca_codigo IN ('DOBRADICA', 'PUXADOR') "
                "OR codigo IN ('DOBRADICA', 'PUXADOR'))"
            ),
            {
                "porta_id": porta["id"],
                "nivel": int(porta["nivel"] or 0) + 1,
                "cabecalho_id": cabecalho_id,
            },
        )


def _reparentear_linhas_modulos(ligacao) -> None:
    cabecalhos = ligacao.execute(
        sa.text(
            "SELECT id, def_modulo_id, ordem FROM def_modulo_linhas "
            "WHERE ativo = 1 AND (def_peca_codigo = :codigo OR codigo = :codigo)"
        ),
        {"codigo": PORTA_DUPLA},
    ).mappings().all()

    for cabecalho in cabecalhos:
        porta = ligacao.execute(
            sa.text(
                "SELECT id, ordem, nivel FROM def_modulo_linhas "
                "WHERE ativo = 1 AND def_modulo_id = :modulo_id "
                "AND linha_pai_ordem = :pai_ordem "
                "AND (def_peca_codigo = :codigo OR codigo = :codigo) "
                "ORDER BY ordem, id LIMIT 1"
            ),
            {
                "modulo_id": cabecalho["def_modulo_id"],
                "pai_ordem": cabecalho["ordem"],
                "codigo": PORTA_SIMPLES,
            },
        ).mappings().first()
        if porta is None:
            continue

        ligacao.execute(
            sa.text(
                "UPDATE def_modulo_linhas "
                "SET linha_pai_ordem = :porta_ordem, nivel = :nivel "
                "WHERE ativo = 1 AND def_modulo_id = :modulo_id "
                "AND linha_pai_ordem = :cabecalho_ordem "
                "AND (def_peca_codigo IN ('DOBRADICA', 'PUXADOR') "
                "OR codigo IN ('DOBRADICA', 'PUXADOR'))"
            ),
            {
                "porta_ordem": porta["ordem"],
                "nivel": int(porta["nivel"] or 0) + 1,
                "modulo_id": cabecalho["def_modulo_id"],
                "cabecalho_ordem": cabecalho["ordem"],
            },
        )


def downgrade() -> None:
    # Correcao aditiva de dados: nao se volta automaticamente a uma hierarquia
    # que produz quantidades erradas. Nenhuma tabela/coluna e removida.
    pass
