"""Tests for production-process filtering."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.producao_service import filtrar_processos


def _processo(**overrides) -> SimpleNamespace:
    base = {
        "codigo_processo": "26.1028_01_01",
        "num_enc_phc": "1028",
        "nome_cliente": "Cliente Alfa",
        "nome_cliente_simplex": "cliente alfa",
        "ref_cliente": "REF-A",
        "obra": "Cozinha Lisboa",
        "localizacao": "Lisboa",
        "num_orcamento": "260001",
        "responsavel": "ana",
        "descricao_producao": "Moveis lacados",
        "estado": "Desenho",
        "data_entrega": "",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_filtrar_processos_pesquisa_multi_termo() -> None:
    processos = [
        _processo(nome_cliente="Cliente Alfa", obra="Cozinha Lisboa"),
        _processo(
            nome_cliente="Cliente Beta",
            obra="Roupeiro Porto",
            localizacao="Porto",
        ),
    ]

    assert filtrar_processos(processos, texto="cliente LISBOA") == [processos[0]]
    assert filtrar_processos(processos, texto="1028%lacados") == processos


def test_filtrar_processos_filtra_por_estado_cliente_responsavel() -> None:
    processos = [
        _processo(estado="Desenho", nome_cliente="Cliente Alfa", responsavel="ana"),
        _processo(estado="Produção", nome_cliente="Cliente Alfa", responsavel="bruno"),
        _processo(estado="Produção", nome_cliente="Cliente Beta", responsavel="ana"),
    ]

    assert filtrar_processos(processos, estado="Produção") == [
        processos[1],
        processos[2],
    ]
    assert filtrar_processos(processos, cliente="Cliente Alfa") == [
        processos[0],
        processos[1],
    ]
    assert filtrar_processos(processos, responsavel="ana") == [
        processos[0],
        processos[2],
    ]
    assert filtrar_processos(
        processos,
        estado="Produção",
        cliente="Cliente Beta",
        responsavel="ana",
    ) == [processos[2]]


def test_filtrar_processos_todos_none_vazio_e_sem_match() -> None:
    processos = [
        _processo(codigo_processo="26.1028_01_01"),
        _processo(codigo_processo="26.1029_01_01"),
    ]

    assert filtrar_processos(
        processos,
        texto="  %% ",
        estado="Todos",
        cliente=None,
        responsavel="",
    ) == processos
    assert filtrar_processos(processos, texto="inexistente") == []


def test_pesquisa_ignora_acentos() -> None:
    """«Márcia» tem de encontrar «Marcia» — a base de dados não tem acentos."""
    obras = [
        _processo(codigo_processo="26.1000_01_01_X", responsavel="Marcia"),
        _processo(codigo_processo="26.1001_01_01_Y", responsavel="Pedro"),
    ]

    assert len(filtrar_processos(obras, texto="Márcia")) == 1
    assert len(filtrar_processos(obras, texto="marcia")) == 1
    # e ao contrário: escrito sem acento tem de achar o que tem acento
    com_acento = [_processo(codigo_processo="26.1002_01_01_Z", obra="MÓVEIS ÂNGULO")]
    assert len(filtrar_processos(com_acento, texto="moveis angulo")) == 1


def test_pesquisa_ignora_pontuacao() -> None:
    """«26.1134_01» tem de encontrar o processo, com ou sem pontos e traços."""
    obras = [_processo(codigo_processo="26.1134_01_01_JF_VIVA", nome_cliente="MÓVEIS J.F. VIVA")]

    assert len(filtrar_processos(obras, texto="26.1134")) == 1
    assert len(filtrar_processos(obras, texto="26 1134")) == 1
    assert len(filtrar_processos(obras, texto="jf-viva")) == 1
    assert len(filtrar_processos(obras, texto="j.f. viva")) == 1
    assert len(filtrar_processos(obras, texto="26.9999")) == 0


def test_filtros_de_combo_tambem_ignoram_acentos() -> None:
    obras = [_processo(codigo_processo="26.1000_01_01_X", responsavel="Marcia")]

    assert len(filtrar_processos(obras, responsavel="Márcia")) == 1


def test_filtro_so_atrasadas_ignora_arquivadas() -> None:
    obras = [
        _processo(codigo_processo="26.1000_01_01_X", data_entrega="01-01-2020", estado="Desenho"),
        _processo(codigo_processo="26.1001_01_01_Y", data_entrega="01-01-2020", estado="Arquivado"),
        _processo(codigo_processo="26.1002_01_01_Z", data_entrega="01-01-2020", estado="Finalizado"),
    ]

    atrasadas = filtrar_processos(obras, so_atrasadas=True)

    # Finalizado continua a contar; só Arquivado sai.
    assert {p.codigo_processo for p in atrasadas} == {
        "26.1000_01_01_X",
        "26.1002_01_01_Z",
    }
