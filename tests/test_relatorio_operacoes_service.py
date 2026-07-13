"""Tests for the industrial operation-line report."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.services.relatorio_operacoes_service import RelatorioOperacoesService


def _operacao(codigo, tipo, *, ordem=1, origem="Peça congelada"):
    return SimpleNamespace(
        ordem=ordem,
        codigo=codigo,
        nome=codigo.title(),
        tipo_operacao=tipo,
        maquina=f"MAQ_{tipo}",
        origem=origem,
        acao=None,
        regra_calculo="FIXA",
        quantidade_base=Decimal("1"),
        tempo_setup_minutos=Decimal("0.5"),
        tempo_por_unidade_minutos=Decimal("1"),
        unidade_tempo="PECA",
    )


def _linha(**kwargs):
    valores = dict(
        id=10,
        ativo=True,
        orcamento_item_id=1,
        tipo_linha="PECA",
        codigo="PORTA",
        def_peca_codigo="PORTA",
        descricao="Porta",
        quantidade=Decimal("3"),
        custo_corte=Decimal("5"),
        custo_orlagem=None,
        custo_cnc=Decimal("10"),
        custo_montagem_manual=None,
        custo_producao=Decimal("15"),
        tempo_corte=Decimal("2"),
        tempo_orlagem=None,
        tempo_cnc=Decimal("4"),
        tempo_montagem=None,
        tempo_manual=None,
    )
    valores.update(kwargs)
    return SimpleNamespace(**valores)


def test_atribuicao_nao_duplica_custo_do_mesmo_centro() -> None:
    linha = _linha(custo_producao=Decimal("30"))  # fator de produção 2
    operacoes = [
        _operacao("CORTE", "CORTE", ordem=1),
        _operacao("CNC_1", "CNC", ordem=2),
        _operacao("CNC_2", "CNC", ordem=3),
    ]

    custos = RelatorioOperacoesService._custos_atribuidos(
        linha, operacoes, Decimal("2")
    )

    assert custos == {0: Decimal("20"), 1: Decimal("40"), 2: None}
    assert sum((valor or Decimal("0") for valor in custos.values())) == Decimal("60")


def test_relatorio_lista_operacoes_e_linha_sem_operacoes() -> None:
    service = object.__new__(RelatorioOperacoesService)
    service.item_repository = SimpleNamespace(
        list_items_by_versao=lambda _id: [
            SimpleNamespace(
                id=1,
                ordem=1,
                codigo="RP01",
                item="Roupeiro",
                quantidade=Decimal("2"),
            )
        ]
    )
    service.custeio_repository = SimpleNamespace(
        list_by_orcamento_versao=lambda _id: [
            _linha(id=10),
            _linha(
                id=11,
                tipo_linha="FERRAGEM",
                codigo="DOBRADICA",
                custo_corte=None,
                custo_cnc=None,
                custo_producao=None,
            ),
        ]
    )
    service.linha_service = SimpleNamespace(
        listar_operacoes_efetivas_da_linha=lambda linha_id: (
            [_operacao("CNC", "CNC", origem="Edição local")]
            if linha_id == 10
            else []
        )
    )

    resultado = service.listar_da_versao(2)

    assert len(resultado) == 2
    assert resultado[0].quantidade_total == Decimal("6")
    assert resultado[0].origem == "Edição local"
    assert resultado[1].operacao == "(sem operações)"
    assert resultado[1].diagnostico
