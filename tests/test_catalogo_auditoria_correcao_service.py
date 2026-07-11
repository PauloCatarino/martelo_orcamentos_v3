"""Tests for supervised catalog-audit corrections."""

from types import SimpleNamespace

import pytest

from app.models import (
    DefModuloLinha,
    DefOperacao,
    DefPeca,
    DefPecaOperacao,
    DefRegraQuantidade,
)
from app.services.catalogo_auditoria_correcao_service import (
    CatalogoAuditoriaCorrecaoService,
)
from app.services.catalogo_auditoria_service import CatalogoAuditoriaItem


class _ScalarResult:
    def __init__(self, value=None) -> None:
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Session:
    def __init__(self, objects=None, results=None) -> None:
        self.objects = objects or {}
        self.results = list(results or [])
        self.committed = False

    def get(self, model, id):
        return self.objects.get((model, id))

    def execute(self, _statement):
        return _ScalarResult(self.results.pop(0) if self.results else None)

    def commit(self) -> None:
        self.committed = True


def _item(codigo, alvo_id):
    return CatalogoAuditoriaItem(
        severidade="ERRO",
        codigo_teste="TESTE",
        area="Teste",
        entidade="Teste",
        entidade_id=1,
        entidade_codigo="TESTE",
        problema="Problema",
        impacto="Impacto",
        sugestao="Sugestão",
        correcao_codigo=codigo,
        correcao_descricao="Correção",
        correcao_alvo_id=alvo_id,
    )


def test_desativa_apenas_ligacao_para_operacao_inativa() -> None:
    ligacao = SimpleNamespace(id=1, def_operacao_id=2, ativo=True)
    operacao = SimpleNamespace(id=2, codigo="CNC", ativo=False)
    session = _Session(
        objects={
            (DefPecaOperacao, 1): ligacao,
            (DefOperacao, 2): operacao,
        }
    )

    mensagem = CatalogoAuditoriaCorrecaoService(session).aplicar(
        _item("DESATIVAR_LIGACAO_OPERACAO_INATIVA", 1)
    )

    assert ligacao.ativo is False
    assert operacao.ativo is False
    assert session.committed is True
    assert "Ligação" in mensagem


def test_cancela_correcao_se_operacao_foi_reativada() -> None:
    ligacao = SimpleNamespace(id=1, def_operacao_id=2, ativo=True)
    operacao = SimpleNamespace(id=2, codigo="CNC", ativo=True)
    session = _Session(
        objects={
            (DefPecaOperacao, 1): ligacao,
            (DefOperacao, 2): operacao,
        }
    )

    with pytest.raises(ValueError, match="já está ativa"):
        CatalogoAuditoriaCorrecaoService(session).aplicar(
            _item("DESATIVAR_LIGACAO_OPERACAO_INATIVA", 1)
        )

    assert ligacao.ativo is True
    assert session.committed is False


def test_desativa_regra_apenas_se_continuar_sem_utilizacao() -> None:
    regra = SimpleNamespace(id=3, codigo="SEM_USO", ativo=True)
    session = _Session(objects={(DefRegraQuantidade, 3): regra}, results=[None, None])

    CatalogoAuditoriaCorrecaoService(session).aplicar(
        _item("DESATIVAR_REGRA_NAO_UTILIZADA", 3)
    )

    assert regra.ativo is False
    assert session.committed is True


def test_atualiza_so_codigo_snapshot_da_linha_modulo() -> None:
    linha = SimpleNamespace(
        id=4,
        ativo=True,
        def_peca_id=5,
        def_peca_codigo="ANTIGO",
        comp="H-20",
    )
    peca = SimpleNamespace(id=5, codigo="NOVO")
    session = _Session(
        objects={(DefModuloLinha, 4): linha, (DefPeca, 5): peca}
    )

    CatalogoAuditoriaCorrecaoService(session).aplicar(
        _item("ATUALIZAR_CODIGO_PECA_MODULO", 4)
    )

    assert linha.def_peca_codigo == "NOVO"
    assert linha.comp == "H-20"
    assert session.committed is True
