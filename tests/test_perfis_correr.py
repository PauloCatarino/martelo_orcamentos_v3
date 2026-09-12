from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.domain.perfis_correr import ordenar_perfis, usa_selecao_comprimento
from app.models import OrcamentoItem, OrcamentoItemValuesetLinha, DefPeca
from app.services.orcamento_item_custeio_linha_service import OrcamentoItemCusteioLinhaService
from app.services.def_peca_service import DefPecaService


def test_ordena_cobertura_menor_sobra_depois_curtas_e_desconhecidas():
    opcoes = [SimpleNamespace(comp_mp=c) for c in (None, 2500, 1800, 2000, 1900)]
    assert [o.comp_mp for o in ordenar_perfis(opcoes, 1960)] == [2000, 2500, 1900, 1800, None]
    assert [o.comp_mp for o in ordenar_perfis(opcoes, 3000)] == [2500, 2000, 1900, 1800, None]


@pytest.mark.parametrize("chave", [
    "SISTEMA_CORRER_RODIZIO_SUP",
    "SISTEMA_CORRER_RODIZIO_INF",
    "SISTEMA_CORRER_AMORTECEDOR",
])
def test_auto_exclui_o_que_se_vende_a_unidade(chave):
    """Rodizios e amortecedores nao tem comprimento comercial nenhum."""
    assert not usa_selecao_comprimento(SimpleNamespace(tipo_linha="FERRAGEM", chave_valueset=chave))


@pytest.mark.parametrize("chave", [
    "SISTEMA_CORRER_CALHA_SUP",
    "SISTEMA_CORRER_CALHA_INF",
    "SISTEMA_CORRER_CALHA_U",
    "SISTEMA_CORRER_CALHA_H",
    "SISTEMA_CORRER_PUXADOR",
])
def test_auto_cobre_tudo_o_que_se_compra_a_barra(chave):
    """A U e a H estavam de fora "desta fase"; entraram a pedido do Paulo.

    A calha U do catalogo vem em 2350 mm: uma porta mais alta que isso passava
    sem aviso nenhum, que e' o caso que isto existe para apanhar.
    """
    assert usa_selecao_comprimento(SimpleNamespace(tipo_linha="FERRAGEM", chave_valueset=chave))


def cenario(session, comprimentos=(2000,), codigo="CALHA_SUP_SISTEMA_CORRER", formula="L-40"):
    item = OrcamentoItem(orcamento_versao_id=1, ordem=1, tipo_item="OUTRO", item="Roupeiro",
                         quantidade=1, altura=2618, largura=2000, profundidade=630)
    peca = DefPeca(codigo=codigo, nome=codigo)
    session.add_all([item, peca])
    session.flush()
    service = OrcamentoItemCusteioLinhaService(session)
    linha = service.repository.create_linha(orcamento_item_id=item.id, tipo_linha="FERRAGEM",
        descricao="Calha", def_peca_id=peca.id, def_peca_codigo=codigo, comp=formula,
        chave_valueset="SISTEMA_CORRER_CALHA_SUP", quantidade=1, qt_mod=1, qt_und=1, ativo=True)
    for i, comp in enumerate(comprimentos):
        session.add(OrcamentoItemValuesetLinha(orcamento_item_id=item.id, chave="SISTEMA_CORRER_CALHA_SUP",
            codigo_opcao=f"CALHA_{i}", prioridade=i+1, ordem=i+1, comp_mp=comp,
            unidade="UND", preco_liquido=18, desperdicio_percentagem=0, ativo=True))
    session.commit()
    return service, item, linha, peca


def test_unica_adequada_aplica_sem_descontar_duas_vezes_e_custa_und(session):
    service, item, linha, _ = cenario(session)
    service.recalcular_item_completo(item.id)
    atual = service.repository.get_by_id(linha.id)
    assert atual.comp_real == Decimal("1960")
    assert atual.comp_mp == Decimal("2000")
    assert atual.mat_default == "CALHA_0"
    assert atual.origem_material == "VALUESET_PERFIL_AUTO"
    assert atual.custo_ferragem == Decimal("18")
    assert atual.unidade.upper() == "UND"


@pytest.mark.parametrize("comprimentos", [(1800,), (None,), (2000, 2500)])
def test_nao_escolhe_automaticamente_curta_desconhecida_ou_varias(session, comprimentos):
    service, item, linha, _ = cenario(session, comprimentos)
    service.recalcular_item_completo(item.id)
    atual = service.repository.get_by_id(linha.id)
    assert atual.origem_material != "VALUESET_PERFIL_AUTO"
    assert "Perfil de correr:" in atual.observacoes


