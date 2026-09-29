"""Gerar no Martelo as listas de ferragens do iMos (.rdl).

O que estes testes guardam:

* o SQL de um .rdl só corre na base do iMos se for só de leitura (tabelas
  temporárias # são aceites — é o que os .rdl reais usam);
* a encomenda certa é encontrada, com a hora da última gravação do desenho;
* nada se perde na pasta da obra: a lista anterior vai para
  ``Listas_IMOS_anteriores`` com a data em que tinha sido gerada;
* cada lista sabe de que gravação saiu (marca nas propriedades do ficheiro),
  e é isso que diz se está atualizada.
"""

from __future__ import annotations

import os
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

import pytest

from app.services import imos_listas_service as svc

# ---------------------------------------------------------------------------
# ajudas
# ---------------------------------------------------------------------------

CORE_VAZIO = (
    '<?xml version="1.0" encoding="utf-8" standalone="yes" ?>'
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/"></cp:coreProperties>'
)
RELS_REPORTVIEWER = (
    '<?xml version="1.0" encoding="utf-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Type="http://schemas.openxmlformats.org/package/2006/relationships/meatadata/core-properties" '
    'Target="/docProps/core.xml" Id="rId4" /></Relationships>'
)


def _xlsx(caminho: Path, conteudo: bytes = b"<folha/>") -> Path:
    """Um .xlsx mínimo, como o ReportViewer o escreve (core.xml vazio)."""
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("xl/workbook.xml", conteudo)
        z.writestr("_rels/.rels", RELS_REPORTVIEWER)
        z.writestr("docProps/core.xml", CORE_VAZIO)
    return caminho


def _mtime(caminho: Path, quando: datetime) -> None:
    ts = quando.timestamp()
    os.utime(caminho, (ts, ts))


def _rdl(caminho: Path, sql: str, *, tipo: str | None = None, com_query: bool = True) -> Path:
    tipo_xml = f"<CommandType>{tipo}</CommandType>" if tipo else ""
    query = (
        f"<Query><DataSourceName>imos</DataSourceName>{tipo_xml}"
        "<QueryParameters><QueryParameter Name=\"@ORDERLIST\"><Value>=Parameters!ORDERLIST.Value</Value>"
        f"</QueryParameter></QueryParameters><CommandText>{sql}</CommandText></Query>"
        if com_query
        else "<SharedDataSet><SharedDataSetReference>x</SharedDataSetReference></SharedDataSet>"
    )
    caminho.write_text(
        '<?xml version="1.0" encoding="utf-8"?>'
        '<Report xmlns="http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition">'
        f'<DataSets><DataSet Name="Ferragens">{query}</DataSet></DataSets></Report>',
        encoding="utf-8",
    )
    return caminho


# ---------------------------------------------------------------------------
# SQL só de leitura
# ---------------------------------------------------------------------------

SQL_COMO_OS_RDL_REAIS = """
-- Uncomment the following lines ... DELETE nothing here
IF OBJECT_ID ('tempdb..#ORDERLIST') IS NOT NULL DROP TABLE #ORDERLIST;
SELECT PROADMIN.ID AS PROADMIN_ID, PROADMIN.NAME INTO #ORDERLIST FROM PROADMIN
WHERE CHARINDEX(',' + (CAST(PROADMIN.ID AS nvarchar(8))) + ',', ',' + @ORDERLIST + ',') != 0;
/* era: UPDATE PROADMIN SET X = 1 */
SELECT *, 'INSERT INTO dbo.X' AS TEXTO, LAST_UPDATE FROM #ORDERLIST
WHERE IDBGRPS.HIGHARTID IS NOT NULL
"""


def test_o_sql_dos_rdl_reais_e_aceite() -> None:
    """Tabelas temporárias, comentários e textos entre plicas não contam."""
    assert svc.problemas_sql_rdl(SQL_COMO_OS_RDL_REAIS) == []


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO dbo.PROADMIN (ID) VALUES (1)",
        "UPDATE PROADMIN SET NAME = 'x'",
        "DELETE FROM IDBPURCH",
        "DELETE IDBPURCH WHERE ID = 1",
        "DROP TABLE PROADMIN",
        "TRUNCATE TABLE IDBGRPS",
        "SELECT * INTO NOVA_TABELA FROM PROADMIN",
        "EXEC sp_executesql N'SELECT 1'",
        "CREATE VIEW V AS SELECT 1",
        "ALTER DATABASE imos_LE SET OFFLINE",
        "MERGE INTO PROADMIN USING X ON 1=1 WHEN MATCHED THEN DELETE;",
    ],
)
def test_escritas_na_base_do_imos_sao_recusadas(sql: str) -> None:
    assert svc.problemas_sql_rdl(sql), sql


