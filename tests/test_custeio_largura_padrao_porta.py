"""O LM automatico e' da porta; as ferragens do sistema de correr nao o levam."""

from __future__ import annotations

from types import SimpleNamespace

from app.domain.peca_funcao_types import FERRAGEM as FUNCAO_FERRAGEM, PORTA, PORTA_CORRER
from app.domain.peca_natureza_types import CONJUNTO, FERRAGEM, MATERIAL
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)


def _largura(peca, qt_und=1):
    return OrcamentoItemCusteioLinhaService._largura_padrao_porta(peca, qt_und)


def test_a_porta_continua_a_sugerir_a_largura_da_divisao() -> None:
    porta = SimpleNamespace(
        funcao=PORTA, codigo="PORTA_SIMPLES", natureza=MATERIAL
    )

    assert _largura(porta, 1) == "LM"
    assert _largura(porta, 2) == "LM/2"


def test_conjunto_de_portas_tambem() -> None:
    conjunto = SimpleNamespace(
        funcao=PORTA, codigo="PORTA_SIMPLES+DOBRADICA", natureza=CONJUNTO
    )

    assert _largura(conjunto, 1) == "LM"


def test_ferragem_com_porta_no_nome_fica_sem_largura() -> None:
    # No catalogo real: PUXADOR_PORTA_CORRER, RODAS_PORTA_CORRER_SUP, etc.
    for codigo in (
        "PUXADOR_PORTA_CORRER",
        "RODAS_PORTA_CORRER_SUP",
        "CALHA_PORTA_CORRER_U",
    ):
        ferragem = SimpleNamespace(
            funcao=FUNCAO_FERRAGEM, codigo=codigo, natureza=FERRAGEM
        )
        assert _largura(ferragem, 1) is None, codigo


def test_ferragem_marcada_como_porta_de_correr_tambem_fica_sem_largura() -> None:
    # Mesmo que a funcao esteja preenchida como porta, a natureza manda.
    ferragem = SimpleNamespace(
        funcao=PORTA_CORRER, codigo="CALHA_SUP_SISTEMA_CORRER", natureza=FERRAGEM
    )

    assert _largura(ferragem, 1) is None


def test_peca_sem_natureza_definida_mantem_o_comportamento_antigo() -> None:
    # Peças antigas do catalogo (e os fakes dos testes) nao trazem natureza.
    porta = SimpleNamespace(funcao=PORTA, codigo="PORTA_SIMPLES")

    assert _largura(porta, 1) == "LM"


def test_nao_escreve_nada_nos_campos_quando_nao_ha_largura() -> None:
    ferragem = SimpleNamespace(
        funcao=FUNCAO_FERRAGEM, codigo="PUXADOR_PORTA_CORRER", natureza=FERRAGEM
    )
    fields: dict = {}

    OrcamentoItemCusteioLinhaService._aplicar_largura_padrao_porta(
        fields, ferragem, 1
    )

    assert "larg" not in fields
