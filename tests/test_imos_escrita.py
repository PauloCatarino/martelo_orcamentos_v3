"""Testes do único canal de escrita do Martelo na base SQL do iMos."""

from __future__ import annotations

import pytest

from app.services import imos_escrita
from app.services.imos_escrita import NoParaCriar
from app.services.imos_sql import (
    IMOS_TIPO_ENCOMENDA,
    IMOS_TIPO_PASTA,
    ImosConfig,
)
from app.services.system_setting_service import SystemSettingService


def _cfg(**overrides) -> ImosConfig:
    cfg: ImosConfig = {
        "server": r"SERVER_LE\SERVER_LE",
        "database": "imos_le",
        "user": "imosadmin",
        "password": "segredo;com;ponto",
        "trusted": False,
        "trust_server_certificate": True,
    }
    cfg.update(overrides)  # type: ignore[typeddict-item]
    return cfg


def _pasta(nome: str, **kwargs) -> NoParaCriar:
    kwargs.setdefault("parent_dir_id", 180)
    return NoParaCriar(nome=nome, tipo=IMOS_TIPO_PASTA, **kwargs)


# --------------------------------------------------------------------------
# Interruptor de segurança
# --------------------------------------------------------------------------


def test_escrita_esta_desligada_por_defeito(session) -> None:
    assert imos_escrita.carregar_escrita_ativa(session) is False
    with pytest.raises(RuntimeError, match="imos_escrita_ativa"):
        imos_escrita.assert_escrita_ativa(session)


@pytest.mark.parametrize("valor", ["ON", "on", "1", "sim", "true"])
def test_escrita_liga_com_o_interruptor(session, valor: str) -> None:
    SystemSettingService(session).guardar_valor(
        imos_escrita.KEY_IMOS_ESCRITA_ATIVA, valor
    )
    assert imos_escrita.carregar_escrita_ativa(session) is True
    imos_escrita.assert_escrita_ativa(session)


def test_criar_nos_nao_toca_no_sql_com_o_interruptor_desligado(
    session, monkeypatch
) -> None:
    chamado = False

    def _executar(_payload):
        nonlocal chamado
        chamado = True
        return []

    monkeypatch.setattr(imos_escrita, "executar_payload", _executar)
    with pytest.raises(RuntimeError):
        imos_escrita.criar_nos(session, _cfg(), [_pasta("ANO_2026")])

    assert chamado is False


# --------------------------------------------------------------------------
# Ligação de escrita
# --------------------------------------------------------------------------


def test_ligacao_de_escrita_nao_pode_ser_read_only() -> None:
    conn = imos_escrita.build_connection_string(_cfg())

    assert "ApplicationIntent" not in conn
    assert 'Password="segredo;com;ponto"' in conn
    assert "TrustServerCertificate=True" in conn


def test_ligacao_de_escrita_exige_credenciais() -> None:
    with pytest.raises(ValueError, match="utilizador"):
        imos_escrita.build_connection_string(_cfg(user=""))
    with pytest.raises(ValueError, match="password"):
        imos_escrita.build_connection_string(_cfg(password=""))


# --------------------------------------------------------------------------
# Validação do que vai ser criado
# --------------------------------------------------------------------------


def test_payload_encadeia_pastas_e_encomenda_na_mesma_transacao() -> None:
    payload = imos_escrita.construir_payload(
        _cfg(),
        [
            _pasta("ANO_2026"),
            NoParaCriar(
                nome="LINHAS_DIREITAS", tipo=IMOS_TIPO_PASTA, parent_indice=0
            ),
            NoParaCriar(
                nome="1260_01_26_LINHAS_DIREITAS",
                tipo=IMOS_TIPO_ENCOMENDA,
                parent_indice=1,
                campos={"COMM": "1260", "CLIENT": "LINHAS_DIREITAS"},
            ),
        ],
    )

    nos = payload["nos"]
    assert [no["nome"] for no in nos] == [
        "ANO_2026",
        "LINHAS_DIREITAS",
        "1260_01_26_LINHAS_DIREITAS",
    ]
    assert nos[0]["parent_dir_id"] == 180 and nos[0]["parent_indice"] is None
    assert nos[1]["parent_indice"] == 0 and nos[1]["parent_dir_id"] is None
    assert nos[2]["parent_indice"] == 1
    assert [campo["coluna"] for campo in nos[2]["campos"]] == ["CLIENT", "COMM"]


