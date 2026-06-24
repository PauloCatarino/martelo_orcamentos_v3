"""Tests for production service helpers."""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models.producao import Producao


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _processo_producao(
    *,
    id: int = 1,
    ano: str = "2026",
    num_enc_phc: str = "1058",
    versao_obra: str = "01",
    versao_plano: str = "01",
) -> Producao:
    return Producao(
        id=id,
        codigo_processo=f"26.{num_enc_phc}_{versao_obra}_{versao_plano}",
        ano=ano,
        num_enc_phc=num_enc_phc,
        versao_obra=versao_obra,
        versao_plano=versao_plano,
        estado="Produção",
        tipo_pasta="Encomenda de Cliente",
        nome_cliente="JF VIVA",
        nome_cliente_simplex="JF_VIVA",
    )


def test_producao_service_has_detail_update_methods() -> None:
    from app.services.producao_service import ProducaoService

    assert hasattr(ProducaoService, "obter_processo")
    assert hasattr(ProducaoService, "atualizar_processo")


def test_producao_service_has_nova_versao_functions() -> None:
    import app.services.producao_service as service_module

    assert hasattr(service_module, "preparar_nova_versao")
    assert hasattr(service_module, "criar_nova_versao")
    assert hasattr(service_module, "listar_versoes_processo")
    assert hasattr(service_module, "codigo_processo_com_cliente")
    assert hasattr(service_module, "eliminar_processo")
    assert hasattr(service_module, "eliminar_processo_completo")


def test_gerar_codigo_processo_formata_chave() -> None:
    from app.services.producao_service import gerar_codigo_processo

    assert gerar_codigo_processo("2026", "475", "01", "01") == "26.0475_01_01"
    assert gerar_codigo_processo("2026", "_054", "1", "1") == "26.0054_01_01"
    assert gerar_codigo_processo("2026", "54", "001", "002") == "26.0054_01_02"


def test_codigo_processo_com_cliente_inclui_cliente_simplex() -> None:
    from app.services.producao_service import codigo_processo_com_cliente

    assert (
        codigo_processo_com_cliente(
            "2026",
            "1055",
            "02",
            "01",
            nome_simplex="RIOCRIATIVO",
        )
        == "26.1055_02_01_RIOCRIATIVO"
    )


def test_derivados_reagem_a_numero_versao_e_cliente() -> None:
    from app.services.producao_service import (
        codigo_processo_com_cliente,
        gerar_nome_enc_imos_ix,
        gerar_nome_plano_cut_rite,
    )

    assert (
        codigo_processo_com_cliente(
            "2026",
            "1055",
            "03",
            "02",
            nome_simplex="NOVO_CLIENTE",
        )
        == "26.1055_03_02_NOVO_CLIENTE"
    )
    assert (
        gerar_nome_plano_cut_rite(
            "2026",
            "1055",
            "03",
            "02",
            nome_cliente_simplex="NOVO_CLIENTE",
        )
        == "1055_03_02_26_NOVO_CLIENTE"
    )
    assert (
        gerar_nome_enc_imos_ix(
            "2026",
            "1055",
            "03",
            nome_cliente_simplex="NOVO_CLIENTE",
        )
        == "1055_03_26_NOVO_CLIENTE"
    )


def test_validar_conversao_regras_de_protecao() -> None:
    from app.services.producao_service import validar_conversao

    assert "Adjudicado" in validar_conversao(
        estado="Enviado",
        is_temporary=False,
        source_system="phc",
        num_cliente_phc="C001",
        enc_phc="475",
    )[0]
    assert "temporário" in validar_conversao(
        estado="Adjudicado",
        is_temporary=True,
        source_system="phc",
        num_cliente_phc="C001",
        enc_phc="475",
    )[0]
    assert "PHC" in validar_conversao(
        estado="Adjudicado",
        is_temporary=False,
        source_system="manual",
        num_cliente_phc="C001",
        enc_phc="475",
    )[0]
    assert "Nº Cliente PHC" in validar_conversao(
        estado="Adjudicado",
        is_temporary=False,
        source_system="phc",
        num_cliente_phc="",
        enc_phc="475",
    )[0]
    assert "Nº Enc PHC" in validar_conversao(
        estado="Adjudicado",
        is_temporary=False,
        source_system="phc",
        num_cliente_phc="C001",
        enc_phc="",
    )[0]
    assert (
        validar_conversao(
            estado="ADJUDICADO",
            is_temporary=False,
            source_system="PHC",
            num_cliente_phc="C001",
            enc_phc="475",
        )
        == []
    )


