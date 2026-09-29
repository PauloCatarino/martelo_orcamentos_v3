"""Gerar no Martelo as listas de ferragens que o iMos exporta a partir de .rdl.

O iMos gera estas listas com o motor de relatórios da Microsoft (ReportViewer)
a partir dos .rdl de ``I:\\Listas_SQL\\LISTA_FERR_ACESSORIOS``. O Martelo usa o
MESMO motor e os MESMOS .rdl: quem muda um .rdl no Report Builder muda a lista
nos dois sítios, sem nada duplicado aqui.

Três regras que não se negoceiam:

* **Só leitura na base do iMos.** O SQL de cada .rdl é verificado antes de
  correr (só pode escrever em tabelas temporárias ``#...``) e corre numa
  transação que é SEMPRE desfeita no fim. A conta configurada no Martelo pode
  escrever no iMos, por isso a proteção não pode depender dela.
* **Nada se perde na pasta da obra.** A lista vai direta para a pasta da obra,
  com o nome que a macro da Lista Material procura; a que lá estava passa
  para ``Listas_IMOS_anteriores`` com a data em que tinha sido gerada.
* **Cada lista sabe de que gravação saiu.** O Martelo escreve nas propriedades
  do ficheiro a hora da gravação do desenho no iMos (``PROADMIN.LCHANGE``) —
  é isso que permite dizer se a lista da pasta está atualizada.
"""

from __future__ import annotations

import hashlib
import html
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Sequence

from sqlalchemy.orm import Session

from app.services.imos_imagem_service import KEY_PASTA_BASE_IMORDER
from app.services.imos_sql import build_connection_string, load_imos_config
from app.services.phc_sql import run_select
from app.services.system_setting_service import SystemSettingService

KEY_PASTA_LISTAS_RDL = "pasta_listas_imos_rdl"
DEFAULT_PASTA_LISTAS_RDL = r"I:\Listas_SQL\LISTA_FERR_ACESSORIOS"
# Pasta com as DLLs do ReportViewer, para os PCs onde não se encontrem sozinhas.
KEY_PASTA_MOTOR_RELATORIOS = "pasta_motor_relatorios"
KEY_PASTA_IMAGENS_IMOS = "pasta_imagens_imos"
DEFAULT_PASTA_LIBRARY = r"I:\Library"
DEFAULT_PASTA_IMORDER = r"I:\Factory\Imorder"

# Onde o iMos deixa as listas. O Martelo não escreve aqui: só olha, para
# avisar quando há uma lista do iMos mais recente do que a da pasta da obra.
PASTA_SAIDA_IMOS = Path(r"C:\IMOS_Output_Batches")
PASTA_ANTERIORES = "Listas_IMOS_anteriores"

MARCA_MARTELO = "Gerada pelo Martelo V3"
FORMATO_GRAVACAO = "%Y-%m-%d %H:%M:%S"

SITUACAO_EM_FALTA = "em_falta"
SITUACAO_ATUALIZADA = "atualizada"
SITUACAO_DESATUALIZADA = "desatualizada"
SITUACAO_SEM_DATA = "sem_data"

NOME_EXE_MOTOR = "GerarListaImos.exe"
TIMEOUT_SQL_SEGUNDOS = 600


@dataclass(frozen=True)
class ListaImos:
    """Uma das listas do iMos (a chave é também o nome do ficheiro)."""

    chave: str
    ficheiro_rdl: str
    titulo: str
    descricao: str
    # Vem marcada na janela? O Resumo não: vai ser descontinuado (29-09-2026).
    marcada_por_defeito: bool = True

    @property
    def nome_ficheiro(self) -> str:
        return f"{self.chave}.xlsx"


LISTAS_IMOS: tuple[ListaImos, ...] = (
    ListaImos(
        "2_List_Ferragens",
        "2_Lista_Ferr_Acessorios.rdl",
        "Lista de ferragens",
        "Ferragens, Purchased Parts e SPP, com imagens. Entra na Lista Material "
        "nos separadores 1_FERRAGENS, 2_PURCH e 3_SPP.",
    ),
    ListaImos(
        "3_Resumo_Precos",
        "4_Resumo_Custos_Encomenda.rdl",
        "Resumo de preços",
        "Resumo global de preços do iMos (separador 4_Resumo_Global_Precos). "
        "Vai ser descontinuada: para custos vale a 5_Custo_Obra_Ferragens.",
        marcada_por_defeito=False,
    ),
    ListaImos(
        "4_Etiqueta_Palete",
        "5_Etiqueta_Palete.rdl",
        "Etiqueta da palete",
        "Folha da etiqueta de palete com a imagem da obra (separador "
        "5_ETIQUETA_PALETE).",
    ),
    ListaImos(
        "5_Custo_Obra_Ferragens",
        "5_Custo_Obra_Ferragens_V1.rdl",
        "Custo de obra — ferragens",
        "Uma linha por referência, com as chaves de ligação ao Martelo "
        "(separador 5_Custo_Obra_Ferragens e análise de custos).",
    ),
)


def lista_por_chave(chave: str) -> ListaImos:
    for lista in LISTAS_IMOS:
        if lista.chave == chave:
            return lista
    raise KeyError(chave)


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfigListasImos:
    """Tudo o que a geração precisa, lido da base do Martelo de uma vez.

    A geração corre numa thread à parte e não pode usar a sessão SQLAlchemy.
    """

    ligacao: str = field(repr=False)
    pasta_rdl: Path
    pasta_motor: str
    parametros: dict[str, str]


