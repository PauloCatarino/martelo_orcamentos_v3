"""Tests for the PHC orders per budget version (phase 5)."""

from __future__ import annotations

import pytest

from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domain.orcamento_estados import ESTADO_INICIAL
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import (
    Cliente,
    OrcamentoVersao,
    OrcamentoVersaoEncomendaPhc,
    Producao,
)
from app.services.orcamento_encomenda_phc_service import (
    EncomendaPhcInput,
    OrcamentoEncomendaPhcService,
    normalizar_encomendas,
)
from app.services.orcamento_service import (
    CriarOrcamentoSimplesData,
    EditarOrcamentoData,
    OrcamentoService,
)


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _criar_cliente(session, *, phc: bool = False) -> int:
    if phc:
        cliente = Cliente(
            nome="Cliente PHC",
            nome_simplex="CLIENTE_PHC",
            is_temporary=False,
            source_system="PHC",
            num_cliente_phc="C001",
        )
    else:
        cliente = Cliente(nome="Cliente X", is_temporary=True)
    session.add(cliente)
    session.flush()
    return cliente.id


def _criar_orcamento(
    session, *, enc_phc: str | None = None, phc: bool = False
) -> tuple[int, int]:
    cliente_id = _criar_cliente(session, phc=phc)
    service = OrcamentoService(session)
    service.criar_orcamento_simples(
        CriarOrcamentoSimplesData(
            cliente_id=cliente_id,
            obra="Obra",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            enc_phc=enc_phc,
            ano=2026,
        )
    )
    resumo = service.list_orcamentos()[0]
    return resumo.orcamento_id, resumo.orcamento_versao_id


# ---------------------------------------------------------------------------
# Normalização


def test_normalizar_rejeita_numero_vazio() -> None:
    with pytest.raises(ValueError, match="vazio"):
        normalizar_encomendas([EncomendaPhcInput(numero="   ")])


def test_normalizar_rejeita_duplicados_case_insensitive() -> None:
    with pytest.raises(ValueError, match="repetida"):
        normalizar_encomendas(
            [
                EncomendaPhcInput(numero="E100"),
                EncomendaPhcInput(numero=" e100 "),
            ]
        )


def test_normalizar_rejeita_mais_do_que_uma_principal() -> None:
    with pytest.raises(ValueError, match="principal"):
        normalizar_encomendas(
            [
                EncomendaPhcInput(numero="100", is_principal=True),
                EncomendaPhcInput(numero="200", is_principal=True),
            ]
        )


def test_normalizar_promove_a_primeira_quando_nenhuma_e_principal() -> None:
    resultado = normalizar_encomendas(
        [EncomendaPhcInput(numero="100"), EncomendaPhcInput(numero="200")]
    )
    assert [(enc.numero, enc.is_principal) for enc in resultado] == [
        ("100", True),
        ("200", False),
    ]


# ---------------------------------------------------------------------------
# Compatibilidade / migração do valor antigo


def test_versao_antiga_so_com_enc_phc_aparece_como_encomenda_principal(
    session,
) -> None:
    _orcamento_id, versao_id = _criar_orcamento(session)
    # Simula uma versão gravada antes da tabela filha existir.
    versao = session.get(OrcamentoVersao, versao_id)
    versao.enc_phc = "475"
    session.flush()

    encomendas = OrcamentoEncomendaPhcService(session).listar_encomendas(versao_id)

    assert [(enc.numero, enc.is_principal) for enc in encomendas] == [("475", True)]


def test_criar_orcamento_com_enc_phc_cria_registo_filho_principal(session) -> None:
    _orcamento_id, versao_id = _criar_orcamento(session, enc_phc="1055")

    registos = session.execute(
        select(OrcamentoVersaoEncomendaPhc).where(
            OrcamentoVersaoEncomendaPhc.orcamento_versao_id == versao_id
        )
    ).scalars().all()

    assert [(reg.numero, reg.is_principal) for reg in registos] == [("1055", True)]
    assert session.get(OrcamentoVersao, versao_id).enc_phc == "1055"


# ---------------------------------------------------------------------------
# Várias encomendas e principal


