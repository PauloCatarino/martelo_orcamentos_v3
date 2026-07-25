"""Tests for the pure parts of the PHC proposal-automation service.

The pywinauto execution can only run with the real PHC window open, so these
tests cover the deterministic keystroke *plan* and the designation helper.
"""

from __future__ import annotations

import pytest

from app.services.phc_automation_service import (
    PAUSA_APOS_CLIENTE,
    PAUSA_CURTA,
    TABS_CLIENTE_ATE_REF,
    TABS_REF_ATE_DESIGNACAO,
    TECLA_NOVA_PROPOSTA,
    PassoEsperarPronto,
    PassoPausa,
    PassoTeclas,
    PassoTexto,
    _escape_literal,
    construir_designacao,
    construir_plano,
    descrever_plano,
    formatar_num_cliente_phc,
)


def test_formatar_num_cliente_phc_preenche_ate_4_digitos():
    assert formatar_num_cliente_phc("35") == "0035"
    assert formatar_num_cliente_phc("3") == "0003"
    assert formatar_num_cliente_phc("7") == "0007"
    assert formatar_num_cliente_phc("035") == "0035"
    assert formatar_num_cliente_phc("0035") == "0035"


def test_formatar_num_cliente_phc_nao_corta_numeros_grandes():
    assert formatar_num_cliente_phc("1234") == "1234"
    assert formatar_num_cliente_phc("12345") == "12345"


def test_formatar_num_cliente_phc_ignora_nao_numericos_e_vazios():
    assert formatar_num_cliente_phc("") == ""
    assert formatar_num_cliente_phc(None) == ""
    assert formatar_num_cliente_phc(" 35 ") == "0035"
    assert formatar_num_cliente_phc("AB12") == "AB12"


def test_plano_escreve_num_cliente_com_4_digitos():
    plano = construir_plano(
        num_cliente_phc="35", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    textos = [p.texto for p in plano if isinstance(p, PassoTexto)]
    assert textos[0] == "0035"


def test_construir_designacao_com_ref():
    assert construir_designacao("2510008") == "Obra: 2510008"


def test_construir_designacao_sem_ref():
    assert construir_designacao("") == "Obra:"
    assert construir_designacao(None) == "Obra:"
    assert construir_designacao("  ") == "Obra:"


def _textos(plano):
    return [p.texto for p in plano if isinstance(p, PassoTexto)]


def _teclas(plano):
    return [p.keys for p in plano if isinstance(p, PassoTeclas)]


def test_plano_comeca_com_nova_proposta():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    assert isinstance(plano[0], PassoTeclas)
    assert plano[0].keys == TECLA_NOVA_PROPOSTA


def test_plano_escreve_cliente_ref_e_designacao_por_ordem():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    assert _textos(plano) == ["0035", "2510008", "Obra: 2510008"]


def test_plano_confirma_cliente_com_enter():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    assert "{ENTER}" in _teclas(plano)


def test_plano_usa_contagem_de_tabs_configurada():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    teclas = _teclas(plano)
    assert f"{{TAB {TABS_CLIENTE_ATE_REF}}}" in teclas
    assert f"{{TAB {TABS_REF_ATE_DESIGNACAO}}}" in teclas


def test_plano_sem_ref_nao_escreve_ref_mas_mantem_tabs():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="", designacao="Obra:"
    )
    assert _textos(plano) == ["0035", "Obra:"]
    teclas = _teclas(plano)
    assert f"{{TAB {TABS_REF_ATE_DESIGNACAO}}}" in teclas


def test_plano_exige_numero_cliente():
    with pytest.raises(ValueError):
        construir_plano(num_cliente_phc="  ", ref_cliente="x", designacao="Obra:")


def test_plano_tem_pausa_apos_nova_proposta():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    # O passo logo a seguir ao ALT+N é uma pausa.
    assert isinstance(plano[1], PassoPausa)


def test_escape_literal_protege_caracteres_especiais():
    assert _escape_literal("a+b(c)") == "a{+}b{(}c{)}"
    assert _escape_literal("Obra: 2510008") == "Obra: 2510008"


def test_plano_pausa_depois_de_cada_escrita_e_tabs():
    """Cada escrita/TAB é seguida de pausa — o PHC precisa de acompanhar."""
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    for indice, passo in enumerate(plano[:-1]):
        if isinstance(passo, (PassoTexto, PassoTeclas)):
            seguinte = plano[indice + 1]
            assert isinstance(seguinte, PassoPausa), (
                f"passo {indice} ({passo}) não é seguido de pausa"
            )