def _pasta_library(pasta_imagens: str) -> str:
    """``I:\\Library\\Info\\BITMAPS`` -> ``I:\\Library`` (o que os .rdl esperam)."""
    texto = str(pasta_imagens or "").strip().rstrip("\\/")
    if not texto:
        return DEFAULT_PASTA_LIBRARY
    caminho = Path(texto)
    partes = [parte.casefold() for parte in caminho.parts[-2:]]
    if partes == ["info", "bitmaps"]:
        return str(caminho.parent.parent)
    return DEFAULT_PASTA_LIBRARY


def carregar_config(session: Session) -> ConfigListasImos:
    """Lê a ligação ao iMos e as pastas. Falha com uma mensagem para o ecrã."""
    settings = SystemSettingService(session)

    def _valor(chave: str, default: str) -> str:
        return str(settings.obter_valor(chave, default) or "").strip() or default

    ligacao = build_connection_string(load_imos_config(session))
    return ConfigListasImos(
        ligacao=ligacao,
        pasta_rdl=Path(_valor(KEY_PASTA_LISTAS_RDL, DEFAULT_PASTA_LISTAS_RDL)),
        pasta_motor=str(settings.obter_valor(KEY_PASTA_MOTOR_RELATORIOS, "") or "").strip(),
        parametros={
            "LIBRARYPATH": _pasta_library(_valor(KEY_PASTA_IMAGENS_IMOS, "")),
            "IMORDERPATH": _valor(KEY_PASTA_BASE_IMORDER, DEFAULT_PASTA_IMORDER),
            "mm2inch": "MM",
        },
    )


# ---------------------------------------------------------------------------
# A encomenda no iMos e a hora da última gravação
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EncomendaImos:
    proadmin_id: int
    nome: str
    ultima_gravacao: datetime | None
    aviso: str = ""


def _data_sql(valor) -> datetime | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        return datetime.strptime(texto[:19], FORMATO_GRAVACAO)
    except ValueError:
        return None


def procurar_encomenda_imos(
    ligacao: str,
    nome_enc: str,
    *,
    dir_id: int | None = None,
    executar: Callable[[str, str], list[dict]] = run_select,
) -> EncomendaImos:
    """Encontra a encomenda da obra no iMos e a hora da última gravação.

    ``LCHANGE`` muda quando o desenho é gravado no iMos (confere com a data do
    ``.DWG``). Quando a obra foi criada pelo Martelo no iMos sabe-se o
    ``DIR_ID``, que identifica a encomenda sem ambiguidade; senão vai pelo nome.
    """
    nome = str(nome_enc or "").strip()
    if not nome:
        raise ValueError(
            "Falta o Nome Enc IMOS IX da obra: é por ele que o Martelo encontra "
            "a encomenda no iMos."
        )
    literal = nome.replace("'", "''")
    condicao = f"NAME = N'{literal}'"
    if dir_id:
        condicao = f"({condicao} OR PRODUCTIONID = {int(dir_id)})"
    linhas = executar(
        ligacao,
        "SELECT ID, NAME, PRODUCTIONID, CONVERT(varchar(19), LCHANGE, 120) AS GRAVADA "
        f"FROM PROADMIN WHERE {condicao} ORDER BY LCHANGE DESC",
    )
    if not linhas:
        raise ValueError(
            f"Não encontrei no iMos a encomenda «{nome}».\n\n"
            "Confirme o Nome Enc IMOS IX da obra: tem de ser igual ao nome da "
            "encomenda no iMos."
        )

    escolhida = None
    if dir_id:
        escolhida = next(
            (l for l in linhas if str(l.get("PRODUCTIONID") or "").strip() == str(int(dir_id))),
            None,
        )
    aviso = ""
    if escolhida is None:
        pelo_nome = [
            l for l in linhas if str(l.get("NAME") or "").strip().casefold() == nome.casefold()
        ] or linhas
        escolhida = pelo_nome[0]
        if len(pelo_nome) > 1:
            aviso = (
                f"Há {len(pelo_nome)} encomendas com o nome «{nome}» no iMos; "
                f"usei a gravada mais recentemente (ID {escolhida.get('ID')})."
            )
    return EncomendaImos(
        proadmin_id=int(escolhida.get("ID")),
        nome=str(escolhida.get("NAME") or nome).strip(),
        ultima_gravacao=_data_sql(escolhida.get("GRAVADA")),
        aviso=aviso,
    )


# ---------------------------------------------------------------------------
# Verificação do SQL dos .rdl (só leitura)
# ---------------------------------------------------------------------------

_SEMPRE_PROIBIDAS = (
    "EXEC", "EXECUTE", "GRANT", "REVOKE", "DENY", "BACKUP", "RESTORE", "DBCC",
    "SHUTDOWN", "KILL", "OPENROWSET", "OPENQUERY", "OPENDATASOURCE", "BULK",
    "RECONFIGURE",
)
# Escritas que só são aceites quando o alvo é uma tabela temporária (#) ou
# uma variável de tabela (@).
_ESCRITAS_COM_ALVO = (
    (r"\bINSERT\s+(?:INTO\s+)?([^\s(]+)", "INSERT"),
    (r"\bUPDATE\s+([^\s(]+)", "UPDATE"),
    (r"\bDELETE\s+(?:FROM\s+)?([^\s(]+)", "DELETE"),
    (r"\bMERGE\s+(?:INTO\s+)?([^\s(]+)", "MERGE"),
    (r"\bTRUNCATE\s+TABLE\s+([^\s(;]+)", "TRUNCATE"),
    (r"\b(?:CREATE|ALTER|DROP)\s+TABLE\s+(?:IF\s+EXISTS\s+)?([^\s(;]+)", "TABLE"),
    (r"\bINTO\s+([^\s(]+)", "INTO"),
)


