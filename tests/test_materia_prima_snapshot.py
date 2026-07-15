"""Tests for the raw material snapshot resolvers used by ValueSet dialogs."""

from __future__ import annotations

from types import SimpleNamespace

from app.domain.materia_prima_snapshot import (
    coresp_orla_0_4,
    coresp_orla_1_0,
    familia_materia_prima,
    preco_orla_m2,
    precos_orlas_m2,
    tipo_materia_prima,
)


def _materia(**kwargs):
    base = {
        "tipo_martelo": None,
        "familia_martelo": None,
        "tipo_original_excel": None,
        "familia_original_excel": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_tipo_prefere_martelo() -> None:
    materia = _materia(tipo_martelo="PLACA", tipo_original_excel="AGLOMERADO")
    assert tipo_materia_prima(materia) == "PLACA"


def test_tipo_fallback_para_original_excel() -> None:
    # Real data: tipo_martelo is empty, the value lives in the Excel column.
    materia = _materia(tipo_martelo=None, tipo_original_excel="PUXADOR")
    assert tipo_materia_prima(materia) == "PUXADOR"


def test_familia_fallback_para_original_excel() -> None:
    materia = _materia(familia_martelo=None, familia_original_excel="FERRAGENS")
    assert familia_materia_prima(materia) == "FERRAGENS"


def test_tipo_e_familia_vazios() -> None:
    materia = _materia()
    assert tipo_materia_prima(materia) is None
    assert familia_materia_prima(materia) is None


def test_orlas_copiadas_quando_existem() -> None:
    materia = _materia(coresp_orla_0_4="ORL0002", coresp_orla_1_0="ORL0003")
    assert coresp_orla_0_4(materia) == "ORL0002"
    assert coresp_orla_1_0(materia) == "ORL0003"


def test_orlas_vazias_quando_nao_existem() -> None:
    # The catalog has no orla columns: resolvers must not raise and return None.
    materia = _materia()
    assert coresp_orla_0_4(materia) is None
    assert coresp_orla_1_0(materia) is None


def test_resolvers_nao_alteram_materia() -> None:
    materia = _materia(tipo_original_excel="PUXADOR", coresp_orla_0_4="ORL0002")
    tipo_materia_prima(materia)
    familia_materia_prima(materia)
    coresp_orla_0_4(materia)
    coresp_orla_1_0(materia)
    assert materia.tipo_original_excel == "PUXADOR"
    assert materia.coresp_orla_0_4 == "ORL0002"
    assert materia.tipo_martelo is None


def test_preco_orla_m2_aceita_apenas_unidade_m2() -> None:
    catalogo = {
        "ORL-M2": SimpleNamespace(preco_liquido=12, unidade="M2"),
        "ORL-ML": SimpleNamespace(preco_liquido=3, unidade="ML"),
    }
    assert preco_orla_m2("ORL-M2", catalogo.get) == 12
    assert preco_orla_m2("ORL-ML", catalogo.get) is None


def test_precos_orlas_m2_resolve_fina_e_grossa() -> None:
    materia = _materia(coresp_orla_0_4="ORL-F", coresp_orla_1_0="ORL-G")
    catalogo = {
        "ORL-F": SimpleNamespace(preco_liquido=4.25, unidade="M2"),
        "ORL-G": SimpleNamespace(preco_liquido=7.50, unidade="M2"),
    }
    assert precos_orlas_m2(materia, catalogo.get) == (4.25, 7.50)
