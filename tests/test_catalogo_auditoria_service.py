"""Tests for the read-only technical catalog audit."""

from decimal import Decimal
from types import SimpleNamespace

from app.services.catalogo_auditoria_service import (
    CatalogoAuditoriaDados,
    CatalogoAuditoriaService,
)


def _obj(**kwargs):
    return SimpleNamespace(**kwargs)


def _peca(id, codigo, **kwargs):
    values = {
        "id": id,
        "codigo": codigo,
        "nome": codigo,
        "ativo": True,
        "tipo_peca": "SIMPLES",
        "natureza": "MATERIAL",
        "sem_material": False,
        "chave_valueset_material": "MATERIAL",
        "orla_c1": 0,
        "orla_c2": 0,
        "orla_l1": 0,
        "orla_l2": 0,
    }
    values.update(kwargs)
    return _obj(**values)


def _dados(**kwargs):
    values = {
        "pecas": tuple(),
        "componentes": tuple(),
        "ligacoes_operacoes": tuple(),
        "operacoes": tuple(),
        "maquinas": tuple(),
        "regras": tuple(),
        "chaves_valueset": tuple(),
        "modelos_valueset": tuple(),
        "linhas_valueset": tuple(),
        "operacoes_valueset": tuple(),
        "modulos": tuple(),
        "linhas_modulo": tuple(),
    }
    values.update(kwargs)
    return CatalogoAuditoriaDados(**values)


def _codigos(resultado):
    return {item.codigo_teste for item in resultado.itens}


def test_audita_nomes_cnc_orlas_operacoes_e_maquinas() -> None:
    pecas = (
        _peca(1, "COSTA_COM_CNC_0000"),
        _peca(2, "COSTA_SEM_CNC_0000"),
        _peca(3, "TRAVESSA", orla_c1=2),
    )
    operacoes = (
        _obj(
            id=10,
            codigo="CNC_VERTICAL",
            nome="CNC vertical",
            tipo_operacao="CNC",
            maquina_id=20,
            ativo=True,
        ),
        _obj(
            id=11,
            codigo="CNC_ANTIGO",
            nome="CNC antigo",
            tipo_operacao="CNC",
            maquina_id=None,
            ativo=False,
        ),
    )
    ligacoes = (
        _obj(id=1, def_peca_id=2, def_operacao_id=10, ativo=True),
        _obj(id=2, def_peca_id=3, def_operacao_id=11, ativo=True),
    )
    resultado = CatalogoAuditoriaService.auditar_dados(
        _dados(
            pecas=pecas,
            operacoes=operacoes,
            ligacoes_operacoes=ligacoes,
            maquinas=(_obj(id=20, codigo="CNC", ativo=False),),
            chaves_valueset=(_obj(id=1, codigo="MATERIAL", ativo=True),),
        )
    )

    assert {
        "PECA_COM_CNC_SEM_CNC",
        "PECA_SEM_CNC_COM_CNC",
        "ORLA_SEM_OPERACAO",
        "OPERACAO_INATIVA_ASSOCIADA",
        "MAQUINA_INATIVA_OPERACAO",
    } <= _codigos(resultado)
    inativa = next(
        item
        for item in resultado.itens
        if item.codigo_teste == "OPERACAO_INATIVA_ASSOCIADA"
    )
    assert inativa.navegacao_tipo == "PECA"
    assert inativa.correcao_codigo == "DESATIVAR_LIGACAO_OPERACAO_INATIVA"


def test_audita_associados_regras_ciclos_e_cnc_potencialmente_duplicado() -> None:
    pai = _peca(1, "PAI")
    filho = _peca(2, "FILHO")
    cnc = _obj(
        id=10,
        codigo="CNC_VERTICAL",
        nome="CNC",
        tipo_operacao="CNC",
        maquina_id=None,
        ativo=True,
    )
    componentes = (
        _obj(
            id=1,
            def_peca_pai_id=1,
            def_peca_componente_id=2,
            referencia_componente="FILHO",
            def_regra_quantidade_id=30,
            ativo=True,
        ),
        _obj(
            id=2,
            def_peca_pai_id=2,
            def_peca_componente_id=1,
            referencia_componente="PAI",
            def_regra_quantidade_id=None,
            ativo=True,
        ),
        _obj(
            id=3,
            def_peca_pai_id=1,
            def_peca_componente_id=None,
            referencia_componente="INEXISTENTE",
            def_regra_quantidade_id=None,
            ativo=True,
        ),
    )
    resultado = CatalogoAuditoriaService.auditar_dados(
        _dados(
            pecas=(pai, filho),
            componentes=componentes,
            operacoes=(cnc,),
            ligacoes_operacoes=(
                _obj(id=1, def_peca_id=1, def_operacao_id=10, ativo=True),
                _obj(id=2, def_peca_id=2, def_operacao_id=10, ativo=True),
            ),
            regras=(
                _obj(id=30, codigo="INATIVA", ativo=False),
                _obj(id=31, codigo="SEM_USO", ativo=True),
            ),
            chaves_valueset=(_obj(id=1, codigo="MATERIAL", ativo=True),),
        )
    )

    assert {
        "ASSOCIADO_SEM_BIBLIOTECA",
        "REGRA_INATIVA_ASSOCIADA",
        "REGRA_NAO_UTILIZADA",
        "ASSOCIACAO_CIRCULAR",
        "CNC_PECA_E_ASSOCIADO",
    } <= _codigos(resultado)
    regra_sem_uso = next(
        item
        for item in resultado.itens
        if item.codigo_teste == "REGRA_NAO_UTILIZADA"
    )
    assert regra_sem_uso.correcao_codigo == "DESATIVAR_REGRA_NAO_UTILIZADA"