def test_producao_service_lista_do_mais_recente_para_o_mais_antigo() -> None:
    from app.services.producao_service import ProducaoService

    source = inspect.getsource(ProducaoService.listar_processos)

    assert "Producao.created_at.desc()" in source
    assert "Producao.ano.desc()" in source
    assert "Producao.num_enc_phc.desc()" in source


def test_campos_editaveis_filtra_apenas_campos_do_formulario() -> None:
    from app.services.producao_service import campos_editaveis

    data = {
        "codigo_processo": "26.1028_01_01_CLIENTE",
        "ano": "2026",
        "num_enc_phc": "1028",
        "versao_obra": "01",
        "versao_plano": "01",
        "cliente_id": 1,
        "nome_cliente": "Cliente",
        "nome_cliente_simplex": "CLIENTE",
        "num_cliente_phc": "C001",
        "num_orcamento": "12",
        "versao_orc": "02",
        "preco_total": "123.45",
        "qt_artigos": 4,
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
        "imagem_path": "C:/obra/imagem.png",
        "orcamento_id": 2,
        "created_by_id": 3,
        "updated_by_id": 4,
    }

    assert campos_editaveis(data) == {
        "codigo_processo": "26.1028_01_01_CLIENTE",
        "ano": "2026",
        "num_enc_phc": "1028",
        "versao_obra": "01",
        "versao_plano": "01",
        "cliente_id": 1,
        "nome_cliente": "Cliente",
        "nome_cliente_simplex": "CLIENTE",
        "num_cliente_phc": "C001",
        "num_orcamento": "12",
        "versao_orc": "02",
        "preco_total": "123.45",
        "qt_artigos": 4,
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
        "imagem_path": "C:/obra/imagem.png",
    }


def test_atualizar_processo_recusa_codigo_duplicado(session) -> None:
    from app.services.producao_service import ProducaoService

    existente = _processo_producao(
        id=1,
        num_enc_phc="1055",
        versao_obra="02",
        versao_plano="01",
    )
    existente.nome_cliente = "RIOCRIATIVO"
    existente.nome_cliente_simplex = "RIOCRIATIVO"
    existente.codigo_processo = "26.1055_02_01_RIOCRIATIVO"
    alvo = _processo_producao(
        id=2,
        num_enc_phc="1056",
        versao_obra="01",
        versao_plano="01",
    )
    alvo.nome_cliente = "OUTRO"
    alvo.nome_cliente_simplex = "OUTRO"
    alvo.codigo_processo = "26.1056_01_01_OUTRO"
    session.add_all([existente, alvo])
    session.commit()

    with pytest.raises(ValueError, match="codigo_processo"):
        ProducaoService(session).atualizar_processo(
            2,
            {
                "ano": "2026",
                "num_enc_phc": "1055",
                "versao_obra": "02",
                "versao_plano": "01",
                "nome_cliente": "RIOCRIATIVO",
                "nome_cliente_simplex": "RIOCRIATIVO",
                "data_inicio": "01-06-2026",
                "data_entrega": "02-06-2026",
            },
            updated_by_id=None,
        )


def test_preparar_nova_versao_sugere_cutrite_e_obra(session, monkeypatch) -> None:
    from app.services import producao_service as service_module
    import app.services.producao_pastas_service as pastas_module

    session.add(_processo_producao())
    session.commit()
    monkeypatch.setattr(
        service_module,
        "listar_pastas_enc_arvore",
        lambda *args, **kwargs: ("root", {}),
    )
    monkeypatch.setattr(
        pastas_module,
        "listar_versoes_obra_em_pastas",
        lambda *args, **kwargs: set(),
    )
    monkeypatch.setattr(
        pastas_module,
        "listar_versoes_plano_em_pastas",
        lambda *args, **kwargs: set(),
    )

    preparado = service_module.preparar_nova_versao(session, processo_id=1)

    assert preparado["existing_keys"] == {("01", "01")}
    assert preparado["sug_cutrite"] == ("01", "02")
    assert preparado["sug_obra"] == ("02", "01")


def test_criar_nova_versao_recusa_duplicado_db(session) -> None:
    from app.services.producao_service import criar_nova_versao

    session.add(_processo_producao())
    session.commit()

    with pytest.raises(ValueError, match="Ja existe"):
        criar_nova_versao(
            session,
            processo_id=1,
            versao_obra="01",
            versao_plano="01",
            criar_pasta=False,
            current_user_id=None,
        )
