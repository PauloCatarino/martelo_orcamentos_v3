"""Validação final: cada tipo de aviso de produção é classificado com sentido.

Matriz que documenta e protege o comportamento do supervisor para TODOS os avisos
de custeio: os graves têm categoria/origens úteis; os informativos não têm botão.
"""

from __future__ import annotations

import pytest

from app.domain import custos, orlas
from app.services import orcamento_item_custeio_linha_service as svc
from app.services.custeio_supervisor import diagnosticar_observacoes, tem_erro_grave

# Avisos GRAVES: (mensagem, categoria esperada, deve apontar a Matérias-Primas?)
AVISOS_GRAVES = [
    (custos.AVISO_MP_DADOS_INCOMPLETOS, "Material", True),
    (custos.AVISO_MATERIA_PRIMA_EM_FALTA, "Material", True),
    (custos.AVISO_UNIDADE_INVALIDA, "Material", True),
    (custos.AVISO_ML_DADOS_INCOMPLETOS, "Material", True),
    (custos.AVISO_FERRAGEM_DADOS_INCOMPLETOS, "Ferragem", True),
    (orlas.AVISO_UNIDADE_ORLA, "Orlagem", True),
    (orlas.AVISO_ESPESSURA_ORLA, "Orlagem", True),
    (svc.AVISO_PRECO_ORLA_EM_FALTA, "Orlagem", True),
]

# Avisos INFORMATIVOS: calculam na mesma / são intencionais -> sem botão.
AVISOS_INFORMATIVOS = [
    svc.AVISO_PRECO_ORLA_CATALOGO,
    svc.AVISO_PRECO_ORLA_ZERO,
]


@pytest.mark.parametrize("mensagem,categoria,aponta_materias", AVISOS_GRAVES)
def test_aviso_grave_tem_categoria_e_origens_uteis(
    mensagem, categoria, aponta_materias
) -> None:
    diagnosticos = diagnosticar_observacoes(mensagem)
    assert len(diagnosticos) == 1
    d = diagnosticos[0]
    assert d.grave is True, mensagem
    assert d.categoria == categoria, mensagem
    assert d.porque and d.sugestao  # explica e sugere
    assert d.origens  # tem para onde ir
    if aponta_materias:
        titulos = {origem.titulo for origem in d.origens}
        assert "Matérias-Primas" in titulos, mensagem


@pytest.mark.parametrize("mensagem", AVISOS_INFORMATIVOS)
def test_aviso_informativo_nao_e_grave(mensagem) -> None:
    assert tem_erro_grave(mensagem) is False
    assert diagnosticar_observacoes(mensagem) == []


def test_avisos_graves_comecam_por_prefixo_de_seccao() -> None:
    # Cada aviso tem de começar pelo prefixo da sua secção para poder ser REMOVIDO
    # ao corrigir (senão fica "preso"). Prefixos usados nos merges do serviço.
    prefixos = ("Custo MP", "Custo ML", "Custo ferragem", "Custo de orla", "Custo não calculado:")
    for mensagem, _cat, _mat in AVISOS_GRAVES:
        assert any(mensagem.startswith(p) for p in prefixos), mensagem