def test_escritas_em_tabelas_temporarias_sao_aceites() -> None:
    sql = (
        "CREATE TABLE #T (ID int); INSERT INTO #T VALUES (1); UPDATE #T SET ID = 2;"
        " DELETE FROM #T; DROP TABLE IF EXISTS #T; SELECT 1 INTO #U; "
        "DECLARE @V TABLE (ID int); INSERT INTO @V VALUES (1)"
    )
    assert svc.problemas_sql_rdl(sql) == []


def test_ler_rdl_devolve_os_conjuntos(tmp_path) -> None:
    rdl = _rdl(tmp_path / "ok.rdl", "SELECT 1 AS X FROM PROADMIN")
    assert [d.nome for d in svc.ler_rdl(rdl)] == ["Ferragens"]


def test_ler_rdl_recusa_escrita_e_diz_onde(tmp_path) -> None:
    rdl = _rdl(tmp_path / "mau.rdl", "DELETE FROM IDBPURCH")
    with pytest.raises(ValueError, match="Ferragens: DELETE em IDBPURCH"):
        svc.ler_rdl(rdl)


def test_ler_rdl_recusa_procedimentos_e_conjuntos_partilhados(tmp_path) -> None:
    with pytest.raises(ValueError, match="StoredProcedure"):
        svc.ler_rdl(_rdl(tmp_path / "sp.rdl", "sp_lista", tipo="StoredProcedure"))
    with pytest.raises(ValueError, match="partilhado"):
        svc.ler_rdl(_rdl(tmp_path / "partilhado.rdl", "", com_query=False))


def test_a_rede_de_seguranca_do_motor_esta_no_codigo() -> None:
    """Mesmo que a verificação falhasse, nada fica gravado no iMos."""
    assert "BeginTransaction()" in svc.FONTE_MOTOR
    assert "tx.Rollback()" in svc.FONTE_MOTOR
    assert "tx.Commit" not in svc.FONTE_MOTOR


# ---------------------------------------------------------------------------
# A encomenda e a última gravação
# ---------------------------------------------------------------------------


def test_encontra_a_encomenda_e_a_ultima_gravacao() -> None:
    consultas: list[str] = []

    def executar(_ligacao, sql):
        consultas.append(sql)
        return [{"ID": 7667, "NAME": "1610_01_26_JF_VIVA", "PRODUCTIONID": 9001, "GRAVADA": "2026-09-22 12:25:30"}]

    enc = svc.procurar_encomenda_imos("x", " 1610_01_26_JF_VIVA ", executar=executar)

    assert enc.proadmin_id == 7667
    assert enc.ultima_gravacao == datetime(2026, 9, 22, 12, 25, 30)
    assert enc.aviso == ""
    assert "NAME = N'1610_01_26_JF_VIVA'" in consultas[0]
    assert consultas[0].lstrip().upper().startswith("SELECT")


def test_plica_no_nome_nao_parte_a_consulta() -> None:
    consultas: list[str] = []

    def executar(_l, sql):
        consultas.append(sql)
        return [{"ID": 1, "NAME": "D'ARC", "GRAVADA": None}]

    enc = svc.procurar_encomenda_imos("x", "D'ARC", executar=executar)
    assert "N'D''ARC'" in consultas[0]
    assert enc.ultima_gravacao is None


def test_encomenda_inexistente_explica_o_que_confirmar() -> None:
    with pytest.raises(ValueError, match="Nome Enc IMOS IX"):
        svc.procurar_encomenda_imos("x", "NAO_EXISTE", executar=lambda *_: [])
    with pytest.raises(ValueError, match="Nome Enc IMOS IX"):
        svc.procurar_encomenda_imos("x", "  ", executar=lambda *_: [])