def test_preserva_escolha_manual_e_avisa_apos_aumento_medida(session):
    service, item, linha, _ = cenario(session, (2000, 2500))
    opcao = service.opcoes_valueset_do_item(item.id)[0]
    service.aplicar_opcao_valueset_na_linha(linha.id, opcao.id)
    item.largura = 2700
    session.commit()
    service.recalcular_item_completo(item.id)
    atual = service.repository.get_by_id(linha.id)
    assert atual.mat_default == "CALHA_0"
    assert atual.material_editado_localmente
    assert "CURTA" in atual.observacoes
    assert atual.custo_ferragem == Decimal("18")


def test_regra_configuravel_desliga_e_puxador_usa_comprimento_vertical(session):
    service, item, linha, peca = cenario(session, (2600,), codigo="PUXADOR_PORTA_CORRER", formula="H-50")
    DefPecaService(session).atualizar_formulas_dimensionais(peca.id, formula_comp="H-50",
        formula_larg=None, formula_esp=None, selecao_perfil="DESLIGADO")
    service.recalcular_item_completo(item.id)
    assert service.repository.get_by_id(linha.id).mat_default is None
    DefPecaService(session).atualizar_formulas_dimensionais(peca.id, formula_comp="H-50",
        formula_larg=None, formula_esp=None, selecao_perfil="COMPRIMENTO")
    service.recalcular_item_completo(item.id)
    atual = service.repository.get_by_id(linha.id)
    assert atual.comp_real == Decimal("2568")
    assert atual.mat_default == "CALHA_0"


def test_combo_mostra_recomendacao_curtas_e_confirma_escolha_atual(session):
    from PySide6.QtWidgets import QApplication
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage
    app = QApplication.instance() or QApplication([])
    service, item, linha, _ = cenario(session, (1800, 2500, 2000, None))
    service.recalcular_item_completo(item.id)
    linha = service.repository.get_by_id(linha.id)
    opcoes = service.opcoes_valueset_do_item(item.id)
    page = SimpleNamespace()
    page._modos_perfil = {}
    page._tooltip_mat_default = lambda l: OrcamentoItemCusteioPage._tooltip_mat_default(page, l)
    page._opcao_atual_id = OrcamentoItemCusteioPage._opcao_atual_id
    page._label_opcao_material = OrcamentoItemCusteioPage._label_opcao_material
    page._on_material_combo_changed = lambda *args: None
    combo = OrcamentoItemCusteioPage._criar_combo_material(page, linha, opcoes)
    assert combo.currentIndex() == 0
    assert "Confirmar perfil" in combo.itemText(0)
    assert "Recomendada" in combo.itemText(1)
    assert "2000" in combo.itemText(1)
    assert "sobra 40" in combo.itemText(1)
    assert "CURTA" in combo.itemText(3)
    assert "desconhecido" in combo.itemText(4)
    assert "1960" in combo.toolTip()
    combo.deleteLater()
    app.processEvents()