def _sem_comentarios_nem_textos(sql: str) -> str:
    """Tira comentários e textos entre plicas: as palavras lá dentro não contam."""
    sem_blocos = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sem_linhas = re.sub(r"--[^\n]*", " ", sem_blocos)
    return re.sub(r"N?'(?:[^']|'')*'", "''", sem_linhas)


def _alvo_temporario(alvo: str) -> bool:
    alvo = alvo.strip().strip("[]")
    return alvo.startswith("#") or alvo.startswith("@")


def problemas_sql_rdl(sql: str) -> list[str]:
    """O que impede este SQL de correr no iMos. Lista vazia = só leitura."""
    codigo = _sem_comentarios_nem_textos(sql or "")
    problemas: list[str] = []
    for palavra in _SEMPRE_PROIBIDAS:
        if re.search(rf"\b{palavra}\b", codigo, flags=re.I):
            problemas.append(f"usa {palavra}")
    for padrao, rotulo in _ESCRITAS_COM_ALVO:
        for alvo in re.findall(padrao, codigo, flags=re.I):
            if not _alvo_temporario(alvo):
                problemas.append(f"{rotulo} em {alvo} (só são aceites tabelas temporárias #)")
    outros = re.findall(r"\b(CREATE|ALTER|DROP)\s+(?!TABLE\b)(\w+)", codigo, flags=re.I)
    for verbo, objeto in outros:
        problemas.append(f"{verbo.upper()} {objeto.upper()}")
    # Sem repetições, pela ordem em que apareceram.
    return list(dict.fromkeys(problemas))


@dataclass(frozen=True)
class DatasetRdl:
    nome: str
    sql: str


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def ler_rdl(caminho: Path) -> list[DatasetRdl]:
    """Lê os conjuntos de dados de um .rdl e recusa o que não seja só leitura."""
    try:
        raiz = ET.parse(caminho).getroot()
    except (ET.ParseError, OSError) as erro:
        raise ValueError(f"Não consegui ler o relatório {caminho.name}: {erro}") from erro

    datasets: list[DatasetRdl] = []
    problemas: list[str] = []
    for elemento in raiz.iter():
        if _local(elemento.tag) != "DataSet":
            continue
        nome = elemento.get("Name") or "?"
        query = next((f for f in elemento if _local(f.tag) == "Query"), None)
        if query is None:
            problemas.append(f"{nome}: não tem SQL próprio (conjunto partilhado)")
            continue
        filhos = {_local(f.tag): f for f in query}
        tipo = (filhos.get("CommandType").text or "").strip() if "CommandType" in filhos else ""
        if tipo and tipo != "Text":
            problemas.append(f"{nome}: é do tipo {tipo}, só SQL de texto é aceite")
        sql = filhos["CommandText"].text if "CommandText" in filhos else ""
        for problema in problemas_sql_rdl(sql or ""):
            problemas.append(f"{nome}: {problema}")
        datasets.append(DatasetRdl(nome=nome, sql=sql or ""))

    if problemas:
        raise ValueError(
            f"O relatório {caminho.name} não é só de leitura, por isso o Martelo "
            "não o corre na base do iMos:\n- " + "\n- ".join(problemas)
        )
    return datasets


# ---------------------------------------------------------------------------
# O motor (ReportViewer da Microsoft, o mesmo que o iMos usa)
# ---------------------------------------------------------------------------