def test_nome_repetido_usa_a_gravada_mais_recentemente_e_avisa() -> None:
    linhas = [
        {"ID": 8, "NAME": "OBRA", "PRODUCTIONID": 1, "GRAVADA": "2026-09-28 10:00:00"},
        {"ID": 5, "NAME": "OBRA", "PRODUCTIONID": 2, "GRAVADA": "2026-09-01 10:00:00"},
    ]
    enc = svc.procurar_encomenda_imos("x", "OBRA", executar=lambda *_: linhas)
    assert enc.proadmin_id == 8
    assert "2 encomendas" in enc.aviso


def test_o_dir_id_da_obra_manda_sobre_o_nome() -> None:
    linhas = [
        {"ID": 8, "NAME": "OBRA", "PRODUCTIONID": 1, "GRAVADA": "2026-09-28 10:00:00"},
        {"ID": 5, "NAME": "OBRA", "PRODUCTIONID": 2, "GRAVADA": "2026-09-01 10:00:00"},
    ]
    consultas: list[str] = []

    def executar(_l, sql):
        consultas.append(sql)
        return linhas

    enc = svc.procurar_encomenda_imos("x", "OBRA", dir_id=2, executar=executar)
    assert enc.proadmin_id == 5 and enc.aviso == ""
    assert "PRODUCTIONID = 2" in consultas[0]


def test_library_path_sai_da_pasta_das_imagens() -> None:
    assert svc._pasta_library(r"I:\Library\Info\BITMAPS") == r"I:\Library"
    assert svc._pasta_library(r"J:\Lib\info\bitmaps\\") == r"J:\Lib"
    assert svc._pasta_library("") == svc.DEFAULT_PASTA_LIBRARY
    assert svc._pasta_library(r"X:\outra") == svc.DEFAULT_PASTA_LIBRARY


# ---------------------------------------------------------------------------
# O motor
# ---------------------------------------------------------------------------


def _pasta_motor(base: Path, nome: str, *, completa: bool = True) -> Path:
    pasta = base / nome
    pasta.mkdir(parents=True)
    dlls = svc._DLLS_OBRIGATORIAS if completa else svc._DLLS_OBRIGATORIAS[:1]
    for dll in dlls:
        (pasta / dll).write_bytes(b"dll")
    return pasta