def test_migracao_acrescenta_configuracao_sem_alterar_pecas_existentes():
    import importlib.util
    from pathlib import Path
    from sqlalchemy import create_engine, text
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    path = Path(__file__).resolve().parents[1] / "alembic/versions/20260912_113_selecao_perfil.py"
    spec = importlib.util.spec_from_file_location("migracao_perfil", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE def_pecas (id INTEGER PRIMARY KEY, nome TEXT)"))
            connection.execute(text("INSERT INTO def_pecas (id, nome) VALUES (1, 'Calha')"))
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                # Uma base reparada pontualmente pode percorrer a cadeia depois.
                migration.upgrade()
            assert connection.execute(text("SELECT nome, selecao_perfil FROM def_pecas WHERE id = 1")).one() == ("Calha", "AUTO")
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# Ronda de revisao: as tres coisas que a analise apanhou antes de isto ir para
# o GitHub. Cada teste guarda uma delas.
# ---------------------------------------------------------------------------


def test_nao_ha_chaves_inventadas_na_lista_dos_perfis():
    """Estava la' a SISTEMA_CORRER_PUXADOR_WAVE, que o Paulo nao tem.

    Nao partia nada — so' nunca acertava. Mas uma chave que nao existe faz
    acreditar que aquele caso esta' coberto quando nao esta'. Veio da lista de
    recurso do `valueset_types`, que e' antiga: tem a WAVE, que a base real nao
    tem, e nao tem a SISTEMA_CORRER_PUXADOR, que e' a verdadeira.
    """
    from app.domain.perfis_correr import CHAVES

    assert "SISTEMA_CORRER_PUXADOR_WAVE" not in CHAVES
    assert "SISTEMA_CORRER_PUXADOR" in CHAVES


def test_todas_as_chaves_dos_perfis_sao_de_sistemas_de_correr():
    """Uma gralha num codigo passava despercebida: e' so' texto."""
    from app.domain.perfis_correr import CHAVES

    assert all(c.startswith("SISTEMA_CORRER_") for c in CHAVES)


def test_a_calha_u_e_a_h_tambem_se_compram_a_barra():
    """Faltavam as duas, e sao barras como as calhas sup/inf.

    A calha U do catalogo vem em 2350 mm: uma porta mais alta que isso passava
    sem aviso nenhum, que e' exatamente o caso que isto existe para apanhar.
    """
    from app.domain.perfis_correr import CHAVES, PECAS

    for chave in ("SISTEMA_CORRER_CALHA_U", "SISTEMA_CORRER_CALHA_H"):
        assert chave in CHAVES
    for peca in ("CALHA_PORTA_CORRER_U", "CALHA_PORTA_CORRER_H"):
        assert peca in PECAS


def test_os_rodizios_e_o_amortecedor_ficam_de_fora():
    """Vendem-se a` unidade: perguntar-lhes o comprimento nao quer dizer nada."""
    from app.domain.perfis_correr import CHAVES

    for chave in (
        "SISTEMA_CORRER_RODIZIO_SUP",
        "SISTEMA_CORRER_RODIZIO_INF",
        "SISTEMA_CORRER_AMORTECEDOR",
    ):
        assert chave not in CHAVES


def test_os_avisos_do_perfil_somam_se_em_vez_de_se_taparem():
    """Um perfil pode estar curto E com a unidade errada.

    Os avisos eram atribuidos por cima uns dos outros e so' o ultimo sobrevivia:
    com a unidade errada perdia-se o "faltam X mm", que e' o unico que diz o que
    fazer. Todos tem de comecar pelo mesmo prefixo, senao a passagem seguinte
    deixava orfaos nas observacoes.
    """
    import inspect

    from app.services.orcamento_item_custeio_linha_service import (
        OrcamentoItemCusteioLinhaService,
    )

    fonte = inspect.getsource(
        OrcamentoItemCusteioLinhaService.analisar_perfis_do_item
    )
    assert "avisos: list[str] = []" in fonte
    assert "aviso = " not in fonte, "voltou a atribuir por cima"
    assert fonte.count("avisos.append(") == 5
    assert "chr(10).join(avisos) or None" in fonte

    for mensagem in fonte.split("avisos.append(")[1:]:
        assert mensagem.lstrip().startswith(('"Perfil de correr:', 'f"Perfil de correr:'))


def test_avisos_somados_sao_apagados_todos_na_passagem_seguinte():
    """O _mesclar_observacao corta por prefixo, linha a linha."""
    from app.services.orcamento_item_custeio_linha_service import (
        OrcamentoItemCusteioLinhaService,
    )

    servico = OrcamentoItemCusteioLinhaService.__new__(
        OrcamentoItemCusteioLinhaService
    )
    dois = "\n".join(
        [
            "Perfil de correr: material atual — 2350 mm · CURTA: faltam 150 mm.",
            "Perfil de correr: confirme unidade e preço do material.",
        ]
    )
    texto = servico._mesclar_observacao("Nota do desenho.", "Perfil de correr:", dois)

    assert texto.splitlines() == [
        "Nota do desenho.",
        "Perfil de correr: material atual — 2350 mm · CURTA: faltam 150 mm.",
        "Perfil de correr: confirme unidade e preço do material.",
    ]

    # Resolvido o problema, nao pode ficar nenhuma das duas linhas para tras.
    assert servico._mesclar_observacao(texto, "Perfil de correr:", None) == (
        "Nota do desenho."
    )


def test_o_supervisor_mostra_cada_aviso_do_perfil_de_permeio():
    from app.services.custeio_auditoria_service import (
        classificar_observacoes_producao,
    )

    achados = classificar_observacoes_producao(
        "Perfil de correr: material atual — CURTA: faltam 150 mm.\n"
        "Perfil de correr: confirme unidade e preço do material."
    )

    assert len(achados) == 2
    assert {categoria for categoria, _sev, _msg in achados} == {"Perfil de correr"}
