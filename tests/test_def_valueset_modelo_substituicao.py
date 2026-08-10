"""Publication of a personal ValueSet model over an explicit global target."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import (
    DefMaquina,
    DefOperacao,
    DefValuesetModelo,
    DefValuesetModeloLinha,
    DefValuesetModeloLinhaOperacao,
)
from app.repositories.def_valueset_modelo_linha_repository import (
    DefValuesetModeloLinhaRepository,
)
from app.services.def_valueset_modelo_service import (
    CriarDefValuesetModeloData,
    DefValuesetModeloService,
)


def _catalogo(session):
    origem = DefValuesetModelo(
        codigo="ROUP_STD",
        nome="Roupeiros Interiores",
        descricao="Modelo pessoal novo",
        tipo="ROUPEIRO",
        ambito="UTILIZADOR",
        visivel_para_todos=False,
        ativo=True,
    )
    destino = DefValuesetModelo(
        codigo="ROUPEIRO_STANDARD",
        nome="Roupeiro standard antigo",
        descricao="Conteúdo antigo",
        tipo="ROUPEIRO",
        ambito="GLOBAL",
        visivel_para_todos=True,
        ativo=True,
    )
    nao_selecionado = DefValuesetModelo(
        codigo="COZINHA_GLOBAL",
        nome="Cozinha intacta",
        ambito="GLOBAL",
        visivel_para_todos=True,
        ativo=False,
    )
    session.add_all([origem, destino, nao_selecionado])
    session.flush()

    maquina = DefMaquina(codigo="CNC_PUB", nome="CNC publicação")
    session.add(maquina)
    session.flush()
    operacao = DefOperacao(
        codigo="CNC_PUBLICAR",
        nome="CNC publicar",
        maquina_id=maquina.id,
    )
    session.add(operacao)
    session.flush()

    linha_origem = DefValuesetModeloLinha(
        def_valueset_modelo_id=origem.id,
        chave="MATERIAL_PORTAS",
        codigo_opcao="PORTA_NOVA",
        nome_opcao="Porta nova",
        prioridade=2,
        ordem=3,
        ref_le="MAT-001",
        preco_tabela=Decimal("12.3400"),
        ativo=True,
    )
    linha_antiga = DefValuesetModeloLinha(
        def_valueset_modelo_id=destino.id,
        chave="MATERIAL_PORTAS",
        codigo_opcao="PORTA_ANTIGA",
        ordem=1,
        ativo=True,
    )
    linha_intacta = DefValuesetModeloLinha(
        def_valueset_modelo_id=nao_selecionado.id,
        chave="MATERIAL_FUNDOS",
        codigo_opcao="FUNDO_INTACTO",
        ordem=1,
        ativo=True,
    )
    session.add_all([linha_origem, linha_antiga, linha_intacta])
    session.flush()
    session.add_all(
        [
            DefValuesetModeloLinhaOperacao(
                def_valueset_modelo_linha_id=linha_origem.id,
                def_operacao_id=operacao.id,
                ordem=2,
                acao="ADICIONAR",
                metodo_calculo="TEMPO",
                regra_calculo="POR_PECA",
                quantidade_base=Decimal("1.0000"),
                tempo_por_unidade_minutos=Decimal("0.5000"),
                unidade_tempo="PECA",
                obrigatorio=True,
                ativo=True,
            ),
            DefValuesetModeloLinhaOperacao(
                def_valueset_modelo_linha_id=linha_antiga.id,
                def_operacao_id=operacao.id,
                ordem=1,
                acao="DESATIVAR",
                obrigatorio=True,
                ativo=False,
            ),
        ]
    )
    session.commit()
    return origem, destino, nao_selecionado, linha_antiga, linha_intacta


def _dados_publicacao() -> CriarDefValuesetModeloData:
    return CriarDefValuesetModeloData(
        codigo="ROUP_STD",
        nome="Roupeiros Interiores | Frentes | Ferragens",
        descricao="Novo conteúdo publicado",
        tipo="ROUPEIRO",
        ambito="GLOBAL",
        user_id=99,
        visivel_para_todos=True,
        observacoes="Ferragens standard novas",
        ativo=False,
    )


def test_lista_destinos_globais_com_estado_e_impacto(session) -> None:
    origem, destino, nao_selecionado, *_ = _catalogo(session)

    resumos = DefValuesetModeloService(
        session
    ).listar_destinos_globais_para_substituicao(excluir_modelo_id=origem.id)

    assert [resumo.modelo.id for resumo in resumos] == [
        nao_selecionado.id,
        destino.id,
    ]
    por_id = {resumo.modelo.id: resumo for resumo in resumos}
    assert por_id[destino.id].linhas == 1
    assert por_id[destino.id].operacoes == 1
    assert por_id[nao_selecionado.id].modelo.ativo is False


def test_substitui_apenas_destino_selecionado_e_mantem_codigo(session) -> None:
    origem, destino, nao_selecionado, linha_antiga, linha_intacta = _catalogo(session)

    resultado = DefValuesetModeloService(session).substituir_modelo_global(
        origem.id,
        destino.id,
        _dados_publicacao(),
        autorizado=True,
    )

    assert resultado.modelo.id == destino.id
    assert resultado.modelo.codigo == "ROUPEIRO_STANDARD"
    assert resultado.modelo.nome == "Roupeiros Interiores | Frentes | Ferragens"
    assert resultado.modelo.ambito == "GLOBAL"
    assert resultado.modelo.user_id is None
    assert resultado.modelo.visivel_para_todos is True
    assert resultado.modelo.ativo is False
    assert resultado.linhas_removidas == 1
    assert resultado.operacoes_removidas == 1
    assert resultado.linhas_copiadas == 1
    assert resultado.operacoes_copiadas == 1

    linhas_destino = DefValuesetModeloLinhaRepository(session).list_by_modelo(destino.id)
    assert len(linhas_destino) == 1
    publicada = linhas_destino[0]
    assert publicada.codigo_opcao == "PORTA_NOVA"
    assert publicada.prioridade == 2
    assert publicada.ref_le == "MAT-001"
    assert publicada.preco_tabela == Decimal("12.3400")
    operacao = session.execute(
        select(DefValuesetModeloLinhaOperacao).where(
            DefValuesetModeloLinhaOperacao.def_valueset_modelo_linha_id
            == publicada.id
        )
    ).scalar_one()
    assert operacao.metodo_calculo == "TEMPO"
    assert operacao.regra_calculo == "POR_PECA"
    assert operacao.tempo_por_unidade_minutos == Decimal("0.5000")

    assert session.get(DefValuesetModeloLinha, linha_antiga.id) is None
    assert session.get(DefValuesetModeloLinha, linha_intacta.id) is not None
    assert (
        session.get(DefValuesetModelo, nao_selecionado.id).nome
        == "Cozinha intacta"
    )
    assert len(DefValuesetModeloLinhaRepository(session).list_by_modelo(origem.id)) == 1


def test_sem_permissao_nao_altera_destino(session) -> None:
    origem, destino, *_ = _catalogo(session)

    with pytest.raises(PermissionError, match="permissão administrativa"):
        DefValuesetModeloService(session).substituir_modelo_global(
            origem.id,
            destino.id,
            _dados_publicacao(),
            autorizado=False,
        )

    assert session.get(DefValuesetModelo, destino.id).nome == "Roupeiro standard antigo"
    linhas = DefValuesetModeloLinhaRepository(session).list_by_modelo(destino.id)
    assert [linha.codigo_opcao for linha in linhas] == ["PORTA_ANTIGA"]


def test_erro_intermedio_faz_rollback_integral(session, monkeypatch) -> None:
    origem, destino, *_ = _catalogo(session)

    def falhar_ao_criar_linha(self, **_fields):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(
        DefValuesetModeloLinhaRepository,
        "create",
        falhar_ao_criar_linha,
    )

    with pytest.raises(RuntimeError, match="falha simulada"):
        DefValuesetModeloService(session).substituir_modelo_global(
            origem.id,
            destino.id,
            _dados_publicacao(),
            autorizado=True,
        )

    session.expire_all()
    assert session.get(DefValuesetModelo, destino.id).nome == "Roupeiro standard antigo"
    linhas = DefValuesetModeloLinhaRepository(session).list_by_modelo(destino.id)
    assert [linha.codigo_opcao for linha in linhas] == ["PORTA_ANTIGA"]


def test_recusa_destino_nao_global(session) -> None:
    origem, *_ = _catalogo(session)
    outro_pessoal = DefValuesetModelo(
        codigo="OUTRO_PESSOAL",
        nome="Outro",
        ambito="UTILIZADOR",
        visivel_para_todos=False,
        ativo=True,
    )
    session.add(outro_pessoal)
    session.commit()

    with pytest.raises(ValueError, match="destino nao e global"):
        DefValuesetModeloService(session).substituir_modelo_global(
            origem.id,
            outro_pessoal.id,
            _dados_publicacao(),
            autorizado=True,
        )