def test_candidatos_do_motor(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(svc, "_versao_ficheiro", lambda _c: (15, 0))
    configurada = _pasta_motor(tmp_path, "config")
    imos = _pasta_motor(tmp_path, "imos2023")
    incompleta = _pasta_motor(tmp_path, "incompleta", completa=False)

    candidatos = svc.candidatos_motor(str(configurada), raizes=[incompleta, imos, configurada])

    assert candidatos == [configurada, imos]


def test_o_motor_do_imos_2025_para_net8_nao_serve(tmp_path, monkeypatch) -> None:
    pasta = _pasta_motor(tmp_path, "imos2025")
    monkeypatch.setattr(svc, "_versao_ficheiro", lambda _c: (15, 1))
    assert svc.candidatos_motor(raizes=[pasta]) == []


def test_motor_e_compilado_uma_vez_e_depois_reaproveitado(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(svc, "_versao_ficheiro", lambda _c: (15, 0))
    pasta = _pasta_motor(tmp_path, "imos2023")
    compilacoes: list[Path] = []

    def compilar(_dlls, destino):
        compilacoes.append(destino)
        destino.mkdir(parents=True, exist_ok=True)
        (destino / svc.NOME_EXE_MOTOR).write_bytes(b"exe")
        return destino / svc.NOME_EXE_MOTOR

    cache = tmp_path / "cache"
    exe1 = svc.preparar_motor(raizes=[pasta], cache=cache, compilar=compilar)
    exe2 = svc.preparar_motor(raizes=[pasta], cache=cache, compilar=compilar)

    assert exe1 == exe2 and exe1.is_file()
    assert len(compilacoes) == 1


def test_se_um_motor_falha_tenta_o_seguinte(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(svc, "_versao_ficheiro", lambda _c: (15, 0))
    mau = _pasta_motor(tmp_path, "mau")
    bom = _pasta_motor(tmp_path, "bom")

    def compilar(dlls, destino):
        if dlls == mau:
            raise RuntimeError("não arrancou")
        destino.mkdir(parents=True, exist_ok=True)
        (destino / svc.NOME_EXE_MOTOR).write_bytes(b"exe")
        return destino / svc.NOME_EXE_MOTOR

    exe = svc.preparar_motor(raizes=[mau, bom], cache=tmp_path / "cache", compilar=compilar)
    assert exe.is_file()


def test_sem_motor_explica_onde_procurou(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="pasta_motor_relatorios") as erro:
        svc.preparar_motor(raizes=[tmp_path / "nada"], cache=tmp_path / "cache")
    assert str(tmp_path / "nada") in str(erro.value)


def test_saida_do_motor_e_interpretada(tmp_path, monkeypatch) -> None:
    saida = tmp_path / "lista.xlsx"

    def correr(cmd, *, timeout, env=None):
        assert env["MARTELO_IMOS_CONN"] == "ligacao-secreta"
        parametros = Path(cmd[3]).read_text(encoding="utf-8")
        assert "PARAM\tORDERLIST\t7667" in parametros
        assert "FOLHA\t4_Etiqueta_Palete" in parametros
        assert "ligacao-secreta" not in parametros  # a ligação nunca vai para ficheiro
        saida.write_bytes(b"x")
        stdout = (
            "DATASET\tA\t10\t5\nDATASET\tB\t3\t1\nRENDER\t999\t40\n"
            "AVISO\trsWarningFetchingExternalImages\tignorar\n"
            "AVISO\trsInvalidImageReference\tThe ImageData for the image 'Logo' is invalid\n"
            "AVISO\trsOutro\tUm aviso que interessa\n"
        )
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(svc, "_correr", correr)
    config = svc.ConfigListasImos(
        ligacao="ligacao-secreta", pasta_rdl=tmp_path, pasta_motor="", parametros={"mm2inch": "MM"}
    )
    resultado = svc.correr_motor(
        tmp_path / "m.exe", config, tmp_path / "x.rdl", saida, proadmin_id=7667, folha="4_Etiqueta_Palete"
    )
    assert resultado.ok
    assert resultado.linhas == 13
    assert resultado.avisos == ["Um aviso que interessa"]


def test_erro_de_tempo_do_sql_e_explicado(tmp_path, monkeypatch) -> None:
    def correr(cmd, *, timeout, env=None):
        return subprocess.CompletedProcess(
            cmd, 1, stdout="ERRO\tSqlException\tTempo Limite de Execução Expirado.\n", stderr=""
        )

    monkeypatch.setattr(svc, "_correr", correr)
    config = svc.ConfigListasImos(ligacao="x", pasta_rdl=tmp_path, pasta_motor="", parametros={})
    resultado = svc.correr_motor(
        tmp_path / "m.exe", config, tmp_path / "x.rdl", tmp_path / "s.xlsx", proadmin_id=1, folha="f"
    )
    assert not resultado.ok
    assert "não respondeu a tempo" in resultado.erro


# ---------------------------------------------------------------------------
# Marca e pasta da obra
# ---------------------------------------------------------------------------


def _encomenda(gravacao: datetime | None = datetime(2026, 9, 22, 12, 25, 30)) -> svc.EncomendaImos:
    return svc.EncomendaImos(proadmin_id=7667, nome="1610_01_26_JF_VIVA", ultima_gravacao=gravacao)


def test_marca_de_origem_ida_e_volta(tmp_path) -> None:
    livro = _xlsx(tmp_path / "l.xlsx", b"<conteudo-intocado/>")
    svc.marcar_origem(livro, svc.texto_marca(_encomenda(), datetime(2026, 9, 29, 11, 0)))

    marca, gravacao = svc.ler_marca(livro)
    assert svc.MARCA_MARTELO in marca and "ID 7667" in marca
    assert gravacao == datetime(2026, 9, 22, 12, 25, 30)
    with zipfile.ZipFile(livro) as z:
        assert z.read("xl/workbook.xml") == b"<conteudo-intocado/>"
        # O ReportViewer escreve «meatadata» e o Excel ignorava as propriedades.
        assert b"relationships/metadata/core-properties" in z.read("_rels/.rels")
        assert b"Martelo V3" in z.read("docProps/core.xml")


def test_lista_do_imos_nao_tem_marca(tmp_path) -> None:
    assert svc.ler_marca(_xlsx(tmp_path / "imos.xlsx")) == ("", None)
    assert svc.ler_marca(tmp_path / "nao_existe.xlsx") == ("", None)


def test_a_anterior_vai_para_a_subpasta_com_a_sua_data(tmp_path) -> None:
    lista = _xlsx(tmp_path / "2_List_Ferragens.xlsx")
    _mtime(lista, datetime(2026, 9, 22, 15, 14, 0))

    guardada = svc.guardar_anterior(lista)

    assert guardada == tmp_path / svc.PASTA_ANTERIORES / "2_List_Ferragens_20260922_151400.xlsx"
    assert guardada.is_file() and not lista.exists()

    outra = _xlsx(tmp_path / "2_List_Ferragens.xlsx")
    _mtime(outra, datetime(2026, 9, 22, 15, 14, 0))
    assert svc.guardar_anterior(outra).name == "2_List_Ferragens_20260922_151400_2.xlsx"


def test_gravar_na_obra_substitui_sem_perder_a_anterior(tmp_path) -> None:
    obra = tmp_path / "obra"
    obra.mkdir()
    lista = svc.lista_por_chave("2_List_Ferragens")
    antiga = _xlsx(obra / lista.nome_ficheiro, b"<antiga/>")
    _mtime(antiga, datetime(2026, 9, 22, 15, 14, 0))
    nova = _xlsx(tmp_path / "gerada.xlsx", b"<nova/>")

    destino, anterior = svc.gravar_na_obra(nova, obra, lista)

    with zipfile.ZipFile(destino) as z:
        assert z.read("xl/workbook.xml") == b"<nova/>"
    with zipfile.ZipFile(anterior) as z:
        assert z.read("xl/workbook.xml") == b"<antiga/>"
    assert sorted(p.name for p in obra.iterdir()) == [lista.nome_ficheiro, svc.PASTA_ANTERIORES]


def test_lista_aberta_no_excel_da_um_erro_claro(tmp_path, monkeypatch) -> None:
    obra = tmp_path / "obra"
    obra.mkdir()
    lista = svc.lista_por_chave("4_Etiqueta_Palete")
    _xlsx(obra / lista.nome_ficheiro, b"<antiga/>")

    def bloqueado(origem, destino):
        if Path(origem).name == lista.nome_ficheiro:
            raise PermissionError("em uso")
        return os_replace(origem, destino)

    os_replace = os.replace
    monkeypatch.setattr(svc.os, "replace", bloqueado)
    with pytest.raises(ValueError, match="aberta"):
        svc.gravar_na_obra(_xlsx(tmp_path / "nova.xlsx", b"<nova/>"), obra, lista)
    with zipfile.ZipFile(obra / lista.nome_ficheiro) as z:
        assert z.read("xl/workbook.xml") == b"<antiga/>"
    assert [p.name for p in obra.iterdir() if p.is_file()] == [lista.nome_ficheiro]


# ---------------------------------------------------------------------------
# Situação das listas
# ---------------------------------------------------------------------------


def _estado(estados, chave):
    return next(e for e in estados if e.lista.chave == chave)


def test_situacao_das_listas(tmp_path) -> None:
    obra = tmp_path / "obra"
    obra.mkdir()
    saida_imos = tmp_path / "IMOS_Output_Batches"
    saida_imos.mkdir()
    enc = _encomenda()

    # Do Martelo, da última gravação -> atualizada.
    martelo = _xlsx(obra / "2_List_Ferragens.xlsx")
    svc.marcar_origem(martelo, svc.texto_marca(enc))
    # Do Martelo, de uma gravação anterior -> desatualizada (mesmo que o ficheiro seja novo).
    antiga = _xlsx(obra / "5_Custo_Obra_Ferragens.xlsx")
    svc.marcar_origem(antiga, svc.texto_marca(_encomenda(datetime(2026, 9, 20, 9, 0))))
    # Do iMos, gerada antes da gravação -> desatualizada pela data do ficheiro.
    imos = _xlsx(obra / "3_Resumo_Precos.xlsx")
    _mtime(imos, datetime(2026, 9, 21, 9, 0))
    # Em falta na obra, mas há uma do iMos por importar.
    _xlsx(saida_imos / "1610_01_26_JF_VIVA_4_Etiqueta_Palete.xlsx")

    estados = svc.estado_listas(obra, enc.nome, enc, pasta_saida_imos=saida_imos)

    assert _estado(estados, "2_List_Ferragens").situacao == svc.SITUACAO_ATUALIZADA
    assert _estado(estados, "2_List_Ferragens").origem == "Martelo"
    assert _estado(estados, "5_Custo_Obra_Ferragens").situacao == svc.SITUACAO_DESATUALIZADA
    assert _estado(estados, "3_Resumo_Precos").situacao == svc.SITUACAO_DESATUALIZADA
    assert _estado(estados, "3_Resumo_Precos").origem == "iMos"
    etiqueta = _estado(estados, "4_Etiqueta_Palete")
    assert etiqueta.situacao == svc.SITUACAO_EM_FALTA
    assert etiqueta.pendente_imos is not None


def test_lista_do_imos_mais_antiga_que_a_da_obra_nao_fica_pendente(tmp_path) -> None:
    obra = tmp_path / "obra"
    obra.mkdir()
    saida_imos = tmp_path / "saida"
    saida_imos.mkdir()
    na_obra = _xlsx(obra / "2_List_Ferragens.xlsx")
    velha = _xlsx(saida_imos / "OBRA_2_List_Ferragens.xlsx")
    _mtime(velha, datetime(2026, 9, 1, 9, 0))
    _mtime(na_obra, datetime(2026, 9, 29, 9, 0))

    estado = _estado(svc.estado_listas(obra, "OBRA", None, pasta_saida_imos=saida_imos), "2_List_Ferragens")
    assert estado.pendente_imos is None
    assert estado.situacao == svc.SITUACAO_SEM_DATA


# ---------------------------------------------------------------------------
# Tudo junto
# ---------------------------------------------------------------------------


def test_gerar_listas_continua_quando_uma_falha(tmp_path) -> None:
    pasta_rdl = tmp_path / "rdl"
    pasta_rdl.mkdir()
    obra = tmp_path / "obra"
    obra.mkdir()
    for lista in svc.LISTAS_IMOS:
        _rdl(pasta_rdl / lista.ficheiro_rdl, "SELECT 1")
    # Um .rdl que alguém alterou para escrever na base: é recusado.
    _rdl(pasta_rdl / svc.lista_por_chave("3_Resumo_Precos").ficheiro_rdl, "UPDATE PROADMIN SET X=1")
    # Outro que falta na pasta.
    (pasta_rdl / svc.lista_por_chave("4_Etiqueta_Palete").ficheiro_rdl).unlink()

    corridas: list[tuple[str, int]] = []

    def executar(exe, config, rdl, saida, *, proadmin_id, folha):
        corridas.append((folha, proadmin_id))
        if folha == "5_Custo_Obra_Ferragens":
            return svc.ResultadoMotor(ok=False, erro="A base do iMos não respondeu a tempo")
        _xlsx(saida)
        return svc.ResultadoMotor(ok=True, linhas=4, segundos=1.0)

    progresso: list[str] = []
    config = svc.ConfigListasImos(ligacao="x", pasta_rdl=pasta_rdl, pasta_motor="", parametros={})
    resultado = svc.gerar_listas(
        config,
        pasta_obra=obra,
        nome_enc="1610_01_26_JF_VIVA",
        listas=svc.LISTAS_IMOS,
        ao_progresso=lambda _i, _n, texto: progresso.append(texto),
        procurar=lambda *_a, **_k: _encomenda(),
        motor=lambda _pasta: tmp_path / "motor.exe",
        executar=executar,
    )

    assert [r.lista.chave for r in resultado.geradas] == ["2_List_Ferragens"]
    erros = {r.lista.chave: r.erro for r in resultado.falhadas}
    assert "não é só de leitura" in erros["3_Resumo_Precos"]
    assert "Não encontrei o relatório" in erros["4_Etiqueta_Palete"]
    assert "não respondeu a tempo" in erros["5_Custo_Obra_Ferragens"]
    # O .rdl que escreve nem chega ao motor.
    assert [f for f, _ in corridas] == ["2_List_Ferragens", "5_Custo_Obra_Ferragens"]
    assert all(pid == 7667 for _, pid in corridas)
    assert svc.ler_marca(obra / "2_List_Ferragens.xlsx")[1] == datetime(2026, 9, 22, 12, 25, 30)
    assert progresso[-1] == "Concluído."


def test_gerar_listas_le_a_gravacao_no_momento(tmp_path) -> None:
    """Grava-se o desenho com o ecrã aberto: a marca tem de ser a de agora."""
    pasta_rdl = tmp_path / "rdl"
    pasta_rdl.mkdir()
    obra = tmp_path / "obra"
    obra.mkdir()
    lista = svc.lista_por_chave("5_Custo_Obra_Ferragens")
    _rdl(pasta_rdl / lista.ficheiro_rdl, "SELECT 1")
    agora = datetime(2026, 9, 29, 10, 42, 0)
    config = svc.ConfigListasImos(ligacao="x", pasta_rdl=pasta_rdl, pasta_motor="", parametros={})

    resultado = svc.gerar_listas(
        config,
        pasta_obra=obra,
        nome_enc="OBRA",
        listas=[lista],
        procurar=lambda *_a, **_k: _encomenda(agora),
        motor=lambda _pasta: tmp_path / "motor.exe",
        executar=lambda *a, **k: (_xlsx(a[3]), svc.ResultadoMotor(ok=True))[1],
    )

    assert resultado.encomenda.ultima_gravacao == agora
    assert svc.ler_marca(obra / lista.nome_ficheiro)[1] == agora


def test_pasta_da_obra_inexistente(tmp_path) -> None:
    config = svc.ConfigListasImos(ligacao="x", pasta_rdl=tmp_path, pasta_motor="", parametros={})
    with pytest.raises(ValueError, match="não existe"):
        svc.gerar_listas(config, pasta_obra=tmp_path / "nada", nome_enc="X", listas=svc.LISTAS_IMOS)


def test_as_quatro_listas_e_os_seus_rdl() -> None:
    assert [(l.chave, l.ficheiro_rdl) for l in svc.LISTAS_IMOS] == [
        ("2_List_Ferragens", "2_Lista_Ferr_Acessorios.rdl"),
        ("3_Resumo_Precos", "4_Resumo_Custos_Encomenda.rdl"),
        ("4_Etiqueta_Palete", "5_Etiqueta_Palete.rdl"),
        ("5_Custo_Obra_Ferragens", "5_Custo_Obra_Ferragens_V1.rdl"),
    ]


def test_marca_fica_em_xml_valido_mesmo_sem_o_prefixo_dc(tmp_path) -> None:
    """Um core.xml sem xmlns:dc ficava inválido e o Excel queixava-se."""
    import xml.etree.ElementTree as ET

    livro = tmp_path / "sem_dc.xlsx"
    with zipfile.ZipFile(livro, "w") as z:
        z.writestr("docProps/core.xml", '<cp:coreProperties xmlns:cp="x"></cp:coreProperties>')
    svc.marcar_origem(livro, svc.texto_marca(_encomenda()) + " & <teste>")

    with zipfile.ZipFile(livro) as z:
        ET.fromstring(z.read("docProps/core.xml"))  # não rebenta
    marca, gravacao = svc.ler_marca(livro)
    assert marca.endswith(" & <teste>")
    assert gravacao == datetime(2026, 9, 22, 12, 25, 30)


def test_imagem_em_falta_e_dita_em_portugues_numa_linha() -> None:
    """O motor dá dois avisos em inglês por cada imagem que não encontra."""
    primeiro = svc._aviso_em_portugues(
        "rsInvalidImageReference",
        "The ImageData for the image 'Image2' is invalid. Details: Não foi possível "
        r"localizar o ficheiro 'I:\Library\LOGO_CLIENTE\468.png'.",
    )
    segundo = svc._aviso_em_portugues(
        "rsInvalidExternalImageProperty",
        "The value of the ImageData property for the image 'Image2' is '', which is not a valid ImageData.",
    )
    assert primeiro == r"Imagem não encontrada: I:\Library\LOGO_CLIENTE\468.png"
    assert segundo == ""
    assert svc._aviso_em_portugues("rsInvalidImageReference", "image 'Logo' is invalid") == ""
    assert svc._aviso_em_portugues("rsOutro", "Outro aviso") == "Outro aviso"
