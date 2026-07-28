"""Testes da tradução de uma obra da Produção para uma encomenda do iMos."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.models.cliente import Cliente
from app.services import imos_encomenda_service as servico
from app.services.imos_sql import (
    IMOS_TIPO_ENCOMENDA,
    IMOS_TIPO_PASTA,
    CaminhoImos,
    ImosConfig,
    NivelCaminho,
)


def _cfg() -> ImosConfig:
    return {
        "server": r"SERVER_LE\SERVER_LE",
        "database": "imos_le",
        "user": "imosadmin",
        "password": "x",
        "trusted": False,
        "trust_server_certificate": True,
    }


def _obra(**overrides) -> SimpleNamespace:
    dados = {
        "ano": "2026",
        "num_enc_phc": "1260",
        "versao_obra": "01",
        "versao_plano": "01",
        "nome_cliente_simplex": "LINHAS_DIREITAS",
        "nome_cliente": "LINHAS DIREITAS - SOLUÇÕES INTERIORES, LDA",
        "num_cliente_phc": "28",
        "cliente_id": None,
        "ref_cliente": "260082",
        "responsavel": "Pedro",
        "descricao_producao": "",
        "materias_usados": "",
        "data_inicio": "14-07-2026",
        "data_entrega": "04-09-2026",
    }
    dados.update(overrides)
    return SimpleNamespace(**dados)


def _cliente(session, **overrides) -> Cliente:
    """Cria a ficha do cliente e devolve-a já com id."""
    dados = {
        "nome": "LINHAS DIREITAS - SOLUÇÕES INTERIORES, LDA",
        "nome_simplex": "LINHAS_DIREITAS",
        "email": "geral@linhasdireitas.pt",
        "telefone": "244741215",
        "telemovel": "919613398",
        "num_cliente_phc": "28",
    }
    dados.update(overrides)
    cliente = Cliente(**dados)
    session.add(cliente)
    session.flush()
    return cliente


def _caminho(
    *,
    raiz: int | None = 180,
    ano: int | None = 6624,
    cliente: int | None = 6641,
    encomenda: int | None = None,
    nome_encomenda: str = "1260_01_26_LINHAS_DIREITAS",
) -> CaminhoImos:
    return CaminhoImos(
        niveis=(
            NivelCaminho("LANCA_ENCANTO", IMOS_TIPO_PASTA, raiz),
            NivelCaminho("ANO_2026", IMOS_TIPO_PASTA, ano),
            NivelCaminho("LINHAS_DIREITAS", IMOS_TIPO_PASTA, cliente),
            NivelCaminho(nome_encomenda, IMOS_TIPO_ENCOMENDA, encomenda),
        )
    )


def _com_caminho(monkeypatch, caminho: CaminhoImos) -> None:
    monkeypatch.setattr(
        servico, "resolver_caminho_encomenda", lambda *_a, **_k: caminho
    )


# --------------------------------------------------------------------------
# Conversões
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("14-07-2026", "14/07/2026"),
        ("2026-07-14", "14/07/2026"),
        ("14/07/2026", "14/07/2026"),
        ("", ""),
        (None, ""),
        ("data marada", ""),
    ],
)
def test_datas_passam_para_o_formato_do_imos(valor, esperado: str) -> None:
    assert servico._data_imos(valor) == esperado


def test_pasta_do_cliente_e_sempre_o_simplex_normalizado() -> None:
    assert servico.nome_pasta_cliente(_obra()) == "LINHAS_DIREITAS"
    assert (
        servico.nome_pasta_cliente(_obra(nome_cliente_simplex="Inovação Positiva"))
        == "INOVACAO_POSITIVA"
    )


def test_pasta_do_cliente_vazia_quando_nao_ha_simplex() -> None:
    assert servico.nome_pasta_cliente(_obra(nome_cliente_simplex="")) == ""


def test_nome_da_encomenda_segue_o_formato_do_imos() -> None:
    assert servico.nome_encomenda_sugerido(_obra()) == "1260_01_26_LINHAS_DIREITAS"


# --------------------------------------------------------------------------
# Mapeamento de campos
# --------------------------------------------------------------------------


def test_mapeamento_acordado_com_o_utilizador() -> None:
    campos = {
        campo.coluna: campo.valor
        for campo in servico.mapear_campos(
            _obra(), nome_encomenda="1260_01_26_LINHAS_DIREITAS"
        )
    }

    assert campos["PROGRAM"] == "1260_01_26_LINHAS_DIREITAS"
    assert campos["COMM"] == "1260"
    assert campos["ARTICLENO"] == "260082"
    assert campos["CLIENT"] == "LINHAS_DIREITAS"
    assert campos["EMPLOYEE"] == "Pedro"
    assert campos["DELIVERY_DATE"] == "04/09/2026"
    assert campos["STARTDATE"] == "14/07/2026"
    assert campos["INFO1"] == "1260_01_01_26_LINHAS_DIREITAS"


def test_descricao_grande_e_cortada_no_limite_da_coluna() -> None:
    obra = _obra(descricao_producao="A" * 400, materias_usados="B" * 300)

    campos = {
        campo.coluna: campo
        for campo in servico.mapear_campos(obra, nome_encomenda="X")
    }

    assert len(campos["TEXT_SHORT"].valor) == 255
    assert campos["TEXT_SHORT"].truncado is True
    assert campos["TEXT_SHORT"].valor_original == "A" * 400
    assert len(campos["TEXT_LONG"].valor) == 255
    assert campos["TEXT_LONG"].truncado is True


def test_texto_multilinha_fica_numa_linha_so() -> None:
    obra = _obra(materias_usados="AGL 19MM\r\nMDF 8MM\n\nORLA 2MM")

    campos = {
        campo.coluna: campo.valor
        for campo in servico.mapear_campos(obra, nome_encomenda="X")
    }

    assert campos["TEXT_LONG"] == "AGL 19MM MDF 8MM ORLA 2MM"


def test_todas_as_colunas_mapeadas_existem_em_proadmin() -> None:
    from app.services.imos_escrita import COLUNAS_PROADMIN

    for campo in servico.mapear_campos(_obra(), nome_encomenda="X"):
        assert campo.coluna in COLUNAS_PROADMIN


# --------------------------------------------------------------------------
# preparar() — o plano
# --------------------------------------------------------------------------


def test_plano_com_tudo_ja_existente_so_cria_a_encomenda(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho())
    cliente = _cliente(session)

    plano = servico.preparar(session, _cfg(), _obra(cliente_id=cliente.id))

    assert plano.pode_criar is True
    assert plano.avisos == ()
    assert plano.pastas_a_criar == ()
    assert plano.nome_encomenda == "1260_01_26_LINHAS_DIREITAS"


def test_plano_avisa_das_pastas_que_vao_ser_criadas(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho(ano=None, cliente=None))

    plano = servico.preparar(session, _cfg(), _obra())

    assert plano.pode_criar is True
    assert plano.pastas_a_criar == ("ANO_2026", "LINHAS_DIREITAS")
    assert any("Vão ser criadas as pastas" in aviso for aviso in plano.avisos)


def test_plano_bloqueia_quando_a_encomenda_ja_existe(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho(encomenda=6765))

    plano = servico.preparar(session, _cfg(), _obra())

    assert plano.pode_criar is False
    assert any("Já existe uma encomenda" in bloqueio for bloqueio in plano.bloqueios)


def test_plano_bloqueia_quando_a_pasta_raiz_nao_existe(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho(raiz=None, ano=None, cliente=None))

    plano = servico.preparar(session, _cfg(), _obra())

    assert plano.pode_criar is False
    assert any("pasta raiz" in bloqueio for bloqueio in plano.bloqueios)


def test_plano_bloqueia_sem_cliente_simplex_e_nao_consulta_o_sql(
    session, monkeypatch
) -> None:
    def _explode(*_a, **_k):
        raise AssertionError("não devia consultar o iMos sem cliente simplex")

    monkeypatch.setattr(servico, "resolver_caminho_encomenda", _explode)

    plano = servico.preparar(session, _cfg(), _obra(nome_cliente_simplex=""))

    assert plano.pode_criar is False
    assert any("Cliente simplex" in bloqueio for bloqueio in plano.bloqueios)


def test_plano_bloqueia_sem_numero_de_encomenda(session, monkeypatch) -> None:
    monkeypatch.setattr(
        servico, "resolver_caminho_encomenda", lambda *_a, **_k: _caminho()
    )

    plano = servico.preparar(session, _cfg(), _obra(num_enc_phc=""))

    assert plano.pode_criar is False
    assert any("Nº Enc PHC" in bloqueio for bloqueio in plano.bloqueios)


def test_nome_grande_demais_e_cortado_com_aviso(session, monkeypatch) -> None:
    """VIRGILIO_PEREIRA_LOPES (22) daria um nome de 33 caracteres."""
    obra = _obra(nome_cliente_simplex="VIRGILIO_PEREIRA_LOPES")
    _com_caminho(
        monkeypatch,
        _caminho(cliente=None, nome_encomenda="1260_01_26_VIRGILIO_PEREIRA_LO"),
    )

    plano = servico.preparar(session, _cfg(), obra)

    assert plano.nome_sugerido == "1260_01_26_VIRGILIO_PEREIRA_LOPES"
    assert plano.nome_encomenda == "1260_01_26_VIRGILIO_PEREIRA_LO"
    assert len(plano.nome_encomenda) == 30
    assert plano.nome_truncado is True
    assert any("só aceita 30" in aviso for aviso in plano.avisos)
    assert plano.pode_criar is True


def test_nome_corrigido_pelo_utilizador_substitui_o_sugerido(
    session, monkeypatch
) -> None:
    _com_caminho(monkeypatch, _caminho(nome_encomenda="1260_01_26_VIRGILIO_PL"))

    plano = servico.preparar(
        session,
        _cfg(),
        _obra(nome_cliente_simplex="VIRGILIO_PEREIRA_LOPES"),
        nome_encomenda="1260_01_26_VIRGILIO_PL",
    )

    assert plano.nome_encomenda == "1260_01_26_VIRGILIO_PL"
    campos = {campo.coluna: campo.valor for campo in plano.campos}
    assert campos["PROGRAM"] == "1260_01_26_VIRGILIO_PL"


def test_nome_corrigido_invalido_bloqueia(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho())

    plano = servico.preparar(
        session, _cfg(), _obra(), nome_encomenda="NOME COM ; PONTO E VIRGULA"
    )

    assert plano.pode_criar is False
    assert any("não é aceite pelo iMos" in bloqueio for bloqueio in plano.bloqueios)


# --------------------------------------------------------------------------
# nos_para_criar() — o encadeamento
# --------------------------------------------------------------------------


def test_so_a_encomenda_quando_as_pastas_existem(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho())
    plano = servico.preparar(session, _cfg(), _obra())

    nos = servico.nos_para_criar(plano)

    assert len(nos) == 1
    assert nos[0].tipo == IMOS_TIPO_ENCOMENDA
    assert nos[0].parent_dir_id == 6641
    assert nos[0].parent_indice is None


def test_pastas_em_falta_encadeiam_se_pelo_indice(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho(ano=None, cliente=None))
    plano = servico.preparar(session, _cfg(), _obra())

    nos = servico.nos_para_criar(plano)

    assert [no.nome for no in nos] == [
        "ANO_2026",
        "LINHAS_DIREITAS",
        "1260_01_26_LINHAS_DIREITAS",
    ]
    # A primeira pasta nova pendura-se na raiz, que já existe.
    assert nos[0].parent_dir_id == 180 and nos[0].parent_indice is None
    # As seguintes só ganham DIR_ID durante a transação.
    assert nos[1].parent_indice == 0 and nos[1].parent_dir_id is None
    assert nos[2].parent_indice == 1 and nos[2].parent_dir_id is None


def test_so_a_pasta_do_cliente_em_falta(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho(cliente=None))
    plano = servico.preparar(session, _cfg(), _obra())

    nos = servico.nos_para_criar(plano)

    assert [no.nome for no in nos] == ["LINHAS_DIREITAS", "1260_01_26_LINHAS_DIREITAS"]
    assert nos[0].parent_dir_id == 6624
    assert nos[1].parent_indice == 0


def test_valores_fixos_da_encomenda_e_da_pasta(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho(cliente=None))
    plano = servico.preparar(session, _cfg(), _obra())

    pasta, encomenda = servico.nos_para_criar(plano)

    assert pasta.campos["CMS_PROCESS"] == 1
    assert pasta.campos["SOURCE"] == "IMOSADMIN"
    assert "CONTYPE" not in pasta.campos
    assert "GLOBAL_SPEC_VERSION" not in pasta.campos

    assert encomenda.campos["CMS_PROCESS"] == 0
    assert encomenda.campos["CMS_CALCULATION"] == 1
    assert encomenda.campos["CNT"] == 1
    assert encomenda.campos["CONTYPE"] == "STANDARD"
    assert encomenda.campos["DESIGN"] == "FOLGAS_FRENTES_2022"
    assert encomenda.campos["GLOBAL_SPEC_VERSION"] == servico.MD5_SEM_ESPECIFICACAO
    assert encomenda.campos["DETAIL_SPEC_VERSION"] == servico.MD5_SEM_ESPECIFICACAO
    assert encomenda.campos["COMM"] == "1260"


def test_plano_bloqueado_nao_gera_nos(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho(encomenda=6765))
    plano = servico.preparar(session, _cfg(), _obra())

    with pytest.raises(RuntimeError, match="não pode ser executado"):
        servico.nos_para_criar(plano)


def test_nos_gerados_passam_na_validacao_do_motor_de_escrita(
    session, monkeypatch
) -> None:
    """O plano tem de produzir um payload que o motor aceita sem retoques."""
    from app.services import imos_escrita

    _com_caminho(monkeypatch, _caminho(ano=None, cliente=None))
    plano = servico.preparar(session, _cfg(), _obra())

    payload = imos_escrita.construir_payload(_cfg(), servico.nos_para_criar(plano))

    assert len(payload["nos"]) == 3
    colunas = {campo["coluna"] for campo in payload["nos"][2]["campos"]}
    assert {"COMM", "CLIENT", "PROGRAM", "INFO1", "STARTDATE"} <= colunas


def test_pasta_ano_alternativa_desvia_a_criacao_e_avisa(session, monkeypatch) -> None:
    recebido: dict = {}

    def _resolver(*_a, **kwargs):
        recebido.update(kwargs)
        return CaminhoImos(
            niveis=(
                NivelCaminho("LANCA_ENCANTO", IMOS_TIPO_PASTA, 180),
                NivelCaminho("ANO_TESTE", IMOS_TIPO_PASTA, None),
                NivelCaminho("LINHAS_DIREITAS", IMOS_TIPO_PASTA, None),
                NivelCaminho("1260_01_26_LINHAS_DIREITAS", IMOS_TIPO_ENCOMENDA, None),
            )
        )

    monkeypatch.setattr(servico, "resolver_caminho_encomenda", _resolver)

    plano = servico.preparar(session, _cfg(), _obra(), pasta_ano="ANO_TESTE")

    assert recebido["pasta_ano"] == "ANO_TESTE"
    assert "não para a pasta do ano da obra" in plano.avisos[0]
    assert plano.pastas_a_criar == ("ANO_TESTE", "LINHAS_DIREITAS")
    assert plano.pode_criar is True


def test_sem_ensaio_a_pasta_do_ano_nao_e_forcada(session, monkeypatch) -> None:
    recebido: dict = {}

    def _resolver(*_a, **kwargs):
        recebido.update(kwargs)
        return _caminho()

    monkeypatch.setattr(servico, "resolver_caminho_encomenda", _resolver)
    plano = servico.preparar(session, _cfg(), _obra())

    assert recebido["pasta_ano"] is None
    assert not any("não para a pasta do ano" in aviso for aviso in plano.avisos)


# --------------------------------------------------------------------------
# Correções locais de TEXT_SHORT / TEXT_LONG
# --------------------------------------------------------------------------


def test_texto_editado_substitui_o_da_obra(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho())
    obra = _obra(descricao_producao="roupeiro 4 portas", materias_usados="AGL 19MM")

    plano = servico.preparar(
        session,
        _cfg(),
        obra,
        textos={"TEXT_SHORT": "ROUPEIRO 4 PORTAS DE ABRIR C/ GAVETAS"},
    )
    campos = {c.coluna: c for c in plano.campos}

    assert campos["TEXT_SHORT"].valor == "ROUPEIRO 4 PORTAS DE ABRIR C/ GAVETAS"
    assert campos["TEXT_SHORT"].origem == "Editado aqui"
    # O que não foi editado continua a vir da obra.
    assert campos["TEXT_LONG"].valor == "AGL 19MM"
    assert campos["TEXT_LONG"].origem == "Matérias usados"


def test_texto_editado_nao_altera_a_obra_no_martelo(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho())
    obra = _obra(descricao_producao="original")

    servico.preparar(session, _cfg(), obra, textos={"TEXT_SHORT": "corrigido"})

    assert obra.descricao_producao == "original"


def test_texto_editado_grande_demais_e_cortado_com_aviso(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho())

    plano = servico.preparar(
        session, _cfg(), _obra(), textos={"TEXT_LONG": "B" * 300}
    )
    campo = next(c for c in plano.campos if c.coluna == "TEXT_LONG")

    assert len(campo.valor) == 255
    assert campo.truncado is True
    assert any("cortados para 255" in aviso for aviso in plano.avisos)


def test_so_as_colunas_editaveis_aceitam_correcao(session, monkeypatch) -> None:
    """Uma correção a uma coluna não editável é simplesmente ignorada."""
    _com_caminho(monkeypatch, _caminho())

    plano = servico.preparar(
        session, _cfg(), _obra(), textos={"COMM": "9999", "CLIENT": "OUTRO"}
    )
    campos = {c.coluna: c.valor for c in plano.campos}

    assert campos["COMM"] == "1260"
    assert campos["CLIENT"] == "LINHAS_DIREITAS"


def test_texto_editado_vai_para_o_no_da_encomenda(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho())

    plano = servico.preparar(
        session, _cfg(), _obra(), textos={"TEXT_SHORT": "corrigido no dialogo"}
    )
    (encomenda,) = servico.nos_para_criar(plano)

    assert encomenda.campos["TEXT_SHORT"] == "corrigido no dialogo"


# --------------------------------------------------------------------------
# Dados do cliente (dbo.CMSINCIDENTADRESS)
# --------------------------------------------------------------------------


def test_mapeamento_dos_dados_do_cliente(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho())
    cliente = _cliente(session)

    plano = servico.preparar(session, _cfg(), _obra(cliente_id=cliente.id))
    contacto = {campo.coluna: campo.valor for campo in plano.contacto}

    assert contacto["FIRMA"] == "LINHAS DIREITAS - SOLUÇÕES INTERIORES, LDA"
    assert contacto["KDNR"] == "28"
    assert contacto["MOBILE"] == "244741215"
    assert contacto["EMAIL1"] == "geral@linhasdireitas.pt"
    assert plano.tem_contacto is True


def test_sem_ficha_de_cliente_avisa_e_deixa_telefone_e_email_vazios(
    session, monkeypatch
) -> None:
    _com_caminho(monkeypatch, _caminho())

    plano = servico.preparar(session, _cfg(), _obra(cliente_id=None))
    contacto = {campo.coluna: campo.valor for campo in plano.contacto}

    assert contacto["MOBILE"] == ""
    assert contacto["EMAIL1"] == ""
    # FIRMA e KDNR saem da propria obra, por isso continuam preenchidos.
    assert contacto["KDNR"] == "28"
    assert any("não está ligada a uma ficha de cliente" in a for a in plano.avisos)
    assert plano.pode_criar is True


def test_nome_de_cliente_grande_e_cortado_no_limite_do_firma(
    session, monkeypatch
) -> None:
    _com_caminho(monkeypatch, _caminho())

    plano = servico.preparar(
        session, _cfg(), _obra(nome_cliente="X" * 200, cliente_id=None)
    )
    firma = next(c for c in plano.contacto if c.coluna == "FIRMA")

    assert len(firma.valor) == 150
    assert firma.truncado is True
    assert any("Cliente: 200 caracteres cortados para 150" in a for a in plano.avisos)


def test_contacto_vai_no_no_da_encomenda(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho(cliente=None))
    cliente = _cliente(session)
    plano = servico.preparar(session, _cfg(), _obra(cliente_id=cliente.id))

    pasta, encomenda = servico.nos_para_criar(plano)

    assert pasta.contacto is None
    assert encomenda.contacto["FIRMA"].startswith("LINHAS DIREITAS")
    assert encomenda.contacto["MOBILE"] == "244741215"


def test_contacto_passa_na_validacao_do_motor(session, monkeypatch) -> None:
    from app.services import imos_escrita

    _com_caminho(monkeypatch, _caminho())
    cliente = _cliente(session)
    plano = servico.preparar(session, _cfg(), _obra(cliente_id=cliente.id))

    payload = imos_escrita.construir_payload(_cfg(), servico.nos_para_criar(plano))
    contacto = {c["coluna"]: c["valor"] for c in payload["nos"][0]["contacto"]}

    assert contacto["EMAIL1"] == "geral@linhasdireitas.pt"
    assert set(contacto) == {"FIRMA", "KDNR", "MOBILE", "EMAIL1"}


def test_obra_sem_cliente_nenhum_nao_cria_linha_de_contacto(
    session, monkeypatch
) -> None:
    """Sem um único valor preenchido, o motor não cria a linha de contacto."""
    from app.services import imos_escrita

    _com_caminho(monkeypatch, _caminho())
    plano = servico.preparar(
        session,
        _cfg(),
        _obra(nome_cliente="", num_cliente_phc="", cliente_id=None),
    )

    payload = imos_escrita.construir_payload(_cfg(), servico.nos_para_criar(plano))

    assert payload["nos"][0]["contacto"] == []
    assert plano.tem_contacto is False


def test_executar_usa_o_motor_de_escrita(session, monkeypatch) -> None:
    _com_caminho(monkeypatch, _caminho())
    plano = servico.preparar(session, _cfg(), _obra())
    recebidos: list = []

    def _criar(_session, _cfg_, nos):
        recebidos.extend(nos)
        return []

    monkeypatch.setattr(servico, "criar_nos", _criar)
    servico.executar(session, _cfg(), plano)

    assert len(recebidos) == 1
    assert recebidos[0].nome == "1260_01_26_LINHAS_DIREITAS"
