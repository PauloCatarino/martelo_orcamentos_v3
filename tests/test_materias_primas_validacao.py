"""Tests for the raw-materials Excel validation rules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain import materias_primas_validacao as validacao
from app.domain.materias_primas_validacao import (
    AVISO,
    CRITICO,
    INFO,
    LinhaExcel,
    validar_linhas,
)

HOJE = date(2026, 8, 24)


def _linha(**overrides) -> LinhaExcel:
    """A valid panel row; each test breaks only what it is about."""
    valores = {
        "numero": 10,
        "ref_le": "PLC0001",
        "descricao": "AGL FOL ALD. BETULA 19MM",
        "familia": "PLACAS",
        "tipo": "AGLOMERADO",
        "unidade": "M2",
        "preco_tabela": Decimal("24.87"),
        "preco_liquido": Decimal("19.90"),
        "espessura": Decimal("19"),
        "data_ultimo_preco": date(2026, 8, 1),
    }
    valores.update(overrides)
    return LinhaExcel(**valores)


def _categorias(relatorio) -> set[str]:
    return {aviso.categoria for aviso in relatorio.avisos}


def test_linha_valida_nao_gera_avisos() -> None:
    relatorio = validar_linhas([_linha()], hoje=HOJE)

    assert relatorio.avisos == ()
    assert relatorio.pode_importar
    assert relatorio.total_linhas == 1
    assert relatorio.linhas_com_ref_le == 1


def test_ref_le_duplicada_e_critica_e_avisa_uma_vez() -> None:
    linhas = [
        _linha(numero=10, ref_le="PLC0001"),
        _linha(numero=11, ref_le="plc0001"),
        _linha(numero=12, ref_le="PLC0002"),
    ]

    relatorio = validar_linhas(linhas, hoje=HOJE)
    duplicados = [
        a for a in relatorio.avisos if a.categoria == validacao.CAT_REF_LE_DUPLICADA
    ]

    assert len(duplicados) == 1
    assert duplicados[0].severidade == CRITICO
    assert not relatorio.pode_importar


def test_linha_com_dados_mas_sem_ref_le_e_critica() -> None:
    relatorio = validar_linhas([_linha(ref_le=None)], hoje=HOJE)

    assert validacao.CAT_SEM_REF_LE in _categorias(relatorio)
    assert not relatorio.pode_importar


def test_linha_vazia_e_apenas_aviso() -> None:
    vazia = LinhaExcel(numero=338, preco_liquido=Decimal("0"))

    relatorio = validar_linhas([vazia], hoje=HOJE)

    assert _categorias(relatorio) == {validacao.CAT_LINHA_VAZIA}
    assert relatorio.avisos[0].severidade == AVISO
    assert relatorio.pode_importar


def test_preco_zero_e_critico_quando_o_preco_vem_da_tabela() -> None:
    relatorio = validar_linhas([_linha(preco_liquido=None)], hoje=HOJE)

    assert validacao.CAT_PRECO_EM_FALTA in _categorias(relatorio)
    assert not relatorio.pode_importar


def test_preco_zero_e_aceite_quando_o_material_e_de_preco_livre() -> None:
    livre = _linha(
        ref_le="PLC0097",
        descricao="PLACAS LIVRES",
        preco_tabela=None,
        preco_liquido=None,
        tipo_preco=validacao.TIPO_PRECO_LIVRE,
        data_ultimo_preco=None,
    )

    relatorio = validar_linhas([livre], hoje=HOJE)

    assert relatorio.avisos == ()


def test_orla_inexistente_e_critica() -> None:
    linhas = [_linha(coresp_orla_0_4="ORL9999")]

    relatorio = validar_linhas(linhas, hoje=HOJE)

    assert validacao.CAT_ORLA_INEXISTENTE in _categorias(relatorio)


def test_orla_existente_no_ficheiro_nao_gera_aviso() -> None:
    linhas = [
        _linha(coresp_orla_0_4="ORL0002"),
        _linha(
            numero=11,
            ref_le="ORL0002",
            descricao="ORLA PVC 0.4",
            familia="ORLA",
            unidade="M2",
            espessura=Decimal("0.4"),
        ),
    ]

    relatorio = validar_linhas(linhas, hoje=HOJE)

    assert validacao.CAT_ORLA_INEXISTENTE not in _categorias(relatorio)


def test_espessura_da_descricao_diferente_de_esp_mp() -> None:
    linha = _linha(descricao="AGL MR MLM BRANCO 16MM", espessura=Decimal("12"))

    relatorio = validar_linhas([linha], hoje=HOJE)
    avisos = [
        a for a in relatorio.avisos if a.categoria == validacao.CAT_ESPESSURA_DIVERGENTE
    ]

    assert len(avisos) == 1
    assert avisos[0].severidade == AVISO
    assert relatorio.pode_importar


def test_espessura_so_e_verificada_nas_placas() -> None:
    ferragem = _linha(
        ref_le="FER0001",
        descricao="CORRED. EXTR. TOTAL (500MM)",
        familia="FERRAGENS",
        unidade="UND",
        espessura=Decimal("0"),
    )

    relatorio = validar_linhas([ferragem], hoje=HOJE)

    assert validacao.CAT_ESPESSURA_DIVERGENTE not in _categorias(relatorio)


def test_preco_com_mais_de_doze_meses_gera_aviso() -> None:
    linha = _linha(data_ultimo_preco=date(2025, 7, 23))

    relatorio = validar_linhas([linha], hoje=HOJE)
    avisos = [
        a for a in relatorio.avisos if a.categoria == validacao.CAT_PRECO_DESATUALIZADO
    ]

    assert len(avisos) == 1
    assert "13 meses" in avisos[0].mensagem


def test_preco_recente_nao_gera_aviso() -> None:
    relatorio = validar_linhas([_linha(data_ultimo_preco=date(2026, 4, 23))], hoje=HOJE)

    assert validacao.CAT_PRECO_DESATUALIZADO not in _categorias(relatorio)


def test_sem_data_de_ultimo_preco_gera_aviso() -> None:
    relatorio = validar_linhas([_linha(data_ultimo_preco=None)], hoje=HOJE)

    assert validacao.CAT_PRECO_DESATUALIZADO in _categorias(relatorio)


def test_familia_e_unidade_fora_da_lista() -> None:
    linha = _linha(familia="PLACA", unidade="M3")

    relatorio = validar_linhas([linha], hoje=HOJE)
    avisos = [
        a for a in relatorio.avisos if a.categoria == validacao.CAT_VALOR_FORA_DA_LISTA
    ]

    assert len(avisos) == 2


def test_sem_familia_e_critico_porque_a_macro_precisa_dela() -> None:
    relatorio = validar_linhas([_linha(familia=None)], hoje=HOJE)
    avisos = [
        a for a in relatorio.avisos if a.categoria == validacao.CAT_VALOR_FORA_DA_LISTA
    ]

    assert avisos[0].severidade == CRITICO


class _MateriaFake:
    def __init__(self, ref_le, preco_tabela=None, ativo=True, descricao="") -> None:
        self.ref_le = ref_le
        self.preco_tabela = preco_tabela
        self.ativo = ativo
        self.descricao = descricao


def test_material_que_desapareceu_do_excel() -> None:
    existentes = [_MateriaFake("FER0001", Decimal("10"), descricao="ANTIGA")]

    relatorio = validar_linhas([_linha()], existentes, hoje=HOJE)
    avisos = [
        a for a in relatorio.avisos if a.categoria == validacao.CAT_DESAPARECEU_DO_EXCEL
    ]

    assert len(avisos) == 1
    assert avisos[0].ref_le == "FER0001"


def test_material_ja_inativo_nao_volta_a_avisar() -> None:
    existentes = [_MateriaFake("FER0001", Decimal("10"), ativo=False)]

    relatorio = validar_linhas([_linha()], existentes, hoje=HOJE)

    assert validacao.CAT_DESAPARECEU_DO_EXCEL not in _categorias(relatorio)


def test_preco_alterado_e_informativo() -> None:
    existentes = [_MateriaFake("PLC0001", Decimal("20.00"))]

    relatorio = validar_linhas([_linha()], existentes, hoje=HOJE)
    avisos = [
        a for a in relatorio.avisos if a.categoria == validacao.CAT_PRECO_ALTERADO
    ]

    assert len(avisos) == 1
    assert avisos[0].severidade == INFO
    assert relatorio.pode_importar


def test_diferenca_de_precos_dentro_da_tolerancia_e_ignorada() -> None:
    existentes = [_MateriaFake("PLC0001", Decimal("24.85"))]

    relatorio = validar_linhas([_linha()], existentes, hoje=HOJE)

    assert validacao.CAT_PRECO_ALTERADO not in _categorias(relatorio)


def test_resumir_conta_por_severidade() -> None:
    linhas = [_linha(ref_le=None), _linha(numero=11, data_ultimo_preco=None)]

    relatorio = validar_linhas(linhas, hoje=HOJE)
    texto = validacao.resumir(relatorio)

    assert "2 linhas" in texto
    assert "críticos" in texto
    assert "avisos" in texto


def test_resumir_sem_problemas() -> None:
    relatorio = validar_linhas([_linha()], hoje=HOJE)

    assert "nenhum problema" in validacao.resumir(relatorio)