# Código do pequeno programa que corre um .rdl. O Martelo compila-o no próprio
# PC com o compilador que vem com o Windows (.NET Framework), ao lado das DLLs
# do ReportViewer: é assim que o motor encontra as suas DLLs quando compila as
# expressões do relatório. C# 5 (é o que esse compilador aceita).
FONTE_MOTOR = r'''
// Motor das listas iMos do Martelo V3 (compilado pelo proprio Martelo).
// Uso: GerarListaImos.exe <rdl> <saida.xlsx> <parametros.txt> | --testar
// Ligacao SQL: variavel de ambiente MARTELO_IMOS_CONN.
// So' leitura: todas as queries correm numa transacao SEMPRE desfeita.
using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml;
using Microsoft.Reporting.WinForms;

static class GerarListaImos
{
    const string TESTE = "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        + "<Report xmlns=\"http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition\">"
        + "<ReportSections><ReportSection><Body><ReportItems>"
        + "<Textbox Name=\"T1\"><Paragraphs><Paragraph><TextRuns><TextRun>"
        + "<Value>=\"OK \" &amp; CStr(1 + 1)</Value></TextRun></TextRuns></Paragraph></Paragraphs>"
        + "<Top>0cm</Top><Left>0cm</Left><Height>1cm</Height><Width>5cm</Width></Textbox>"
        + "</ReportItems><Height>2cm</Height></Body><Width>6cm</Width>"
        + "<Page><PageHeight>29.7cm</PageHeight><PageWidth>21cm</PageWidth></Page>"
        + "</ReportSection></ReportSections></Report>";

    static void Saida(string tipo, params object[] campos)
    {
        var partes = new List<string>();
        partes.Add(tipo);
        foreach (var c in campos)
        {
            string t = Convert.ToString(c, CultureInfo.InvariantCulture) ?? "";
            partes.Add(t.Replace("\t", " ").Replace("\r", " ").Replace("\n", " "));
        }
        Console.WriteLine(string.Join("\t", partes.ToArray()));
    }

    static int Main(string[] args)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        try
        {
            if (args.Length == 1 && args[0] == "--testar")
            {
                var lr = new LocalReport();
                using (var sr = new StringReader(TESTE)) lr.LoadReportDefinition(sr);
                byte[] b = lr.Render("EXCELOPENXML");
                Saida("OK", typeof(LocalReport).Assembly.GetName().Version, b.Length);
                return 0;
            }
            if (args.Length < 3)
            {
                Saida("ERRO", "Argumentos", "Uso: GerarListaImos.exe <rdl> <saida> <parametros>");
                return 2;
            }
            return Gerar(args[0], args[1], args[2]);
        }
        catch (Exception e)
        {
            for (var x = e; x != null; x = x.InnerException) Saida("ERRO", x.GetType().Name, x.Message);
            return 1;
        }
    }

    static int Gerar(string rdl, string saida, string ficheiroParametros)
    {
        var sw = Stopwatch.StartNew();
        var parametros = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        string folha = null;
        int timeout = 600;
        foreach (var linha in File.ReadAllLines(ficheiroParametros, Encoding.UTF8))
        {
            var p = linha.Split('\t');
            if (p.Length >= 3 && p[0] == "PARAM") parametros[p[1]] = p[2];
            else if (p.Length >= 2 && p[0] == "FOLHA") folha = p[1];
            else if (p.Length >= 2 && p[0] == "TIMEOUT") timeout = int.Parse(p[1], CultureInfo.InvariantCulture);
        }
        string conn = Environment.GetEnvironmentVariable("MARTELO_IMOS_CONN");
        if (string.IsNullOrEmpty(conn))
        {
            Saida("ERRO", "Ligacao", "Ligacao ao iMos em falta.");
            return 1;
        }

        var doc = new XmlDocument();
        doc.PreserveWhitespace = true;
        doc.Load(rdl);
        var ns = new XmlNamespaceManager(doc.NameTable);
        ns.AddNamespace("r", doc.DocumentElement.NamespaceURI);

        // O iMos da' ao separador o nome da lista; sem isto sairia "Sheet1".
        if (!string.IsNullOrEmpty(folha) && doc.SelectSingleNode("/r:Report/r:InitialPageName", ns) == null)
        {
            var el = doc.CreateElement("InitialPageName", doc.DocumentElement.NamespaceURI);
            el.InnerText = folha;
            doc.DocumentElement.AppendChild(el);
        }

        var lr = new LocalReport();
        using (var sr = new StringReader(doc.OuterXml)) lr.LoadReportDefinition(sr);
        lr.EnableExternalImages = true;

        var refParam = new Regex(@"^=\s*Parameters!(\w+)\.Value\s*$", RegexOptions.IgnoreCase);
        using (var c = new SqlConnection(conn))
        {
            c.Open();
            var tx = c.BeginTransaction();
            try
            {
                foreach (XmlElement d in doc.SelectNodes("//r:DataSets/r:DataSet", ns))
                {
                    string nome = d.GetAttribute("Name");
                    var q = d.SelectSingleNode("r:Query", ns);
                    if (q == null) throw new InvalidOperationException("O conjunto " + nome + " nao tem SQL proprio.");
                    var tipo = q.SelectSingleNode("r:CommandType", ns);
                    if (tipo != null && tipo.InnerText.Trim() != "Text")
                        throw new InvalidOperationException("O conjunto " + nome + " nao e' SQL de texto.");
                    var cmd = c.CreateCommand();
                    cmd.Transaction = tx;
                    cmd.CommandText = q.SelectSingleNode("r:CommandText", ns).InnerText;
                    cmd.CommandTimeout = timeout;
                    foreach (XmlElement qp in q.SelectNodes("r:QueryParameters/r:QueryParameter", ns))
                    {
                        string valor = qp.SelectSingleNode("r:Value", ns).InnerText;
                        var m = refParam.Match(valor);
                        string v;
                        if (!m.Success || !parametros.TryGetValue(m.Groups[1].Value, out v))
                            throw new InvalidOperationException("Parametro sem valor: " + qp.GetAttribute("Name") + " = " + valor);
                        cmd.Parameters.AddWithValue(qp.GetAttribute("Name"), v);
                    }
                    var dt = new DataTable();
                    long t0 = sw.ElapsedMilliseconds;
                    new SqlDataAdapter(cmd).Fill(dt);
                    Saida("DATASET", nome, dt.Rows.Count, sw.ElapsedMilliseconds - t0);
                    lr.DataSources.Add(new ReportDataSource(nome, dt));
                }
            }
            finally
            {
                try { tx.Rollback(); } catch (InvalidOperationException) { }
            }
        }

        var lista = new List<ReportParameter>();
        foreach (XmlElement p in doc.SelectNodes("//r:ReportParameters/r:ReportParameter", ns))
        {
            string n = p.GetAttribute("Name");
            string v;
            if (parametros.TryGetValue(n, out v)) lista.Add(new ReportParameter(n, v));
        }
        lr.SetParameters(lista);

        long t1 = sw.ElapsedMilliseconds;
        Warning[] avisos; string[] streams; string mime, enc, ext;
        byte[] bytes = lr.Render("EXCELOPENXML", null, out mime, out enc, out ext, out streams, out avisos);
        File.WriteAllBytes(saida, bytes);
        Saida("RENDER", bytes.Length, sw.ElapsedMilliseconds - t1);
        foreach (var w in avisos) Saida("AVISO", w.Code, w.Message);
        return 0;
    }
}
'''

_DLLS_MOTOR = (
    "Microsoft.ReportViewer.Common.dll",
    "Microsoft.ReportViewer.WinForms.dll",
    "Microsoft.ReportViewer.ProcessingObjectModel.dll",
    "Microsoft.ReportViewer.DataVisualization.dll",
    "Microsoft.SqlServer.Types.dll",
)
_DLLS_OBRIGATORIAS = _DLLS_MOTOR[:2]


