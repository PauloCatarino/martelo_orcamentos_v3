"""Tests for production service helpers."""

from __future__ import annotations

import inspect


def test_producao_service_has_detail_update_methods() -> None:
    from app.services.producao_service import ProducaoService

    assert hasattr(ProducaoService, "obter_processo")
    assert hasattr(ProducaoService, "atualizar_processo")


def test_producao_service_lista_do_mais_antigo_para_o_mais_recente() -> None:
    from app.services.producao_service import ProducaoService

    source = inspect.getsource(ProducaoService.listar_processos)

    assert "Producao.ano.asc()" in source
    assert "Producao.num_enc_phc.asc()" in source
    assert "Producao.versao_obra.asc()" in source
    assert "Producao.versao_plano.asc()" in source


def test_campos_editaveis_filtra_apenas_campos_do_formulario() -> None:
    from app.services.producao_service import campos_editaveis

    data = {
        "estado": "Produção",
        "responsavel": "ana",
        "ref_cliente": "REF-A",
        "obra": "Cozinha",
        "localizacao": "Lisboa",
        "data_inicio": "2026-06-01",
        "data_entrega": "15-06-2026",
        "tipo_pasta": "Encomenda de Cliente",
        "descricao_artigos": "Artigos",
        "materias_usados": "MDF",
        "descricao_producao": "Produzir",
        "notas1": "N1",
        "notas2": "N2",
        "notas3": "N3",
        "codigo_processo": "26.1028_01_01",
        "ano": "2026",
        "num_enc_phc": "1028",
        "cliente_id": 1,
        "orcamento_id": 2,
        "created_by_id": 3,
        "updated_by_id": 4,
    }

    assert campos_editaveis(data) == {
        "estado": "Produção",
        "responsavel": "ana",
        "ref_cliente": "REF-A",
        "obra": "Cozinha",
        "localizacao": "Lisboa",
        "data_inicio": "2026-06-01",
        "data_entrega": "15-06-2026",
        "tipo_pasta": "Encomenda de Cliente",
        "descricao_artigos": "Artigos",
        "materias_usados": "MDF",
        "descricao_producao": "Produzir",
        "notas1": "N1",
        "notas2": "N2",
        "notas3": "N3",
    }
