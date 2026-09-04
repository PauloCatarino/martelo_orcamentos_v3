"""Uma operação manual tem de sobreviver ao ciclo gravar módulo → importar.

O módulo copiava a descrição e as quantidades e deixava para trás a máquina e
os minutos por unidade — que numa OPERACAO_MANUAL são o trabalho todo. A linha
voltava com o nome certo e **0 €**, e ninguém dava por isso: aconteceu num
bloco de gavetas que devia levar 50 € de montagem.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import (
    Cliente,
    DefMaquina,
    DefModulo,
    DefModuloLinha,
    Orcamento,
    OrcamentoItem,
    OrcamentoItemCusteioLinha,
    OrcamentoVersao,
)
from app.services.def_modulo_service import DefModuloService
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)


@pytest.fixture()
def cenario(session: Session):
    """Um item com uma montagem manual de 30 min/un a 40 €/h, e uma máquina."""
    cliente = Cliente(nome="Cliente Modulos", is_temporary=True)
    session.add(cliente)
    session.flush()
    orcamento = Orcamento(ano=2026, num_orcamento="260881", cliente_id=cliente.id)
    session.add(orcamento)
    session.flush()
    versao = OrcamentoVersao(
        orcamento_id=orcamento.id,
        numero_versao=1,
        codigo_versao="260881_01",
        estado="Falta Orçamentar",
        tipo_producao_default="STD",
    )
    session.add(versao)
    session.flush()
    item = OrcamentoItem(
        orcamento_versao_id=versao.id,
        ordem=1,
        codigo="LAVANDARIA",
        tipo_item="OUTRO",
        item="LAVANDARIA",
        quantidade=Decimal("1"),
        unidade="un",
    )
    session.add(item)

    maquina = DefMaquina(codigo="MANUAL", nome="Manual", custo_hora=Decimal("40"))
    session.add(maquina)
    session.flush()

    return item, maquina


def _guardar_e_importar(session, item, linha_ids, destino) -> list:
    """Grava as linhas como módulo e importa-o num item de destino."""
    modulo = DefModuloService(session).guardar_de_linhas_custeio(
        codigo="MOD_LAVANDARIA",
        nome="Módulo lavandaria",
        orcamento_item_id=item.id,
        linha_ids=linha_ids,
        ambito="GLOBAL",
    )
    session.flush()
    OrcamentoItemCusteioLinhaService(session).inserir_modulo_no_item(
        destino.id, modulo.modulo.id
    )
    session.flush()
    return list(
        session.execute(
            select(OrcamentoItemCusteioLinha).where(
                OrcamentoItemCusteioLinha.orcamento_item_id == destino.id
            )
        ).scalars()
    )


def test_a_operacao_manual_leva_a_maquina_e_os_minutos_para_o_modulo(
    session: Session, cenario
) -> None:
    item, maquina = cenario
    service = OrcamentoItemCusteioLinhaService(session)
    linha = service.inserir_operacao_manual(
        item.id,
        descricao="MONTAGEM GAVETA",
        def_maquina_id=maquina.id,
        tempo_minutos=Decimal("30"),
        quantidade=Decimal("3"),
    )

    resultado = DefModuloService(session).guardar_de_linhas_custeio(
        codigo="MOD_MONTAGEM",
        nome="Módulo montagem",
        orcamento_item_id=item.id,
        linha_ids=[linha.id],
        ambito="GLOBAL",
    )
    session.flush()

    linhas = session.execute(
        select(DefModuloLinha).where(
            DefModuloLinha.def_modulo_id == resultado.modulo.id
        )
    ).scalars().all()

    assert len(linhas) == 1
    assert linhas[0].tipo_linha == "OPERACAO_MANUAL"
    assert linhas[0].def_maquina_id == maquina.id
    assert linhas[0].minutos_unitarios == Decimal("30.0000")


def test_importar_o_modulo_devolve_o_tempo_e_o_custo(
    session: Session, cenario
) -> None:
    item, maquina = cenario
    service = OrcamentoItemCusteioLinhaService(session)
    linha = service.inserir_operacao_manual(
        item.id,
        descricao="MONTAGEM GAVETA",
        def_maquina_id=maquina.id,
        tempo_minutos=Decimal("30"),
        quantidade=Decimal("3"),
    )
    # 3 × 30 min = 90 min a 40 €/h = 60 €
    assert linha.custo_montagem_manual == Decimal("60.0000")

    destino = OrcamentoItem(
        orcamento_versao_id=item.orcamento_versao_id,
        ordem=2,
        codigo="LAVANDARIA_2",
        tipo_item="OUTRO",
        item="LAVANDARIA 2",
        quantidade=Decimal("1"),
        unidade="un",
    )
    session.add(destino)
    session.flush()

    criadas = _guardar_e_importar(session, item, [linha.id], destino)

    assert len(criadas) == 1
    importada = criadas[0]
    assert importada.descricao == "MONTAGEM GAVETA"
    assert importada.def_maquina_id == maquina.id
    assert importada.minutos_unitarios == Decimal("30.0000")
    assert importada.qt_und == Decimal("3")
    assert importada.tempo_manual == Decimal("90.0000")
    assert importada.custo_montagem_manual == Decimal("60.0000")


def test_modulo_antigo_sem_tempo_avisa_em_vez_de_ficar_calado(
    session: Session, cenario
) -> None:
    """Os módulos guardados antes disto ficam sem tempo: têm de gritar."""
    item, _maquina = cenario
    modulo = DefModulo(codigo="MOD_ANTIGO", nome="Módulo antigo", ativo=True)
    session.add(modulo)
    session.flush()
    session.add(
        DefModuloLinha(
            def_modulo_id=modulo.id,
            ordem=1,
            tipo_linha="OPERACAO_MANUAL",
            descricao="MONTAGEM GAVETEIRO",
            descricao_livre="MONTAGEM GAVETEIRO",
            qt_mod="1",
            qt_und="1",
            nivel=0,
            ativo=True,
        )
    )
    session.flush()

    resultado = OrcamentoItemCusteioLinhaService(session).inserir_modulo_no_item(
        item.id, modulo.id
    )
    session.flush()

    assert any("em falta" in aviso for aviso in resultado.avisos)

    criada = session.execute(
        select(OrcamentoItemCusteioLinha).where(
            OrcamentoItemCusteioLinha.orcamento_item_id == item.id
        )
    ).scalars().one()
    assert criada.descricao == "MONTAGEM GAVETEIRO"
    # E fica escrito na linha, para o aviso pós-«Atualizar» o apanhar.
    assert "em falta" in (criada.observacoes or "")