def _raizes_motor_por_defeito() -> list[Path]:
    """Onde costuma haver um ReportViewer instalado (iMos e SQL Management Studio)."""
    raizes: list[Path] = []
    for programas in (r"C:\Program Files", r"C:\Program Files (x86)"):
        base = Path(programas)
        # O iMos mais recente primeiro; cada versão tem a sua pasta BIN.
        raizes += sorted(base.glob(r"imos AG\*\BIN"), reverse=True)
        raizes += sorted(
            base.glob(r"Microsoft SQL Server Management Studio *\Common7\IDE"), reverse=True
        )
    return raizes


def _versao_ficheiro(caminho: Path) -> tuple[int, int] | None:
    try:
        import win32api  # type: ignore[import-not-found]

        info = win32api.GetFileVersionInfo(str(caminho), "\\")
        ms = info["FileVersionMS"]
        return (ms >> 16, ms & 0xFFFF)
    except Exception:  # noqa: BLE001 - sem pywin32 ou sem versão: não sabemos
        return None


def motor_compativel(pasta: Path) -> bool:
    """A pasta tem o ReportViewer para .NET Framework (15.0)?

    O iX CAD 2025 traz uma versão para .NET 8 (15.1): o compilador do Windows
    não a consegue usar. A do iX CAD 2023 e a do SQL Management Studio servem.
    """
    try:
        if not all((pasta / dll).is_file() for dll in _DLLS_OBRIGATORIAS):
            return False
    except OSError:
        return False
    versao = _versao_ficheiro(pasta / "Microsoft.ReportViewer.WinForms.dll")
    return versao is None or versao == (15, 0)


def candidatos_motor(
    pasta_configurada: str = "", *, raizes: Sequence[Path] | None = None
) -> list[Path]:
    """Pastas onde há um motor utilizável, pela ordem em que se tentam."""
    lista: list[Path] = []
    if str(pasta_configurada or "").strip():
        lista.append(Path(str(pasta_configurada).strip()))
    lista += list(raizes if raizes is not None else _raizes_motor_por_defeito())
    vistos: set[str] = set()
    resultado: list[Path] = []
    for pasta in lista:
        chave = str(pasta).casefold()
        if chave in vistos:
            continue
        vistos.add(chave)
        if motor_compativel(pasta):
            resultado.append(pasta)
    return resultado


def _compilador_csharp() -> Path:
    windir = Path(os.environ.get("WINDIR") or r"C:\Windows")
    for pasta in ("Framework64", "Framework"):
        csc = windir / "Microsoft.NET" / pasta / "v4.0.30319" / "csc.exe"
        if csc.is_file():
            return csc
    raise RuntimeError(
        "Não encontrei o compilador do .NET Framework (csc.exe) neste PC; "
        "sem ele o Martelo não consegue preparar o motor das listas."
    )


def _pasta_cache_motor() -> Path:
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    return Path(base) / "Martelo_Orcamentos_V3" / "motor_listas_imos"


def _impressao_motor(pasta_dlls: Path) -> str:
    """Muda quando muda o código do motor ou as DLLs de onde é feito."""
    h = hashlib.sha1(FONTE_MOTOR.encode("utf-8"))
    for dll in _DLLS_MOTOR:
        caminho = pasta_dlls / dll
        if caminho.is_file():
            estado = caminho.stat()
            h.update(f"{dll}|{estado.st_size}|{int(estado.st_mtime)}".encode())
    h.update(str(pasta_dlls).casefold().encode("utf-8"))
    return h.hexdigest()[:12]


def _correr(cmd: list[str], *, timeout: int, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=timeout,
        env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )


def _compilar_motor(pasta_dlls: Path, destino: Path) -> Path:
    """Compila o motor numa pasta nova, ao lado de cópias das DLLs, e testa-o."""
    destino.mkdir(parents=True, exist_ok=True)
    for dll in _DLLS_MOTOR:
        origem = pasta_dlls / dll
        if origem.is_file():
            shutil.copy2(origem, destino / dll)
    fonte = destino / "GerarListaImos.cs"
    fonte.write_text(FONTE_MOTOR, encoding="utf-8")
    exe = destino / NOME_EXE_MOTOR
    resultado = _correr(
        [
            str(_compilador_csharp()),
            "/nologo",
            "/target:exe",
            "/optimize+",
            f"/out:{exe}",
            f"/r:{destino / 'Microsoft.ReportViewer.WinForms.dll'}",
            f"/r:{destino / 'Microsoft.ReportViewer.Common.dll'}",
            "/r:System.Data.dll",
            "/r:System.Xml.dll",
            str(fonte),
        ],
        timeout=120,
    )
    if resultado.returncode != 0 or not exe.is_file():
        raise RuntimeError(
            "A compilação do motor falhou:\n" + (resultado.stdout or resultado.stderr or "")[-1500:]
        )
    teste = _correr([str(exe), "--testar"], timeout=120)
    if teste.returncode != 0 or not teste.stdout.startswith("OK"):
        raise RuntimeError(
            "O motor foi compilado mas não arrancou:\n" + (teste.stdout or teste.stderr or "")[-1500:]
        )
    return exe


