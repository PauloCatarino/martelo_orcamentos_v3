"""Renomear uma chave ValueSet tem de levar atrás quem a usa.

O código da chave é texto solto em sete tabelas, sem chave estrangeira nenhuma.
Antes disto, mudar o código no vocabulário deixava toda a gente com o nome
antigo — e sem dar erro: no custeio a lista de materiais vinha vazia e mais
nada. Estes testes fixam as duas metades da solução: contar antes, e propagar
só até onde foi pedido.
"""

from __future__ import annotations

import pytest

from app.models import (
    DefModulo,
    DefModuloLinha,
    DefPeca,
    DefValuesetChave,
    DefValuesetModelo,
    DefValuesetModeloLinha,
    OrcamentoValuesetLinha,
)
from app.services.def_valueset_chave_renomeacao_service import (
    DefValuesetChaveRenomeacaoService,
)

ANTIGA = "FERRAGEM_SUPORTE_VARAO"
NOVA = "FERRAGEM_SUPORTE_LATERAL_VARAO"


@pytest.fixture()
def cenario(session):
    """Uma chave usada num modelo, numa peça, num módulo e num orçamento."""
    chave = DefValuesetChave(
        codigo=ANTIGA, nome="Suporte varão", tipo="FERRAGEM",
        grupo="FERRAGENS", sistema=False, ativo=True, ordem=5,
    )
    session.add(chave)

    modelo = DefValuesetModelo(
        codigo="ROUP_STD", nome="Roupeiro", tipo="ROUPEIRO",
        ambito="GLOBAL", ativo=True,
    )
    session.add(modelo)
    session.flush()

    session.add_all(
        DefValuesetModeloLinha(
            def_valueset_modelo_id=modelo.id,
            chave=ANTIGA,
            codigo_opcao=f"OPC_{i}",
            nome_opcao=f"Opção {i}",
            ordem=i,
            prioridade=i,
            ativo=True,
        )
        for i in (1, 2)
    )
    session.add(
        DefPeca(
            codigo="COSTA", nome="Costa", ativo=True,
            chave_valueset_material=ANTIGA,
        )
    )

    modulo = DefModulo(codigo="MOD", nome="Módulo", ativo=True)
    session.add(modulo)
    session.flush()
    session.add(
        DefModuloLinha(
            def_modulo_id=modulo.id, ordem=1, chave_valueset=ANTIGA, ativo=True
        )
    )

    # A linha de ValueSet do orçamento pendura-se numa VERSÃO do orçamento;
    # aqui só interessa que exista com esta chave.
    session.add_all(
        OrcamentoValuesetLinha(
            orcamento_versao_id=1,
            chave=ANTIGA,
            codigo_opcao=f"ORC_{i}",
            ordem=i,
            ativo=True,
        )
        for i in (1, 2, 3)
    )
    session.commit()

    return DefValuesetChaveRenomeacaoService(session), chave.id


def test_contar_diz_onde_a_chave_e_usada(cenario) -> None:
    service, _id = cenario

    ocorrencias = service.contar_utilizacoes(ANTIGA)

    por_etiqueta = {o.etiqueta: o.total for o in ocorrencias.ocorrencias}
    assert por_etiqueta["Linhas de modelos ValueSet"] == 2
    assert por_etiqueta["Peças — material"] == 1
    assert por_etiqueta["Linhas de módulos guardados"] == 1
    assert por_etiqueta["Orçamentos — ValueSet do orçamento"] == 3
    # Os dois mundos contam-se em separado: é neles que assenta a escolha.
    assert ocorrencias.total_catalogos == 4
    assert ocorrencias.total_orcamentos == 3
    assert ocorrencias.total == 7


def test_contar_codigo_vazio_nao_rebenta(cenario) -> None:
    service, _id = cenario

    assert service.contar_utilizacoes(None).total == 0
    assert service.contar_utilizacoes("   ").ocorrencias == tuple()