def test_audita_substituicao_valueset_e_referencia_modulo_desatualizada() -> None:
    peca = _peca(1, "FUNDO_NOVO")
    op = _obj(
        id=10,
        codigo="CNC_VERTICAL",
        nome="CNC",
        tipo_operacao="CNC",
        maquina_id=None,
        ativo=True,
    )
    resultado = CatalogoAuditoriaService.auditar_dados(
        _dados(
            pecas=(peca,),
            operacoes=(op,),
            chaves_valueset=(_obj(id=1, codigo="MATERIAL", ativo=True),),
            modelos_valueset=(_obj(id=20, codigo="STANDARD", ativo=True),),
            linhas_valueset=(
                _obj(
                    id=21,
                    def_valueset_modelo_id=20,
                    codigo_opcao="SUPORTE",
                    ativo=True,
                ),
            ),
            operacoes_valueset=(
                _obj(
                    id=22,
                    def_valueset_modelo_linha_id=21,
                    def_operacao_id=10,
                    acao="SUBSTITUIR",
                    ativo=True,
                ),
            ),
            modulos=(_obj(id=30, codigo="MODULO_A", ativo=True),),
            linhas_modulo=(
                _obj(
                    id=31,
                    def_modulo_id=30,
                    def_peca_id=1,
                    def_peca_codigo="FUNDO_ANTIGO",
                    def_regra_quantidade_id=None,
                    ativo=True,
                ),
            ),
        )
    )

    assert "VALUESET_SUBSTITUICAO" in _codigos(resultado)
    assert "MODULO_CODIGO_DESATUALIZADO" in _codigos(resultado)
    modulo = next(
        item
        for item in resultado.itens
        if item.codigo_teste == "MODULO_CODIGO_DESATUALIZADO"
    )
    assert modulo.navegacao_tipo == "MODULO"
    assert modulo.correcao_codigo == "ATUALIZAR_CODIGO_PECA_MODULO"


def test_conjunto_virtual_nao_exige_chave_valueset() -> None:
    conjunto = _peca(
        1,
        "CONJUNTO",
        natureza="CONJUNTO",
        tipo_peca="COMPOSTA",
        chave_valueset_material=None,
    )
    resultado = CatalogoAuditoriaService.auditar_dados(
        _dados(pecas=(conjunto,))
    )

    assert "PECA_SEM_VALUESET" not in _codigos(resultado)


def test_audita_protecoes_do_piloto_de_unioes() -> None:
    modelo = _obj(id=20, codigo="STANDARD", ativo=True)
    linhas = (
        _obj(
            id=21, def_valueset_modelo_id=20, chave="FERRAGEM_UNIOES",
            codigo_opcao="CAVILHA", prioridade=1, ativo=True,
        ),
        _obj(
            id=22, def_valueset_modelo_id=20, chave="FERRAGEM_UNIOES",
            codigo_opcao="PARAFUSO", prioridade=1, ativo=True,
        ),
        _obj(
            id=23, def_valueset_modelo_id=20, chave="SISTEMA_UNIAO",
            codigo_opcao="SEM_PRIORIDADE", prioridade=None, ativo=True,
        ),
    )
    cnc = _obj(
        id=10, codigo="CNC_VERTICAL", nome="CNC vertical",
        tipo_operacao="CNC", maquina_id=None, ativo=True,
    )
    resultado = CatalogoAuditoriaService.auditar_dados(
        _dados(
            operacoes=(cnc,),
            modelos_valueset=(modelo,),
            linhas_valueset=linhas,
            operacoes_valueset=(
                _obj(
                    id=30, def_valueset_modelo_linha_id=21,
                    def_operacao_id=10, acao="ADICIONAR", ativo=True,
                    tempo_por_unidade_minutos=Decimal("0.01"),
                ),
                _obj(
                    id=31, def_valueset_modelo_linha_id=22,
                    def_operacao_id=10, acao="ADICIONAR", ativo=True,
                    tempo_por_unidade_minutos=Decimal("0"),
                ),
            ),
        )
    )

    assert {
        "UNIAO_VALUESET_PRIORIDADE_DUPLICADA",
        "UNIAO_VALUESET_SEM_PRIORIDADE",
        "UNIAO_CNC_SEM_TEMPO_UNITARIO",
        "UNIAO_SEM_CNC",
    } <= _codigos(resultado)
