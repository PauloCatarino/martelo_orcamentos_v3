"""Regras do passo Desenho → Aprovisionamento do Escritório (Streamlit).

As strings comparadas aqui são o contrato com o Streamlit: o teste do Leitor
(``descrever_evento``) compara-as letra a letra do lado de lá.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, timezone
from types import SimpleNamespace

import pytest

from app.domain import escritorio_streamlit as regras
from app.domain.escritorio_streamlit import (
    DadosEscritorio,
    UtilizadorStreamlit,
    avaliar_envio,
    chave_versao,
)

# --------------------------------------------------------------------------
# Chave do modelo/versão
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("numero", "esperado"),
    [
        ("599", "0599"),  # 18 obras do Martelo real estavam assim
        ("0599", "0599"),
        ("1497", "1497"),
        ("_1", "_001"),
        ("_253", "_253"),
        ("a7", "A007"),
        ("A187", "A187"),
    ],
)
def test_numero_canonico(numero, esperado) -> None:
    assert regras.numero_canonico(numero) == esperado


@pytest.mark.parametrize("numero", ["", None, "12a", "_", "X12", "1 2"])
def test_numero_invalido(numero) -> None:
    with pytest.raises(ValueError):
        regras.numero_canonico(numero)


def test_bd_key_como_no_streamlit() -> None:
    assert chave_versao("2026", "599", "5", "1").bd_key == "2026_0599_05_01"
    # Obras do Criar Encomendas: dois «_» seguidos (o separador e o prefixo).
    assert chave_versao("2026", "_1", "01", "01").bd_key == "2026__001_01_01"


def test_tabelas_gemeas_so_nas_obras_com_underscore() -> None:
    assert chave_versao("2026", "_253", "01", "01").sufixo == "_"
    assert chave_versao("2026", "1497", "02", "01").sufixo == ""


@pytest.mark.parametrize(
    ("ano", "modelo", "versao"),
    [("26", "01", "01"), ("2026", "0", "01"), ("2026", "01", "100"), ("2026", "", "01")],
)
def test_chave_invalida(ano, modelo, versao) -> None:
    with pytest.raises(ValueError):
        chave_versao(ano, "1497", modelo, versao)


# --------------------------------------------------------------------------
# Material, avisos, datas
# --------------------------------------------------------------------------


def test_material_so_do_cliente_com_orla_do_cliente() -> None:
    ce = {"bd_placas_cl": True, "bd_placas_le": False, "bd_placas_ambos": False,
          "bd_de_quem_orla_cl": True, "bd_de_quem_orla_le": False,
          "bd_de_quem_orla_ambos": False}
    assert regras.material_so_do_cliente(ce) == "placas: Cliente · orla: Cliente"


def test_material_so_do_cliente_sem_orla_indicada() -> None:
    ce = {"bd_placas_cl": True, "bd_placas_le": False, "bd_placas_ambos": None}
    assert regras.material_so_do_cliente(ce) == "placas: Cliente · orla: não indicada"


@pytest.mark.parametrize(
    "ce",
    [
        {"bd_placas_cl": True, "bd_de_quem_orla_ambos": True},  # a orla compra-se
        {"bd_placas_cl": True, "bd_de_quem_orla_le": True},
        {"bd_placas_cl": True, "bd_placas_ambos": True},
        {"bd_placas_le": True},
        {},
        None,
    ],
)
def test_material_com_compras_passa_pelo_aprovisionamento(ce) -> None:
    assert regras.material_so_do_cliente(ce) == ""


@pytest.mark.parametrize("valor", [True, 1, "1", "true", "Sim", "s", "YES", "on"])
def test_verdadeiro(valor) -> None:
    assert regras.verdadeiro(valor) is True


@pytest.mark.parametrize("valor", [False, 0, None, "", "0", "nao", "N"])
def test_falso(valor) -> None:
    assert regras.verdadeiro(valor) is False


@pytest.mark.parametrize(
    ("status", "ok"),
    [
        ("🟢 ENVIADO", True),
        ("🔴 NAO ENVIADO", False),
        ("🔴 NÃO ENVIADO", False),
        ("🔴 NÃO CRIADO", False),
        ("🟠 DESATUALIZADO", False),
        ("", False),
        (None, False),
    ],
)
def test_envio_ok(status, ok) -> None:
    assert regras.envio_ok(status) is ok


def test_avisos_como_no_streamlit() -> None:
    assert regras.avisos_do_envio({"tem_materias": 0}, {}) == (
        "sem plano de corte",
        "sem materiais calculados",
    )
    assert regras.avisos_do_envio(
        {"tem_materias": 1}, {"bd_plano_corte": "P1", "bd_status_envio": "🔴 NAO ENVIADO"}
    ) == ("plano de corte não enviado",)
    assert regras.avisos_do_envio(
        {"tem_materias": 1}, {"bd_plano_corte": "P1", "bd_status_envio": "🟢 ENVIADO"}
    ) == ()


def test_datas_vem_em_utc_e_mostram_se_na_hora_local() -> None:
    assert regras.data_local("2026-10-28T14:30:35", fuso=timezone.utc) == "28/10/2026 14:30"
    assert regras.data_local(None) == ""
    assert regras.data_local("lixo") == ""


# --------------------------------------------------------------------------
# Quem clica
# --------------------------------------------------------------------------


def _utilizadores() -> list[UtilizadorStreamlit]:
    """Os nomes reais do Streamlit (28-10-2026), resumidos."""
    linhas = [
        {"username": "admin", "nome": "Adriano", "is_admin": True, "ativo": True,
         "local_trabalho": None, "permissoes": '["Escritorio_ALL"]'},
        {"username": "ana.felix", "nome": "Ana Félix", "ativo": True,
         "local_trabalho": "Escritório - Desenho", "permissoes": "[]"},
        {"username": "marcia.silva", "nome": "Márcia Silva", "ativo": True,
         "local_trabalho": "Escritório - Desenho", "permissoes": "[]"},
        {"username": "paulo_catarino", "nome": "Paulo Catarino", "ativo": True,
         "local_trabalho": "Escritório - Desenho", "permissoes": "[]"},
        {"username": "pedro", "nome": "Pedro Reis", "ativo": True,
         "local_trabalho": "Escritório - Desenho", "permissoes": "[]"},
        {"username": "elisabete", "nome": "Elisabete Vieira", "ativo": True,
         "local_trabalho": "Escritório - Orçamentos", "permissoes": "[]"},
        {"username": "dulce.faria", "nome": "Dulce Faria", "ativo": True,
         "local_trabalho": "Escritório - Aprovisionamento", "permissoes": "[]"},
        {"username": "velho", "nome": "Pedro Antigo", "ativo": False,
         "local_trabalho": "Escritório - Desenho", "permissoes": "[]"},
    ]
    locais = [
        {"Nome": "Escritório - Desenho", "Permissoes": '["Escritorio_Desenhos"]', "Ativo": True},
        {"Nome": "Escritório - Orçamentos", "Permissoes": '["Escritorio_Consulta"]', "Ativo": True},
    ]
    return regras.utilizadores_streamlit(linhas, locais)


@pytest.mark.parametrize(
    ("username", "nome", "esperado"),
    [
        ("Ana", "Ana", "ana.felix"),
        ("Marcia", "Marcia", "marcia.silva"),  # sem acento no Martelo
        ("paulo", "Paulo Catarino", "paulo_catarino"),
        ("Pedro", "Pedro", "pedro"),  # o «Pedro Antigo» está inativo
    ],
)
def test_resolver_utilizador_pelo_nome(username, nome, esperado) -> None:
    utilizador, mensagem = regras.resolver_utilizador(username, nome, _utilizadores())
    assert mensagem == ""
    assert utilizador.username == esperado


def test_o_admin_do_martelo_nao_e_o_admin_do_streamlit() -> None:
    utilizador, mensagem = regras.resolver_utilizador(
        "admin", "Administrador Martelo", _utilizadores()
    )
    assert utilizador is None
    assert "streamlit_mapa_utilizadores" in mensagem


def test_mapa_manual_ganha_a_tudo() -> None:
    mapa = regras.ler_mapa_utilizadores("admin = paulo_catarino; Ana=ana.felix")
    utilizador, _ = regras.resolver_utilizador(
        "admin", "Administrador Martelo", _utilizadores(), mapa
    )
    assert utilizador.username == "paulo_catarino"


def test_mapa_manual_com_nome_que_nao_existe() -> None:
    utilizador, mensagem = regras.resolver_utilizador(
        "Ana", "Ana", _utilizadores(), {"ana": "nao.existe"}
    )
    assert utilizador is None
    assert "nao.existe" in mensagem


def test_permissoes_vem_tambem_do_local() -> None:
    por_nome = {u.username: u for u in _utilizadores()}
    assert por_nome["pedro"].pode_enviar  # pelo Local «Escritório - Desenho»
    assert por_nome["admin"].pode_enviar
    assert not por_nome["elisabete"].pode_enviar  # Escritorio_Consulta só lê
    assert not por_nome["dulce.faria"].pode_enviar


# --------------------------------------------------------------------------
# A decisão, pela ordem do Streamlit
# --------------------------------------------------------------------------


def _chave(numero="1497", modelo="02", versao="01"):
    return chave_versao("2026", numero, modelo, versao)


def _pedro():
    return next(u for u in _utilizadores() if u.username == "pedro")


def _dados(**kw) -> DadosEscritorio:
    base = {
        "obra": {"estado_obra": "COM_DESENHO", "desenhador_username": "pedro"},
        "versao": None,
        "ce": {"bd_ano": "2026", "bd_n_encomenda": "1497", "bd_cliente": "CRW",
               "tem_materias": 1, "bd_placas_le": True},
        "tp": {"bd_plano_corte": "1497_02_01_26_CRW", "bd_status_envio": "🟢 ENVIADO"},
        "utilizadores": tuple(_utilizadores()),
    }
    base.update(kw)
    return DadosEscritorio(**base)


def test_caso_feliz() -> None:
    avaliacao = avaliar_envio(_chave(), _dados(), _pedro())
    assert avaliacao.pronto
    assert avaliacao.utilizador == "pedro"
    assert avaliacao.desenhador == "pedro"
    assert avaliacao.em_nome_de == ""
    assert avaliacao.avisos == ()
    assert avaliacao.material_cliente == ""
    assert avaliacao.plano_corte == "1497_02_01_26_CRW"


@pytest.mark.parametrize(
    ("chave", "motivo", "texto"),
    [
        (("A012", "01", "01"), "assistencia", "assistências"),
        (("1497", "02", "02"), "versao", "Só a versão 01"),
    ],
)
def test_recusas_sem_servidor(chave, motivo, texto) -> None:
    avaliacao = avaliar_envio(chave_versao("2026", *chave), DadosEscritorio(), None)
    assert avaliacao.resultado == regras.RECUSADO
    assert avaliacao.motivo_recusa == motivo
    assert texto in avaliacao.mensagem
    assert avaliacao.discreta


@pytest.mark.parametrize(
    ("obra", "texto", "discreta"),
    [
        (None, "ainda não está no Escritório", True),
        ({"estado_obra": "POR_DECIDIR"}, "ainda não está no Escritório", True),
        ({"estado_obra": "SEM_DESENHO"}, "sem desenho", True),
        ({"estado_obra": "ARQUIVADA"}, "retirada do Escritório", False),
        ({"estado_obra": "COM_DESENHO", "desenhador_username": None}, "sem desenhador", False),
    ],
)
def test_estado_da_obra(obra, texto, discreta) -> None:
    avaliacao = avaliar_envio(_chave(), _dados(obra=obra), _pedro())
    assert avaliacao.resultado == regras.RECUSADO
    assert texto in avaliacao.mensagem
    assert avaliacao.discreta is discreta


def test_assistencia_marcada_no_tempos_de_producao() -> None:
    avaliacao = avaliar_envio(
        _chave(), _dados(tp={"bd_assistencia": True}), _pedro()
    )
    assert avaliacao.motivo_recusa == "assistencia"


def test_obra_de_outro_desenhador() -> None:
    ana = next(u for u in _utilizadores() if u.username == "ana.felix")
    avaliacao = avaliar_envio(_chave(), _dados(), ana)
    assert avaliacao.motivo_recusa == "dono"
    assert avaliacao.mensagem == (
        "Esta obra está atribuída a Pedro Reis. Peça a Orçamentos para a reatribuir."
    )


def test_administrador_envia_em_nome_do_desenhador() -> None:
    admin = next(u for u in _utilizadores() if u.username == "admin")
    avaliacao = avaliar_envio(_chave(), _dados(), admin)
    assert avaliacao.pronto
    assert avaliacao.em_nome_de == "pedro"


def test_so_consulta_nao_envia() -> None:
    elisabete = next(u for u in _utilizadores() if u.username == "elisabete")
    avaliacao = avaliar_envio(
        _chave(),
        _dados(obra={"estado_obra": "COM_DESENHO", "desenhador_username": "elisabete"}),
        elisabete,
    )
    assert avaliacao.motivo_recusa == "utilizador"


def test_utilizador_desconhecido_leva_a_mensagem_da_resolucao() -> None:
    avaliacao = avaliar_envio(_chave(), _dados(), None, "Não encontrei «admin»")
    assert avaliacao.mensagem == "Não encontrei «admin»"


def test_sem_caderno_de_encargos_e_bloqueio_duro() -> None:
    avaliacao = avaliar_envio(_chave(), _dados(ce=None), _pedro())
    assert avaliacao.mensagem == (
        "Falta criar o Caderno de Encargos desta versão (no Streamlit) antes de a enviar."
    )
    assert not avaliacao.discreta


def test_ja_enviado_diz_quem_quando_e_por_onde() -> None:
    avaliacao = avaliar_envio(
        _chave(),
        _dados(
            versao={"etapa": "APROVISIONAMENTO", "desenho_concluido_por": "pedro",
                    "desenho_concluido_em": "2026-10-28T14:30:35"},
            ultimo_avanco={"utilizador": "pedro", "detalhe": json.dumps({"via": "MARTELO"})},
        ),
        _pedro(),
    )
    assert avaliacao.resultado == regras.JA_ENVIADO
    assert "por pedro (via MARTELO)" in avaliacao.mensagem
    assert avaliacao.discreta


def test_ja_libertado() -> None:
    avaliacao = avaliar_envio(_chave(), _dados(versao={"etapa": "LIBERTADA"}), _pedro())
    assert avaliacao.mensagem == "Este modelo/versão já foi libertado para a fábrica."


def test_sem_linha_da_versao_vale_como_desenho() -> None:
    assert avaliar_envio(_chave(), _dados(versao=None), _pedro()).pronto
    assert avaliar_envio(_chave(), _dados(versao={"etapa": "DESENHO"}), _pedro()).pronto


def test_avisos_e_material_seguem_na_avaliacao() -> None:
    avaliacao = avaliar_envio(
        _chave(),
        _dados(ce={"tem_materias": 0, "bd_placas_cl": True}, tp={}),
        _pedro(),
    )
    assert avaliacao.pronto
    assert avaliacao.avisos == ("sem plano de corte", "sem materiais calculados")
    assert avaliacao.material_cliente == "placas: Cliente · orla: não indicada"


# --------------------------------------------------------------------------
# O que fica gravado (contrato com o Streamlit)
# --------------------------------------------------------------------------


def test_espelho_igual_dos_dois_lados() -> None:
    assert regras.texto_espelho(
        regras.ROTULO_AVANCAR, via=regras.VIA_MARTELO, motivo=regras.MOTIVO_AVANCAR
    ) == "Desenho → Aprovisionamento · via MARTELO · motivo: Desenho concluído."
    assert regras.texto_espelho(
        regras.ROTULO_LIBERTAR_AUTO,
        via=regras.VIA_MARTELO,
        motivo=regras.MOTIVO_LIBERTAR_AUTO,
    ) == (
        "Libertada automaticamente · via MARTELO · motivo: Placas e orla só do "
        "cliente: sem compras, não passa pelo Aprovisionamento."
    )
    # O que o Streamlit grava hoje, sem via:
    assert regras.texto_espelho(regras.ROTULO_AVANCAR) == "Desenho → Aprovisionamento"
    assert "\u2192" in regras.ROTULO_AVANCAR


def test_detalhe_avancar() -> None:
    detalhe = regras.detalhe_avancar(
        _chave("599", "05", "01"),
        versao_programa="1.0.30",
        posto="PC-PAULO",
        em_nome_de="pedro",
        avisos_aceites=["sem plano de corte"],
        pasta=r"\\SERVER_LE\obra",
    )
    assert detalhe == {
        "mensagem": "Obra 0599: 1 modelo/versão enviado(s) para o Aprovisionamento pelo MARTELO.",
        "via": "MARTELO",
        "versao_programa": "1.0.30",
        "posto": "PC-PAULO",
        "em_nome_de": "pedro",
        "avisos_aceites": ["sem plano de corte"],
        "pasta": r"\\SERVER_LE\obra",
    }
    # Os opcionais só aparecem quando existem.
    assert set(regras.detalhe_avancar(_chave())) == {"mensagem", "via"}
    # JSON válido, com os acentos tal e qual.
    assert "ã" in regras.json_detalhe({"x": "não"})
    json.loads(regras.json_detalhe(detalhe))


def test_detalhe_libertar_auto() -> None:
    detalhe = regras.detalhe_libertar_auto(
        _chave("599", "05", "01"),
        material="placas: Cliente · orla: Cliente",
        acionado_por="pedro",
    )
    assert detalhe["mensagem"] == (
        "Versão 05/01 libertada automaticamente (material só do cliente)."
    )
    assert detalhe["automatico"] is True
    assert detalhe["via"] == "MARTELO"
    assert detalhe["acionado_por"] == "pedro"


def test_id_filho_e_sempre_o_mesmo_para_o_mesmo_clique() -> None:
    clique = regras.novo_command_id()
    assert regras.id_filho(clique, "2026_0599_05_01") == regras.id_filho(
        clique, "2026_0599_05_01"
    )
    assert regras.id_filho(clique, "2026_0599_05_01") != clique
    esperado = uuid.uuid5(uuid.UUID(clique), "libertar_auto:2026_0599_05_01")
    assert regras.id_filho(clique, "2026_0599_05_01") == str(esperado)


def test_mensagem_de_sucesso() -> None:
    assert regras.mensagem_sucesso(_chave("599", "05", "01")) == (
        "✔ Modelo 05 · Versão 01 enviado para o Aprovisionamento."
    )


# --------------------------------------------------------------------------
# Sentido contrário: o Streamlit avançou, o Martelo ainda diz Desenho
# --------------------------------------------------------------------------


def _obra(id_, num, estado="Desenho", modelo="01", versao="01", responsavel="Pedro"):
    return SimpleNamespace(
        id=id_, codigo_processo=f"26.{num}_{modelo}_{versao}_CLIENTE", ano="2026",
        num_enc_phc=num, versao_obra=modelo, versao_plano=versao, estado=estado,
        nome_cliente="Cliente", responsavel=responsavel, data_entrega="", ref_cliente="",
    )


def test_sugere_producao_so_para_obras_em_desenho_ja_avancadas() -> None:
    versoes = {
        "2026_1098_01_01": {"etapa": "LIBERTADA", "libertada_por": "dulce.faria",
                            "libertada_em": "2026-10-22T16:05:00"},
        "2026_1712_01_01": {"etapa": "APROVISIONAMENTO", "desenho_concluido_por": "ruben",
                            "desenho_concluido_em": "2026-10-16T09:36:00"},
        "2026_0555_01_01": {"etapa": "APROVISIONAMENTO"},
    }
    obras = [
        _obra(1, "1098"),
        _obra(2, "1712"),
        _obra(3, "555", estado="Producao"),  # já está: nada a sugerir
        _obra(4, "1999"),  # o Escritório não a conhece
        _obra(5, "1098", estado="Arquivado"),  # nunca recua
    ]
    sugestoes = regras.sugestoes_de_producao(obras, versoes, fuso=timezone.utc)
    assert [s["id"] for s in sugestoes] == [1, 2]
    assert sugestoes[0]["estado_sugerido"] == "Producao"
    assert sugestoes[0]["fonte"] == "Escritório"
    assert sugestoes[0]["estado_phc_raw"] == (
        "Libertado para a fábrica desde 22/10/2026 16:05 (dulce.faria)"
    )
    assert sugestoes[1]["estado_phc_raw"] == (
        "No Aprovisionamento desde 16/10/2026 09:36 (ruben)"
    )
    assert sugestoes[0]["marca"] == "2026_1098_01_01|LIBERTADA"


def test_numero_nao_canonico_do_martelo_tambem_casa() -> None:
    sugestoes = regras.sugestoes_de_producao(
        [_obra(1, "599")], {"2026_0599_01_01": {"etapa": "APROVISIONAMENTO"}}
    )
    assert [s["bd_key"] for s in sugestoes] == ["2026_0599_01_01"]


def test_recusadas_e_adiadas_nao_voltam() -> None:
    hoje = date(2026, 10, 28)
    sugestoes = [{"marca": "a|LIBERTADA"}, {"marca": "b|APROVISIONAMENTO"}, {"marca": "c|X"}]
    vistos = {"a|LIBERTADA": "sempre", "b|APROVISIONAMENTO": "2026-10-28"}
    assert regras.por_mostrar(sugestoes, vistos, hoje) == [{"marca": "c|X"}]
    # «Ver depois» de ontem volta hoje.
    vistos = {"b|APROVISIONAMENTO": "2026-10-27"}
    assert len(regras.por_mostrar(sugestoes, vistos, hoje)) == 3