def test_por_omissao_muda_catalogos_e_deixa_os_orcamentos(cenario) -> None:
    """O orçamento é o registo do que foi vendido: não se reescreve à sorte."""
    service, chave_id = cenario

    resultado = service.renomear(chave_id, NOVA)

    assert resultado.catalogos_atualizados == 4
    assert resultado.orcamentos_atualizados == 0
    assert resultado.incluiu_orcamentos is False

    depois = service.contar_utilizacoes(NOVA)
    assert depois.total_catalogos == 4
    assert depois.total_orcamentos == 0
    # E o nome antigo sobrevive só nos orçamentos.
    antigo = service.contar_utilizacoes(ANTIGA)
    assert antigo.total_catalogos == 0
    assert antigo.total_orcamentos == 3


def test_com_orcamentos_muda_tudo(cenario) -> None:
    service, chave_id = cenario

    resultado = service.renomear(chave_id, NOVA, incluir_orcamentos=True)

    assert resultado.catalogos_atualizados == 4
    assert resultado.orcamentos_atualizados == 3
    assert service.contar_utilizacoes(ANTIGA).total == 0
    assert service.contar_utilizacoes(NOVA).total == 7


def test_o_vocabulario_tambem_muda(cenario, session) -> None:
    service, chave_id = cenario

    service.renomear(chave_id, NOVA)

    session.expire_all()
    assert session.get(DefValuesetChave, chave_id).codigo == NOVA


def test_o_resto_da_chave_fica_igual(cenario, session) -> None:
    """Renomear é só o código — o nome, o grupo e a ordem não se mexem."""
    service, chave_id = cenario

    service.renomear(chave_id, NOVA)

    session.expire_all()
    chave = session.get(DefValuesetChave, chave_id)
    assert chave.nome == "Suporte varão"
    assert chave.grupo == "FERRAGENS"
    assert chave.tipo == "FERRAGEM"
    assert chave.ordem == 5
    assert chave.ativo is True


def test_codigo_novo_e_normalizado_como_no_resto_da_app(cenario) -> None:
    service, chave_id = cenario

    resultado = service.renomear(chave_id, "  ferragem suporte lateral varao  ")

    assert resultado.codigo_novo == NOVA
    assert service.contar_utilizacoes(NOVA).total_catalogos == 4


def test_nao_deixa_ficar_com_o_codigo_de_outra_chave(cenario, session) -> None:
    service, chave_id = cenario
    session.add(
        DefValuesetChave(
            codigo="FERRAGEM_VARAO", nome="Varão", tipo="FERRAGEM",
            grupo="FERRAGENS", sistema=False, ativo=True, ordem=4,
        )
    )
    session.commit()

    with pytest.raises(ValueError, match="codigo ja existe"):
        service.renomear(chave_id, "FERRAGEM_VARAO")

    # E nada foi tocado pelo caminho.
    assert service.contar_utilizacoes(ANTIGA).total_catalogos == 4


def test_codigo_igual_ao_atual_nao_passa(cenario) -> None:
    service, chave_id = cenario

    with pytest.raises(ValueError, match="igual ao atual"):
        service.renomear(chave_id, ANTIGA)


def test_codigo_vazio_nao_passa(cenario) -> None:
    service, chave_id = cenario

    with pytest.raises(ValueError, match="codigo is required"):
        service.renomear(chave_id, "   ")


def test_chave_desconhecida_nao_passa(cenario) -> None:
    service, _id = cenario

    with pytest.raises(ValueError, match="chave nao encontrada"):
        service.renomear(9999, NOVA)


def test_nao_apanha_chaves_parecidas(cenario, session) -> None:
    """``FERRAGEM_SUPORTE_VARAO_2`` não é ``FERRAGEM_SUPORTE_VARAO``."""
    service, chave_id = cenario
    modelo_id = session.query(DefValuesetModelo).first().id
    session.add(
        DefValuesetModeloLinha(
            def_valueset_modelo_id=modelo_id,
            chave=f"{ANTIGA}_2",
            codigo_opcao="OPC_X",
            nome_opcao="Outra",
            ordem=9,
            prioridade=1,
            ativo=True,
        )
    )
    session.commit()

    service.renomear(chave_id, NOVA)

    assert service.contar_utilizacoes(f"{ANTIGA}_2").total_catalogos == 1