def test_payload_recusa_nome_maior_do_que_a_coluna_do_imos() -> None:
    with pytest.raises(ValueError, match="Nome inválido"):
        imos_escrita.construir_payload(_cfg(), [_pasta("A" * 31)])


def test_payload_recusa_tipo_de_no_desconhecido() -> None:
    with pytest.raises(ValueError, match="Tipo de nó não permitido"):
        imos_escrita.construir_payload(
            _cfg(), [NoParaCriar(nome="X", tipo=1000032, parent_dir_id=120)]
        )


@pytest.mark.parametrize(
    "no",
    [
        NoParaCriar(nome="SEM_PAI", tipo=IMOS_TIPO_PASTA),
        NoParaCriar(
            nome="DOIS_PAIS", tipo=IMOS_TIPO_PASTA, parent_dir_id=180, parent_indice=0
        ),
    ],
)
def test_payload_exige_exatamente_um_pai(no: NoParaCriar) -> None:
    with pytest.raises(ValueError, match="exatamente um pai"):
        imos_escrita.construir_payload(_cfg(), [no])


def test_payload_recusa_pai_criado_depois_dele_proprio() -> None:
    with pytest.raises(ValueError, match="ainda não foi criado"):
        imos_escrita.construir_payload(
            _cfg(),
            [
                NoParaCriar(nome="FILHA", tipo=IMOS_TIPO_PASTA, parent_indice=1),
                _pasta("MAE"),
            ],
        )


def test_payload_recusa_lista_vazia() -> None:
    with pytest.raises(ValueError, match="Não há nós"):
        imos_escrita.construir_payload(_cfg(), [])


# --------------------------------------------------------------------------
# Colunas de dbo.PROADMIN
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "coluna", ["ID", "PRODUCTIONID", "NAME", "TYPE", "DATECREATE", "LCHANGE"]
)
def test_colunas_do_motor_nao_podem_vir_do_chamador(coluna: str) -> None:
    with pytest.raises(ValueError, match="gerida pelo motor"):
        imos_escrita.construir_payload(_cfg(), [_pasta("X", campos={coluna: "1"})])


@pytest.mark.parametrize("coluna", ["SENHA", "DROP", "SELECT 1", "COMM; DELETE"])
def test_coluna_desconhecida_e_recusada(coluna: str) -> None:
    with pytest.raises(ValueError, match="Coluna desconhecida"):
        imos_escrita.construir_payload(_cfg(), [_pasta("X", campos={coluna: "1"})])


def test_valor_maior_do_que_a_coluna_e_recusado_com_o_limite_certo() -> None:
    with pytest.raises(ValueError, match="TEXT_SHORT tem 256 caracteres.*255"):
        imos_escrita.construir_payload(
            _cfg(), [_pasta("X", campos={"TEXT_SHORT": "a" * 256})]
        )
    with pytest.raises(ValueError, match="ARTICLENO tem 31 caracteres.*30"):
        imos_escrita.construir_payload(
            _cfg(), [_pasta("X", campos={"ARTICLENO": "a" * 31})]
        )


def test_texto_multilinha_fica_numa_linha_e_sem_nulos() -> None:
    payload = imos_escrita.construir_payload(
        _cfg(),
        [_pasta("X", campos={"TEXT_LONG": " AGL 19MM\r\nMDF 8MM\x00 "})],
    )

    assert payload["nos"][0]["campos"][0]["valor"] == "AGL 19MM MDF 8MM"


def test_plica_nao_passa_nem_por_aqui() -> None:
    """Última barreira: mesmo que o diálogo falhasse, a plica não chega ao iMos."""
    payload = imos_escrita.construir_payload(
        _cfg(), [_pasta("X", campos={"TEXT_SHORT": "PUXADOR 'J' H1030"})]
    )

    assert payload["nos"][0]["campos"][0]["valor"] == 'PUXADOR "J" H1030'


