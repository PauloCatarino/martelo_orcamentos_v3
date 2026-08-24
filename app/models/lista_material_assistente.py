"""Persistência do Assistente Lista Material e do Centro de PDFs.

Estas tabelas são deliberadamente independentes de ``def_materias_primas``.
O catálogo de orçamentação não é uma fonte operacional para placa/orla.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ListaMaterialPerfil(Base):
    __tablename__ = "lm_assistente_perfis"
    __table_args__ = (
        UniqueConstraint("user_id", "cliente_chave", name="uq_lm_perfil_user_cliente"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    cliente_chave: Mapped[str] = mapped_column(String(160), nullable=False, server_default="")
    puxador_default: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lacagem_formal: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    configuracao_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ListaMaterialModulo(Base):
    __tablename__ = "lm_assistente_modulos"
    __table_args__ = (
        UniqueConstraint("user_id", "cliente_chave", "modulo", name="uq_lm_modulo_ambito"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    cliente_chave: Mapped[str] = mapped_column(String(160), nullable=False, server_default="")
    modulo: Mapped[str] = mapped_column(String(80), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ListaMaterialObraConfig(Base):
    __tablename__ = "lm_assistente_obras"
    __table_args__ = (Index("ix_lm_obra_producao", "producao_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    producao_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cliente_chave: Mapped[str] = mapped_column(String(160), nullable=False, server_default="")
    workbook_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    puxador_obra: Mapped[str | None] = mapped_column(String(255), nullable=True)
    puxadores_excecoes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    modulos_json: Mapped[str] = mapped_column(Text, nullable=False)
    configuracao_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class ListaMaterialExecucao(Base):
    __tablename__ = "lm_assistente_execucoes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    obra_config_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    producao_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, server_default="iniciada")
    resumo_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ListaMaterialSugestao(Base):
    __tablename__ = "lm_assistente_sugestoes"
    __table_args__ = (Index("ix_lm_sug_exec_estado", "execucao_id", "estado"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execucao_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    folha: Mapped[str] = mapped_column(String(120), nullable=False)
    linha: Mapped[int | None] = mapped_column(Integer, nullable=True)
    campo: Mapped[str] = mapped_column(String(120), nullable=False)
    original: Mapped[str | None] = mapped_column(Text, nullable=True)
    sugerido: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    confianca: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, server_default="0")
    estado: Mapped[str] = mapped_column(String(30), nullable=False, server_default="pendente")
    decidido_por_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    decidido_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ListaMaterialAliasPlaca(Base):
    __tablename__ = "lm_material_placa_aliases"
    __table_args__ = (
        UniqueConstraint("texto_normalizado", "user_id", "cliente_chave", name="uq_lm_alias_ambito"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    texto_original: Mapped[str] = mapped_column(String(500), nullable=False)
    texto_normalizado: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    placa_externa_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    cliente_chave: Mapped[str] = mapped_column(String(160), nullable=False, server_default="")
    origem: Mapped[str] = mapped_column(String(40), nullable=False, server_default="historico")
    estado: Mapped[str] = mapped_column(String(30), nullable=False, server_default="candidato")
    confianca: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, server_default="0")
    suporte: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    confirmado_por_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    evidencia_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ListaMaterialRelacaoOrla(Base):
    __tablename__ = "lm_material_orla_relacoes"
    __table_args__ = (
        UniqueConstraint("material_normalizado", "orla_normalizada", "user_id", "cliente_chave", name="uq_lm_orla_ambito"),
        Index("ix_lm_orla_material_estado", "material_normalizado", "estado"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    material_normalizado: Mapped[str] = mapped_column(String(255), nullable=False)
    placa_externa_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    orla_normalizada: Mapped[str] = mapped_column(String(255), nullable=False)
    espessura_orla: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    cliente_chave: Mapped[str] = mapped_column(String(160), nullable=False, server_default="")
    origem: Mapped[str] = mapped_column(String(40), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, server_default="candidato")
    confianca: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, server_default="0")
    suporte: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    confirmacoes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    rejeicoes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    confirmado_por_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    primeira_utilizacao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ultima_utilizacao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ListaMaterialPlacaSnapshot(Base):
    __tablename__ = "lm_armazem_placas_snapshot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    codigo_externo: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    descricao: Mapped[str] = mapped_column(String(500), nullable=False)
    comprimento: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    largura: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    espessura: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    unidade: Mapped[str] = mapped_column(String(20), nullable=False, server_default="mm")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    stock: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    reservado: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    disponivel: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    source_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class ListaMaterialBarraReceita(Base):
    __tablename__ = "lm_barra_receitas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    descricao_normalizada: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    material_normalizado: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    cliente_chave: Mapped[str] = mapped_column(String(160), nullable=False, server_default="")
    largura: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    comprimento: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    formula: Mapped[str | None] = mapped_column(String(255), nullable=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, server_default="candidato")
    suporte: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class ListaMaterialCncOperacao(Base):
    __tablename__ = "lm_cnc_operacoes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execucao_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(160), nullable=False)
    lado: Mapped[str] = mapped_column(String(30), nullable=False)
    operacao: Mapped[str] = mapped_column(String(80), nullable=False, server_default="CNC_FRESAR")
    orla_original: Mapped[str | None] = mapped_column(String(500), nullable=True)
    orla_resolvida: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, server_default="pendente")


class ListaMaterialPdfDocumento(Base):
    __tablename__ = "lm_pdf_documentos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    identificador: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)
    origem_tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    origem_valor: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_ficheiro: Mapped[str] = mapped_column(String(255), nullable=False)
    combinavel: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    prerequisitos_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class ListaMaterialPdfPreset(Base):
    __tablename__ = "lm_pdf_presets"
    __table_args__ = (UniqueConstraint("user_id", "cliente_chave", "nome", name="uq_lm_pdf_preset"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    cliente_chave: Mapped[str] = mapped_column(String(160), nullable=False, server_default="")
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    documentos_json: Mapped[str] = mapped_column(Text, nullable=False)
    exportar_separados: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    criar_pacote: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    ultimo_usado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    predefinido: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ListaMaterialPdfExportacao(Base):
    __tablename__ = "lm_pdf_exportacoes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    producao_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    workbook_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    destino: Mapped[str] = mapped_column(String(1024), nullable=False)
    documentos_json: Mapped[str] = mapped_column(Text, nullable=False)
    resultado_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, server_default="iniciada")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
