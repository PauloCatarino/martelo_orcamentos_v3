import json
from decimal import Decimal

from app.domain.colar_excel import parse_bloco_medidas_excel
from app.domain.custeio_simplificado import (
    ORLAGEM_SIMPLIFICADA_LASER,
    ORLAGEM_SIMPLIFICADA_PUR,
    TARIFA_ESPESSURA_GROSSA_PADRAO,
    TARIFAS_SIMPLIFICADO_PADRAO,
    TarifaEspessuraGrossa,
    calcular_custo_simplificado_linha,
    calcular_opcoes_simplificado,
    escolher_escalao_simplificado,
    espessura_e_grossa,
    rotulo_escalao,
)
from app.services.custeio_simplificado_tarifas_service import parse_tarifas_simplificado


def test_escaloes_incluem_25_no_preco_mais_favoravel():
    assert escolher_escalao_simplificado(4).corte_por_peca == Decimal("2.40")
    assert escolher_escalao_simplificado(5).corte_por_peca == Decimal("1.95")
    assert escolher_escalao_simplificado(15).corte_por_peca == Decimal("1.55")
    assert escolher_escalao_simplificado(24).corte_por_peca == Decimal("1.55")
    assert escolher_escalao_simplificado(25).corte_por_peca == Decimal("1.15")


def test_rotulo_escalao():
    assert rotulo_escalao(escolher_escalao_simplificado(3)) == "1–4"
    assert rotulo_escalao(escolher_escalao_simplificado(25)) == "≥25"


def test_orlagem_e_proporcional_aos_lados_reais():
    tarifa = escolher_escalao_simplificado(1)
    assert calcular_custo_simplificado_linha(2, "2222", ORLAGEM_SIMPLIFICADA_PUR, tarifa) == (Decimal("4.80"), Decimal("7.20"))
    assert calcular_custo_simplificado_linha(2, "2000", ORLAGEM_SIMPLIFICADA_PUR, tarifa) == (Decimal("4.80"), Decimal("1.80"))
    assert calcular_custo_simplificado_linha(1, "1100", ORLAGEM_SIMPLIFICADA_LASER, tarifa) == (Decimal("2.40"), Decimal("2.30"))


def test_espessura_ate_19_usa_escaloes_e_acima_usa_tarifa_grossa():
    tarifa = escolher_escalao_simplificado(1)
    # Exatamente 19 mm ainda usa as tarifas do escalão.
    assert calcular_custo_simplificado_linha(1, "2222", ORLAGEM_SIMPLIFICADA_PUR, tarifa, esp=Decimal("19")) == (Decimal("2.40"), Decimal("3.60"))
    # Acima de 19 mm: corte 2,85 €/peça e orlagem 1,15 €/lado orlado.
    assert calcular_custo_simplificado_linha(1, "2222", ORLAGEM_SIMPLIFICADA_PUR, tarifa, esp=Decimal("19.001")) == (Decimal("2.85"), Decimal("4.60"))
    assert calcular_custo_simplificado_linha(2, "2100", ORLAGEM_SIMPLIFICADA_PUR, tarifa, esp=Decimal("22")) == (Decimal("5.70"), Decimal("4.60"))
    assert calcular_custo_simplificado_linha(1, "0022", ORLAGEM_SIMPLIFICADA_PUR, tarifa, esp=Decimal("30")) == (Decimal("2.85"), Decimal("2.30"))
    # Acima de 19 mm o preço é único: PUR e LASER pagam o mesmo.
    assert calcular_custo_simplificado_linha(1, "2222", ORLAGEM_SIMPLIFICADA_LASER, tarifa, esp=Decimal("22")) == (Decimal("2.85"), Decimal("4.60"))
    # Sem espessura conhecida mantém as tarifas do escalão.
    assert calcular_custo_simplificado_linha(1, "2222", ORLAGEM_SIMPLIFICADA_PUR, tarifa, esp=None) == (Decimal("2.40"), Decimal("3.60"))


def test_espessura_e_grossa():
    assert not espessura_e_grossa(None)
    assert not espessura_e_grossa(Decimal("19"))
    assert espessura_e_grossa(Decimal("19.5"))
    assert espessura_e_grossa("22")


def test_urgencia_e_valor_unico_por_item_por_escalao():
    # A urgência nunca multiplica pela quantidade de peças.
    tarifa = escolher_escalao_simplificado(3)
    assert calcular_opcoes_simplificado(3, tarifa, urgente=True, sem_excel=False) == (Decimal("2.30"), Decimal("0"))
    tarifa = escolher_escalao_simplificado(14)
    assert calcular_opcoes_simplificado(14, tarifa, urgente=True, sem_excel=False) == (Decimal("1.85"), Decimal("0"))
    tarifa = escolher_escalao_simplificado(20)
    assert calcular_opcoes_simplificado(20, tarifa, urgente=True, sem_excel=False) == (Decimal("1.70"), Decimal("0"))
    tarifa = escolher_escalao_simplificado(25)
    assert calcular_opcoes_simplificado(25, tarifa, urgente=True, sem_excel=True) == (Decimal("40.00"), Decimal("2.50"))


