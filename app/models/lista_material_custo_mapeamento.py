"""Associações operacionais partilhadas; não são configurações do sistema."""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ListaMaterialCustoMapeamento(Base):
    __tablename__ = 'lista_material_custo_mapeamentos'
    chave: Mapped[str] = mapped_column(String(100), primary_key=True)
    valor: Mapped[str] = mapped_column(Text, nullable=False)
