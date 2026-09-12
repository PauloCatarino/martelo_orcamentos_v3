"""Copiar chaves inteiras de um modelo ValueSet para outros.

Duas regras que não se negoceiam, e que estes testes prendem:

1. **Nunca apagar nada no destino.** Uma opção que só exista lá pode ter sido
   posta de propósito por quem é dono do modelo.
2. **Respeitar o dono.** Um modelo de outra pessoa, ou global, só se toca com a
   permissão própria — a mesma da propagação de operações.
"""

from __future__ import annotations

import pytest

from app.models import (
    DefValuesetChave,
    DefValuesetModelo,
    DefValuesetModeloLinha,
    User,
)
from app.services.def_valueset_chave_copia_service import (
    ACRESCENTAR_E_ATUALIZAR,
    SO_ACRESCENTAR,
    DefValuesetChaveCopiaService,
)
from app.services.permission_service import (
    PERMISSAO_PROPAGAR_OPERACOES_VALUESET_OUTROS,
    set_user_permissions,
)

VARAO = "FERRAGEM_VARAO"
SUPORTE = "FERRAGEM_SUPORTE_LATERAL_VARAO"


def _linha(modelo_id, chave, codigo, *, preco=10, prioridade=1, ordem=1, ativo=True):
    return DefValuesetModeloLinha(
        def_valueset_modelo_id=modelo_id,
        chave=chave,
        codigo_opcao=codigo,
        nome_opcao=codigo.replace("_", " ").title(),
        ref_le=f"REF_{codigo}",
        descricao_no_orcamento=f"Descrição de {codigo}",
        preco_tabela=preco,
        preco_liquido=preco,
        unidade="UND",
        prioridade=prioridade,
        ordem=ordem,
        ativo=ativo,
    )


@pytest.fixture()
def cenario(session):
    """Origem do paulo, um destino dele, um da Ana e um global."""
    session.add_all(
        [
            DefValuesetChave(
                codigo=VARAO, nome="Varão", tipo="FERRAGEM",
                grupo="FERRAGENS", sistema=False, ativo=True, ordem=4,
            ),
            DefValuesetChave(
                codigo=SUPORTE, nome="Suporte lateral", tipo="FERRAGEM",
                grupo="FERRAGENS", sistema=False, ativo=True, ordem=5,
            ),
        ]
    )
    paulo = User(
        username="paulo", nome="Paulo", email="paulo@exemplo.pt",
        password_hash="x", role="user",
    )
    ana = User(
        username="ana", nome="Ana", email="ana@exemplo.pt",
        password_hash="x", role="user",
    )
    session.add_all([paulo, ana])
    session.flush()

    origem = DefValuesetModelo(
        codigo="ORIGEM", nome="Origem", tipo="ROUPEIRO",
        ambito="UTILIZADOR", user_id=paulo.id, ativo=True,
    )
    meu = DefValuesetModelo(
        codigo="MEU", nome="Meu destino", tipo="ROUPEIRO",
        ambito="UTILIZADOR", user_id=paulo.id, ativo=True,
    )
    dela = DefValuesetModelo(
        codigo="DELA", nome="Da Ana", tipo="ROUPEIRO",
        ambito="UTILIZADOR", user_id=ana.id, ativo=True,
    )
    global_ = DefValuesetModelo(
        codigo="GLOBAL", nome="Global", tipo="ROUPEIRO",
        ambito="GLOBAL", user_id=None, ativo=True,
    )
    desativado = DefValuesetModelo(
        codigo="VELHO", nome="Desativado", tipo="ROUPEIRO",
        ambito="UTILIZADOR", user_id=paulo.id, ativo=False,
    )
    session.add_all([origem, meu, dela, global_, desativado])
    session.flush()

    session.add_all(
        [
            # A origem tem duas opções de varão e uma de suporte.
            _linha(origem.id, VARAO, "VARAO_A", preco=10, prioridade=1, ordem=1),
            _linha(origem.id, VARAO, "VARAO_B", preco=20, prioridade=2, ordem=2),
            _linha(origem.id, SUPORTE, "SUP_A", preco=5, ordem=3),
            # O meu destino já tem o VARAO_A, mas com outro preço, e uma opção
            # que a origem não tem.
            _linha(meu.id, VARAO, "VARAO_A", preco=99, prioridade=1, ordem=1),
            _linha(meu.id, VARAO, "SO_MEU", preco=7, prioridade=3, ordem=2),
        ]
    )
    session.commit()

    return {
        "service": DefValuesetChaveCopiaService(session),
        "session": session,
        "origem": origem.id,
        "meu": meu.id,
        "dela": dela.id,
        "global": global_.id,
        "desativado": desativado.id,
        "paulo": paulo,
        "ana": ana,
    }