def test_varias_encomendas_na_mesma_versao_com_principal(session) -> None:
    _orcamento_id, versao_id = _criar_orcamento(session, enc_phc="100")
    service = OrcamentoEncomendaPhcService(session)

    service.substituir_encomendas(
        versao_id,
        [
            EncomendaPhcInput(numero="100"),
            EncomendaPhcInput(numero="200", is_principal=True),
            EncomendaPhcInput(numero="300"),
        ],
    )

    encomendas = service.listar_encomendas(versao_id)
    assert [enc.numero for enc in encomendas] == ["200", "100", "300"]
    assert [enc.is_principal for enc in encomendas] == [True, False, False]
    # Espelho de compatibilidade: enc_phc guarda sempre a principal.
    assert session.get(OrcamentoVersao, versao_id).enc_phc == "200"


def test_definir_principal_atualiza_espelho(session) -> None:
    _orcamento_id, versao_id = _criar_orcamento(session, enc_phc="100")
    service = OrcamentoEncomendaPhcService(session)
    service.substituir_encomendas(
        versao_id,
        [EncomendaPhcInput(numero="100"), EncomendaPhcInput(numero="200")],
    )

    service.definir_principal(versao_id, "200")

    assert service.get_principal(versao_id) == "200"
    assert session.get(OrcamentoVersao, versao_id).enc_phc == "200"


def test_definir_principal_de_numero_inexistente_da_erro(session) -> None:
    _orcamento_id, versao_id = _criar_orcamento(session, enc_phc="100")

    with pytest.raises(ValueError, match="não existe"):
        OrcamentoEncomendaPhcService(session).definir_principal(versao_id, "999")


def test_substituir_com_duplicados_da_erro(session) -> None:
    _orcamento_id, versao_id = _criar_orcamento(session, enc_phc="100")

    with pytest.raises(ValueError, match="repetida"):
        OrcamentoEncomendaPhcService(session).substituir_encomendas(
            versao_id,
            [EncomendaPhcInput(numero="200"), EncomendaPhcInput(numero="200")],
        )


# ---------------------------------------------------------------------------
# Edição pelo serviço de orçamentos


def test_editar_orcamento_grava_o_conjunto_de_encomendas(session) -> None:
    orcamento_id, versao_id = _criar_orcamento(session, enc_phc="100")

    OrcamentoService(session).editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="Obra",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado=ESTADO_INICIAL,
            encomendas_phc=(
                EncomendaPhcInput(numero="100"),
                EncomendaPhcInput(numero="200", is_principal=True),
            ),
        ),
        orcamento_versao_id=versao_id,
    )

    service = OrcamentoEncomendaPhcService(session)
    assert [enc.numero for enc in service.listar_encomendas(versao_id)] == [
        "200",
        "100",
    ]
    assert session.get(OrcamentoVersao, versao_id).enc_phc == "200"


def test_editar_orcamento_compatibilidade_enc_phc_legado(session) -> None:
    orcamento_id, versao_id = _criar_orcamento(session)

    OrcamentoService(session).editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="Obra",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado=ESTADO_INICIAL,
            enc_phc="475",
        ),
        orcamento_versao_id=versao_id,
    )

    encomendas = OrcamentoEncomendaPhcService(session).listar_encomendas(versao_id)
    assert [(enc.numero, enc.is_principal) for enc in encomendas] == [("475", True)]
    assert session.get(OrcamentoVersao, versao_id).enc_phc == "475"


def test_editar_orcamento_com_lista_vazia_limpa_encomendas(session) -> None:
    orcamento_id, versao_id = _criar_orcamento(session, enc_phc="100")

    OrcamentoService(session).editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="Obra",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado=ESTADO_INICIAL,
            encomendas_phc=(),
        ),
        orcamento_versao_id=versao_id,
    )

    assert OrcamentoEncomendaPhcService(session).listar_encomendas(versao_id) == []
    assert session.get(OrcamentoVersao, versao_id).enc_phc is None


def test_lista_conta_encomendas_da_versao(session) -> None:
    _orcamento_id, versao_id = _criar_orcamento(session, enc_phc="100")
    OrcamentoEncomendaPhcService(session).substituir_encomendas(
        versao_id,
        [
            EncomendaPhcInput(numero="100", is_principal=True),
            EncomendaPhcInput(numero="200"),
            EncomendaPhcInput(numero="300"),
        ],
    )

    resumo = OrcamentoService(session).list_orcamentos()[0]

    assert resumo.enc_phc == "100"
    assert resumo.encomendas_phc_total == 3


