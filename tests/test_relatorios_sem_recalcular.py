"""Os relatórios e as exportações LEEM o custeio; não o recalculam.

Cada exportação a partir dos Relatórios voltava a correr a pipeline completa do
custeio -- e a página já a tinha corrido ao abrir. No orçamento 260868 (30
itens, 2022 linhas) isso são ~27 s e ~27 000 consultas de cada vez: abrir os
relatórios e exportar quatro formatos custava cinco vezes o mesmo cálculo sobre
números que não mudaram entre eles.

Quem atualiza os custos é o botão "Atualizar Custos" do orçamento. Para nunca
sair um relatório com números velhos, a versão guarda a impressão digital do
custeio no momento do último recálculo -- e é isso que estes testes protegem.
"""

from __future__ import annotations

import inspect
from decimal import Decimal

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import OrcamentoItem, OrcamentoVersao
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.services.orcamento_export_service import OrcamentoExportService
from app.services.plano_corte_service import PlanoCorteService
from app.services.relatorio_consumos_service import RelatorioConsumosService


def _criar_versao(session) -> int:
    versao = OrcamentoVersao(
        orcamento_id=1, numero_versao=1, codigo_versao="V1", estado="ATIVO",
    )
    session.add(versao)
    session.flush()
    return versao.id


def _criar_item(session, versao_id, *, ordem=1, quantidade=1) -> int:
    item = OrcamentoItem(
        orcamento_versao_id=versao_id, ordem=ordem, tipo_item="OUTRO",
        item=f"Item {ordem}", quantidade=Decimal(quantidade),
    )
    session.add(item)
    session.flush()
    return item.id


def _linha(session, item_id, **kw):
    base = dict(
        orcamento_item_id=item_id, tipo_linha="PECA", descricao="Lateral",
        unidade="m2", quantidade=Decimal("1"), area_m2=Decimal("1"),
        comp_mp=Decimal("2000"), larg_mp=Decimal("1000"), esp_mp=Decimal("19"),
        preco_liquido=Decimal("5"), desperdicio_percentagem=Decimal("0"),
        custo_mp=Decimal("8"), custo_total=Decimal("8"), ref_le="LE01",
        descricao_no_orcamento="AGL", nivel=0, ativo=True,
    )
    base.update(kw)
    return OrcamentoItemCusteioLinhaRepository(session).create_linha(**base)


# ----- Impressão digital -----


def test_impressao_digital_muda_quando_o_custeio_muda(session) -> None:
    versao_id = _criar_versao(session)
    item_id = _criar_item(session, versao_id)
    linha = _linha(session, item_id)
    session.commit()

    servico = RelatorioConsumosService(session)
    antes = servico.impressao_digital_custeio(versao_id)
    assert antes == servico.impressao_digital_custeio(versao_id)  # estável

    OrcamentoItemCusteioLinhaRepository(session).update_linha(
        id=linha.id, custo_total=Decimal("99")
    )
    session.commit()

    assert servico.impressao_digital_custeio(versao_id) != antes


def test_impressao_digital_muda_ao_apagar_e_ao_juntar_linhas(session) -> None:
    versao_id = _criar_versao(session)
    item_id = _criar_item(session, versao_id)
    _linha(session, item_id)
    segunda = _linha(session, item_id, descricao="Prateleira")
    session.commit()

    servico = RelatorioConsumosService(session)
    com_duas = servico.impressao_digital_custeio(versao_id)

    OrcamentoItemCusteioLinhaRepository(session).delete_linhas([segunda.id])
    session.commit()
    com_uma = servico.impressao_digital_custeio(versao_id)
    assert com_uma != com_duas

    _linha(
        session, item_id, descricao="Prateleira nova",
        custo_mp=Decimal("30"), custo_total=Decimal("30"),
    )
    session.commit()
    assert servico.impressao_digital_custeio(versao_id) not in (com_uma, com_duas)


def test_impressao_digital_muda_com_as_margens_da_versao(session) -> None:
    versao_id = _criar_versao(session)
    item_id = _criar_item(session, versao_id)
    _linha(session, item_id)
    session.commit()

    servico = RelatorioConsumosService(session)
    antes = servico.impressao_digital_custeio(versao_id)

    session.get(OrcamentoVersao, versao_id).margem_lucro_pct = Decimal("15")
    session.commit()

    assert servico.impressao_digital_custeio(versao_id) != antes