def _destino(contexto, modelo_id):
    return next(d for d in contexto.destinos if d.modelo_id == modelo_id)


def test_listar_chaves_do_modelo_de_origem(cenario) -> None:
    chaves = cenario["service"].listar_chaves_do_modelo(cenario["origem"])

    por_codigo = {c.chave: c for c in chaves}
    assert por_codigo[VARAO].opcoes == 2
    assert por_codigo[SUPORTE].opcoes == 1
    assert por_codigo[VARAO].grupo == "Ferragens"


def test_previsao_conta_o_que_falta_sem_escrever(cenario) -> None:
    service, session = cenario["service"], cenario["session"]

    contexto = service.preparar_contexto(
        cenario["origem"], [VARAO], cenario["paulo"]
    )

    meu = _destino(contexto, cenario["meu"])
    # Falta o VARAO_B; o VARAO_A existe (diferente, mas neste modo não se toca).
    assert meu.total_a_criar == 1
    assert meu.total_a_atualizar == 0
    assert meu.previsoes[0].so_no_destino == 1  # o SO_MEU

    # E nada foi escrito.
    assert (
        session.query(DefValuesetModeloLinha)
        .filter_by(def_valueset_modelo_id=cenario["meu"])
        .count()
        == 2
    )


def test_modo_atualizar_conta_tambem_as_diferentes(cenario) -> None:
    service = cenario["service"]

    contexto = service.preparar_contexto(
        cenario["origem"], [VARAO], cenario["paulo"], modo=ACRESCENTAR_E_ATUALIZAR
    )

    meu = _destino(contexto, cenario["meu"])
    assert meu.total_a_criar == 1  # VARAO_B
    assert meu.total_a_atualizar == 1  # VARAO_A, que tem preço diferente


def test_copiar_cria_o_que_falta_e_nao_apaga_nada(cenario) -> None:
    service, session = cenario["service"], cenario["session"]
    contexto = service.preparar_contexto(
        cenario["origem"], [VARAO], cenario["paulo"]
    )

    resultado = service.executar(contexto, [cenario["meu"]], cenario["paulo"])

    assert resultado.linhas_criadas == 1
    assert resultado.linhas_atualizadas == 0
    linhas = {
        l.codigo_opcao: l
        for l in session.query(DefValuesetModeloLinha)
        .filter_by(def_valueset_modelo_id=cenario["meu"])
        .all()
    }
    assert set(linhas) == {"VARAO_A", "VARAO_B", "SO_MEU"}
    # A opção que só existia no destino ficou intacta...
    assert linhas["SO_MEU"].preco_tabela == 7
    # ...e a que já lá estava não foi tocada neste modo.
    assert linhas["VARAO_A"].preco_tabela == 99


def test_modo_atualizar_poe_as_comuns_iguais_a_origem(cenario) -> None:
    service, session = cenario["service"], cenario["session"]
    contexto = service.preparar_contexto(
        cenario["origem"], [VARAO], cenario["paulo"], modo=ACRESCENTAR_E_ATUALIZAR
    )

    resultado = service.executar(contexto, [cenario["meu"]], cenario["paulo"])

    assert resultado.linhas_criadas == 1
    assert resultado.linhas_atualizadas == 1
    linhas = {
        l.codigo_opcao: l
        for l in session.query(DefValuesetModeloLinha)
        .filter_by(def_valueset_modelo_id=cenario["meu"])
        .all()
    }
    assert linhas["VARAO_A"].preco_tabela == 10  # veio da origem
    assert linhas["SO_MEU"].preco_tabela == 7  # continua intacta


def test_copiar_duas_vezes_nao_duplica(cenario) -> None:
    """A segunda passagem não tem nada para fazer."""
    service = cenario["service"]
    contexto = service.preparar_contexto(
        cenario["origem"], [VARAO], cenario["paulo"]
    )
    service.executar(contexto, [cenario["meu"]], cenario["paulo"])

    segundo = service.preparar_contexto(
        cenario["origem"], [VARAO], cenario["paulo"]
    )

    assert _destino(segundo, cenario["meu"]).sem_efeito is True


def test_modelo_de_outra_pessoa_bloqueado_sem_permissao(cenario) -> None:
    service = cenario["service"]

    contexto = service.preparar_contexto(cenario["origem"], [VARAO], cenario["paulo"])

    dela = _destino(contexto, cenario["dela"])
    global_ = _destino(contexto, cenario["global"])
    assert dela.permitido is False
    assert "permissão" in (dela.motivo_bloqueio or "")
    assert dela.ambito == "Outro utilizador"
    assert global_.permitido is False
    assert global_.ambito == "Global"
    # E o meu continua meu.
    assert _destino(contexto, cenario["meu"]).permitido is True