def test_plano_espera_pelo_phc_antes_de_gravar():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    assert isinstance(plano[-1], PassoEsperarPronto)
    assert isinstance(plano[-2], PassoPausa)


# -- Espera pela tradução do nº de cliente em nome -------------------------


def test_plano_espera_mais_depois_de_confirmar_o_cliente():
    """O PHC vai à BD buscar o nome; avançar cedo perde os TABs seguintes."""
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    indice_enter = next(
        i
        for i, p in enumerate(plano)
        if isinstance(p, PassoTeclas) and p.keys == "{ENTER}"
    )
    seguinte = plano[indice_enter + 1]
    assert isinstance(seguinte, PassoPausa)
    assert seguinte.segundos == PAUSA_APOS_CLIENTE
    # A pausa do cliente é a mais longa das pausas entre campos.
    assert seguinte.segundos > PAUSA_CURTA
    # E é seguida de espera ativa até o PHC acalmar.
    assert isinstance(plano[indice_enter + 2], PassoEsperarPronto)


def test_plano_espera_ativa_nos_momentos_criticos():
    """Abertura da proposta, tradução do cliente e antes de gravar."""
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    esperas = [p for p in plano if isinstance(p, PassoEsperarPronto)]
    assert len(esperas) == 3


def test_esperar_phc_pronto_sem_ligacao_nao_rebenta():
    """Sem app ligada (ou sem medição de CPU), segue em frente."""
    from app.services.phc_automation_service import PhcAutomationService

    servico = PhcAutomationService()
    assert servico._app is None
    servico._esperar_phc_pronto()  # não deve levantar


def test_esperar_phc_pronto_usa_o_limiar_configurado():
    from app.services.phc_automation_service import (
        CPU_ESPERA_MAXIMA,
        CPU_OCIOSO_PERCENTAGEM,
        PhcAutomationService,
    )

    recebido: dict[str, float] = {}

    class _AppFalsa:
        def wait_cpu_usage_lower(self, *, threshold, timeout):
            recebido["threshold"] = threshold
            recebido["timeout"] = timeout

    servico = PhcAutomationService()
    servico._app = _AppFalsa()
    servico._esperar_phc_pronto()

    assert recebido["threshold"] == CPU_OCIOSO_PERCENTAGEM
    assert recebido["timeout"] == CPU_ESPERA_MAXIMA


def test_esperar_phc_pronto_tolera_falha_da_medicao():
    from app.services.phc_automation_service import PhcAutomationService

    class _AppQueFalha:
        def wait_cpu_usage_lower(self, **_kwargs):
            raise RuntimeError("sem contadores de CPU")

    servico = PhcAutomationService()
    servico._app = _AppQueFalha()
    servico._esperar_phc_pronto()  # não deve levantar


def test_descrever_plano_mostra_as_esperas():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    assert "PHC pronto" in descrever_plano(plano)


def test_gravar_usa_alt_g():
    from app.services.phc_automation_service import TECLA_GRAVAR

    assert TECLA_GRAVAR == "%g"


def test_descrever_plano_menciona_textos():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    descricao = descrever_plano(plano)
    assert "0035" in descricao
    assert "Obra: 2510008" in descricao


# -- Diagnóstico e avisos do pywinauto -------------------------------------


def test_diagnostico_desligado_por_omissao():
    """Ler a árvore de controlos só serve para depurar — o nº vem do SQL."""
    from app.services.phc_automation_service import PhcAutomationService

    assert PhcAutomationService().diagnostico is False
    assert PhcAutomationService(diagnostico=True).diagnostico is True


def test_sem_avisos_pywinauto_silencia_userwarning():
    import warnings as _w

    from app.services.phc_automation_service import _sem_avisos_pywinauto

    with _w.catch_warnings(record=True) as capturados:
        _w.simplefilter("always")
        with _sem_avisos_pywinauto():
            _w.warn_explicit(
                "32-bit application should be automated using 32-bit Python",
                UserWarning,
                "pywinauto/application.py",
                1085,
                module="pywinauto.application",
            )
    assert capturados == []


def test_sem_avisos_pywinauto_nao_engole_outros_avisos():
    """Só os do pywinauto são silenciados; o resto continua visível."""
    import warnings as _w

    from app.services.phc_automation_service import _sem_avisos_pywinauto

    with _w.catch_warnings(record=True) as capturados:
        _w.simplefilter("always")
        with _sem_avisos_pywinauto():
            _w.warn("aviso da nossa aplicação", UserWarning)
    assert len(capturados) == 1
