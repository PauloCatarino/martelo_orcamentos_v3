"""Os componentes de uma matéria-prima composta, com dados da obra 1367.

O Martelo orça a ``FER0015`` como uma dobradiça completa; o iMos exporta o copo
e o calço em linhas separadas. Estes testes provam as três regras que tornam a
contagem de uma obra possível:

1. um filho SECUNDÁRIO pode servir muitos conjuntos (o calço H0 entra em várias
   dobradiças);
2. um conjunto pode ter vários PRINCIPAIS — apelidos, como os dois pés AXILO;
3. mas a mesma referência nunca é principal em dois conjuntos, senão ao ler uma
   obra ninguém saberia qual deles contar.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.materia_prima_types import (
    PAPEL_PRINCIPAL,
    PAPEL_SECUNDARIO,
    normalizar_ref_fornecedor,
)
from app.repositories.def_materia_prima_componente_repository import ComponenteDados
from app.services.def_materia_prima_componente_service import (
    DefMateriaPrimaComponenteService,
    ReferenciaJaUsadaError,
)
from app.services.def_materia_prima_service import (
    CriarDefMateriaPrimaData,
    DefMateriaPrimaService,
)


@pytest.fixture()
def catalogo(session) -> DefMateriaPrimaService:
    return DefMateriaPrimaService(session)


@pytest.fixture()
def componentes(session) -> DefMateriaPrimaComponenteService:
    return DefMateriaPrimaComponenteService(session)


def _conjunto(catalogo: DefMateriaPrimaService, descricao: str):
    return catalogo.criar_materia_prima(
        CriarDefMateriaPrimaData(
            descricao=descricao,
            familia_original_excel="FERRAGENS",
            tipo_original_excel="DOBRADICAS",
            unidade="UND",
            preco_tabela=Decimal("2.53"),
        )
    )


def _copo_soft_close(**overrides) -> ComponenteDados:
    campos = {
        "papel": PAPEL_PRINCIPAL,
        "descricao": "Dobradiça de copo recta BLUMOTION",
        "quantidade": Decimal("1"),
        "nome_imos": "BL_DOB_RETA_75B1550_pontear",
        "ref_phc": "FF00060",
        "ref_fornecedor": "75B1550    BLUM",
    }
    campos.update(overrides)
    return ComponenteDados(**campos)


def _calco_h0(**overrides) -> ComponenteDados:
    campos = {
        "papel": PAPEL_SECUNDARIO,
        "descricao": "Calço Euro H0",
        "quantidade": Decimal("1"),
        "nome_imos": "BL_CALCO_H0_174H7100E",
        "ref_phc": "FF00003",
        "ref_fornecedor": "174H7100E    BLUM",
    }
    campos.update(overrides)
    return ComponenteDados(**campos)


# --- O caso normal ----------------------------------------------------------


def test_um_conjunto_com_principal_e_secundario(catalogo, componentes) -> None:
    fer0015 = _conjunto(catalogo, "DOBRADIÇA BLUM RETA 107º (SOFT CLOSE) + CALÇO H0")

    componentes.criar(fer0015.id, _copo_soft_close())
    componentes.criar(fer0015.id, _calco_h0())

    linhas = componentes.listar(fer0015.id)
    assert [c.papel for c in linhas] == [PAPEL_PRINCIPAL, PAPEL_SECUNDARIO]
    assert [c.ordem for c in linhas] == [1, 2]
    assert componentes.contar_principais(fer0015.id) == 1


def test_a_referencia_do_fornecedor_e_guardada_limpa_e_como_veio(catalogo, componentes) -> None:
    # O iMos escreve "75B1550    BLUM": marca colada e espaços a mais. A
    # normalizada é a que serve para procurar; a original fica para mostrar.
    fer0015 = _conjunto(catalogo, "DOBRADIÇA SOFT CLOSE")

    criado = componentes.criar(fer0015.id, _copo_soft_close())

    assert criado.ref_fornecedor == "75B1550    BLUM"
    assert criado.ref_fornecedor_norm == "75B1550"


# --- Regra 1: um secundário serve muitos conjuntos --------------------------


def test_o_mesmo_calco_pode_estar_em_duas_dobradicas(catalogo, componentes) -> None:
    fer0015 = _conjunto(catalogo, "DOBRADIÇA BLUM RETA 107º (SOFT CLOSE) + CALÇO H0")
    fer0016 = _conjunto(catalogo, "DOBRADIÇA BLUM RETA 107º (MOLA) + CALÇO H0")

    componentes.criar(fer0015.id, _calco_h0())
    componentes.criar(fer0016.id, _calco_h0())

    assert len(componentes.listar(fer0015.id)) == 1
    assert len(componentes.listar(fer0016.id)) == 1


# --- Regra 2: apelidos (vários principais no mesmo conjunto) ----------------


def test_dois_pes_axilo_podem_ser_principais_do_mesmo_conjunto(catalogo, componentes) -> None:
    # O iMos tem dois pés AXILO (H55→H70 e H72→H92) e uma base comum.
    fer0058 = _conjunto(catalogo, "PE NIVELADOR AXILO + BASE")

    componentes.criar(
        fer0058.id,
        ComponenteDados(
            papel=PAPEL_PRINCIPAL,
            descricao="Pé AXILO regulável H55→H70",
            nome_imos="PE_AXILO_H55_70_63776351",
            ref_phc="FF01176",
            ref_fornecedor="637.76.351   HAFELE",
        ),
    )
    componentes.criar(
        fer0058.id,
        ComponenteDados(
            papel=PAPEL_PRINCIPAL,
            descricao="Pé AXILO regulável H72→H92",
            nome_imos="PE_AXILO_H72_92_63776352",
            ref_phc="FF01295",
            ref_fornecedor="108000194   HAFELE",
        ),
    )
    componentes.criar(
        fer0058.id,
        ComponenteDados(
            papel=PAPEL_SECUNDARIO,
            descricao="Base AXILO c/ 4 parafusos",
            nome_imos="PE_BASE_AXILO_63776333_4f",
            ref_phc="FF01177",
        ),
    )

    assert componentes.contar_principais(fer0058.id) == 2
    assert len(componentes.listar(fer0058.id)) == 3


# --- Regra 3: um principal só serve um conjunto -----------------------------


def test_a_mesma_referencia_nao_pode_ser_principal_em_dois_conjuntos(catalogo, componentes) -> None:
    fer0015 = _conjunto(catalogo, "DOBRADIÇA BLUM RETA 107º (SOFT CLOSE) + CALÇO H0")
    fer0016 = _conjunto(catalogo, "DOBRADIÇA BLUM RETA 107º (MOLA) + CALÇO H0")
    componentes.criar(fer0015.id, _copo_soft_close())

    with pytest.raises(ReferenciaJaUsadaError) as erro:
        componentes.criar(fer0016.id, _copo_soft_close())

    # A mensagem tem de dizer ONDE está a primeira ligação.
    assert fer0015.ref_le in str(erro.value)


def test_a_colisao_e_apanhada_por_qualquer_das_tres_chaves(catalogo, componentes) -> None:
    fer0015 = _conjunto(catalogo, "DOBRADIÇA SOFT CLOSE")
    outro = _conjunto(catalogo, "OUTRA DOBRADIÇA")
    componentes.criar(fer0015.id, _copo_soft_close())

    # Só a Ref PHC repetida.
    with pytest.raises(ReferenciaJaUsadaError):
        componentes.criar(
            outro.id,
            _copo_soft_close(nome_imos="OUTRO_NOME", ref_fornecedor="OUTRA REF"),
        )

    # Só a referência do fornecedor repetida — e escrita de outra maneira, com
    # a marca noutro sítio. A normalização tem de a apanhar na mesma.
    with pytest.raises(ReferenciaJaUsadaError):
        componentes.criar(
            outro.id,
            _copo_soft_close(nome_imos="OUTRO", ref_phc="FF99999", ref_fornecedor="BLUM 75B1550"),
        )


def test_um_secundario_repetido_nunca_e_recusado(catalogo, componentes) -> None:
    # É o principal que manda na contagem; o secundário é livre.
    fer0015 = _conjunto(catalogo, "DOBRADIÇA SOFT CLOSE")
    fer0016 = _conjunto(catalogo, "DOBRADIÇA MOLA")
    componentes.criar(fer0015.id, _copo_soft_close())

    componentes.criar(fer0016.id, _copo_soft_close(papel=PAPEL_SECUNDARIO))

    assert componentes.contar_principais(fer0016.id) == 0


def test_alterar_o_proprio_componente_nao_colide_consigo_mesmo(catalogo, componentes) -> None:
    fer0015 = _conjunto(catalogo, "DOBRADIÇA SOFT CLOSE")
    criado = componentes.criar(fer0015.id, _copo_soft_close())

    alterado = componentes.atualizar(
        criado.id, _copo_soft_close(descricao="Dobradiça de copo (descrição nova)")
    )

    assert alterado.descricao == "Dobradiça de copo (descrição nova)"


# --- Validações do dia-a-dia ------------------------------------------------


def test_componente_sem_referencia_nenhuma_e_recusado(catalogo, componentes) -> None:
    fer0015 = _conjunto(catalogo, "DOBRADIÇA SOFT CLOSE")

    with pytest.raises(ValueError) as erro:
        componentes.criar(
            fer0015.id, ComponenteDados(descricao="Uma peça qualquer sem referência")
        )

    assert "referência" in str(erro.value)


def test_quantidade_zero_ou_negativa_e_recusada(catalogo, componentes) -> None:
    fer0015 = _conjunto(catalogo, "DOBRADIÇA SOFT CLOSE")

    for quantidade in (Decimal("0"), Decimal("-1")):
        with pytest.raises(ValueError) as erro:
            componentes.criar(fer0015.id, _calco_h0(quantidade=quantidade))
        assert "maior do que zero" in str(erro.value)


def test_papel_desconhecido_e_recusado(catalogo, componentes) -> None:
    fer0015 = _conjunto(catalogo, "DOBRADIÇA SOFT CLOSE")

    with pytest.raises(ValueError) as erro:
        componentes.criar(fer0015.id, _calco_h0(papel="CHEFE"))

    assert "CHEFE" in str(erro.value)


def test_papel_em_minusculas_e_aceito(catalogo, componentes) -> None:
    fer0015 = _conjunto(catalogo, "DOBRADIÇA SOFT CLOSE")

    criado = componentes.criar(fer0015.id, _copo_soft_close(papel="principal"))

    assert criado.papel == PAPEL_PRINCIPAL


# --- Gravar a ficha toda de uma vez -----------------------------------------


def test_guardar_lista_substitui_e_renumera(catalogo, componentes) -> None:
    fer0015 = _conjunto(catalogo, "DOBRADIÇA SOFT CLOSE")
    componentes.criar(fer0015.id, _calco_h0())

    guardadas = componentes.guardar_lista(
        fer0015.id, [_copo_soft_close(), _calco_h0()]
    )

    assert [c.ordem for c in guardadas] == [1, 2]
    assert [c.papel for c in guardadas] == [PAPEL_PRINCIPAL, PAPEL_SECUNDARIO]
    assert len(componentes.listar(fer0015.id)) == 2


def test_guardar_lista_nao_deixa_a_ficha_meio_gravada(catalogo, componentes) -> None:
    # A segunda linha está errada: a ficha tem de ficar exactamente como estava.
    fer0015 = _conjunto(catalogo, "DOBRADIÇA SOFT CLOSE")
    componentes.criar(fer0015.id, _calco_h0())

    with pytest.raises(ValueError):
        componentes.guardar_lista(
            fer0015.id,
            [_copo_soft_close(), ComponenteDados(descricao="sem referência nenhuma")],
        )

    intactas = componentes.listar(fer0015.id)
    assert len(intactas) == 1
    assert intactas[0].nome_imos == "BL_CALCO_H0_174H7100E"


def test_guardar_lista_recusa_dois_principais_com_a_mesma_chave(catalogo, componentes) -> None:
    fer0015 = _conjunto(catalogo, "DOBRADIÇA SOFT CLOSE")

    with pytest.raises(ReferenciaJaUsadaError) as erro:
        componentes.guardar_lista(
            fer0015.id, [_copo_soft_close(), _copo_soft_close(descricao="repetida")]
        )

    assert "linhas 1 e 2" in str(erro.value)


def test_guardar_lista_regrava_os_apelidos_do_mesmo_conjunto(catalogo, componentes) -> None:
    # Regravar a ficha dos pés AXILO não pode acusar colisão com as linhas
    # antigas dela própria, que ainda estão na base no momento da validação.
    fer0058 = _conjunto(catalogo, "PE NIVELADOR AXILO + BASE")
    pe_baixo = ComponenteDados(
        papel=PAPEL_PRINCIPAL, descricao="Pé H55→H70", nome_imos="PE_AXILO_H55_70_63776351"
    )
    pe_alto = ComponenteDados(
        papel=PAPEL_PRINCIPAL, descricao="Pé H72→H92", nome_imos="PE_AXILO_H72_92_63776352"
    )
    componentes.guardar_lista(fer0058.id, [pe_baixo, pe_alto])

    guardadas = componentes.guardar_lista(fer0058.id, [pe_baixo, pe_alto])

    assert componentes.contar_principais(fer0058.id) == 2
    assert len(guardadas) == 2


def test_eliminar_um_componente(catalogo, componentes) -> None:
    fer0015 = _conjunto(catalogo, "DOBRADIÇA SOFT CLOSE")
    criado = componentes.criar(fer0015.id, _calco_h0())

    assert componentes.eliminar(criado.id) is True
    assert componentes.listar(fer0015.id) == []
    assert componentes.eliminar(criado.id) is False


# --- O nome do iMos na própria matéria-prima (casos 1 para 1) ---------------


def test_nome_imos_na_materia_prima_para_os_casos_simples(catalogo) -> None:
    # Placas, orlas e ferragens simples não são compostas: basta o nome do
    # artigo ao lado da Ref PHC, sem tabela de componentes nenhuma.
    placa = catalogo.criar_materia_prima(
        CriarDefMateriaPrimaData(
            descricao="AGL MLM LINHO CANCUN 19MM",
            familia_original_excel="PLACAS",
            unidade="M2",
            nome_imos="AGL_MLM_LINHO_CANCUN_19MM",
            ref_phc="PL00123",
        )
    )

    assert placa.nome_imos == "AGL_MLM_LINHO_CANCUN_19MM"
    assert catalogo.obter_por_id(placa.id).nome_imos == "AGL_MLM_LINHO_CANCUN_19MM"


# --- A normalização, sozinha ------------------------------------------------


def test_normalizar_ref_fornecedor_tira_a_marca_e_os_espacos() -> None:
    assert normalizar_ref_fornecedor("174H7100E    BLUM") == "174H7100E"
    assert normalizar_ref_fornecedor("637.76.351   HAFELE") == "637.76.351"
    assert normalizar_ref_fornecedor("31204.05     EMUCA") == "31204.05"
    assert normalizar_ref_fornecedor("F233") == "F233"
    # Uma referência que é só a marca não serve de chave nenhuma.
    assert normalizar_ref_fornecedor("BLUM") is None
    assert normalizar_ref_fornecedor("   ") is None
    assert normalizar_ref_fornecedor(None) is None
