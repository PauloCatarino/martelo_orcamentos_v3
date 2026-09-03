"""DefMateriaPrimaComponente — os filhos de uma matéria-prima composta.

O Martelo orça uma ferragem como UM todo: a ``FER0015`` é uma dobradiça
completa, com um preço e uma linha no orçamento. O iMos exporta a mesma obra
desmontada — o copo numa linha, o calço noutra, cada um com a sua referência.

Cada linha desta tabela é um componente do conjunto: o que é, quantos entram
em UM conjunto, e as três moradas por onde esse componente aparece nas listas
do iMos (nome do artigo, Ref PHC, referência do fornecedor).

**O preço continua no pai.** Isto é um mapa de referências, não uma segunda
maneira de calcular o preço: assim o custeio, o snapshot de cada linha de
orçamento e os orçamentos já feitos não mudam nada.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.materia_prima_types import PAPEL_SECUNDARIO

if TYPE_CHECKING:
    from app.models.def_materia_prima import DefMateriaPrima
    from app.models.user import User


class DefMateriaPrimaComponente(Base):
    """Um componente (filho) de uma matéria-prima do catálogo."""

    __tablename__ = "def_materias_primas_componentes"
    __table_args__ = (
        Index("ix_def_mp_componentes_materia_prima_id", "materia_prima_id"),
        Index("ix_def_mp_componentes_papel", "papel"),
        # As três chaves da ponte ao iMos. Indexadas porque a importação de uma
        # obra procura por elas linha a linha.
        Index("ix_def_mp_componentes_nome_imos", "nome_imos"),
        Index("ix_def_mp_componentes_ref_phc", "ref_phc"),
        Index("ix_def_mp_componentes_ref_fornecedor", "ref_fornecedor_norm"),
        Index("ix_def_mp_componentes_ativo", "ativo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    materia_prima_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("def_materias_primas.id"), nullable=False
    )
    #: PRINCIPAL (conta os conjuntos) ou SECUNDARIO (só confere).
    papel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PAPEL_SECUNDARIO,
        server_default=PAPEL_SECUNDARIO,
    )
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Quantos deste componente entram em UM conjunto (1 copo, 1 calço, 2 pernos).
    quantidade: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("1"),
        server_default="1",
    )

    # --- As três chaves, por ordem de confiança ---------------------------
    #: 1.ª: o nome do artigo no iMos (BL_DOB_RETA_75B1550_pontear). É a
    #: identidade do artigo do lado do iMos e nunca vem vazia.
    nome_imos: Mapped[str | None] = mapped_column(String(150), nullable=True)
    #: 2.ª: a Ref PHC (FF00060). O iMos já usa este nome no artigo-mestre.
    ref_phc: Mapped[str | None] = mapped_column(String(100), nullable=True)
    #: 3.ª: a referência do fornecedor JÁ NORMALIZADA (75B1550, sem a marca
    #: colada nem os espaços a mais que o iMos escreve).
    ref_fornecedor_norm: Mapped[str | None] = mapped_column(String(150), nullable=True)
    #: A referência do fornecedor como veio, para se poder mostrar tal e qual.
    ref_fornecedor: Mapped[str | None] = mapped_column(String(150), nullable=True)

    #: Quando o filho TAMBÉM existe como matéria-prima própria, aponta-se para
    #: ela em vez de repetir os dados.
    componente_materia_prima_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("def_materias_primas.id"), nullable=True
    )
    #: Só quando o filho não é matéria-prima própria e se quer saber quanto
    #: vale sozinho. NÃO entra no preço do conjunto.
    preco_liquido: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)

    ordem: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Quem ensinou esta ligação e quando — é o registo de que o Manufactor do
    # PHC não deixa rasto e que aqui interessa ter.
    criado_por_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    alterado_por_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    materia_prima: Mapped["DefMateriaPrima"] = relationship(
        "DefMateriaPrima",
        foreign_keys=[materia_prima_id],
    )
    componente_materia_prima: Mapped["DefMateriaPrima | None"] = relationship(
        "DefMateriaPrima",
        foreign_keys=[componente_materia_prima_id],
    )
    criado_por: Mapped["User | None"] = relationship(
        "User", foreign_keys=[criado_por_id]
    )
    alterado_por: Mapped["User | None"] = relationship(
        "User", foreign_keys=[alterado_por_id]
    )
