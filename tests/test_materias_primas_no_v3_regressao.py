"""Regressão: gerir matérias-primas no V3 não pode mexer em orçamentos feitos.

O catálogo passou a ser editado dentro da aplicação (criar, alterar preços,
descontinuar). Estes testes existem para provar, com dados a sério, que nada
disso altera um orçamento já calculado — e que um material descontinuado
desaparece das escolhas novas sem desaparecer do passado.

A garantia vem do desenho: cada linha de custeio guarda a sua própria cópia da
referência, da descrição e do preço com que foi calculada.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.domain.materia_prima_types import (
    ORIGEM_PRECO_MANUAL,
    TIPO_PRECO_LIVRE,
    TIPO_PRECO_TABELA,
    preco_desatualizado,
    preco_em_falta,
)
from app.models import DefMateriaPrima, OrcamentoItemCusteioLinha
from app.repositories.def_materia_prima_repository import DefMateriaPrimaRepository
from app.services.def_materia_prima_service import (
    CriarDefMateriaPrimaData,
    DefMateriaPrimaService,
    EditarDefMateriaPrimaData,
)

HOJE = date(2026, 8, 25)


@pytest.fixture()
def service(session) -> DefMateriaPrimaService:
    return DefMateriaPrimaService(session)


def _criar(service: DefMateriaPrimaService, **overrides):
    """Uma placa normal; cada teste muda só o que lhe interessa."""
    campos = {
        "descricao": "AGL TERM BEGE ARDENNE 19MM",
        "familia_original_excel": "PLACAS",
        "tipo_original_excel": "AGLOMERADO",
        "unidade": "M2",
        "preco_tabela": Decimal("31.20"),
        "desconto": Decimal("18"),
        "preco_liquido": Decimal("25.58"),
        "data_ultimo_preco": date(2026, 8, 1),
    }
    campos.update(overrides)
    return service.criar_materia_prima(CriarDefMateriaPrimaData(**campos))


def _linha_de_orcamento(session, materia) -> OrcamentoItemCusteioLinha:
    """Uma linha de custeio como o V3 a grava: com a cópia do material."""
    linha = OrcamentoItemCusteioLinha(
        orcamento_item_id=1,
        tipo_linha="PECA",
        descricao="Lateral",
        materia_prima_id=materia.id,
        ref_le=materia.ref_le,
        descricao_materia_prima=materia.descricao,
        descricao_no_orcamento=materia.descricao,
        preco_liquido=materia.preco_liquido,
    )
    session.add(linha)
    session.commit()
    return linha


# --------------------------------------------------------------- referências


def test_ref_le_e_atribuida_a_partir_da_familia(service) -> None:
    materia = _criar(service)

    assert materia.ref_le == "PLC0001"


def test_ref_le_continua_a_contagem_por_familia(service) -> None:
    _criar(service, ref_le="PLC0120")
    _criar(service, descricao="Outra placa")
    ferragem = _criar(
        service,
        descricao="Dobradiça",
        familia_original_excel="FERRAGENS",
        unidade="UND",
    )

    assert service.proxima_ref_le("PLACAS") == "PLC0122"
    assert ferragem.ref_le == "FER0001"


def test_ref_le_nunca_e_reaproveitada_mesmo_estando_desativada(service) -> None:
    materia = _criar(service, ref_le="PLC0050")
    service.definir_ativo(materia.id, ativo=False)

    assert service.proxima_ref_le("PLACAS") == "PLC0051"


def test_ref_le_repetida_e_recusada(service) -> None:
    _criar(service, ref_le="PLC0001")

    with pytest.raises(ValueError):
        _criar(service, ref_le="PLC0001", descricao="Outra qualquer")


# ------------------------------------------------- orçamentos já calculados


def test_desativar_material_nao_mexe_na_linha_de_orcamento(service, session) -> None:
    materia = _criar(service)
    linha = _linha_de_orcamento(session, materia)

    service.definir_ativo(materia.id, ativo=False)
    session.refresh(linha)

    assert linha.ref_le == "PLC0001"
    assert linha.descricao_materia_prima == "AGL TERM BEGE ARDENNE 19MM"
    assert linha.preco_liquido == Decimal("25.58")
    assert linha.materia_prima_id == materia.id


def test_alterar_o_preco_nao_mexe_na_linha_de_orcamento(service, session) -> None:
    materia = _criar(service)
    linha = _linha_de_orcamento(session, materia)

    service.editar_materia_prima(
        materia.id,
        EditarDefMateriaPrimaData(
            descricao="AGL TERM BEGE ARDENNE 19MM",
            ref_le=materia.ref_le,
            familia_original_excel="PLACAS",
            unidade="M2",
            preco_tabela=Decimal("40.00"),
            desconto=Decimal("18"),
            preco_liquido=Decimal("32.80"),
        ),
    )
    session.refresh(linha)

    assert linha.preco_liquido == Decimal("25.58")


def test_mudar_a_descricao_nao_mexe_na_linha_de_orcamento(service, session) -> None:
    materia = _criar(service)
    linha = _linha_de_orcamento(session, materia)

    service.editar_materia_prima(
        materia.id,
        EditarDefMateriaPrimaData(
            descricao="AGL TERM BEGE ARDENNE 19MM (novo nome)",
            ref_le=materia.ref_le,
            familia_original_excel="PLACAS",
            unidade="M2",
            preco_tabela=Decimal("31.20"),
            desconto=Decimal("18"),
            preco_liquido=Decimal("25.58"),
        ),
    )
    session.refresh(linha)

    assert linha.descricao_materia_prima == "AGL TERM BEGE ARDENNE 19MM"
    assert linha.descricao_no_orcamento == "AGL TERM BEGE ARDENNE 19MM"


# ------------------------------------------------------- escolhas de novas


def test_material_desativado_sai_das_escolhas_mas_continua_a_existir(
    service, session
) -> None:
    materia = _criar(service)
    service.definir_ativo(materia.id, ativo=False)

    assert service.pesquisar("AGL") == []
    assert service.listar_materias_primas_ativas() == []
    # Continua no catálogo, e pode ser reposto.
    assert len(service.listar_materias_primas()) == 1
    assert service.obter_por_id(materia.id) is not None

    service.definir_ativo(materia.id, ativo=True)
    assert len(service.pesquisar("AGL")) == 1


def test_utilizacoes_conta_as_linhas_de_orcamento(service, session) -> None:
    materia = _criar(service)
    _linha_de_orcamento(session, materia)
    _linha_de_orcamento(session, materia)

    assert service.contar_utilizacoes(materia.id) == 2
    assert service.contar_utilizacoes(materia.id + 999) == 0


# ------------------------------------------------------------- histórico


def test_criar_com_preco_deixa_registo_no_historico(service) -> None:
    materia = _criar(service)

    historico = service.historico_precos(materia.id)

    assert len(historico) == 1
    assert historico[0].preco_tabela == Decimal("31.20")
    assert historico[0].origem == ORIGEM_PRECO_MANUAL


def test_alterar_o_preco_acrescenta_ao_historico(service) -> None:
    materia = _criar(service)

    service.editar_materia_prima(
        materia.id,
        EditarDefMateriaPrimaData(
            descricao=materia.descricao,
            ref_le=materia.ref_le,
            familia_original_excel="PLACAS",
            unidade="M2",
            preco_tabela=Decimal("40.00"),
            desconto=Decimal("18"),
            preco_liquido=Decimal("32.80"),
        ),
    )

    historico = service.historico_precos(materia.id)
    assert [registo.preco_tabela for registo in historico] == [
        Decimal("40.00"),
        Decimal("31.20"),
    ]


def test_alterar_so_a_descricao_nao_sujaAo_historico(service) -> None:
    materia = _criar(service)

    service.editar_materia_prima(
        materia.id,
        EditarDefMateriaPrimaData(
            descricao="Outro nome",
            ref_le=materia.ref_le,
            familia_original_excel="PLACAS",
            unidade="M2",
            preco_tabela=Decimal("31.20"),
            desconto=Decimal("18"),
            preco_liquido=Decimal("25.58"),
        ),
    )

    assert len(service.historico_precos(materia.id)) == 1


def test_material_sem_preco_nao_gera_historico(service) -> None:
    materia = _criar(
        service,
        descricao="PLACAS LIVRES",
        tipo_preco=TIPO_PRECO_LIVRE,
        preco_tabela=None,
        desconto=None,
        preco_liquido=None,
        data_ultimo_preco=None,
    )

    assert service.historico_precos(materia.id) == []


# --------------------------------------------------------- estado do preço


def test_preco_em_falta_ignora_os_materiais_de_preco_livre(service) -> None:
    livre = _criar(
        service,
        descricao="FERRAGEM LIVRE",
        familia_original_excel="FERRAGENS",
        tipo_preco=TIPO_PRECO_LIVRE,
        preco_tabela=None,
        preco_liquido=None,
    )
    esquecido = _criar(
        service,
        descricao="AGL sem preço",
        preco_tabela=None,
        preco_liquido=None,
    )

    assert preco_em_falta(livre) is False
    assert preco_em_falta(esquecido) is True


def test_preco_desatualizado_conta_meses_e_ignora_os_livres(service) -> None:
    antigo = _criar(service, data_ultimo_preco=date(2025, 7, 23))
    recente = _criar(
        service, descricao="Placa recente", data_ultimo_preco=date(2026, 4, 23)
    )
    sem_data = _criar(service, descricao="Placa sem data", data_ultimo_preco=None)
    livre = _criar(
        service,
        descricao="PLACAS LIVRES",
        tipo_preco=TIPO_PRECO_LIVRE,
        preco_tabela=None,
        preco_liquido=None,
        data_ultimo_preco=None,
    )

    assert preco_desatualizado(antigo, HOJE) is True
    assert preco_desatualizado(recente, HOJE) is False
    assert preco_desatualizado(sem_data, HOJE) is True
    assert preco_desatualizado(livre, HOJE) is False


def test_tipo_preco_por_omissao_e_tabela(service) -> None:
    materia = _criar(service)

    assert materia.tipo_preco == TIPO_PRECO_TABELA
    assert materia.preco_livre is False


# ------------------------------------------------------------- auditoria


def test_regista_quem_criou_e_quem_alterou(service, session) -> None:
    from app.core.session import app_session
    from app.models import User

    utilizador = User(
        username="paulo",
        nome="Paulo Catarino",
        email="paulo@exemplo.pt",
        password_hash="x",
        role="user",
    )
    session.add(utilizador)
    session.commit()

    app_session.set_current_user(utilizador)
    try:
        materia = _criar(service)
    finally:
        app_session.clear_current_user()

    guardado = session.get(DefMateriaPrima, materia.id)
    assert guardado.criado_por_id == utilizador.id
    assert guardado.alterado_por_id == utilizador.id
    assert service.obter_por_id(materia.id).criado_por == "Paulo Catarino"


def test_sem_utilizador_autenticado_grava_na_mesma(service) -> None:
    """Os scripts (seed, importação) correm sem ninguém autenticado."""
    materia = _criar(service)

    assert materia.id is not None


def test_repositorio_conta_a_partir_do_maior_numero_existente(session) -> None:
    repositorio = DefMateriaPrimaRepository(session)
    repositorio.create_materia_prima(descricao="A", ref_le="PLC0007")
    repositorio.create_materia_prima(descricao="B", ref_le="PLC0120")
    repositorio.create_materia_prima(descricao="C", ref_le="PLCXXXX")
    session.commit()

    assert repositorio.ultimo_numero_ref_le("PLC") == 120
    assert repositorio.ultimo_numero_ref_le("FER") == 0
