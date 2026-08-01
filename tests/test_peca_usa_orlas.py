"""A peça trabalha com orlas? Guarda, limpa as orlas e avisa no custeio."""

from __future__ import annotations

import dataclasses

from app.services.def_peca_service import (
    CriarDefPecaData,
    DefPecaService,
    EditarDefPecaData,
)


def test_por_defeito_a_peca_leva_orlas(session) -> None:
    peca = DefPecaService(session).criar_peca(
        CriarDefPecaData(
            codigo="LATERAL_TESTE",
            nome="Lateral teste",
            orla_c1=2,
            orla_c2=2,
            orla_l1=1,
            orla_l2=1,
        )
    )

    assert peca.usa_orlas is True
    assert (peca.orla_c1, peca.orla_c2, peca.orla_l1, peca.orla_l2) == (2, 2, 1, 1)


def test_sem_orlas_as_quatro_ficam_a_zero(session) -> None:
    # Uma ferragem não leva orla nenhuma: guardar 2222 aqui seria contraditório
    # e faria a orlagem ser cobrada.
    peca = DefPecaService(session).criar_peca(
        CriarDefPecaData(
            codigo="DOBRADICA_TESTE",
            nome="Dobradiça teste",
            usa_orlas=False,
            orla_c1=2,
            orla_c2=2,
            orla_l1=2,
            orla_l2=2,
        )
    )

    assert peca.usa_orlas is False
    assert (peca.orla_c1, peca.orla_c2, peca.orla_l1, peca.orla_l2) == (0, 0, 0, 0)


def test_desligar_o_visto_ao_editar_limpa_as_orlas(session) -> None:
    service = DefPecaService(session)
    peca = service.criar_peca(
        CriarDefPecaData(
            codigo="PERFIL_TESTE",
            nome="Perfil teste",
            orla_c1=2,
            orla_c2=2,
            orla_l1=2,
            orla_l2=2,
        )
    )

    editada = service.editar_peca(
        peca.id,
        EditarDefPecaData(
            codigo=peca.codigo,
            nome=peca.nome,
            usa_orlas=False,
            orla_c1=2,
            orla_c2=2,
            orla_l1=2,
            orla_l2=2,
        ),
    )

    assert editada.usa_orlas is False
    assert (editada.orla_c1, editada.orla_c2, editada.orla_l1, editada.orla_l2) == (
        0,
        0,
        0,
        0,
    )


def test_duplicar_leva_o_visto(session) -> None:
    service = DefPecaService(session)
    peca = service.criar_peca(
        CriarDefPecaData(codigo="PUXADOR_TESTE", nome="Puxador teste", usa_orlas=False)
    )

    copia = service.duplicar_peca(peca.id, "PUXADOR_TESTE_2")

    assert copia.usa_orlas is False


def test_dialogos_pedem_o_visto() -> None:
    from app.ui.dialogs.editar_def_peca_dialog import EditarDefPecaDialogData
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialogData

    for data_class in (NovaDefPecaDialogData, EditarDefPecaDialogData):
        campos = {campo.name for campo in dataclasses.fields(data_class)}
        assert "usa_orlas" in campos
