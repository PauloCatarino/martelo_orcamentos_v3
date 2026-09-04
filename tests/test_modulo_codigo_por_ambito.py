"""O código de um módulo é único DENTRO da sua prateleira, não na base toda.

O mesmo módulo costuma existir duas vezes: uma cópia global, gerida pelo
administrador, e a cópia de quem o usa. Com o código único na base inteira era
preciso inventar um segundo nome, e nasciam pares como `1_MOD_2_PORTAS_3GVTS`
(global) e `1_MOD_2_PORTAS_3_GVTS` (utilizador) — o mesmo módulo, com um
underscore de diferença.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.services.def_modulo_service import (
    CriarDefModuloData,
    DefModuloService,
    EditarDefModuloCabecalhoData,
)


def _criar(service, codigo, *, ambito, user_id=None, nome="Módulo"):
    return service.criar(
        CriarDefModuloData(
            codigo=codigo, nome=nome, ambito=ambito, user_id=user_id
        )
    )


def test_o_mesmo_codigo_pode_existir_no_global_e_no_utilizador(
    session: Session,
) -> None:
    service = DefModuloService(session)

    global_ = _criar(service, "1_MOD_2_PORTAS_3GVTS", ambito="GLOBAL")
    do_paulo = _criar(
        service, "1_MOD_2_PORTAS_3GVTS", ambito="UTILIZADOR", user_id=2
    )

    assert global_.modulo.id != do_paulo.modulo.id
    assert global_.modulo.codigo == do_paulo.modulo.codigo


def test_dois_utilizadores_podem_ter_o_mesmo_codigo(session: Session) -> None:
    service = DefModuloService(session)

    do_paulo = _criar(service, "MODULO_COZINHA", ambito="UTILIZADOR", user_id=2)
    da_andreia = _criar(service, "MODULO_COZINHA", ambito="UTILIZADOR", user_id=4)

    assert do_paulo.modulo.id != da_andreia.modulo.id


def test_repetir_o_codigo_na_mesma_prateleira_continua_proibido(
    session: Session,
) -> None:
    service = DefModuloService(session)
    _criar(service, "MODULO_COZINHA", ambito="UTILIZADOR", user_id=2)

    with pytest.raises(ValueError, match="nos seus módulos"):
        _criar(service, "MODULO_COZINHA", ambito="UTILIZADOR", user_id=2)


def test_repetir_o_codigo_no_global_continua_proibido(session: Session) -> None:
    """Em MySQL dois NULL não colidem: quem guarda este caso é o serviço."""
    service = DefModuloService(session)
    _criar(service, "REMATES", ambito="GLOBAL")

    with pytest.raises(ValueError, match="nos módulos globais"):
        _criar(service, "REMATES", ambito="GLOBAL")


def test_converter_para_global_recusa_se_o_codigo_ja_la_estiver(
    session: Session,
) -> None:
    service = DefModuloService(session)
    _criar(service, "REMATES", ambito="GLOBAL")
    do_paulo = _criar(service, "REMATES", ambito="UTILIZADOR", user_id=2)

    with pytest.raises(ValueError, match="nos módulos globais"):
        service.converter_ambito(
            do_paulo.modulo.id, "GLOBAL", acting_user_id=2, is_admin=True
        )


def test_converter_para_global_deixa_passar_quando_esta_livre(
    session: Session,
) -> None:
    service = DefModuloService(session)
    do_paulo = _criar(service, "REMATES", ambito="UTILIZADOR", user_id=2)

    convertido = service.converter_ambito(
        do_paulo.modulo.id, "GLOBAL", acting_user_id=2, is_admin=True
    )

    assert convertido.ambito == "GLOBAL"
    assert convertido.user_id is None


def test_editar_cabecalho_para_um_ambito_ocupado_e_recusado(
    session: Session,
) -> None:
    service = DefModuloService(session)
    _criar(service, "REMATES", ambito="GLOBAL")
    do_paulo = _criar(service, "REMATES", ambito="UTILIZADOR", user_id=2)

    with pytest.raises(ValueError, match="nos módulos globais"):
        service.editar_cabecalho(
            do_paulo.modulo.id,
            EditarDefModuloCabecalhoData(nome="Remates", ambito="GLOBAL"),
        )
