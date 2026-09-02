"""Converter Orçamento: a lista só mostra o que falta passar para produção.

Cobre o levantamento (convertíveis + motivo de quem ficou de fora), os campos
que a obra herda do PHC, e a explicação que o diálogo dá numa pesquisa vazia.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import Cliente, OrcamentoVersao
from app.services import producao_service
from app.services.orcamento_encomenda_phc_service import (
    EncomendaPhcInput,
    OrcamentoEncomendaPhcService,
)
from app.services.orcamento_service import (
    CriarOrcamentoSimplesData,
    OrcamentoService,
)
from app.services.producao_service import (
    converter_orcamento,
    extrair_dados_encomenda_phc,
    levantar_orcamentos_para_conversao,
)


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication(sys.argv)


def _orcamento(session, *, encomendas, estado="Adjudicado", ano=2026):
    cliente = Cliente(
        nome="Cliente PHC",
        nome_simplex="CLIENTE_PHC",
        is_temporary=False,
        source_system="PHC",
        num_cliente_phc="C001",
    )
    session.add(cliente)
    session.flush()
    service = OrcamentoService(session)
    service.criar_orcamento_simples(
        CriarOrcamentoSimplesData(
            cliente_id=cliente.id,
            obra="Obra",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            enc_phc=encomendas[0] if encomendas else None,
            ano=ano,
        )
    )
    resumo = service.list_orcamentos()[0]
    versao = session.get(OrcamentoVersao, resumo.orcamento_versao_id)
    versao.estado = estado
    session.flush()
    if encomendas:
        OrcamentoEncomendaPhcService(session).substituir_encomendas(
            resumo.orcamento_versao_id,
            [
                EncomendaPhcInput(numero=numero, is_principal=(i == 0))
                for i, numero in enumerate(encomendas)
            ],
        )
        session.flush()
    return resumo.orcamento_id, resumo.orcamento_versao_id


@pytest.fixture()
def sem_pastas(monkeypatch):
    """A conversão não deve tocar no servidor durante os testes."""
    monkeypatch.setattr(producao_service, "criar_pasta_versao", lambda *a, **k: None)


# ---- a lista ---------------------------------------------------------------


def test_orcamento_por_converter_aparece(session) -> None:
    _orcamento(session, encomendas=["100"])

    convertiveis, excluidos = levantar_orcamentos_para_conversao(session)

    assert [item["enc_phc"] for item in convertiveis] == ["100"]
    assert excluidos == []


def test_orcamento_ja_convertido_desaparece_da_lista(session, sem_pastas) -> None:
    orcamento_id, versao_id = _orcamento(session, encomendas=["100"])
    converter_orcamento(
        session,
        orcamento_id=orcamento_id,
        versao_id=versao_id,
        created_by_id=None,
    )

    convertiveis, excluidos = levantar_orcamentos_para_conversao(session)

    assert convertiveis == []
    assert len(excluidos) == 1
    assert "já foi passado para produção" in excluidos[0]["motivo"]


def test_versao_fica_na_lista_ate_a_ultima_encomenda_ser_convertida(
    session, sem_pastas
) -> None:
    orcamento_id, versao_id = _orcamento(session, encomendas=["100", "200"])
    converter_orcamento(
        session,
        orcamento_id=orcamento_id,
        versao_id=versao_id,
        created_by_id=None,
        num_enc_phc="100",
    )

    convertiveis, _excluidos = levantar_orcamentos_para_conversao(session)

    # Continua lá, mas só oferece a encomenda que falta — e diz que a "100" já foi.
    assert len(convertiveis) == 1
    assert convertiveis[0]["encomendas_phc"] == ["200"]
    assert convertiveis[0]["enc_phc"] == "200"
    assert convertiveis[0]["encomendas_convertidas"]

    converter_orcamento(
        session,
        orcamento_id=orcamento_id,
        versao_id=versao_id,
        created_by_id=None,
        num_enc_phc="200",
    )
    convertiveis, excluidos = levantar_orcamentos_para_conversao(session)
    assert convertiveis == []
    assert len(excluidos) == 1


def test_orcamento_nao_adjudicado_fica_de_fora_com_o_motivo(session) -> None:
    _orcamento(session, encomendas=["100"], estado="Em elaboração")

    convertiveis, excluidos = levantar_orcamentos_para_conversao(session)

    assert convertiveis == []
    assert "Em elaboração" in excluidos[0]["motivo"]


def test_orcamento_sem_encomenda_phc_fica_de_fora_com_o_motivo(session) -> None:
    _orcamento(session, encomendas=[])

    convertiveis, excluidos = levantar_orcamentos_para_conversao(session)

    assert convertiveis == []
    assert excluidos[0]["motivo"] == "não tem Nº Enc PHC"


# ---- campos vindos do PHC --------------------------------------------------


def test_extrair_dados_da_encomenda_junta_descricoes_sem_repetir() -> None:
    linhas = [
        {
            "Descricao_Artigo": "1 COZINHA C/ ILHA",
            "Data_Encomenda": "02-09-2026",
            "Data_Entrega": "30-10-2026",
        },
        {"Descricao_Artigo": "1 ROUPEIRO", "Data_Encomenda": "02-09-2026"},
        {"Descricao_Artigo": "1 COZINHA C/ ILHA"},  # repetida
        {"Descricao_Artigo": "   "},  # vazia
    ]

    dados = extrair_dados_encomenda_phc(linhas)

    assert dados["descricao_artigos"] == "1 COZINHA C/ ILHA\n1 ROUPEIRO"
    assert dados["data_inicio"] == "02-09-2026"
    assert dados["data_entrega"] == "30-10-2026"


def test_extrair_dados_sem_linhas_devolve_vazio() -> None:
    assert extrair_dados_encomenda_phc([]) == {}
    assert extrair_dados_encomenda_phc(None) == {}


def test_phc_em_baixo_nao_impede_a_conversao(session, monkeypatch) -> None:
    def _rebenta(*_args, **_kwargs):
        raise RuntimeError("sem ligação ao PHC")

    monkeypatch.setattr(
        "app.services.encomendas_phc_service.query_phc_encomenda_itens", _rebenta
    )

    assert producao_service.dados_encomenda_phc(
        session, ano=2026, num_enc_phc="100"
    ) == {}


def test_obra_nasce_com_as_datas_e_descricoes_do_phc(session, sem_pastas) -> None:
    orcamento_id, versao_id = _orcamento(session, encomendas=["100"])

    processo = converter_orcamento(
        session,
        orcamento_id=orcamento_id,
        versao_id=versao_id,
        created_by_id=None,
        responsavel="Paulo",
        dados_encomenda={
            "data_inicio": "02-09-2026",
            "data_entrega": "30-10-2026",
            "descricao_artigos": "1 COZINHA C/ ILHA",
        },
    )

    assert processo.descricao_artigos == "1 COZINHA C/ ILHA"
    # As datas ficam em dd-mm-aaaa, como as que vêm do «Novo Processo».
    assert processo.data_inicio == "02-09-2026"
    assert processo.data_entrega == "30-10-2026"
    assert processo.responsavel == "Paulo"


def test_sem_dados_do_phc_a_obra_e_criada_na_mesma(session, sem_pastas) -> None:
    orcamento_id, versao_id = _orcamento(session, encomendas=["100"])

    processo = converter_orcamento(
        session,
        orcamento_id=orcamento_id,
        versao_id=versao_id,
        created_by_id=None,
    )

    assert processo.id is not None
    assert processo.descricao_artigos is None
    assert processo.data_inicio is None


# ---- o diálogo -------------------------------------------------------------


def test_pesquisa_vazia_explica_porque_o_orcamento_nao_aparece(_app) -> None:
    from app.ui.dialogs.converter_orcamento_dialog import ConverterOrcamentoDialog

    dialog = ConverterOrcamentoDialog()
    dialog._todos = []
    dialog._excluidos = [
        {
            "ano": 2026,
            "num_orcamento": "260875",
            "numero_versao": 1,
            "cliente_nome": "MÓVEIS J.F. VIVA",
            "motivo": "está em «Em elaboração», não Adjudicado",
        }
    ]
    dialog.campo_pesquisa.definir_texto("260875")

    dialog._render()

    texto = dialog.status_label.text()
    assert "260875" in texto
    assert "Em elaboração" in texto
    assert dialog.table.rowCount() == 0
    dialog.close()


def test_pesquisa_sem_nada_parecido_diz_que_nao_encontrou(_app) -> None:
    from app.ui.dialogs.converter_orcamento_dialog import ConverterOrcamentoDialog

    dialog = ConverterOrcamentoDialog()
    dialog._todos = []
    dialog._excluidos = []
    dialog.campo_pesquisa.definir_texto("999999")

    dialog._render()

    assert "Nada encontrado" in dialog.status_label.text()
    dialog.close()


def test_dialogo_avisa_sempre_qual_e_o_criterio(_app) -> None:
    from app.ui.dialogs.converter_orcamento_dialog import ConverterOrcamentoDialog

    dialog = ConverterOrcamentoDialog()

    texto = dialog.criterios_label.text()
    assert "Adjudicados" in texto
    assert "Nº Enc PHC" in texto
    assert "ainda não foram passados para produção" in texto
    dialog.close()
