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
        "CNC_DUPLICADO_PECA_ASSOCIADO",
    } <= _codigos(resultado)
    regra_sem_uso = next(
        item
        for item in resultado.itens
        if item.codigo_teste == "REGRA_NAO_UTILIZADA"
    )
    assert regra_sem_uso.correcao_codigo == "DESATIVAR_REGRA_NAO_UTILIZADA"


def test_audita_cnc_diferentes_na_peca_e_associado_como_aviso() -> None:
    pai = _peca(1, "DIVISORIA_2000")
    filho = _peca(2, "SISTEMAS_UNIAO")
    cnc_vertical = _obj(
        id=10, codigo="CNC_VERTICAL", nome="CNC vertical",
        tipo_operacao="CNC", maquina_id=None, ativo=True,
    )
    cnc_abd = _obj(
        id=11, codigo="CNC_ABD", nome="CNC ABD",
        tipo_operacao="CNC", maquina_id=None, ativo=True,
    )
    resultado = CatalogoAuditoriaService.auditar_dados(
        _dados(
            pecas=(pai, filho),
            componentes=(
                _obj(
                    id=1, def_peca_pai_id=1, def_peca_componente_id=2,
                    referencia_componente="SISTEMAS_UNIAO",
                    def_regra_quantidade_id=None, ativo=True,
                ),
            ),
            operacoes=(cnc_vertical, cnc_abd),
            ligacoes_operacoes=(
                _obj(id=1, def_peca_id=1, def_operacao_id=10, ativo=True),
                _obj(id=2, def_peca_id=2, def_operacao_id=11, ativo=True),
            ),
            chaves_valueset=(_obj(id=1, codigo="MATERIAL", ativo=True),),
        )
    )

    assert "CNC_PECA_E_ASSOCIADO" in _codigos(resultado)
    assert "CNC_DUPLICADO_PECA_ASSOCIADO" not in _codigos(resultado)


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


# --- Peça 2: as chaves ValueSet dos modelos e dos módulos --------------------
#
# O código da chave é texto solto em sete tabelas, sem chave estrangeira
# nenhuma. Renomear uma chave no vocabulário não avisa ninguém, e quem ficou
# com a antiga cala-se: no custeio a lista de materiais vem vazia, sem erro.
# É esse silêncio que estes testes vão apanhar.


def _chave_vs(codigo, *, ativo=True, grupo="FERRAGENS", ordem=1):
    return _obj(
        id=abs(hash(codigo)) % 10000,
        codigo=codigo,
        nome=codigo.replace("_", " ").title(),
        grupo=grupo,
        ordem=ordem,
        ativo=ativo,
    )


def _modelo_vs(id, codigo, *, tipo="ROUPEIRO", ativo=True):
    return _obj(id=id, codigo=codigo, nome=codigo, tipo=tipo, ativo=ativo)


def _linha_vs(id, modelo_id, chave, *, ativo=True):
    return _obj(
        id=id,
        def_valueset_modelo_id=modelo_id,
        chave=chave,
        codigo_opcao=f"OPC_{id}",
        prioridade=1,
        ativo=ativo,
    )


def _item(resultado, codigo_teste):
    return next(i for i in resultado.itens if i.codigo_teste == codigo_teste)


def test_chave_de_modelo_fora_do_vocabulario_e_erro() -> None:
    dados = _dados(
        chaves_valueset=(_chave_vs("FERRAGEM_SUPORTE_LATERAL_VARAO"),),
        modelos_valueset=(_modelo_vs(1, "ROUP_STD"),),
        linhas_valueset=(
            _linha_vs(10, 1, "FERRAGEM_SUPORTE_LATERAL_VARAO"),
            _linha_vs(11, 1, "FERRAGEM_SUPORTE_VARAO"),  # a chave antiga
        ),
    )

    resultado = CatalogoAuditoriaService.auditar_dados(dados)

    item = _item(resultado, "VALUESET_MODELO_CHAVE_INEXISTENTE")
    assert item.severidade == "ERRO"
    assert item.entidade_codigo == "ROUP_STD"
    assert "FERRAGEM_SUPORTE_VARAO" in item.problema
    assert item.navegacao_tipo == "VALUESET_MODELO"
    assert item.navegacao_id == 1


def test_varias_linhas_da_mesma_chave_orfa_dao_um_so_item() -> None:
    dados = _dados(
        chaves_valueset=tuple(),
        modelos_valueset=(_modelo_vs(1, "ROUP_STD"),),
        linhas_valueset=tuple(
            _linha_vs(id, 1, "FERRAGEM_SUPORTE_VARAO") for id in range(10, 16)
        ),
    )

    resultado = CatalogoAuditoriaService.auditar_dados(dados)

    itens = [
        i for i in resultado.itens
        if i.codigo_teste == "VALUESET_MODELO_CHAVE_INEXISTENTE"
    ]
    assert len(itens) == 1
    assert "6 linha(s)" in itens[0].problema


def test_chave_inativa_no_modelo_e_aviso_e_nao_erro() -> None:
    dados = _dados(
        chaves_valueset=(_chave_vs("FERRAGEM_VARAO", ativo=False),),
        modelos_valueset=(_modelo_vs(1, "ROUP_STD"),),
        linhas_valueset=(_linha_vs(10, 1, "FERRAGEM_VARAO"),),
    )

    resultado = CatalogoAuditoriaService.auditar_dados(dados)

    assert "VALUESET_MODELO_CHAVE_INEXISTENTE" not in _codigos(resultado)
    assert _item(resultado, "VALUESET_MODELO_CHAVE_INATIVA").severidade == "AVISO"


