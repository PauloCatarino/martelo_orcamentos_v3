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


@pytest.fixture()
def fer_conjunto(catalogo):
    """Um conjunto qualquer, para os testes do jogo de uniões."""
    return _conjunto(catalogo, "DOBRADICA RECTA BLUMOTION + CALCO H0")


@pytest.fixture()
def outra_fer(catalogo):
    return _conjunto(catalogo, "PE NIVELADOR AXILO + BASE")


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


# --- O Jogo de Unioes do iMos (4.a chave) -----------------------------------
#
# Descoberto na base do iMos a 06-09-2026: a IDBPURCH tem CONNECTORSETNAME e
# ja' agrupa a dobradica + calco + batente + parafusos num jogo -- exactamente
# o que o Martelo orca numa linha so'. E' a chave mais segura, porque o mesmo
# parafuso entra em varios jogos e por si so' nao identifica conjunto nenhum.


def test_o_jogo_de_unioes_e_gravado_e_lido(session, fer_conjunto) -> None:
    servico = DefMateriaPrimaComponenteService(session)

    servico.guardar_lista(
        fer_conjunto.id,
        [
            ComponenteDados(
                papel=PAPEL_PRINCIPAL,
                nome_jogo_imos="Dob_Recta_BL_75B1550_H0",
                descricao="Dobradiça recta BLUMOTION",
                nome_imos="BL_DOB_RETA_75B1550_pontear",
                ref_phc="FF00060",
            )
        ],
    )

    guardado = servico.listar(fer_conjunto.id)[0]
    assert guardado.nome_jogo_imos == "Dob_Recta_BL_75B1550_H0"


def test_uma_linha_so_com_o_jogo_chega(session, fer_conjunto) -> None:
    # Mapear pelo jogo dispensa repetir os componentes um a um.
    servico = DefMateriaPrimaComponenteService(session)

    servico.guardar_lista(
        fer_conjunto.id,
        [ComponenteDados(papel=PAPEL_PRINCIPAL, nome_jogo_imos="Pe_Axilo_H72_92_4pontear")],
    )

    assert servico.listar(fer_conjunto.id)[0].nome_jogo_imos == "Pe_Axilo_H72_92_4pontear"


def test_o_mesmo_jogo_em_duas_materias_primas_e_recusado(
    session, fer_conjunto, outra_fer
) -> None:
    # Se o mesmo jogo do iMos valesse duas Ref LE, ao ler uma obra ninguem
    # saberia qual delas contar.
    servico = DefMateriaPrimaComponenteService(session)
    jogo = ComponenteDados(
        papel=PAPEL_PRINCIPAL, nome_jogo_imos="Dob_Recta_BL_75B1550_H0"
    )
    servico.guardar_lista(fer_conjunto.id, [jogo])

    with pytest.raises(ReferenciaJaUsadaError) as erro:
        servico.guardar_lista(outra_fer.id, [jogo])

    assert fer_conjunto.ref_le in str(erro.value)


def test_varios_jogos_na_mesma_materia_prima_sao_apelidos(
    session, fer_conjunto
) -> None:
    # Os tres pes AXILO sao tres jogos diferentes que valem a mesma FER0058.
    servico = DefMateriaPrimaComponenteService(session)

    servico.guardar_lista(
        fer_conjunto.id,
        [
            ComponenteDados(
                papel=PAPEL_PRINCIPAL, nome_jogo_imos="Pe_Axilo_H55_70_4pontear"
            ),
            ComponenteDados(
                papel=PAPEL_PRINCIPAL, nome_jogo_imos="Pe_Axilo_H72_92_4pontear"
            ),
        ],
    )

    assert servico.contar_principais(fer_conjunto.id) == 2


def test_o_mesmo_jogo_duas_vezes_na_mesma_ficha_e_recusado(
    session, fer_conjunto
) -> None:
    servico = DefMateriaPrimaComponenteService(session)
    jogo = ComponenteDados(
        papel=PAPEL_PRINCIPAL, nome_jogo_imos="Pe_Axilo_H72_92_4pontear"
    )

    with pytest.raises(ReferenciaJaUsadaError) as erro:
        servico.guardar_lista(fer_conjunto.id, [jogo, jogo])

    assert "Pe_Axilo_H72_92_4pontear" in str(erro.value)


def test_um_secundario_pode_repetir_o_jogo_noutro_conjunto(
    session, fer_conjunto, outra_fer
) -> None:
    # So' o PRINCIPAL reclama a chave; o SECUNDARIO e' informativo.
    servico = DefMateriaPrimaComponenteService(session)
    servico.guardar_lista(
        fer_conjunto.id,
        [ComponenteDados(papel=PAPEL_PRINCIPAL, nome_jogo_imos="Engate_System_14mm")],
    )

    servico.guardar_lista(
        outra_fer.id,
        [
            ComponenteDados(
                papel=PAPEL_SECUNDARIO,
                nome_jogo_imos="Engate_System_14mm",
                nome_imos="ENGATE_14",
            )
        ],
    )

    assert servico.listar(outra_fer.id)[0].nome_jogo_imos == "Engate_System_14mm"