def test_valores_nulos_viram_string_vazia_porque_as_colunas_sao_not_null() -> None:
    payload = imos_escrita.construir_payload(
        _cfg(), [_pasta("X", campos={"ARTICLENO": None})]
    )

    assert payload["nos"][0]["campos"][0]["valor"] == ""


def test_colunas_numericas_sao_convertidas() -> None:
    payload = imos_escrita.construir_payload(
        _cfg(),
        [_pasta("X", campos={"CNT": "1", "CMS_PROCESS": 1, "CMS_PRICE": "0"})],
    )

    valores = {campo["coluna"]: campo for campo in payload["nos"][0]["campos"]}
    assert valores["CNT"]["valor"] == 1 and valores["CNT"]["tipo"] == "int"
    assert valores["CMS_PRICE"]["valor"] == 0.0
    assert valores["CMS_PRICE"]["tipo"] == "real"


def test_lista_branca_cobre_as_colunas_do_mapeamento_acordado() -> None:
    """As colunas que o Passo 3 vai preencher têm de estar todas permitidas."""
    esperadas = {
        "COMM",
        "ARTICLENO",
        "CLIENT",
        "PROGRAM",
        "EMPLOYEE",
        "TEXT_SHORT",
        "TEXT_LONG",
        "DELIVERY_DATE",
        "STARTDATE",
        "INFO1",
        "CONTYPE",
        "DESIGN",
    }
    assert esperadas <= set(imos_escrita.COLUNAS_PROADMIN)


# --------------------------------------------------------------------------
# Dados do cliente (dbo.CMSINCIDENTADRESS)
# --------------------------------------------------------------------------


def _encomenda(**kwargs) -> NoParaCriar:
    kwargs.setdefault("parent_dir_id", 6641)
    return NoParaCriar(nome="1260_01_26_LD", tipo=IMOS_TIPO_ENCOMENDA, **kwargs)


def test_contacto_normalizado_com_os_limites_da_sua_tabela() -> None:
    payload = imos_escrita.construir_payload(
        _cfg(),
        [_encomenda(contacto={"FIRMA": "LINHAS DIREITAS, LDA", "KDNR": "28"})],
    )

    campos = {c["coluna"]: c for c in payload["nos"][0]["contacto"]}
    assert campos["FIRMA"]["tamanho"] == 150
    assert campos["KDNR"]["tamanho"] == 100
    assert payload["orderid_de"] == imos_escrita.CONTACTO_ORDERID_DE


def test_contacto_todo_vazio_nao_gera_linha() -> None:
    payload = imos_escrita.construir_payload(
        _cfg(), [_encomenda(contacto={"FIRMA": "", "KDNR": "   "})]
    )

    assert payload["nos"][0]["contacto"] == []


def test_pasta_nao_pode_ter_dados_de_cliente() -> None:
    with pytest.raises(ValueError, match="só uma encomenda"):
        imos_escrita.construir_payload(
            _cfg(), [_pasta("ANO_2026", contacto={"FIRMA": "X"})]
        )


@pytest.mark.parametrize(
    "coluna", ["ID", "PARENT_ID", "ORDERNAME", "ORDERID", "SOURCE", "SYS", "MWST"]
)
def test_colunas_de_contacto_do_motor_sao_recusadas(coluna: str) -> None:
    with pytest.raises(ValueError, match="gerida pelo motor"):
        imos_escrita.construir_payload(_cfg(), [_encomenda(contacto={coluna: "1"})])


def test_coluna_de_contacto_desconhecida_nomeia_a_tabela_certa() -> None:
    with pytest.raises(ValueError, match="dbo.CMSINCIDENTADRESS"):
        imos_escrita.construir_payload(_cfg(), [_encomenda(contacto={"TELEMOVEL": "1"})])


def test_valor_de_contacto_grande_demais_e_recusado() -> None:
    with pytest.raises(ValueError, match="MOBILE tem 51 caracteres.*50"):
        imos_escrita.construir_payload(
            _cfg(), [_encomenda(contacto={"MOBILE": "9" * 51})]
        )


