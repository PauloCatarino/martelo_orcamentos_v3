"""Tests for the PHC proposal registration flow (PHC assigns the number).

The keystroke automation and the SQL reads are stubbed; what is covered here
is the orchestration: which number the V3 adopts, what happens when the read
fails, and the wrong-document-type detection.
"""

from __future__ import annotations

import pytest

from app.services.phc_propostas_service import PropostaPhc
from app.services.registar_proposta_phc_service import (
    RegistoPropostaResultado,
    descrever_resultado,
    designacao_sugerida,
    formatar_codigo_v3,
)


# -- Código do orçamento no V3 ---------------------------------------------


def test_codigo_v3_junta_ano_e_numero():
    assert formatar_codigo_v3(2026, 806) == "260806"


def test_codigo_v3_preenche_o_numero_com_zeros():
    assert formatar_codigo_v3(2026, 1) == "260001"
    assert formatar_codigo_v3(2026, 45) == "260045"


def test_codigo_v3_aceita_numeros_de_4_digitos():
    """Em 2024 o PHC chegou ao 1231 — não pode ser truncado."""
    assert formatar_codigo_v3(2024, 1231) == "241231"


def test_codigo_v3_distingue_o_mesmo_numero_em_anos_diferentes():
    """O OBRANO repete-se entre anos; o ano é o que desambigua."""
    assert formatar_codigo_v3(2025, 806) != formatar_codigo_v3(2026, 806)


# -- Designação sugerida ---------------------------------------------------


def test_designacao_sugerida_com_ref():
    assert designacao_sugerida("2510008") == "Obra: 2510008"


def test_designacao_sugerida_sem_ref_fica_vazia():
    """Sem ref não há convenção — o utilizador escreve o que precisar."""
    assert designacao_sugerida("") == ""
    assert designacao_sugerida(None) == ""
    assert designacao_sugerida("   ") == ""


# -- Resultado -------------------------------------------------------------


def _proposta(numero=806, ano=2026, ref="25100010"):
    return PropostaPhc(
        numero=numero,
        ano=ano,
        num_cliente="35",
        ref_cliente=ref,
        data="25.07.2026",
    )


def test_resultado_com_proposta_expoe_numero_e_codigo():
    resultado = RegistoPropostaResultado(proposta=_proposta())
    assert resultado.numero_confirmado == 806
    assert resultado.codigo_v3 == "260806"
    assert resultado.precisa_confirmacao_manual is False


def test_resultado_sem_proposta_pede_confirmacao():
    resultado = RegistoPropostaResultado(erro_leitura="sem ligação ao SQL")
    assert resultado.numero_confirmado is None
    assert resultado.codigo_v3 is None
    assert resultado.precisa_confirmacao_manual is True


# -- Texto mostrado ao utilizador ------------------------------------------


def test_descrever_tipo_errado_avisa_e_manda_apagar():
    resultado = RegistoPropostaResultado(tipo_errado="Encomenda de Cliente nº 1330")
    texto = descrever_resultado(resultado, num_cliente_phc="35")
    assert "NÃO foi criada" in texto
    assert "Encomenda de Cliente nº 1330" in texto
    assert "apaga" in texto.casefold()


def test_descrever_sucesso_mostra_numero_codigo_e_verificacao():
    resultado = RegistoPropostaResultado(proposta=_proposta())
    texto = descrever_resultado(resultado, num_cliente_phc="35")
    assert "806" in texto
    assert "260806" in texto
    assert "verificadas" in texto
    # O nº de cliente aparece no formato do PHC (3 dígitos).
    assert "035" in texto


def test_descrever_com_avisos_nao_diz_que_esta_verificado():
    resultado = RegistoPropostaResultado(
        proposta=_proposta(),
        avisos=["A Ref. Cliente no PHC ficou '(vazia)' em vez de '25100010'."],
    )
    texto = descrever_resultado(resultado, num_cliente_phc="35")
    assert "verificadas" not in texto
    assert "Ref. Cliente" in texto
    assert "colunas noutra ordem" in texto


def test_descrever_sem_leitura_inclui_o_motivo():
    resultado = RegistoPropostaResultado(erro_leitura="ligação recusada")
    texto = descrever_resultado(resultado, num_cliente_phc="35")
    assert "não consegui confirmar o número" in texto
    assert "ligação recusada" in texto


# -- Orquestração (automação e SQL simulados) ------------------------------


class _AutomacaoFalsa:
    """Substitui a automação da janela: registra o que lhe foi pedido."""

    def __init__(self) -> None:
        self.chamadas: list[dict] = []

    def criar_proposta(self, **kwargs):
        self.chamadas.append(kwargs)
        return None


def test_registar_adota_o_numero_lido_do_phc(monkeypatch):
    from app.services import registar_proposta_phc_service as servico

    monkeypatch.setattr(
        servico, "ler_max_obrano", lambda *a, **k: 805
    )
    monkeypatch.setattr(
        servico, "localizar_proposta_criada", lambda *a, **k: _proposta()
    )
    monkeypatch.setattr(
        servico, "ler_designacoes_proposta", lambda *a, **k: ["Obra: 25100010"]
    )

    automacao = _AutomacaoFalsa()
    resultado = servico.registar_proposta_no_phc(
        None,
        ano=2026,
        num_cliente_phc="35",
        ref_cliente="25100010",
        designacao="Obra: 25100010",
        automation=automacao,
    )

    assert resultado.numero_confirmado == 806
    assert resultado.codigo_v3 == "260806"
    assert resultado.avisos == []
    # A automação foi chamada uma única vez, com os dados do formulário.
    assert len(automacao.chamadas) == 1
    assert automacao.chamadas[0]["ref_cliente"] == "25100010"