def test_a_mensagem_de_falta_de_chave_fala_no_jogo(session, fer_conjunto) -> None:
    servico = DefMateriaPrimaComponenteService(session)

    with pytest.raises(ValueError) as erro:
        servico.guardar_lista(
            fer_conjunto.id, [ComponenteDados(descricao="uma linha sem nada")]
        )

    assert "jogo de uniões" in str(erro.value)


def test_a_migracao_do_jogo_chama_os_grants() -> None:
    from pathlib import Path

    migracao = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260906_109_jogo_de_unioes_do_imos.py"
    )
    fonte = migracao.read_text(encoding="utf-8")

    assert "CALL martelo_aplicar_grants()" in fonte
    assert 'down_revision: str | Sequence[str] | None = "20260904_108"' in fonte
    assert "ix_def_mp_componentes_nome_jogo_imos" in fonte


# --- O mesmo componente em varios jogos (FER0086, 07-09-2026) --------------
#
# O suporte de prateleira Rafix tem QUATRO jogos de unioes que so' diferem na
# furacao (1F00, 3F32, 3F64, Mlf) e partilham o mesmo copo, FF00381. Ele
# escreveu as quatro linhas e o Martelo recusou, porque a regra ainda olhava
# para a Ref PHC de todas elas.


def _rafix(furacao: str) -> ComponenteDados:
    return ComponenteDados(
        papel=PAPEL_PRINCIPAL,
        nome_jogo_imos=f"Ligador_Rafix_RTA20_19mm_{furacao}",
        descricao="Suporte Engate Copo 20mm",
        # O copo e' o MESMO nos quatro jogos.
        nome_imos="Cas_Rafix_20_R_26315705_19mm",
        ref_phc="FF00381",
        ref_fornecedor="8175121",
    )


def test_quatro_jogos_com_o_mesmo_componente_gravam(session, fer_conjunto) -> None:
    servico = DefMateriaPrimaComponenteService(session)

    servico.guardar_lista(
        fer_conjunto.id,
        [_rafix("1F00"), _rafix("3F32"), _rafix("3F64"), _rafix("Mlf")],
    )

    guardados = servico.listar(fer_conjunto.id)
    assert [c.nome_jogo_imos for c in guardados] == [
        "Ligador_Rafix_RTA20_19mm_1F00",
        "Ligador_Rafix_RTA20_19mm_3F32",
        "Ligador_Rafix_RTA20_19mm_3F64",
        "Ligador_Rafix_RTA20_19mm_Mlf",
    ]
    assert servico.contar_principais(fer_conjunto.id) == 4


def test_o_mesmo_jogo_repetido_continua_a_ser_recusado(
    session, fer_conjunto
) -> None:
    # A regra que interessa nao se perdeu: o que nao pode e' o JOGO repetir-se.
    servico = DefMateriaPrimaComponenteService(session)

    with pytest.raises(ReferenciaJaUsadaError) as erro:
        servico.guardar_lista(fer_conjunto.id, [_rafix("1F00"), _rafix("1F00")])

    assert "Ligador_Rafix_RTA20_19mm_1F00" in str(erro.value)
    assert "só pode aparecer uma vez" in str(erro.value)


def test_sem_jogo_a_ref_phc_continua_a_identificar(session, fer_conjunto) -> None:
    # Quem nao usa jogos fica exactamente como estava.
    servico = DefMateriaPrimaComponenteService(session)
    sem_jogo = ComponenteDados(papel=PAPEL_PRINCIPAL, ref_phc="FF00381")

    with pytest.raises(ReferenciaJaUsadaError):
        servico.guardar_lista(fer_conjunto.id, [sem_jogo, sem_jogo])


def test_a_ref_phc_de_uma_linha_com_jogo_nao_choca_com_outro_conjunto(
    session, fer_conjunto, outra_fer
) -> None:
    # O copo do Rafix e' documentacao na linha do jogo: pode aparecer noutra
    # materia-prima sem ambiguidade nenhuma.
    servico = DefMateriaPrimaComponenteService(session)
    servico.guardar_lista(fer_conjunto.id, [_rafix("1F00")])

    servico.guardar_lista(
        outra_fer.id,
        [
            ComponenteDados(
                papel=PAPEL_PRINCIPAL,
                nome_jogo_imos="Ligador_Rafix_RTA20_19mm_3F32",
                nome_imos="Cas_Rafix_20_R_26315705_19mm",
                ref_phc="FF00381",
            )
        ],
    )

    assert servico.contar_principais(outra_fer.id) == 1


def test_a_mensagem_ensina_a_usar_o_jogo_quando_ha_choque(
    session, fer_conjunto
) -> None:
    servico = DefMateriaPrimaComponenteService(session)
    linha = ComponenteDados(
        papel=PAPEL_PRINCIPAL, nome_imos="Cas_Rafix_20_R_26315705_19mm"
    )

    with pytest.raises(ReferenciaJaUsadaError) as erro:
        servico.guardar_lista(fer_conjunto.id, [linha, linha])

    assert "Jogo de Uniões (iMos)" in str(erro.value)