def test_no_sem_contacto_continua_a_funcionar() -> None:
    payload = imos_escrita.construir_payload(_cfg(), [_encomenda()])

    assert payload["nos"][0]["contacto"] == []


# --------------------------------------------------------------------------
# Script PowerShell
# --------------------------------------------------------------------------


def test_script_so_conhece_insert_nas_tres_tabelas_permitidas() -> None:
    script = imos_escrita._powershell_script()

    assert script.count("INSERT INTO dbo.IMORDFOLDER") == 1
    assert script.count("INSERT INTO dbo.PROADMIN") == 1
    assert script.count("INSERT INTO dbo.CMSINCIDENTADRESS") == 1
    assert script.count("INSERT INTO dbo.") == 3
    limpo = (
        script.upper().replace("EXECUTESCALAR", "").replace("EXECUTENONQUERY", "")
    )
    for proibido in ("UPDATE ", "DELETE ", "DROP ", "ALTER ", "TRUNCATE", "EXEC "):
        assert proibido not in limpo


def test_script_gera_os_guids_do_contacto_e_liga_ao_nome_da_encomenda() -> None:
    script = imos_escrita._powershell_script()

    assert script.count("[guid]::NewGuid()") == 2  # ID e PARENT_ID
    assert "$par.Value = [string]$no.nome" in script
    assert "if ([string]$p.orderid_de -eq 'dir') { $orderId = $dir } else" in script


def test_script_leva_a_lista_branca_das_colunas_de_contacto() -> None:
    script = imos_escrita._powershell_script()

    assert "'MOBILE'" in script and "'KDNR'" in script and "'FIRMA'" in script
    assert "COLUNAS_CONTACTO_PERMITIDAS" not in script


def test_script_reverte_a_transacao_em_erro() -> None:
    script = imos_escrita._powershell_script()

    assert "$tx = $conn.BeginTransaction()" in script
    assert "$tx.Rollback()" in script
    assert "$tx.Commit()" in script


def test_script_leva_a_lista_branca_de_colunas_injetada() -> None:
    script = imos_escrita._powershell_script()

    assert "'ARTICLENO'" in script and "'TEXT_LONG'" in script
    assert "COLUNAS_PERMITIDAS" not in script
    assert "TIPOS_PERMITIDOS" not in script


def test_script_liga_proadmin_a_imordfolder_pelo_scope_identity() -> None:
    script = imos_escrita._powershell_script()

    assert "SELECT CAST(SCOPE_IDENTITY() AS int)" in script
    assert "'PRODUCTIONID'" in script or "PRODUCTIONID" in script
    assert "$par.Value = $dir" in script


# --------------------------------------------------------------------------
# Resultado
# --------------------------------------------------------------------------


def test_criar_nos_devolve_os_ids_criados(session, monkeypatch) -> None:
    SystemSettingService(session).guardar_valor(
        imos_escrita.KEY_IMOS_ESCRITA_ATIVA, "ON"
    )
    monkeypatch.setattr(
        imos_escrita,
        "executar_payload",
        lambda payload: [
            imos_escrita.NoCriado(
                nome=payload["nos"][0]["nome"],
                tipo=IMOS_TIPO_PASTA,
                dir_id=7510,
                proadmin_id=7487,
                parent_dir_id=180,
            )
        ],
    )

    criados = imos_escrita.criar_nos(session, _cfg(), [_pasta("ANO_TESTE")])

    assert criados[0].nome == "ANO_TESTE"
    assert criados[0].dir_id == 7510
    assert criados[0].proadmin_id == 7487


def test_explicar_erro_esconde_o_caminho_do_script_temporario() -> None:
    texto = imos_escrita.explicar_erro_escrita(
        RuntimeError(r"C:\Temp\tmp123.ps1: algo correu mal")
    )

    assert "tmp123" not in texto
    assert "algo correu mal" in texto


def test_explicar_erro_traduz_falta_de_permissao() -> None:
    texto = imos_escrita.explicar_erro_escrita(
        RuntimeError("INSERT permission was denied on object 'PROADMIN'")
    )

    assert "não tem permissão de INSERT" in texto
