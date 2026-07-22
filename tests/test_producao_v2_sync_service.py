"""Tests for the temporary V2 -> V3 production comparison helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.producao import Producao
from app.services import producao_v2_sync_service as sync


def _linha_v2(**overrides) -> dict:
    linha = {
        "codigo_processo": "26.1134_01_01_JF_VIVA",
        "ano": "2026",
        "num_enc_phc": "1134",
        "versao_obra": "01",
        "versao_plano": "01",
        "estado": "Planeamento",
        "responsavel": "Paulo",
        "nome_cliente": "MÓVEIS J.F. VIVA",
        "nome_cliente_simplex": "JF_VIVA",
        "num_cliente_phc": "35",
        "ref_cliente": "2507018",
        "data_inicio": "25-06-2026",
        "data_entrega": "10-08-2026",
        "preco_total": Decimal("1000.00"),
        "tipo_pasta": "Encomenda de Cliente",
    }
    linha.update(overrides)
    return linha


def _processo_v3(**overrides) -> Producao:
    processo = Producao(
        codigo_processo="26.1134_01_01_JF_VIVA",
        ano="2026",
        num_enc_phc="1134",
        versao_obra="01",
        versao_plano="01",
        estado="Desenho",
        responsavel="Paulo",
        nome_cliente="MÓVEIS J.F. VIVA",
        nome_cliente_simplex="JF_VIVA",
        num_cliente_phc="35",
        ref_cliente="2507018",
        data_inicio="25-06-2026",
        data_entrega="10-08-2026",
        preco_total=Decimal("1000.00"),
        tipo_pasta="Encomenda de Cliente",
    )
    for campo, valor in overrides.items():
        setattr(processo, campo, valor)
    return processo


def test_mapear_estado_planeamento_para_desenho() -> None:
    assert sync.mapear_estado("Planeamento") == "Desenho"
    assert sync.mapear_estado("Arquivado") == "Arquivado"
    assert sync.mapear_estado(None) is None


def test_mapear_linha_normaliza_datas_e_estado() -> None:
    valores = sync.mapear_linha(_linha_v2(data_entrega="2026-08-10"))

    assert valores["estado"] == "Desenho"
    assert valores["data_entrega"] == "10-08-2026"
    assert "id" not in valores


def test_difere_ignora_diferencas_so_de_formato_numerico() -> None:
    assert sync._difere("1000.00", Decimal("1000")) is False
    assert sync._difere("  Paulo ", "Paulo") is False
    assert sync._difere("Paulo", "Ana") is True
    assert sync._difere(None, "Ana") is True


def test_comparar_linhas_marca_obra_nova(session) -> None:
    comparacao = sync.comparar_linhas(session, [_linha_v2()])

    assert comparacao.total_v2 == 1
    assert len(comparacao.obras_novas) == 1
    assert comparacao.obras_novas[0].codigo_processo == "26.1134_01_01_JF_VIVA"
    assert comparacao.diferencas == []


def test_comparar_linhas_sem_diferencas(session) -> None:
    session.add(_processo_v3())
    session.commit()

    comparacao = sync.comparar_linhas(session, [_linha_v2()])

    assert comparacao.obras_novas == []
    assert comparacao.diferencas == []
    assert comparacao.sem_alteracoes == 1


def test_comparar_linhas_lista_campos_diferentes(session) -> None:
    session.add(_processo_v3(responsavel="Ana", obra=None))
    session.commit()

    comparacao = sync.comparar_linhas(
        session,
        [_linha_v2(responsavel="Paulo", obra="COZINHA")],
    )

    campos = {diferenca.campo for diferenca in comparacao.diferencas}
    assert campos == {"responsavel", "obra"}

    por_campo = {diferenca.campo: diferenca for diferenca in comparacao.diferencas}
    # V3 tem valor -> não vem marcado por defeito; V3 vazio -> vem marcado.
    assert por_campo["responsavel"].v3_vazio is False
    assert por_campo["obra"].v3_vazio is True
    assert por_campo["obra"].texto_v3 == "(vazio)"
    assert por_campo["responsavel"].rotulo == "Responsável"


def test_aplicar_selecao_so_altera_o_que_foi_escolhido(session) -> None:
    session.add(_processo_v3(responsavel="Ana", obra=None))
    session.commit()

    comparacao = sync.comparar_linhas(
        session,
        [_linha_v2(responsavel="Paulo", obra="COZINHA")],
    )
    escolhidas = [d for d in comparacao.diferencas if d.campo == "obra"]

    resultado = sync.aplicar_selecao(session, diferencas=escolhidas)

    processo = session.query(Producao).one()
    assert resultado.campos_atualizados == 1
    assert processo.obra == "COZINHA"
    assert processo.responsavel == "Ana"  # não escolhido: o V3 prevalece


def test_aplicar_selecao_cria_obra_nova(session) -> None:
    comparacao = sync.comparar_linhas(session, [_linha_v2()])

    resultado = sync.aplicar_selecao(session, obras_novas=comparacao.obras_novas)

    processo = session.query(Producao).one()
    assert resultado.criados == 1
    assert processo.codigo_processo == "26.1134_01_01_JF_VIVA"
    assert processo.estado == "Desenho"


def test_criar_engine_v2_sem_credenciais(monkeypatch) -> None:
    for chave in ("V2_DATABASE_URL", "V2_DB_USER", "V2_DB_PASSWORD"):
        monkeypatch.delenv(chave, raising=False)

    with pytest.raises(sync.ProducaoV2ConfigError):
        sync.criar_engine_v2()