def test_marca_de_agua_e_so_de_propostas(monkeypatch):
    """Regressão: cada tipo de dossier tem a sua própria série de OBRANO.

    As Encomendas de Cliente vão em 1329 enquanto as Propostas vão em 805.
    Se a marca de água fosse "de qualquer tipo", ficaria em 1329 e a proposta
    806 nunca apareceria — foi exactamente este o bug.
    """
    from app.services import registar_proposta_phc_service as servico

    vistos: dict[str, int] = {}

    def _max_propostas(_session, *, ano):
        vistos["ano"] = ano
        return 805  # só propostas; NÃO 1329 (que é das encomendas)

    monkeypatch.setattr(servico, "ler_max_obrano", _max_propostas)

    bases: list[int] = []

    def _localizar(_session, *, ano, obrano_base, num_cliente, ref_cliente):
        bases.append(obrano_base)
        return _proposta() if obrano_base < 806 else None

    monkeypatch.setattr(servico, "localizar_proposta_criada", _localizar)
    monkeypatch.setattr(
        servico, "ler_designacoes_proposta", lambda *a, **k: ["Obra: 25100010"]
    )

    resultado = servico.registar_proposta_no_phc(
        None,
        ano=2026,
        num_cliente_phc="35",
        ref_cliente="25100010",
        designacao="Obra: 25100010",
        automation=_AutomacaoFalsa(),
    )

    assert bases == [805], "a marca de água tem de vir só das propostas"
    assert resultado.numero_confirmado == 806
    assert vistos["ano"] == 2026


def test_deteta_tipo_errado_procura_por_data_nao_por_numero(monkeypatch):
    """A busca do documento indevido é por data: séries são por tipo."""
    from app.services import registar_proposta_phc_service as servico

    monkeypatch.setattr(servico, "ler_max_obrano", lambda *a, **k: 805)
    monkeypatch.setattr(servico, "localizar_proposta_criada", lambda *a, **k: None)

    recebido: dict[str, object] = {}

    def _procurar(_session, *, data_iso, num_cliente, ref_cliente):
        recebido["data_iso"] = data_iso
        recebido["ref"] = ref_cliente
        return "Encomenda de Cliente nº 1330"

    monkeypatch.setattr(servico, "procurar_dossier_tipo_errado", _procurar)

    resultado = servico.registar_proposta_no_phc(
        None,
        ano=2026,
        num_cliente_phc="35",
        ref_cliente="25100010",
        designacao="Obra: 25100010",
        data_iso="20260725",
        automation=_AutomacaoFalsa(),
    )

    assert recebido["data_iso"] == "20260725"
    assert recebido["ref"] == "25100010"
    assert resultado.tipo_errado == "Encomenda de Cliente nº 1330"


def test_registar_deteta_documento_do_tipo_errado(monkeypatch):
    """Seletor do PHC noutro tipo: nenhuma proposta nova aparece."""
    from app.services import registar_proposta_phc_service as servico

    monkeypatch.setattr(
        servico, "ler_max_obrano", lambda *a, **k: 805
    )
    monkeypatch.setattr(servico, "localizar_proposta_criada", lambda *a, **k: None)
    monkeypatch.setattr(
        servico,
        "procurar_dossier_tipo_errado",
        lambda *a, **k: "Encomenda de Cliente nº 1330",
    )
    monkeypatch.setattr(servico, "_hoje_iso", lambda: "20260725")

    resultado = servico.registar_proposta_no_phc(
        None,
        ano=2026,
        num_cliente_phc="35",
        ref_cliente="25100010",
        designacao="Obra: 25100010",
        automation=_AutomacaoFalsa(),
    )

    assert resultado.tipo_errado == "Encomenda de Cliente nº 1330"
    assert resultado.numero_confirmado is None


def test_registar_sem_sql_nao_inventa_numero(monkeypatch):
    """Sem ligação ao PHC a proposta é criada, mas o número não é adivinhado."""
    from app.services import registar_proposta_phc_service as servico

    def _falha(*_a, **_k):
        raise RuntimeError("sem ligação")

    monkeypatch.setattr(servico, "ler_max_obrano", _falha)

    automacao = _AutomacaoFalsa()
    resultado = servico.registar_proposta_no_phc(
        None,
        ano=2026,
        num_cliente_phc="35",
        ref_cliente="25100010",
        designacao="Obra: 25100010",
        automation=automacao,
    )

    assert resultado.numero_confirmado is None
    assert resultado.precisa_confirmacao_manual is True
    assert "sem ligação" in (resultado.erro_leitura or "")
    # Mesmo sem SQL, a proposta foi criada no PHC.
    assert len(automacao.chamadas) == 1


def test_registar_propaga_avisos_de_campos_trocados(monkeypatch):
    from app.services import registar_proposta_phc_service as servico

    monkeypatch.setattr(
        servico, "ler_max_obrano", lambda *a, **k: 805
    )
    monkeypatch.setattr(
        servico,
        "localizar_proposta_criada",
        lambda *a, **k: _proposta(ref=None),
    )
    monkeypatch.setattr(servico, "ler_designacoes_proposta", lambda *a, **k: [])

    resultado = servico.registar_proposta_no_phc(
        None,
        ano=2026,
        num_cliente_phc="35",
        ref_cliente="25100010",
        designacao="Obra: 25100010",
        automation=_AutomacaoFalsa(),
    )

    assert resultado.numero_confirmado == 806
    assert len(resultado.avisos) == 2
