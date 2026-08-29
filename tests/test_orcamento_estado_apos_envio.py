"""Enviar o orçamento por email passa-o a "Enviado".

Pedido do Paulo: hoje é preciso ir ao Editar Orçamento mudar o estado à mão
depois de o email sair, e é fácil esquecer.
"""

from __future__ import annotations

import pytest

from app.domain.orcamento_estados import (
    ESTADO_ENVIADO,
    ESTADO_INICIAL,
    estado_apos_envio,
)


@pytest.mark.parametrize("estado", [ESTADO_INICIAL, "Não Enviado"])
def test_sobe_a_enviado_a_partir_dos_estados_por_enviar(estado: str) -> None:
    assert estado_apos_envio(estado) == ESTADO_ENVIADO


@pytest.mark.parametrize(
    "estado",
    ["Adjudicado", "Concluído", "Não Adjudicado", "Sem Interesse", "Cancelado"],
)
def test_nao_recua_um_estado_que_alguem_pos_de_proposito(estado: str) -> None:
    """Reenviar um orçamento já Adjudicado não pode apagar essa informação."""
    assert estado_apos_envio(estado) is None


def test_reenviar_um_ja_enviado_nao_muda_nada() -> None:
    assert estado_apos_envio(ESTADO_ENVIADO) is None


def test_sem_estado_nao_inventa() -> None:
    assert estado_apos_envio(None) is None
    assert estado_apos_envio("") is None