def test_versao_nunca_recalculada_conta_como_desatualizada(session) -> None:
    versao_id = _criar_versao(session)
    _criar_item(session, versao_id)
    session.commit()

    # Sem marca nenhuma (orçamentos anteriores a esta funcionalidade), o lado
    # seguro é avisar: mais vale um recálculo a mais do que números velhos.
    assert RelatorioConsumosService(session).custeio_desatualizado(versao_id) is True


def test_marcar_recalculado_limpa_o_aviso_ate_alguem_mexer(session) -> None:
    versao_id = _criar_versao(session)
    item_id = _criar_item(session, versao_id)
    linha = _linha(session, item_id)
    session.commit()

    servico = RelatorioConsumosService(session)
    servico.marcar_custeio_recalculado(versao_id)

    assert servico.custeio_desatualizado(versao_id) is False
    versao = session.get(OrcamentoVersao, versao_id)
    assert versao.custeio_impressao_digital
    assert versao.custeio_recalculado_em is not None

    OrcamentoItemCusteioLinhaRepository(session).update_linha(
        id=linha.id, custo_total=Decimal("42")
    )
    session.commit()

    assert servico.custeio_desatualizado(versao_id) is True


def test_recalcular_se_necessario_nao_corre_com_o_custeio_em_dia(session) -> None:
    versao_id = _criar_versao(session)
    _criar_item(session, versao_id)
    session.commit()

    servico = RelatorioConsumosService(session)
    servico.marcar_custeio_recalculado(versao_id)

    correu = []
    servico.recalcular_versao = lambda _id: correu.append(_id)  # type: ignore[method-assign]

    assert servico.recalcular_versao_se_necessario(versao_id) is False
    assert correu == []


def test_recalcular_se_necessario_corre_quando_o_custeio_mexeu(session) -> None:
    versao_id = _criar_versao(session)
    _criar_item(session, versao_id)
    session.commit()

    servico = RelatorioConsumosService(session)
    correu = []
    servico.recalcular_versao = lambda _id: correu.append(_id)  # type: ignore[method-assign]

    assert servico.recalcular_versao_se_necessario(versao_id) is True
    assert correu == [versao_id]


def test_custeio_desatualizado_de_versao_inexistente_nao_rebenta(session) -> None:
    assert RelatorioConsumosService(session).custeio_desatualizado(9999) is False


# ----- As exportações não recalculam -----


def test_exportacoes_nao_chamam_a_pipeline() -> None:
    for metodo in (
        OrcamentoExportService.exportar_pdf_orcamento,
        OrcamentoExportService.exportar_excel_orcamento,
        OrcamentoExportService.exportar_excel_phc,
        OrcamentoExportService.exportar_resumo_custos,
        OrcamentoExportService.exportar_plano_corte,
        PlanoCorteService.dados_plano_corte,
    ):
        assert "recalcular_versao" not in inspect.getsource(metodo), metodo.__name__


def test_recalcular_versao_marca_a_versao_como_em_dia() -> None:
    fonte = inspect.getsource(RelatorioConsumosService.recalcular_versao)
    assert "marcar_custeio_recalculado" in fonte


def test_botao_atualizar_custos_corre_a_mesma_pipeline_dos_relatorios() -> None:
    # Desde que as exportações deixaram de recalcular, é este botão que fixa os
    # números que vão sair no PDF/Excel -- por isso tem de correr a pipeline
    # COMPLETA (incluindo as placas Não-Stock), e não só item a item.
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    fonte = inspect.getsource(OrcamentoItemsPage.atualizar_custos)
    assert "RelatorioConsumosService" in fonte
    assert "recalcular_versao" in fonte


def test_separador_custeio_so_recalcula_quando_o_custeio_mexeu() -> None:
    from app.ui.pages.orcamento_custeio_page import OrcamentoCusteioPage

    fonte = inspect.getsource(OrcamentoCusteioPage.carregar)
    assert "recalcular_versao_se_necessario" in fonte
    assert "forcar" in fonte


def test_supervisor_avisa_quando_o_custeio_esta_por_recalcular() -> None:
    from app.ui.pages.orcamento_relatorios_page import OrcamentoRelatoriosPage

    fonte = inspect.getsource(OrcamentoRelatoriosPage._confirmar_supervisor)
    # A auditoria mantém-se…
    assert "executar_versao" in fonte
    # …e ganha o aviso do custeio por recalcular, com o recálculo à mão.
    assert "custeio_desatualizado" in fonte
    assert "Atualizar custos agora" in fonte
    assert "recalcular_e_carregar" in fonte