def test_executar_num_modelo_bloqueado_recusa(cenario) -> None:
    service, session = cenario["service"], cenario["session"]
    contexto = service.preparar_contexto(cenario["origem"], [VARAO], cenario["paulo"])

    with pytest.raises(PermissionError):
        service.executar(contexto, [cenario["dela"]], cenario["paulo"])

    # A recusa não pode deixar meio trabalho feito.
    assert (
        session.query(DefValuesetModeloLinha)
        .filter_by(def_valueset_modelo_id=cenario["dela"])
        .count()
        == 0
    )


def test_com_a_permissao_ja_pode_tocar_nos_outros(cenario) -> None:
    service, session = cenario["service"], cenario["session"]
    set_user_permissions(
        session,
        cenario["paulo"].id,
        {PERMISSAO_PROPAGAR_OPERACOES_VALUESET_OUTROS: True},
    )
    session.commit()

    contexto = service.preparar_contexto(cenario["origem"], [VARAO], cenario["paulo"])

    assert _destino(contexto, cenario["dela"]).permitido is True
    assert _destino(contexto, cenario["global"]).permitido is True


def test_modelos_desativados_ficam_de_fora(cenario) -> None:
    service = cenario["service"]

    contexto = service.preparar_contexto(cenario["origem"], [VARAO], cenario["paulo"])

    assert cenario["desativado"] not in {d.modelo_id for d in contexto.destinos}
    assert cenario["origem"] not in {d.modelo_id for d in contexto.destinos}


def test_destinos_do_mesmo_tipo_aparecem_primeiro(cenario, session) -> None:
    service = cenario["service"]
    session.add(
        DefValuesetModelo(
            codigo="COZINHA", nome="Cozinha", tipo="COZINHA",
            ambito="UTILIZADOR", user_id=cenario["paulo"].id, ativo=True,
        )
    )
    session.commit()

    contexto = service.preparar_contexto(cenario["origem"], [VARAO], cenario["paulo"])

    codigos = [d.modelo_codigo for d in contexto.destinos]
    assert codigos.index("MEU") < codigos.index("COZINHA")


def test_chave_que_a_origem_nao_tem_e_recusada(cenario) -> None:
    service = cenario["service"]

    with pytest.raises(ValueError, match="não tem opções ativas"):
        service.preparar_contexto(
            cenario["origem"], ["CHAVE_INEXISTENTE"], cenario["paulo"]
        )


def test_sem_chaves_ou_sem_destinos_nao_avanca(cenario) -> None:
    service = cenario["service"]

    with pytest.raises(ValueError, match="pelo menos uma chave"):
        service.preparar_contexto(cenario["origem"], [], cenario["paulo"])

    contexto = service.preparar_contexto(cenario["origem"], [VARAO], cenario["paulo"])
    with pytest.raises(ValueError, match="pelo menos um modelo"):
        service.executar(contexto, [], cenario["paulo"])


def test_destino_fora_da_previsao_e_recusado(cenario) -> None:
    service = cenario["service"]
    contexto = service.preparar_contexto(cenario["origem"], [VARAO], cenario["paulo"])

    with pytest.raises(ValueError, match="fora da pré-visualização"):
        service.executar(contexto, [9999], cenario["paulo"])


def test_modo_invalido_nao_passa(cenario) -> None:
    service = cenario["service"]

    with pytest.raises(ValueError, match="modo invalido"):
        service.preparar_contexto(
            cenario["origem"], [VARAO], cenario["paulo"], modo="APAGAR_TUDO"
        )


def test_copiar_varias_chaves_de_uma_vez(cenario) -> None:
    service, session = cenario["service"], cenario["session"]
    contexto = service.preparar_contexto(
        cenario["origem"], [VARAO, SUPORTE], cenario["paulo"]
    )

    resultado = service.executar(contexto, [cenario["meu"]], cenario["paulo"])

    # VARAO_B (falta) + SUP_A (chave inteira em falta).
    assert resultado.linhas_criadas == 2
    chaves = {
        l.chave
        for l in session.query(DefValuesetModeloLinha)
        .filter_by(def_valueset_modelo_id=cenario["meu"])
        .all()
    }
    assert chaves == {VARAO, SUPORTE}


def test_modo_so_acrescentar_e_o_de_partida(cenario) -> None:
    """O menos destrutivo é o que sai por omissão."""
    service = cenario["service"]

    contexto = service.preparar_contexto(cenario["origem"], [VARAO], cenario["paulo"])

    assert contexto.modo == SO_ACRESCENTAR
