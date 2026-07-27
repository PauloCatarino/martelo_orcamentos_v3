"""Testes da comparacao de Ref. Cliente (iguais e parecidas)."""

from __future__ import annotations

import pytest

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.domain.ref_cliente_semelhanca import chave_ref, comparar
from app.models import Cliente
from app.repositories.orcamento_repository import OrcamentoRepository
from app.services.orcamento_service import (
    CriarOrcamentoSimplesData,
    OrcamentoService,
)


@pytest.mark.parametrize(
    "nova, existente",
    [
        ("REF-NOVO", "ref novo"),          # maiusculas e pontuacao
        ("Ref. Cliente-X", "refclientex"),  # pontuacao e espacos
        ("ROUPEIROS", "roupeiro"),          # plural
        ("Cozinhas Sala", "cozinha sala"),  # plural no meio
        ("  2512023  ", "2512023"),         # espacos nas pontas
        ("Móveis WC", "moveis wc"),         # acentos
    ],
)
def test_referencias_iguais_apesar_da_escrita(nova: str, existente: str) -> None:
    semelhanca = comparar(nova, existente)

    assert semelhanca is not None
    assert semelhanca.e_igual is True
    assert semelhanca.etiqueta == "Igual"


@pytest.mark.parametrize(
    "nova, existente",
    [
        ("2512023", "2512024"),   # um digito trocado = obra diferente
        ("1234", "4321"),         # os mesmos digitos por outra ordem
        ("2606999", "2606998"),
    ],
)
def test_referencias_so_com_digitos_nao_avisam_por_semelhanca(
    nova: str, existente: str
) -> None:
    assert comparar(nova, existente) is None


@pytest.mark.parametrize(
    "nova, existente",
    [
        ("Torres Belas", "Tores Belas"),   # erro de escrita
        ("REF-NOVO-2", "REF-NOVO"),        # uma contem a outra
        ("2512023A", "2512023"),           # sufixo numa referencia do PHC
        ("Obra Azeitao", "Obra Azeitaum"),
    ],
)
def test_referencias_parecidas(nova: str, existente: str) -> None:
    semelhanca = comparar(nova, existente)

    assert semelhanca is not None
    assert semelhanca.e_igual is False
    assert semelhanca.etiqueta.startswith("Parecida (")


@pytest.mark.parametrize(
    "nova, existente",
    [
        ("Cozinha Faro", "Roupeiros Lisboa"),  # nada a ver
        ("REF-NOVO", ""),                      # sem referencia do outro lado
        ("", "REF-NOVO"),
        ("ABC", "ABCDEFGHIJ"),                 # curta de mais para contar
    ],
)
def test_referencias_diferentes_nao_avisam(nova: str, existente: str) -> None:
    assert comparar(nova, existente) is None


def test_chave_ref_junta_as_raizes_sem_pontuacao() -> None:
    assert chave_ref(" Ref. NOVOS - 2026 ") == "refnovo2026"
    assert chave_ref(None) == ""


def _criar_cliente(session, nome: str) -> int:
    cliente = Cliente(nome=nome, is_temporary=True)
    session.add(cliente)
    session.flush()
    return cliente.id


def _criar_orcamento(session, cliente_id: int, ref_cliente: str) -> None:
    OrcamentoService(session).criar_orcamento_simples(
        CriarOrcamentoSimplesData(
            cliente_id=cliente_id,
            obra=f"Obra {ref_cliente}",
            descricao=None,
            localizacao=None,
            ref_cliente=ref_cliente,
            created_by_id=None,
            ano=2026,
        )
    )


def test_ref_igual_avisa_mesmo_escrita_de_outra_maneira(session) -> None:
    cliente_id = _criar_cliente(session, "Cliente A")
    _criar_orcamento(session, cliente_id, "REF-NOVO")

    correspondencias = OrcamentoService(
        session
    ).find_orcamentos_ref_cliente_semelhante("ref novo", cliente_id)

    assert len(correspondencias) == 1
    assert correspondencias[0].semelhanca.e_igual is True
    assert correspondencias[0].orcamento.ref_cliente == "REF-NOVO"


def test_ref_parecida_so_conta_dentro_do_mesmo_cliente(session) -> None:
    cliente_a = _criar_cliente(session, "Cliente A")
    cliente_b = _criar_cliente(session, "Cliente B")
    _criar_orcamento(session, cliente_a, "REF-NOVO")

    service = OrcamentoService(session)

    # Mesmo cliente: a referencia parecida avisa.
    assert (
        len(service.find_orcamentos_ref_cliente_semelhante("REF-NOVO-2", cliente_a))
        == 1
    )
    # Outro cliente: parecida nao avisa...
    assert service.find_orcamentos_ref_cliente_semelhante("REF-NOVO-2", cliente_b) == []
    # ... mas igual continua a avisar em qualquer cliente.
    assert (
        len(service.find_orcamentos_ref_cliente_semelhante("ref novo", cliente_b)) == 1
    )


def test_ref_numerica_parecida_nao_avisa(session) -> None:
    cliente_id = _criar_cliente(session, "Cliente A")
    _criar_orcamento(session, cliente_id, "2512023")

    service = OrcamentoService(session)

    assert service.find_orcamentos_ref_cliente_semelhante("2512024", cliente_id) == []
    assert len(service.find_orcamentos_ref_cliente_semelhante("2512023", cliente_id)) == 1


def test_correspondencias_ordenadas_com_as_iguais_primeiro(session) -> None:
    cliente_id = _criar_cliente(session, "Cliente A")
    _criar_orcamento(session, cliente_id, "REF-NOVO-2")
    _criar_orcamento(session, cliente_id, "REF NOVO")

    correspondencias = OrcamentoService(
        session
    ).find_orcamentos_ref_cliente_semelhante("ref-novo", cliente_id)

    assert [item.semelhanca.grau for item in correspondencias] == [
        "igual",
        "parecida",
    ]


def test_ref_cliente_vazia_nao_procura(session) -> None:
    cliente_id = _criar_cliente(session, "Cliente A")
    _criar_orcamento(session, cliente_id, "REF-NOVO")

    service = OrcamentoService(session)

    assert service.find_orcamentos_ref_cliente_semelhante("   ", cliente_id) == []
    assert service.find_orcamentos_ref_cliente_semelhante("---", cliente_id) == []


def test_list_com_ref_cliente_ignora_referencias_vazias(session) -> None:
    cliente_id = _criar_cliente(session, "Cliente A")
    _criar_orcamento(session, cliente_id, "REF-NOVO")
    _criar_orcamento(session, cliente_id, "   ")

    resultados = OrcamentoRepository(session).list_com_ref_cliente()

    assert [orcamento.ref_cliente for orcamento in resultados] == ["REF-NOVO"]
    assert resultados[0].cliente_id == cliente_id