def preparar_motor(
    pasta_configurada: str = "",
    *,
    raizes: Sequence[Path] | None = None,
    cache: Path | None = None,
    compilar: Callable[[Path, Path], Path] = _compilar_motor,
) -> Path:
    """Devolve o executável do motor, compilando-o da primeira vez neste PC."""
    candidatos = candidatos_motor(pasta_configurada, raizes=raizes)
    if not candidatos:
        onde = [str(p) for p in ([Path(pasta_configurada)] if pasta_configurada else [])]
        onde += [str(p) for p in (raizes if raizes is not None else _raizes_motor_por_defeito())]
        raise RuntimeError(
            "Não encontrei neste PC o motor de relatórios da Microsoft "
            "(ReportViewer para .NET Framework), que é o que o iMos usa para "
            "gerar estas listas.\n\nProcurei em:\n- "
            + ("\n- ".join(onde) or "(nenhuma pasta)")
            + "\n\nSe este PC não tiver o iX CAD 2023 nem o SQL Management Studio, "
            "indique em Caminhos do Sistema («pasta_motor_relatorios») uma pasta "
            "com as DLLs Microsoft.ReportViewer*."
        )

    base = cache or _pasta_cache_motor()
    falhas: list[str] = []
    for pasta in candidatos:
        final = base / _impressao_motor(pasta)
        exe = final / NOME_EXE_MOTOR
        if exe.is_file():
            return exe
        provisoria = base / f"{final.name}_a_preparar_{os.getpid()}"
        try:
            compilar(pasta, provisoria)
            try:
                provisoria.rename(final)
            except OSError:
                # Outro Martelo preparou-o ao mesmo tempo (serve o dele), ou a
                # pasta final ficou a meio de uma vez anterior (serve este).
                return exe if exe.is_file() else provisoria / NOME_EXE_MOTOR
            return exe
        except (OSError, RuntimeError, subprocess.SubprocessError) as erro:
            falhas.append(f"{pasta}: {erro}")
    raise RuntimeError(
        "Não consegui preparar o motor das listas:\n- " + "\n- ".join(falhas)
    )


# ---------------------------------------------------------------------------
# Gerar uma lista
# ---------------------------------------------------------------------------


@dataclass
class ResultadoMotor:
    ok: bool
    linhas: int = 0
    segundos: float = 0.0
    avisos: list[str] = field(default_factory=list)
    erro: str = ""


# Avisos do motor que não dizem nada a quem usa o Martelo. O segundo é o eco
# de uma imagem em falta (o primeiro aviso já diz qual é).
_AVISOS_IGNORADOS = ("rsWarningFetchingExternalImages", "rsInvalidExternalImageProperty")


def _aviso_em_portugues(codigo: str, mensagem: str) -> str:
    """O aviso do motor como se diz a quem usa o Martelo ("" = não interessa)."""
    if codigo in _AVISOS_IGNORADOS:
        return ""
    # O logotipo do Resumo vem de uma pasta do iMos que o Martelo não conhece;
    # a lista vai ser descontinuada, por isso não se avisa.
    if "Logo" in mensagem:
        return ""
    if codigo == "rsInvalidImageReference":
        caminho = re.search(r"'([^']+\.(?:png|jpe?g|bmp|gif))'", mensagem, flags=re.I)
        if caminho:
            return f"Imagem não encontrada: {caminho.group(1)}"
    return mensagem


