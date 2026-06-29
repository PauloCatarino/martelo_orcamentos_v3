"""Testes da extração (pura) dos dados do plano de corte (C3.2)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domain.plano_corte_dados import _rodar, construir_grupos_corte


@pytest.mark.parametrize(
    ("def_peca", "esperado"),
    [
        ("LATERAL GAVETA", True),
        ("RODAPE AGL", True),
        ("RODAPÉ", True),
        ("COSTA CHAPAR", False),
        ("RODATETO", False),
        ("TETO [2000]", False),
        (None, False),
    ],
)
def test_rodar(def_peca, esperado) -> None:
    assert _rodar(def_peca) is esperado


def _placa(ref, esp, comp, larg, qt) -> SimpleNamespace:
    return SimpleNamespace(
        descricao_no_orcamento=ref,
        esp_mp=esp,
        comp_mp=comp,
        larg_mp=larg,
        qt_placas=qt,
    )


def _linha(**kwargs) -> dict:
    base = {
        "descricao_no_orcamento": None,
        "esp_mp": None,
        "comp_mp": None,
        "larg_mp": None,
        "comp_real": None,
        "larg_real": None,
        "qt_total": None,
        "def_peca": None,
    }
    base.update(kwargs)
    return base


def test_construir_grupos_corte_so_material_placa() -> None:
    placas = [_placa("MDF 19", 19, 2750, 1830, 3)]
    linhas = [
        # Material-placa (MDF 19): 2 peças (gaveta -> roda) + 1 peça (costa).
        _linha(
            descricao_no_orcamento="MDF 19", esp_mp=19, comp_mp=2750, larg_mp=1830,
            comp_real=600, larg_real=400, qt_total=2, def_peca="LATERAL GAVETA",
        ),
        _linha(
            descricao_no_orcamento="MDF 19", esp_mp=19, comp_mp=2750, larg_mp=1830,
            comp_real=700, larg_real=500, qt_total=1, def_peca="COSTA",
        ),
        # Peça sem comprimento real -> ignorada.
        _linha(
            descricao_no_orcamento="MDF 19", esp_mp=19, comp_mp=2750, larg_mp=1830,
            comp_real=0, larg_real=400, qt_total=2, def_peca="X",
        ),
        # Peça sem quantidade -> ignorada.
        _linha(
            descricao_no_orcamento="MDF 19", esp_mp=19, comp_mp=2750, larg_mp=1830,
            comp_real=600, larg_real=400, qt_total=0, def_peca="Y",
        ),
        # Material NÃO-placa (orla, sem dims de placa) -> não vira grupo.
        _linha(
            descricao_no_orcamento="ORLA ABS", esp_mp=1, comp_mp=None, larg_mp=None,
            comp_real=600, larg_real=23, qt_total=5, def_peca="FRENTE",
        ),
    ]

    grupos = construir_grupos_corte(linhas, placas)

    assert len(grupos) == 1
    grupo = grupos[0]
    assert grupo.ref == "MDF 19"
    assert grupo.esp == 19.0
    assert grupo.placa_comp == 2750.0
    assert grupo.placa_larg == 1830.0
    assert grupo.placas_orcamento == 3
    # 2 (gaveta) + 1 (costa) = 3 peças; as inválidas e a não-placa foram ignoradas.
    assert len(grupo.pecas) == 3
    rodar_por_desc = {p.desc: p.rodar for p in grupo.pecas}
    assert rodar_por_desc["LATERAL GAVETA"] is True
    assert rodar_por_desc["COSTA"] is False
    # Dimensões reais preservadas.
    gaveta = [p for p in grupo.pecas if p.desc == "LATERAL GAVETA"]
    assert len(gaveta) == 2
    assert (gaveta[0].comp, gaveta[0].larg) == (600.0, 400.0)


def test_construir_grupos_corte_soma_qt_placas() -> None:
    # Duas placas do mesmo material/esp/dims -> placas_orcamento somado.
    placas = [
        _placa("MDF 19", 19, 2750, 1830, 3),
        _placa("MDF 19", 19, 2750, 1830, 2),
    ]
    linhas = [
        _linha(
            descricao_no_orcamento="MDF 19", esp_mp=19, comp_mp=2750, larg_mp=1830,
            comp_real=600, larg_real=400, qt_total=1, def_peca="COSTA",
        ),
    ]

    grupos = construir_grupos_corte(linhas, placas)

    assert len(grupos) == 1
    assert grupos[0].placas_orcamento == 5


def test_construir_grupos_corte_sem_placas_devolve_vazio() -> None:
    linhas = [
        _linha(
            descricao_no_orcamento="MDF 19", esp_mp=19, comp_mp=2750, larg_mp=1830,
            comp_real=600, larg_real=400, qt_total=2, def_peca="COSTA",
        ),
    ]

    assert construir_grupos_corte(linhas, []) == []
