"""Tests for the V2 production import helpers."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from scripts import importar_producao_v2 as importer


def test_mapear_estado_planeamento_para_desenho_e_passthrough() -> None:
    assert importer.mapear_estado("Planeamento") == "Desenho"
    assert importer.mapear_estado("Arquivado") == "Arquivado"
    assert importer.mapear_estado("Produção") == "Produção"
    assert importer.mapear_estado("Finalizado") == "Finalizado"


def test_mapear_linha_copia_campos_de_negocio_sem_ids_v2() -> None:
    created_at = datetime(2025, 1, 2, 10, 30)
    updated_at = datetime(2025, 2, 3, 11, 45)
    v2_row = {
        "id": 99,
        "codigo_processo": "26.1028_01_01",
        "ano": "2026",
        "num_enc_phc": "1028",
        "versao_obra": "01",
        "versao_plano": "02",
        "orcamento_id": 123,
        "client_id": 456,
        "cliente_id": 789,
        "responsavel": "ana",
        "estado": "Planeamento",
        "nome_cliente": "Cliente Alfa",
        "nome_cliente_simplex": "cliente alfa",
        "num_cliente_phc": "C001",
        "ref_cliente": "REF-A",
        "num_orcamento": "260001",
        "versao_orc": "01",
        "obra": "Cozinha Lisboa",
        "localizacao": "Lisboa",
        "descricao_orcamento": "Descricao do orcamento",
        "data_inicio": "2026-06-01",
        "data_entrega": "2026/6/15",
        "preco_total": Decimal("1234.56"),
        "qt_artigos": 12,
        "descricao_artigos": "Artigos teste",
        "materias_usados": "MDF",
        "descricao_producao": "Descricao de producao",
        "notas1": "Nota 1",
        "notas2": "Nota 2",
        "notas3": "Nota 3",
        "imagem_path": "C:/imagens/a.png",
        "pasta_servidor": "\\\\srv\\obra",
        "tipo_pasta": "Encomenda de Cliente",
        "created_by": 1,
        "updated_by": 2,
        "created_by_id": 3,
        "updated_by_id": 4,
        "created_at": created_at,
        "updated_at": updated_at,
    }

    valores = importer.mapear_linha(v2_row)

    assert valores["codigo_processo"] == "26.1028_01_01"
    assert valores["ano"] == "2026"
    assert valores["num_enc_phc"] == "1028"
    assert valores["versao_obra"] == "01"
    assert valores["versao_plano"] == "02"
    assert valores["estado"] == "Desenho"
    assert valores["nome_cliente"] == "Cliente Alfa"
    assert valores["num_cliente_phc"] == "C001"
    assert valores["num_orcamento"] == "260001"
    assert valores["data_inicio"] == "01-06-2026"
    assert valores["data_entrega"] == "15-06-2026"
    assert valores["preco_total"] == Decimal("1234.56")
    assert valores["qt_artigos"] == 12
    assert valores["descricao_artigos"] == "Artigos teste"
    assert valores["materias_usados"] == "MDF"
    assert valores["descricao_producao"] == "Descricao de producao"
    assert valores["tipo_pasta"] == "Encomenda de Cliente"
    assert valores["created_at"] == created_at
    assert valores["updated_at"] == updated_at

    for forbidden_key in (
        "id",
        "client_id",
        "cliente_id",
        "orcamento_id",
        "created_by",
        "updated_by",
        "created_by_id",
        "updated_by_id",
    ):
        assert forbidden_key not in valores
