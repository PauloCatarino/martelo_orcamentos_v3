"""Lista de corte lida da base do iMos (ensaio em paralelo com o CSV do .cfg)."""

from __future__ import annotations

import pytest

from app.services import lista_corte_imos_base_service as svc


def _peca(pid, nome, *, cnt=1, mat="AGL_19MM", grid=0, comp=500, larg=300, esp=19.2,
          info1="", info2="", pos="RP_01.10001", ispec=0, matid=None):
    return {
        "ID": pid, "CNT": cnt, "NAME1": nome, "MATID": matid if matid is not None else mat,
        "MATNAME": mat, "MATGRID": grid, "CLENG": comp, "CWIDTH": larg, "CTHK": esp,
        "INFO1": info1, "INFO2": info2, "PARTPOSSTR": pos, "ISPEC": ispec,
    }


def _dados(**kw):
    """Obra com o RP_01 (piso R/C) e um gaveteiro dentro (sub-artigo, «Name» = o ID)."""
    base = dict(
        nome="TESTE",
        cabecalho={"ARTICLENO": "1608", "CLIENT": "CLIENTE_X", "CUSTOMER": ""},
        grupos=[
            {"ID": 100, "TYP": 2, "ARTID": 0, "ASSID": 0, "NAME": "RP_01"},
            {"ID": 101, "TYP": 3, "ARTID": 100, "ASSID": 0, "NAME": "Corpo"},
            {"ID": 200, "TYP": 2, "ARTID": 0, "ASSID": 101, "NAME": "BL_GVT"},
            {"ID": 201, "TYP": 3, "ARTID": 200, "ASSID": 0, "NAME": "Gaveta"},
            {"ID": 1, "TYP": 4, "ARTID": 0, "ASSID": 101, "NAME": "Lateral"},
            {"ID": 2, "TYP": 4, "ARTID": 0, "ASSID": 201, "NAME": "Frente"},
        ],
        artigos=[
            {"ID": 100, "GROUPNAME": "RP_01", "CPID": "R/C", "BOMFACTOR": 1},
            {"ID": 200, "GROUPNAME": "BL_GVT", "CPID": "200", "BOMFACTOR": 1},
        ],
        pecas=[_peca(1, "Lateral"), _peca(2, "Frente de gaveta", comp=160, larg=870)],
        orlas=[],
        programas=[],
    )
    base.update(kw)
    return svc.DadosObraImos(**base)


def _por_descricao(linhas):
    return {l.valor("Descricao"): l for l in linhas}


def test_sub_artigo_leva_o_piso_do_artigo_principal():
    linhas = _por_descricao(svc.montar_lista(_dados()))
    frente = linhas["Frente de gaveta"]
    assert frente.valor("Artigo/SubArtigo") == "BL_GVT"
    assert frente.valor("ArtigoNome") == "RP_01"
    # O «Name» do gaveteiro é o número dele (como o 49187 da APAGAR_14): o piso é o do RP.
    assert frente.valor("Piso") == "R/C"
    lateral = linhas["Lateral"]
    assert lateral.valor("Artigo/SubArtigo") == "RP_01"
    assert lateral.valor("Piso") == "R/C"
    assert lateral.valor("RP") == "RP_01"


def test_artigo_pendurado_pelo_artid_tambem_sobe_ao_principal():
    # Obra 1608_03: o sub-artigo «AT» liga ao AT_APT2_17 pelo ARTID, não pelo ASSID.
    dados = _dados(
        grupos=[
            {"ID": 100, "TYP": 2, "ARTID": 0, "ASSID": 0, "NAME": "RP_01"},
            {"ID": 200, "TYP": 2, "ARTID": 100, "ASSID": 0, "NAME": "AT"},
            {"ID": 201, "TYP": 3, "ARTID": 200, "ASSID": 0, "NAME": "Lateral"},
            {"ID": 1, "TYP": 4, "ARTID": 0, "ASSID": 201, "NAME": "Lateral"},
        ],
        artigos=[
            {"ID": 100, "GROUPNAME": "RP_01", "CPID": ".", "BOMFACTOR": 2},
            {"ID": 200, "GROUPNAME": "AT", "CPID": "200", "BOMFACTOR": 1},
        ],
        pecas=[_peca(1, "Lateral", cnt=1)],
    )
    (linha,) = svc.montar_lista(dados)
    assert linha.valor("ArtigoNome") == "RP_01"
    assert linha.valor("Artigo/SubArtigo") == "AT"
    assert linha.qt == 2  # a quantidade do artigo principal multiplica
    assert linha.valor("Piso") == ""  # "." não é piso


