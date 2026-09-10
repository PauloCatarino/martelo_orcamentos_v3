"""O vocabulário de substratos: o que faz a comparação entre fornecedores ter sentido.

Cada fornecedor chama outra coisa ao mesmo núcleo de placa. Se estes testes
falharem, a pergunta «quanto custa o 19 mm em aglomerado, em qualquer
fornecedor» deixa de ter resposta — que é o motivo de existir a base dos
catálogos.
"""

from __future__ import annotations

import pytest

from app.services.catalogos import substratos


# ---------------------------------------------------------------------------
# Os três fornecedores encontram-se no mesmo código
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "designacao",
    [
        # EGGER, nas duas grafias que o OCR do PDF deixou
        "Eurodekor Tableros de partículas revestidos E1E05 TSCA P2",
        "Eurodekor Tableros de partículas revestidos El E05 TSCA P2",
        # Innovus
        "PB STD",
        "PB STD CARB2",
        "Aglomerado de partículas standard",
        # Finsa
        "AGL STD",
        "AGL STD EZ",
    ],
)
def test_aglomerado_standard_de_qualquer_fornecedor_da_pb_std(designacao: str) -> None:
    assert substratos.canonico(designacao) == "PB STD"


@pytest.mark.parametrize(
    "designacao",
    ["PB HID", "PB HID CARB2", "AGL HID", "AGL HID EZ", "Aglomerado de partículas hidrófugo"],
)
def test_aglomerado_hidrofugo_da_pb_hid(designacao: str) -> None:
    assert substratos.canonico(designacao) == "PB HID"


@pytest.mark.parametrize(
    ("designacao", "esperado"),
    [
        ("PB IGN", "PB IGN"),
        ("AGL IGN EZ", "PB IGN"),
        ("MDF STD CARB2", "MDF STD"),
        ("MDF STD EZ", "MDF STD"),
        ("MDF HID CARB2", "MDF HID"),
        ("MDF HID EZ", "MDF HID"),
        ("MDF IGN CARB2", "MDF IGN"),
        ("MDF IGN EZ", "MDF IGN"),
        ("COLOURED MDF PRETO CARB2", "MDF COLOR"),
        ("COLOURED MDF CINZA CARB2", "MDF COLOR"),
        ("MDF PINTADO CARB2", "MDF PINTADO"),
        ("MDF PINTADO DECORATIVOS CARB2", "MDF PINTADO"),
        ("MDF PINTADO UNICOLORES CARB2", "MDF PINTADO"),
        ("Painel compacto", "COMPACTO"),
    ],
)
def test_os_outros_nucleos(designacao: str, esperado: str) -> None:
    assert substratos.canonico(designacao) == esperado


# ---------------------------------------------------------------------------
# O SUPERPAN não é nem aglomerado nem MDF
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("designacao", "esperado"),
    [
        ("SUPERPAN STD", "SUPERPAN STD"),
        ("SUPERPAN STD EZ", "SUPERPAN STD"),
        ("SUPERPAN HID", "SUPERPAN HID"),
        ("SUPERPAN STAR", "SUPERPAN STAR"),
    ],
)
def test_superpan_e_nucleo_proprio(designacao: str, esperado: str) -> None:
    """Alma de aglomerado com faces de MDF, e preço próprio.

    Se caísse em ``PB`` ou em ``MDF``, uma comparação de preços punha lado a
    lado duas coisas que não são a mesma placa.
    """
    assert substratos.canonico(designacao) == esperado


# ---------------------------------------------------------------------------
# O que não se adivinha
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("designacao", [None, "", "   ", "Coisa nova do catálogo", "XPTO 7"])
def test_o_que_nao_se_reconhece_devolve_none(designacao: object) -> None:
    """Um substrato errado é pior do que nenhum: quem chama faz disto um aviso."""
    assert substratos.canonico(designacao) is None


def test_hid_so_conta_como_palavra_inteira() -> None:
    """Um ``in`` solto fazia qualquer texto com «hid» lá dentro virar hidrófugo."""
    assert substratos.canonico("Aglomerado Hidalgo") == "PB STD"
    assert substratos.canonico("AGL HID") == "PB HID"


def test_todos_os_codigos_produzidos_estao_no_contrato() -> None:
    """A lista ``CANONICOS`` é o que uma consulta pode contar que existe."""
    amostra = [
        "AGL STD", "AGL HID", "AGL IGN EZ", "PB STD CARB2",
        "MDF STD EZ", "MDF HID CARB2", "MDF IGN EZ",
        "COLOURED MDF PRETO CARB2", "MDF PINTADO CARB2",
        "SUPERPAN STD", "SUPERPAN HID", "SUPERPAN STAR",
        "Painel compacto",
        "Eurodekor Tableros de partículas revestidos E1E05 TSCA P2",
    ]
    for designacao in amostra:
        codigo = substratos.canonico(designacao)
        assert codigo in substratos.CANONICOS, f"{designacao} deu {codigo}"