def test_lista_conta_uma_encomenda_para_versao_legada(session) -> None:
    _orcamento_id, versao_id = _criar_orcamento(session)
    versao = session.get(OrcamentoVersao, versao_id)
    versao.enc_phc = "475"
    session.flush()

    resumo = OrcamentoService(session).list_orcamentos()[0]

    assert resumo.encomendas_phc_total == 1


# ---------------------------------------------------------------------------
# Conversão para produção


def _preparar_orcamento_adjudicado(session) -> tuple[int, int]:
    orcamento_id, versao_id = _criar_orcamento(session, enc_phc="100", phc=True)
    versao = session.get(OrcamentoVersao, versao_id)
    versao.estado = "Adjudicado"
    session.flush()
    OrcamentoEncomendaPhcService(session).substituir_encomendas(
        versao_id,
        [
            EncomendaPhcInput(numero="100", is_principal=True),
            EncomendaPhcInput(numero="200"),
        ],
    )
    session.flush()
    return orcamento_id, versao_id


def test_listar_convertiveis_inclui_todas_as_encomendas(session) -> None:
    from app.services.producao_service import listar_orcamentos_convertiveis

    _preparar_orcamento_adjudicado(session)

    linhas = listar_orcamentos_convertiveis(session)

    assert len(linhas) == 1
    assert linhas[0]["enc_phc"] == "100"
    assert linhas[0]["encomendas_phc"] == ["100", "200"]


def test_converter_sem_escolha_usa_a_principal(session, monkeypatch) -> None:
    from app.services import producao_service

    monkeypatch.setattr(
        producao_service, "criar_pasta_versao", lambda *a, **k: None
    )
    orcamento_id, versao_id = _preparar_orcamento_adjudicado(session)

    processo = producao_service.converter_orcamento(
        session,
        orcamento_id=orcamento_id,
        versao_id=versao_id,
        created_by_id=None,
    )

    assert processo.num_enc_phc == "100"
    assert "0100" in processo.codigo_processo


def test_converter_com_encomenda_escolhida(session, monkeypatch) -> None:
    from app.services import producao_service

    monkeypatch.setattr(
        producao_service, "criar_pasta_versao", lambda *a, **k: None
    )
    orcamento_id, versao_id = _preparar_orcamento_adjudicado(session)

    processo = producao_service.converter_orcamento(
        session,
        orcamento_id=orcamento_id,
        versao_id=versao_id,
        created_by_id=None,
        num_enc_phc="200",
    )

    assert processo.num_enc_phc == "200"


def test_converter_encomenda_que_nao_pertence_da_erro(session) -> None:
    from app.services.producao_service import converter_orcamento

    orcamento_id, versao_id = _preparar_orcamento_adjudicado(session)

    with pytest.raises(ValueError, match="não pertence"):
        converter_orcamento(
            session,
            orcamento_id=orcamento_id,
            versao_id=versao_id,
            created_by_id=None,
            num_enc_phc="999",
        )


def test_converter_cada_encomenda_cria_o_seu_processo(session, monkeypatch) -> None:
    from app.services import producao_service

    monkeypatch.setattr(
        producao_service, "criar_pasta_versao", lambda *a, **k: None
    )
    orcamento_id, versao_id = _preparar_orcamento_adjudicado(session)

    producao_service.converter_orcamento(
        session,
        orcamento_id=orcamento_id,
        versao_id=versao_id,
        created_by_id=None,
        num_enc_phc="100",
    )
    producao_service.converter_orcamento(
        session,
        orcamento_id=orcamento_id,
        versao_id=versao_id,
        created_by_id=None,
        num_enc_phc="200",
    )

    numeros = session.execute(select(Producao.num_enc_phc)).scalars().all()
    assert sorted(numeros) == ["100", "200"]


def test_converter_a_mesma_encomenda_duas_vezes_da_erro(
    session, monkeypatch
) -> None:
    from app.services import producao_service

    monkeypatch.setattr(
        producao_service, "criar_pasta_versao", lambda *a, **k: None
    )
    orcamento_id, versao_id = _preparar_orcamento_adjudicado(session)

    producao_service.converter_orcamento(
        session,
        orcamento_id=orcamento_id,
        versao_id=versao_id,
        created_by_id=None,
        num_enc_phc="200",
    )
    with pytest.raises(ValueError, match="Já existe"):
        producao_service.converter_orcamento(
            session,
            orcamento_id=orcamento_id,
            versao_id=versao_id,
            created_by_id=None,
            num_enc_phc="200",
        )