def test_linha_ou_modelo_inativos_nao_sao_auditados() -> None:
    dados = _dados(
        chaves_valueset=tuple(),
        modelos_valueset=(
            _modelo_vs(1, "ROUP_STD"),
            _modelo_vs(2, "ROUP_VELHO", ativo=False),
        ),
        linhas_valueset=(
            _linha_vs(10, 1, "CHAVE_QUE_NAO_EXISTE", ativo=False),
            _linha_vs(11, 2, "OUTRA_QUE_NAO_EXISTE"),
        ),
    )

    resultado = CatalogoAuditoriaService.auditar_dados(dados)

    assert "VALUESET_MODELO_CHAVE_INEXISTENTE" not in _codigos(resultado)


def test_chave_valueset_de_modulo_fora_do_vocabulario_e_erro() -> None:
    dados = _dados(
        chaves_valueset=(_chave_vs("FERRAGEM_VARAO"),),
        modulos=(_obj(id=1, codigo="MOD_ROUPEIRO", nome="Roupeiro", ativo=True),),
        linhas_modulo=(
            _obj(
                id=5,
                def_modulo_id=1,
                def_peca_id=None,
                def_peca_codigo=None,
                ordem=3,
                chave_valueset="FERRAGEM_SUPORTE_VARAO",
                def_regra_quantidade_id=None,
                ativo=True,
            ),
        ),
    )

    resultado = CatalogoAuditoriaService.auditar_dados(dados)

    item = _item(resultado, "MODULO_CHAVE_VALUESET_INEXISTENTE")
    assert item.severidade == "ERRO"
    assert "FERRAGEM_SUPORTE_VARAO" in item.problema
    assert item.navegacao_tipo == "MODULO"


def test_modulo_sem_chave_valueset_nao_gera_ruido() -> None:
    dados = _dados(
        chaves_valueset=(_chave_vs("FERRAGEM_VARAO"),),
        modulos=(_obj(id=1, codigo="MOD", nome="Mod", ativo=True),),
        linhas_modulo=(
            _obj(
                id=5, def_modulo_id=1, def_peca_id=None, def_peca_codigo=None,
                ordem=1, chave_valueset=None, def_regra_quantidade_id=None,
                ativo=True,
            ),
            _obj(
                id=6, def_modulo_id=1, def_peca_id=None, def_peca_codigo=None,
                ordem=2, chave_valueset="", def_regra_quantidade_id=None,
                ativo=True,
            ),
        ),
    )

    resultado = CatalogoAuditoriaService.auditar_dados(dados)

    assert "MODULO_CHAVE_VALUESET_INEXISTENTE" not in _codigos(resultado)


def test_chaves_em_falta_comparam_com_os_irmaos_do_mesmo_tipo() -> None:
    """Um item por modelo, e só com as chaves que TODOS os irmãos têm.

    Comparar com o vocabulário inteiro dava dezenas de avisos inúteis: um
    roupeiro não precisa das chaves de cozinha.
    """
    chaves = (
        _chave_vs("FERRAGEM_VARAO"),
        _chave_vs("FERRAGEM_PUXADOR"),
        _chave_vs("FERRAGEM_SO_DE_UM"),
        _chave_vs("FERRAGEM_DE_COZINHA"),
    )
    modelos = (
        _modelo_vs(1, "ROUP_A"),
        _modelo_vs(2, "ROUP_B"),
        _modelo_vs(3, "ROUP_POBRE"),
        _modelo_vs(4, "COZINHA", tipo="COZINHA"),
    )
    linhas = (
        _linha_vs(10, 1, "FERRAGEM_VARAO"),
        _linha_vs(11, 1, "FERRAGEM_PUXADOR"),
        _linha_vs(12, 1, "FERRAGEM_SO_DE_UM"),
        _linha_vs(13, 2, "FERRAGEM_VARAO"),
        _linha_vs(14, 2, "FERRAGEM_PUXADOR"),
        _linha_vs(15, 3, "FERRAGEM_VARAO"),
        _linha_vs(16, 4, "FERRAGEM_DE_COZINHA"),
    )

    resultado = CatalogoAuditoriaService.auditar_dados(
        _dados(chaves_valueset=chaves, modelos_valueset=modelos, linhas_valueset=linhas)
    )

    itens = [
        i for i in resultado.itens
        if i.codigo_teste == "VALUESET_MODELO_CHAVES_EM_FALTA"
    ]
    # Só o ROUP_POBRE: o A e o B têm ambos o PUXADOR, que lhe falta.
    assert [i.entidade_codigo for i in itens] == ["ROUP_POBRE"]
    assert "FERRAGEM_PUXADOR" in itens[0].problema
    # O SO_DE_UM está num só irmão, logo não conta como falta.
    assert "FERRAGEM_SO_DE_UM" not in itens[0].problema
    # A cozinha está sozinha no seu tipo: não há com que a comparar.
    assert "COZINHA" not in {i.entidade_codigo for i in itens}


def test_modelo_completo_nao_aparece_nas_chaves_em_falta() -> None:
    chaves = (_chave_vs("FERRAGEM_VARAO"),)
    modelos = (_modelo_vs(1, "ROUP_A"), _modelo_vs(2, "ROUP_B"))
    linhas = (_linha_vs(10, 1, "FERRAGEM_VARAO"), _linha_vs(11, 2, "FERRAGEM_VARAO"))

    resultado = CatalogoAuditoriaService.auditar_dados(
        _dados(chaves_valueset=chaves, modelos_valueset=modelos, linhas_valueset=linhas)
    )

    assert "VALUESET_MODELO_CHAVES_EM_FALTA" not in _codigos(resultado)