def test_artigo_com_quantidade_zero_da_linha_com_qt_zero():
    dados = _dados(artigos=[
        {"ID": 100, "GROUPNAME": "RP_01", "CPID": "R/C", "BOMFACTOR": 0},
        {"ID": 200, "GROUPNAME": "BL_GVT", "CPID": "200", "BOMFACTOR": 1},
    ])
    linhas = svc.montar_lista(dados)
    assert [l.valor("Qt.") for l in linhas] == ["0", "0"]


def test_peca_sem_material_fica_de_fora():
    dados = _dados(pecas=[_peca(1, "Lateral"), _peca(2, "Teto", mat="", matid="")])
    assert [l.valor("Descricao") for l in svc.montar_lista(dados)] == ["Lateral"]


def test_colunas_do_iMos():
    dados = _dados(
        pecas=[_peca(1, "Lateral", grid=2, comp=2225.8, larg=530, esp=19.2, info1="Rasgo",
                     info2="X", ispec=2)],
        orlas=[
            {"ID": 1, "PRFNO": 1, "PRFNAME": "PVC_1.0", "PTYPE": "N"},
            {"ID": 1, "PRFNO": 2, "PRFNAME": "PVC_0.4_B", "PTYPE": "N"},
            {"ID": 1, "PRFNO": 3, "PRFNAME": "PVC_0.4_D", "PTYPE": "N"},
            {"ID": 1, "PRFNO": 4, "PRFNAME": "PVC_0.4_C", "PTYPE": "N"},
            {"ID": 1, "PRFNO": 5, "PRFNAME": "RECORTE", "PTYPE": "I"},
        ],
    )
    (linha,) = svc.montar_lista(dados)
    assert [linha.valor(c) for c in svc.COLUNAS_IMOS] == [
        "Lateral", "AGL_19MM", "2225.8", "530.0", "19.2", "1", "1",
        "PVC_1.0", "PVC_0.4_D", "PVC_0.4_C", "PVC_0.4_B", "", "",
        "1608", "CLIENTE_X", "RP_01", "Rasgo", "X", "", "", "", "",
    ]
    assert linha.valor("ISPEC") == "2"


def test_programas_cnc_sem_dummy_nem_espelhados():
    def prog(pid, seq, maq, nc, espelho="no"):
        return [
            {"PARTID": 1, "PROGRAMID": pid, "SEQUENCENUM": seq, "ATTRIBUTE": "machine", "ATTRVALUE": maq},
            {"PARTID": 1, "PROGRAMID": pid, "SEQUENCENUM": seq, "ATTRIBUTE": "ncnum", "ATTRVALUE": nc},
            {"PARTID": 1, "PROGRAMID": pid, "SEQUENCENUM": seq, "ATTRIBUTE": "mirrored", "ATTRVALUE": espelho},
        ]
    programas = (
        prog("a", 1, "Dummy_ABD", "10050_01") + prog("b", 1, "LE_CNC", "10050")
        + prog("c", 1, "LE_BHT_500_V1", "10050M", espelho="yes")
        + prog("d", 2, "LE_ABD", "10050") + prog("e", 3, "LE_ABD", "10050_2")
    )
    (linha,) = svc.montar_lista(_dados(pecas=[_peca(1, "Fundo")], programas=programas))
    assert (linha.valor("CNC_1"), linha.valor("CNC_2")) == ("10050", "10050_2")


def test_junta_pecas_iguais_e_separa_notas_diferentes():
    dados = _dados(pecas=[
        _peca(1, "Lateral"), _peca(2, "Lateral"), _peca(3, "Lateral", info1="Rasgo 'Tupia'"),
    ], grupos=[
        {"ID": 100, "TYP": 2, "ARTID": 0, "ASSID": 0, "NAME": "RP_01"},
        {"ID": 101, "TYP": 3, "ARTID": 100, "ASSID": 0, "NAME": "Corpo"},
        {"ID": 1, "TYP": 4, "ARTID": 0, "ASSID": 101, "NAME": "Lateral"},
        {"ID": 2, "TYP": 4, "ARTID": 0, "ASSID": 101, "NAME": "Lateral"},
        {"ID": 3, "TYP": 4, "ARTID": 0, "ASSID": 101, "NAME": "Lateral"},
    ])
    linhas = svc.montar_lista(dados)
    assert sorted((l.valor("Notas"), l.qt) for l in linhas) == [("", 2), ("Rasgo 'Tupia'", 1)]