def correr_motor(
    exe: Path,
    config: ConfigListasImos,
    rdl: Path,
    saida: Path,
    *,
    proadmin_id: int,
    folha: str,
    timeout: int = TIMEOUT_SQL_SEGUNDOS + 120,
) -> ResultadoMotor:
    parametros = dict(config.parametros)
    parametros["ORDERLIST"] = str(int(proadmin_id))
    ficheiro = saida.with_suffix(".parametros.txt")
    linhas = [f"PARAM\t{k}\t{v}" for k, v in parametros.items()]
    linhas += [f"FOLHA\t{folha}", f"TIMEOUT\t{TIMEOUT_SQL_SEGUNDOS}"]
    ficheiro.write_text("\n".join(linhas), encoding="utf-8")

    env = dict(os.environ, MARTELO_IMOS_CONN=config.ligacao)
    inicio = datetime.now()
    try:
        processo = _correr([str(exe), str(rdl), str(saida), str(ficheiro)], timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return ResultadoMotor(ok=False, erro=f"Demorou mais de {timeout // 60} minutos e foi interrompida.")
    segundos = (datetime.now() - inicio).total_seconds()

    resultado = ResultadoMotor(ok=processo.returncode == 0, segundos=segundos)
    erros: list[str] = []
    for linha in (processo.stdout or "").splitlines():
        campos = linha.split("\t")
        if campos[0] == "DATASET" and len(campos) >= 3:
            try:
                resultado.linhas += int(campos[2])
            except ValueError:
                pass
        elif campos[0] == "AVISO" and len(campos) >= 3:
            aviso = _aviso_em_portugues(campos[1], campos[2])
            if aviso and aviso not in resultado.avisos:
                resultado.avisos.append(aviso)
        elif campos[0] == "ERRO" and len(campos) >= 3:
            erros.append(campos[2])
    if not resultado.ok or not saida.is_file():
        resultado.ok = False
        resultado.erro = "\n".join(erros) or (processo.stderr or "").strip()[-800:] or (
            f"O motor terminou com o código {processo.returncode}."
        )
        if "Tempo Limite" in resultado.erro or "Timeout" in resultado.erro:
            resultado.erro = (
                "A base do iMos não respondeu a tempo (mais de "
                f"{TIMEOUT_SQL_SEGUNDOS // 60} minutos). Tente de novo mais tarde.\n\n"
                + resultado.erro
            )
    return resultado


# ---------------------------------------------------------------------------
# Marca de origem e gravação na pasta da obra
# ---------------------------------------------------------------------------

_NS_CORE = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def texto_marca(encomenda: EncomendaImos, agora: datetime | None = None) -> str:
    gravacao = (
        encomenda.ultima_gravacao.strftime(FORMATO_GRAVACAO)
        if encomenda.ultima_gravacao
        else "desconhecida"
    )
    agora = agora or datetime.now()
    return (
        f"{MARCA_MARTELO} | encomenda iMos {encomenda.nome} (ID {encomenda.proadmin_id}) | "
        f"gravacao {gravacao} | gerada {agora.strftime(FORMATO_GRAVACAO)}"
    )


def _escapar_xml(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def marcar_origem(xlsx: Path, marca: str) -> None:
    """Escreve a marca nas propriedades do ficheiro (Autor e Comentários).

    Mexe só no ``docProps/core.xml``; as outras partes do Excel são copiadas
    byte a byte.
    """
    temporario = xlsx.with_name(xlsx.name + ".marca")
    # Um Excel sem core.xml (não devia acontecer) fica sem marca: a data do
    # ficheiro continua a servir para dizer se está atualizado.
    with zipfile.ZipFile(xlsx) as origem, zipfile.ZipFile(
        temporario, "w", compression=zipfile.ZIP_DEFLATED
    ) as destino:
        for info in origem.infolist():
            dados = origem.read(info.filename)
            if info.filename == "docProps/core.xml":
                texto = dados.decode("utf-8")
                texto = re.sub(r"<dc:creator>.*?</dc:creator>|<dc:description>.*?</dc:description>", "", texto, flags=re.S)
                extra = (
                    f"<dc:creator>Martelo V3</dc:creator>"
                    f"<dc:description>{_escapar_xml(marca)}</dc:description>"
                )
                if "</cp:coreProperties>" in texto:
                    texto = texto.replace("</cp:coreProperties>", extra + "</cp:coreProperties>")
                else:
                    texto = re.sub(r"<cp:coreProperties([^>]*)/>", rf"<cp:coreProperties\1>{extra}</cp:coreProperties>", texto)
                if "xmlns:dc=" not in texto:
                    # Sem a declaração o XML ficava inválido e o Excel queixava-se.
                    texto = texto.replace(
                        "<cp:coreProperties", f'<cp:coreProperties xmlns:dc="{_NS_CORE["dc"]}"', 1
                    )
                dados = texto.encode("utf-8")
            elif info.filename == "_rels/.rels":
                # O ReportViewer escreve «meatadata» nesta ligação e o Excel
                # ignora as propriedades; corrigida, o Excel e o Explorador do
                # Windows mostram o Autor e os Comentários com a marca.
                dados = dados.replace(
                    b"relationships/meatadata/core-properties",
                    b"relationships/metadata/core-properties",
                )
            destino.writestr(info, dados)
    os.replace(temporario, xlsx)


def ler_marca(xlsx: Path) -> tuple[str, datetime | None]:
    """(texto da marca, gravação do iMos de que saiu). Vazio se não for do Martelo."""
    try:
        with zipfile.ZipFile(xlsx) as livro:
            core = livro.read("docProps/core.xml").decode("utf-8", errors="replace")
    except (OSError, KeyError, zipfile.BadZipFile):
        return "", None
    # Por texto e não por XML: uma lista com o core.xml estragado não pode
    # impedir o ecrã de abrir.
    encontrada = re.search(r"<dc:description>(.*?)</dc:description>", core, flags=re.S)
    descricao = html.unescape(encontrada.group(1)) if encontrada else ""
    if MARCA_MARTELO not in descricao:
        return "", None
    encontrado = re.search(r"gravacao (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)", descricao)
    return descricao, (_data_sql(encontrado.group(1)) if encontrado else None)


def _data_ficheiro(caminho: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(caminho.stat().st_mtime)
    except OSError:
        return None


def guardar_anterior(caminho: Path) -> Path:
    """Passa a lista que lá estava para ``Listas_IMOS_anteriores``.

    O nome leva a data em que ESSA lista tinha sido gerada (é o que interessa
    para comparar), e um número se já existir outra com a mesma data.
    """
    pasta = caminho.parent / PASTA_ANTERIORES
    pasta.mkdir(exist_ok=True)
    data = _data_ficheiro(caminho) or datetime.now()
    base = f"{caminho.stem}_{data:%Y%m%d_%H%M%S}"
    destino = pasta / f"{base}{caminho.suffix}"
    repetido = 2
    while destino.exists():
        destino = pasta / f"{base}_{repetido}{caminho.suffix}"
        repetido += 1
    try:
        os.replace(caminho, destino)
    except PermissionError as erro:
        raise ValueError(
            f"A lista {caminho.name} está aberta (provavelmente no Excel). "
            "Feche-a e volte a gerar."
        ) from erro
    return destino


def gravar_na_obra(gerado: Path, pasta_obra: Path, lista: ListaImos) -> tuple[Path, Path | None]:
    """Põe a lista gerada na pasta da obra. Devolve (lista, anterior guardada)."""
    destino = pasta_obra / lista.nome_ficheiro
    # Primeiro copia-se ao lado com um nome que a macro não apanha; só depois
    # se tira a antiga e se troca o nome — nunca fica a obra sem lista.
    provisorio = pasta_obra / f".{lista.nome_ficheiro}.martelo_tmp"
    shutil.copyfile(gerado, provisorio)
    anterior = None
    try:
        if destino.exists():
            anterior = guardar_anterior(destino)
        os.replace(provisorio, destino)
    except Exception:
        if anterior is not None and not destino.exists():
            os.replace(anterior, destino)
        if provisorio.exists():
            provisorio.unlink()
        raise
    return destino, anterior


# ---------------------------------------------------------------------------
# Situação das listas na pasta da obra
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EstadoLista:
    lista: ListaImos
    caminho: Path | None = None
    gerada_em: datetime | None = None
    origem: str = ""  # "Martelo" ou "iMos"
    gravacao_origem: datetime | None = None
    situacao: str = SITUACAO_EM_FALTA
    pendente_imos: Path | None = None


def _mais_recente(ficheiros: Iterable[Path]) -> Path | None:
    candidatos = []
    for ficheiro in ficheiros:
        data = _data_ficheiro(ficheiro)
        if data is not None and not ficheiro.name.startswith("~$"):
            candidatos.append((data, ficheiro))
    return max(candidatos)[1] if candidatos else None


def estado_listas(
    pasta_obra: Path,
    nome_enc: str,
    encomenda: EncomendaImos | None,
    *,
    listas: Sequence[ListaImos] = LISTAS_IMOS,
    pasta_saida_imos: Path = PASTA_SAIDA_IMOS,
) -> list[EstadoLista]:
    """Para cada lista: está na obra? Saiu da última gravação do desenho?"""
    gravacao = encomenda.ultima_gravacao if encomenda else None
    estados: list[EstadoLista] = []
    for lista in listas:
        caminho = pasta_obra / lista.nome_ficheiro
        pendente = None
        nome = str(nome_enc or "").strip()
        if nome:
            try:
                pendente = _mais_recente(pasta_saida_imos.glob(f"{nome}_{lista.chave}*.xls*"))
            except OSError:
                pendente = None
        if not caminho.is_file():
            estados.append(EstadoLista(lista=lista, pendente_imos=pendente))
            continue

        gerada = _data_ficheiro(caminho)
        marca, gravacao_origem = ler_marca(caminho)
        origem = "Martelo" if marca else "iMos"
        if pendente is not None and gerada is not None and (_data_ficheiro(pendente) or gerada) <= gerada:
            pendente = None
        if gravacao is None:
            situacao = SITUACAO_SEM_DATA
        elif marca and gravacao_origem is not None:
            situacao = SITUACAO_ATUALIZADA if gravacao_origem >= gravacao else SITUACAO_DESATUALIZADA
        elif gerada is not None:
            situacao = SITUACAO_ATUALIZADA if gerada >= gravacao else SITUACAO_DESATUALIZADA
        else:
            situacao = SITUACAO_SEM_DATA
        estados.append(
            EstadoLista(
                lista=lista,
                caminho=caminho,
                gerada_em=gerada,
                origem=origem,
                gravacao_origem=gravacao_origem,
                situacao=situacao,
                pendente_imos=pendente,
            )
        )
    return estados


# ---------------------------------------------------------------------------
# Tudo junto
# ---------------------------------------------------------------------------


@dataclass
class ResultadoLista:
    lista: ListaImos
    ok: bool
    destino: Path | None = None
    anterior: Path | None = None
    segundos: float = 0.0
    linhas: int = 0
    avisos: list[str] = field(default_factory=list)
    erro: str = ""


@dataclass
class ResultadoGeracao:
    encomenda: EncomendaImos
    resultados: list[ResultadoLista]

    @property
    def geradas(self) -> list[ResultadoLista]:
        return [r for r in self.resultados if r.ok]

    @property
    def falhadas(self) -> list[ResultadoLista]:
        return [r for r in self.resultados if not r.ok]


def gerar_listas(
    config: ConfigListasImos,
    *,
    pasta_obra: Path,
    nome_enc: str,
    dir_id: int | None = None,
    listas: Sequence[ListaImos],
    ao_progresso: Callable[[int, int, str], None] | None = None,
    procurar: Callable[..., EncomendaImos] = procurar_encomenda_imos,
    motor: Callable[[str], Path] = preparar_motor,
    executar: Callable[..., ResultadoMotor] = correr_motor,
) -> ResultadoGeracao:
    """Gera as listas escolhidas para a pasta da obra.

    A gravação do iMos volta a ser lida AGORA, e não quando o ecrã abriu: é
    comum gravar o desenho com o ecrã do Martelo aberto.
    """
    pasta_obra = Path(pasta_obra)
    if not pasta_obra.is_dir():
        raise ValueError(f"A pasta da obra não existe:\n{pasta_obra}")
    total = len(listas)

    def _avisar(indice: int, texto: str) -> None:
        if ao_progresso is not None:
            ao_progresso(indice, total, texto)

    _avisar(0, "A ler a última gravação do desenho no iMos…")
    encomenda = procurar(config.ligacao, nome_enc, dir_id=dir_id)
    _avisar(0, "A preparar o motor de relatórios…")
    exe = motor(config.pasta_motor)
    marca = texto_marca(encomenda)

    resultados: list[ResultadoLista] = []
    for indice, lista in enumerate(listas):
        _avisar(indice, f"A gerar {lista.chave} ({indice + 1} de {total})…")
        rdl = config.pasta_rdl / lista.ficheiro_rdl
        try:
            if not rdl.is_file():
                raise ValueError(f"Não encontrei o relatório {rdl}.")
            ler_rdl(rdl)
            with tempfile.TemporaryDirectory(prefix="martelo_lista_imos_") as pasta_tmp:
                gerado = Path(pasta_tmp) / lista.nome_ficheiro
                motor_resultado = executar(
                    exe, config, rdl, gerado, proadmin_id=encomenda.proadmin_id, folha=lista.chave
                )
                if not motor_resultado.ok:
                    raise ValueError(motor_resultado.erro)
                marcar_origem(gerado, marca)
                destino, anterior = gravar_na_obra(gerado, pasta_obra, lista)
            resultados.append(
                ResultadoLista(
                    lista=lista,
                    ok=True,
                    destino=destino,
                    anterior=anterior,
                    segundos=motor_resultado.segundos,
                    linhas=motor_resultado.linhas,
                    avisos=motor_resultado.avisos,
                )
            )
        except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as erro:
            resultados.append(ResultadoLista(lista=lista, ok=False, erro=str(erro)))
    _avisar(total, "Concluído.")
    return ResultadoGeracao(encomenda=encomenda, resultados=resultados)