def test_sem_excel_continua_por_peca():
    tarifa = escolher_escalao_simplificado(14)
    assert calcular_opcoes_simplificado(14, tarifa, urgente=False, sem_excel=True) == (Decimal("0"), Decimal("1.40"))


def test_parse_tarifas_formato_antigo_migra_urgencia():
    antigo = json.dumps([
        {"minimo_pecas": 1, "corte_por_peca": "2.40", "pur_4_lados": "3.60", "laser_4_lados": "4.60", "urgencia_por_peca": "2.30", "urgencia_fixa": None, "sem_excel_por_peca": "0.10"},
        {"minimo_pecas": 5, "corte_por_peca": "1.95", "pur_4_lados": "3.00", "laser_4_lados": "4.00", "urgencia_por_peca": "1.85", "urgencia_fixa": None, "sem_excel_por_peca": "0.10"},
        {"minimo_pecas": 15, "corte_por_peca": "1.55", "pur_4_lados": "2.60", "laser_4_lados": "3.60", "urgencia_por_peca": "1.70", "urgencia_fixa": None, "sem_excel_por_peca": "0.10"},
        {"minimo_pecas": 25, "corte_por_peca": "1.15", "pur_4_lados": "2.40", "laser_4_lados": "3.40", "urgencia_por_peca": None, "urgencia_fixa": "40.00", "sem_excel_por_peca": "0.10"},
    ])
    tarifas, grossa = parse_tarifas_simplificado(antigo)
    assert [tarifa.urgencia_item for tarifa in tarifas] == [Decimal("2.30"), Decimal("1.85"), Decimal("1.70"), Decimal("40.00")]
    assert grossa == TARIFA_ESPESSURA_GROSSA_PADRAO


def test_parse_tarifas_formato_novo_com_espessura_grossa():
    novo = json.dumps({
        "escaloes": [
            {"minimo_pecas": 1, "corte_por_peca": "2.50", "pur_4_lados": "3.60", "laser_4_lados": "4.60", "urgencia_item": "2.30", "sem_excel_por_peca": "0.10"},
            {"minimo_pecas": 5, "corte_por_peca": "1.95", "pur_4_lados": "3.00", "laser_4_lados": "4.00", "urgencia_item": "1.85", "sem_excel_por_peca": "0.10"},
            {"minimo_pecas": 15, "corte_por_peca": "1.55", "pur_4_lados": "2.60", "laser_4_lados": "3.60", "urgencia_item": "1.70", "sem_excel_por_peca": "0.10"},
            {"minimo_pecas": 25, "corte_por_peca": "1.15", "pur_4_lados": "2.40", "laser_4_lados": "3.40", "urgencia_item": "40.00", "sem_excel_por_peca": "0.10"},
        ],
        "espessura_grossa": {"corte_por_peca": "2.85", "orlagem_por_lado": "1.15"},
    })
    tarifas, grossa = parse_tarifas_simplificado(novo)
    assert tarifas[0].corte_por_peca == Decimal("2.50")
    assert grossa == TarifaEspessuraGrossa(Decimal("2.85"), Decimal("1.15"))


def test_parse_tarifas_invalido_volta_aos_padroes():
    assert parse_tarifas_simplificado(None) == (TARIFAS_SIMPLIFICADO_PADRAO, TARIFA_ESPESSURA_GROSSA_PADRAO)
    assert parse_tarifas_simplificado("nao é json") == (TARIFAS_SIMPLIFICADO_PADRAO, TARIFA_ESPESSURA_GROSSA_PADRAO)
    assert parse_tarifas_simplificado(json.dumps({"escaloes": []})) == (TARIFAS_SIMPLIFICADO_PADRAO, TARIFA_ESPESSURA_GROSSA_PADRAO)


def test_colar_excel_aceita_bloco_numerico_com_virgula_ou_ponto():
    assert parse_bloco_medidas_excel("600\t400\r\n1200,5\t297.4\r\n") == [("600", "400"), ("1200.5", "297.4")]
    assert parse_bloco_medidas_excel("600\n700") == [("600",), ("700",)]
    # Células vazias no meio mantêm a coluna (esse valor não é alterado).
    assert parse_bloco_medidas_excel("600\t\n\t400") == [("600", ""), ("", "400")]


def test_colar_excel_rejeita_texto_nao_numerico():
    assert parse_bloco_medidas_excel(None) is None
    assert parse_bloco_medidas_excel("") is None
    assert parse_bloco_medidas_excel("abc\t400") is None
    assert parse_bloco_medidas_excel("600;400") is None
    assert parse_bloco_medidas_excel("=A1*2\t400") is None
    assert parse_bloco_medidas_excel("600.4.2") is None