@pytest.mark.parametrize("name, esperado", [
    (".", ""), ("", ""), ("100", ""), ("RP_01", ""), ("Piso 1º", "Piso 1º"),
])
def test_o_que_conta_como_piso(name, esperado):
    dados = _dados(artigos=[
        {"ID": 100, "GROUPNAME": "RP_01", "CPID": name, "BOMFACTOR": 1},
        {"ID": 200, "GROUPNAME": "BL_GVT", "CPID": "200", "BOMFACTOR": 1},
    ])
    assert {l.valor("Piso") for l in svc.montar_lista(dados)} == {esperado}


def test_sem_piso_no_principal_vale_o_do_sub_artigo():
    dados = _dados(artigos=[
        {"ID": 100, "GROUPNAME": "RP_01", "CPID": ".", "BOMFACTOR": 1},
        {"ID": 200, "GROUPNAME": "BL_GVT", "CPID": "Cave", "BOMFACTOR": 1},
    ])
    linhas = _por_descricao(svc.montar_lista(dados))
    assert linhas["Frente de gaveta"].valor("Piso") == "Cave"
    assert linhas["Lateral"].valor("Piso") == ""


def test_csv_como_o_do_imos(tmp_path):
    destino = svc.escrever_csv(svc.montar_lista(_dados()), tmp_path / "x" / "lista.csv")
    bruto = destino.read_bytes()
    texto = bruto.decode("cp1252")
    linhas = texto.split("\r\n")
    assert linhas[-1] == ""  # termina com CRLF
    assert "\n" not in texto.replace("\r\n", "")
    assert linhas[0] == ";".join(svc.COLUNAS_CSV) + ";"
    assert linhas[0].startswith("Descricao;Material;Comp.;Larg.;Esp;Qt.;Veio;")
    assert all(ln.count(";") == len(svc.COLUNAS_CSV) for ln in linhas[:-1])
    # As 22 primeiras colunas são as do CSV do .cfg, pela mesma ordem (a macro copia por posição).
    assert linhas[0].split(";")[15] == "RP" and linhas[0].split(";")[21] == "BHT"
    lidas = svc.ler_csv(destino)
    assert {r["Piso"] for r in lidas} == {"R/C"}


def test_ponto_e_virgula_no_texto_nao_parte_a_coluna(tmp_path):
    dados = _dados(pecas=[_peca(1, "Lateral", info1="Rasgo; furo")])
    destino = svc.escrever_csv(svc.montar_lista(dados), tmp_path / "l.csv")
    (linha,) = svc.ler_csv(destino)
    assert linha["Notas"] == "Rasgo, furo"


def test_comparacao_igual_e_diferente(tmp_path):
    linhas = svc.montar_lista(_dados())
    lidas = svc.ler_csv(svc.escrever_csv(linhas, tmp_path / "l.csv"))
    assert svc.comparar_com_csv_imos(linhas, lidas).iguais
    lidas[0]["Qt."] = "5"
    lidas[1]["Orla ESQ"] = "PVC_X"
    comp = svc.comparar_com_csv_imos(linhas, lidas)
    assert not comp.iguais
    assert any("base 1, CSV 5" in d for d in comp.diferencas)
    assert any(d.startswith("Coluna Orla ESQ") for d in comp.diferencas)


def test_comparacao_aceita_csv_do_cfg_v1_com_posicao(tmp_path):
    linhas = svc.montar_lista(_dados())
    lidas = svc.ler_csv(svc.escrever_csv(linhas, tmp_path / "l.csv"))
    for r in lidas:
        r["Posicao"] = r.pop("RP")
    assert svc.comparar_com_csv_imos(linhas, lidas).iguais


def test_ler_obra_so_faz_select_e_recusa_nomes_invalidos():
    consultas = []

    def executar(cfg, sql):
        consultas.append(sql)
        if "FROM PROADMIN" in sql:
            return [{"ID": 1, "ARTICLENO": "1", "CLIENT": "C", "CUSTOMER": "",
                     "GRAVADA": "2026-10-29 16:19:52"}]
        return []

    dados = svc.ler_obra({}, "1608_03_26_HIRONDELLES", executar=executar)
    assert dados.ultima_gravacao is not None and dados.ultima_gravacao.hour == 16
    assert all(sql.lstrip().upper().startswith("SELECT") for sql in consultas)
    assert all("N'1608_03_26_HIRONDELLES'" in sql for sql in consultas)
    with pytest.raises(ValueError):
        svc.ler_obra({}, "X'; DROP TABLE IDBGPL--", executar=executar)


def test_obra_que_nao_existe_no_imos():
    with pytest.raises(ValueError, match="Não encontrei"):
        svc.ler_obra({}, "APAGAR_99", executar=lambda cfg, sql: [])
