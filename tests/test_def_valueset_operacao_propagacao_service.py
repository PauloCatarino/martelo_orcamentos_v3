"""Controlled propagation of ValueSet model-line operations."""

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
    User,
)
from app.services.def_valueset_operacao_propagacao_service import (
    DefValuesetOperacaoPropagacaoService,
)
from app.services.permission_service import (
    PERMISSAO_PROPAGAR_OPERACOES_VALUESET_OUTROS,
    set_user_permissions,
)


def _user(session, username: str, role: str = "user") -> User:
    user = User(
        username=username,
        nome=username.title(),
        email=f"{username}@example.test",
        password_hash="hash",
        role=role,
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user


def _modelo(
    session,
    codigo: str,
    user: User | None,
    *,
    ambito: str = "UTILIZADOR",
    ativo: bool = True,
) -> DefValuesetModelo:
    modelo = DefValuesetModelo(
        codigo=codigo,
        nome=f"Modelo {codigo}",
        ambito=ambito,
        user_id=user.id if user is not None else None,
        visivel_para_todos=ambito == "GLOBAL",
        ativo=ativo,
    )
    session.add(modelo)
    session.flush()
    return modelo


def _linha(
    session,
    modelo: DefValuesetModelo,
    codigo: str,
    *,
    chave: str = "FERRAGEM_PE_NIVELADOR",
    ref_le: str = "NIV-01",
    ativo: bool = True,
) -> DefValuesetModeloLinha:
    linha = DefValuesetModeloLinha(
        def_valueset_modelo_id=modelo.id,
        chave=chave,
        codigo_opcao=codigo,
        nome_opcao=codigo,
        ref_le=ref_le,
        ordem=1,
        ativo=ativo,
    )
    session.add(linha)
    session.flush()
    return linha


def _ligar(
    session,
    linha: DefValuesetModeloLinha,
    operacao: DefOperacao,
    *,
    ordem: int = 1,
    tempo: str = "1.0",
    ativo: bool = True,
) -> DefValuesetModeloLinhaOperacao:
    ligacao = DefValuesetModeloLinhaOperacao(
        def_valueset_modelo_linha_id=linha.id,
        def_operacao_id=operacao.id,
        ordem=ordem,
        acao="ADICIONAR",
        metodo_calculo="TEMPO",
        regra_calculo="FIXA",
        tempo_por_unidade_minutos=Decimal(tempo),
        obrigatorio=True,
        ativo=ativo,
    )
    session.add(ligacao)
    session.flush()
    return ligacao


def _operacoes(session, linha_id: int) -> list[DefValuesetModeloLinhaOperacao]:
    return list(
        session.execute(
            select(DefValuesetModeloLinhaOperacao)
            .where(
                DefValuesetModeloLinhaOperacao.def_valueset_modelo_linha_id
                == linha_id
            )
            .order_by(
                DefValuesetModeloLinhaOperacao.ordem,
                DefValuesetModeloLinhaOperacao.id,
            )
        ).scalars()
    )


@pytest.fixture()
def catalogo(session):
    paulo = _user(session, "paulo")
    ana = _user(session, "ana")
    admin = _user(session, "admin", role="admin")
    maquina = DefMaquina(codigo="CNC_PROP", nome="CNC Propagação")
    session.add(maquina)
    session.flush()
    cnc = DefOperacao(codigo="CNC_NIV", nome="CNC", maquina_id=maquina.id)
    tempo = DefOperacao(codigo="TEMPO_NIV", nome="Tempo", maquina_id=maquina.id)
    antiga = DefOperacao(codigo="ANTIGA_NIV", nome="Antiga", maquina_id=maquina.id)
    session.add_all([cnc, tempo, antiga])
    session.flush()

    modelo_paulo = _modelo(session, "PAULO", paulo)
    modelo_ana = _modelo(session, "ANA", ana)
    modelo_global = _modelo(session, "GLOBAL", None, ambito="GLOBAL", ativo=False)
    origem = _linha(session, modelo_paulo, "ORIGEM")
    proprio_1 = _linha(session, modelo_paulo, "PROPRIO_1")
    proprio_2 = _linha(session, modelo_paulo, "PROPRIO_2", ativo=False)
    outro = _linha(session, modelo_ana, "OUTRO")
    global_ = _linha(session, modelo_global, "GLOBAL")
    chave_errada = _linha(
        session, modelo_paulo, "CHAVE_ERRADA", chave="MATERIAL_PORTAS"
    )
    ref_errada = _linha(session, modelo_paulo, "REF_ERRADA", ref_le="OUTRA")

    _ligar(session, origem, cnc, ordem=1, tempo="2.5")
    _ligar(session, origem, tempo, ordem=2, tempo="4")
    for destino in (proprio_1, proprio_2, outro, global_, chave_errada, ref_errada):
        _ligar(session, destino, antiga, tempo="9")
    session.commit()
    return {
        "paulo": paulo,
        "ana": ana,
        "admin": admin,
        "origem": origem,
        "proprio_1": proprio_1,
        "proprio_2": proprio_2,
        "outro": outro,
        "global": global_,
        "chave_errada": chave_errada,
        "ref_errada": ref_errada,
    }


def test_contexto_isola_mesma_chave_e_ref_le_e_mostra_estado(session, catalogo) -> None:
    contexto = DefValuesetOperacaoPropagacaoService(session).preparar_contexto(
        catalogo["origem"].id, catalogo["paulo"]
    )

    ids = {destino.linha_id for destino in contexto.destinos}
    assert ids == {
        catalogo["proprio_1"].id,
        catalogo["proprio_2"].id,
        catalogo["outro"].id,
        catalogo["global"].id,
    }
    assert catalogo["chave_errada"].id not in ids
    assert catalogo["ref_errada"].id not in ids
    global_ = next(d for d in contexto.destinos if d.linha_id == catalogo["global"].id)
    assert global_.ambito == "Global"
    assert global_.modelo_ativo is False
    proprio_inativo = next(
        d for d in contexto.destinos if d.linha_id == catalogo["proprio_2"].id
    )
    assert proprio_inativo.linha_ativa is False
    assert proprio_inativo.substituidas == 1
    assert proprio_inativo.adicionadas == 1


def test_utilizador_normal_so_pode_selecionar_modelos_proprios(session, catalogo) -> None:
    contexto = DefValuesetOperacaoPropagacaoService(session).preparar_contexto(
        catalogo["origem"].id, catalogo["paulo"]
    )
    permitidos = {d.linha_id for d in contexto.destinos if d.permitido}
    assert permitidos == {catalogo["proprio_1"].id, catalogo["proprio_2"].id}

    service = DefValuesetOperacaoPropagacaoService(session)
    with pytest.raises(PermissionError, match="permissão administrativa"):
        service.executar(contexto, [catalogo["outro"].id], catalogo["paulo"])


def test_admin_pode_alterar_outros_e_globais(session, catalogo) -> None:
    service = DefValuesetOperacaoPropagacaoService(session)
    contexto = service.preparar_contexto(catalogo["origem"].id, catalogo["admin"])
    assert all(destino.permitido for destino in contexto.destinos)

    resultado = service.executar(
        contexto,
        [catalogo["outro"].id, catalogo["global"].id],
        catalogo["admin"],
    )
    assert resultado.destinos_atualizados == 2
    assert len(_operacoes(session, catalogo["outro"].id)) == 2
    assert len(_operacoes(session, catalogo["global"].id)) == 2


def test_permissao_especifica_liberta_outros_e_globais(session, catalogo) -> None:
    set_user_permissions(
        session,
        catalogo["paulo"].id,
        {PERMISSAO_PROPAGAR_OPERACOES_VALUESET_OUTROS: True},
    )
    session.flush()

    contexto = DefValuesetOperacaoPropagacaoService(session).preparar_contexto(
        catalogo["origem"].id, catalogo["paulo"]
    )
    assert all(destino.permitido for destino in contexto.destinos)


def test_so_altera_destinos_explicitamente_selecionados(session, catalogo) -> None:
    service = DefValuesetOperacaoPropagacaoService(session)
    contexto = service.preparar_contexto(catalogo["origem"].id, catalogo["paulo"])
    outro_antes = [op.def_operacao_id for op in _operacoes(session, catalogo["outro"].id)]

    service.executar(contexto, [catalogo["proprio_1"].id], catalogo["paulo"])

    assert len(_operacoes(session, catalogo["proprio_1"].id)) == 2
    assert [op.def_operacao_id for op in _operacoes(session, catalogo["outro"].id)] == outro_antes
    assert len(_operacoes(session, catalogo["proprio_2"].id)) == 1


def test_preparar_e_cancelar_nao_altera_dados(session, catalogo) -> None:
    antes = [op.id for op in _operacoes(session, catalogo["proprio_1"].id)]
    DefValuesetOperacaoPropagacaoService(session).preparar_contexto(
        catalogo["origem"].id, catalogo["paulo"]
    )
    assert [op.id for op in _operacoes(session, catalogo["proprio_1"].id)] == antes


def test_rollback_na_segunda_linha_nao_deixa_primeira_parcial(
    session, catalogo, monkeypatch
) -> None:
    service = DefValuesetOperacaoPropagacaoService(session)
    contexto = service.preparar_contexto(catalogo["origem"].id, catalogo["paulo"])
    primeira_antes = [
        (op.id, op.def_operacao_id, op.ativo)
        for op in _operacoes(session, catalogo["proprio_1"].id)
    ]
    original = service.operacao_service.substituir_operacoes_de
    chamadas = 0

    def falhar_na_segunda(*args, **kwargs):
        nonlocal chamadas
        chamadas += 1
        if chamadas == 2:
            raise RuntimeError("falha simulada")
        return original(*args, **kwargs)

    monkeypatch.setattr(
        service.operacao_service, "substituir_operacoes_de", falhar_na_segunda
    )
    with pytest.raises(RuntimeError, match="falha simulada"):
        service.executar(
            contexto,
            [catalogo["proprio_1"].id, catalogo["proprio_2"].id],
            catalogo["paulo"],
        )

    session.expire_all()
    assert [
        (op.id, op.def_operacao_id, op.ativo)
        for op in _operacoes(session, catalogo["proprio_1"].id)
    ] == primeira_antes


def test_repetir_propagacao_e_idempotente(session, catalogo) -> None:
    service = DefValuesetOperacaoPropagacaoService(session)
    contexto = service.preparar_contexto(catalogo["origem"].id, catalogo["paulo"])
    service.executar(contexto, [catalogo["proprio_1"].id], catalogo["paulo"])
    ids_primeira = [op.id for op in _operacoes(session, catalogo["proprio_1"].id)]

    contexto_2 = service.preparar_contexto(catalogo["origem"].id, catalogo["paulo"])
    destino_2 = next(
        d for d in contexto_2.destinos if d.linha_id == catalogo["proprio_1"].id
    )
    assert destino_2.substituidas == 0
    assert destino_2.adicionadas == 0
    assert destino_2.desativadas == 0
    service.executar(contexto_2, [catalogo["proprio_1"].id], catalogo["paulo"])

    assert [op.id for op in _operacoes(session, catalogo["proprio_1"].id)] == ids_primeira


def test_mudanca_depois_da_previsualizacao_aborta_sem_escrever(session, catalogo) -> None:
    service = DefValuesetOperacaoPropagacaoService(session)
    contexto = service.preparar_contexto(catalogo["origem"].id, catalogo["paulo"])
    operacao = _operacoes(session, catalogo["proprio_1"].id)[0]
    operacao.tempo_por_unidade_minutos = Decimal("77")
    session.commit()

    with pytest.raises(ValueError, match="destino mudaram"):
        service.executar(contexto, [catalogo["proprio_1"].id], catalogo["paulo"])
