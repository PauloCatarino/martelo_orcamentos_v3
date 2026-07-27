"""Photos and files attached to one occurrence ticket."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProducaoOcorrenciaAnexo(Base):
    """One file attached to a ticket — normalmente a foto que o cliente mandou.

    O ficheiro vive na pasta da obra (``…\\Ocorrencias\\T0007\\``); aqui guarda-se
    só o caminho. Guardar a imagem na base de dados fá-la-ia crescer depressa e
    tirava-a de onde toda a gente já vai buscar as coisas da obra.
    """

    __tablename__ = "producao_ocorrencia_anexos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ocorrencia_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("producao_ocorrencias.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    caminho: Mapped[str] = mapped_column(String(1024), nullable=False)
    #: Nome que o ficheiro tinha na origem — ajuda a perceber o que é.
    nome_original: Mapped[str | None] = mapped_column(String(255), nullable=True)
    legenda: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    ocorrencia = relationship("ProducaoOcorrencia", back_populates="anexos")
