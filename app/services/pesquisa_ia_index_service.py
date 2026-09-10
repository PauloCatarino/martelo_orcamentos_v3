"""Indexador RAG dos catalogos de fornecedores para a Pesquisa IA.

O indice tem duas origens, e a diferenca entre elas e' o que a Fase 3 mudou:

* **A base ``martelo_catalogos``** da' uma frase por artigo, ja' com o preco,
  a espessura e o substrato arrumados em campos. Antes cada linha do Excel ia
  para o indice como o texto cru da folha -- e uma linha de precos por
  espessura, com dez colunas, virava uma frase que nao dizia a que espessura
  pertencia cada numero. Uma pergunta como <<quanto custa o U702 em 19mm>>
  nao tinha como ser respondida.
* **Os ficheiros da pasta** -- os PDFs dos fornecedores e os Excel que ainda
  nao tem adaptador. Continuam a ser lidos como eram.

O ``12_Placas_Referencias_COMPLETO.xlsx`` fica **de fora** da varredura da
pasta: e' dele que a base foi feita, e indexa-lo outra vez punha cada artigo no
indice duas vezes, uma delas na versao pior.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.services.catalogos import exportador
from app.services.catalogos.consulta import ArtigoConsulta, listar_artigos
from app.services.pesquisa_ia_search_service import resolver_modelo
from app.services.placas_referencias_service import FICHEIRO_REFERENCIAS
from app.services.system_setting_service import SystemSettingService

EMBEDDINGS_FILENAME = "embeddings.npy"
META_FILENAME = "meta.jsonl"
EXTENSOES = (".xlsx", ".xlsm", ".pdf")

#: Pastas da árvore dos catálogos que não são catálogos.
#:
#: O ``_backups/`` guarda cópias datadas do ficheiro curado — cinco só do dia em
#: que isto foi escrito. Indexadas, punham no índice cinco versões antigas dos
#: mesmos preços a contradizer a base, e a resposta IA citava a que calhasse.
#: O ``_scripts/`` são os extractores, código que ninguém quer procurar aqui. E
#: o ``_gerado/`` é o Excel que **nós** escrevemos a partir da base: indexá-lo
#: punha cada artigo no índice duas vezes, a segunda em segunda mão.
PASTAS_IGNORADAS = ("_backups", "_scripts", exportador.PASTA_GERADOS)
MODELO_EMBEDDINGS_DEFAULT = "paraphrase-multilingual-MiniLM-L12-v2"


@dataclass(frozen=True)
class ResultadoIndexacao:
    ficheiros: int
    chunks: int
    erros: int
    pasta_indice: str
    #: Quantas frases vieram da base, das ``chunks`` todas.
    artigos: int = 0


def _config(session: Session) -> tuple[str, str, str]:
    svc = SystemSettingService(session)
    catalogos = (svc.obter_valor("pasta_pesquisa_profunda_ia", "") or "").strip()
    indice = (svc.obter_valor("pasta_embeddings_ia", "") or "").strip()
    # O mesmo modelo que a pesquisa usa. Indexar com um modelo e pesquisar com
    # outro daria resultados sem nexo, e nada avisaria.
    modelo = resolver_modelo(
        indice, (svc.obter_valor("modelo_embeddings_ia", "") or "").strip()
    )
    return catalogos, indice, modelo


def _preco(valor: Decimal) -> str:
    """``3.5900`` escreve-se ``3.59``.

    A coluna guarda quatro casas porque ha' precos que as usam; deixar os zeros
    a mais na frase indexada so' dava mais uma forma de o mesmo numero nao ser
    reconhecido por quem o procura.
    """
    texto = f"{valor:.4f}".rstrip("0").rstrip(".")
    return texto or "0"


def _frase(artigo: ArtigoConsulta) -> str:
    """A frase que vai para o indice, um artigo de cada vez.

    Escrita com <<campo: valor>> e nao em prosa: e' o que a pesquisa por
    palavras encontra e o que a resposta IA cita sem ter de interpretar.
    """
    partes = [
        f"Fornecedor: {artigo.fornecedor}",
        f"Fabricante: {artigo.fabricante}" if artigo.fabricante else "",
        f"Referencia: {artigo.referencia}",
        f"Descricao: {artigo.descricao}",
        f"Design: {artigo.nome_design}" if artigo.nome_design else "",
        f"Acabamento: {artigo.acabamento}" if artigo.acabamento else "",
        f"Substrato: {artigo.substrato}" if artigo.substrato else "",
        (
            f"Substrato do fornecedor: {artigo.substrato_origem}"
            if artigo.substrato_origem
            else ""
        ),
        f"Espessura: {artigo.espessura}" if artigo.espessura else "",
        f"Grupo: {artigo.grupo}" if artigo.grupo else "",
        f"Familia: {artigo.familia}" if artigo.familia else "",
        (
            f"Preco: {_preco(artigo.preco)} EUR/{artigo.unidade}"
            if artigo.preco is not None
            else "Preco: sob consulta"
        ),
        f"Tabela: {artigo.tabela}",
        f"Data da tabela: {artigo.data_tabela}" if artigo.data_tabela else "",
        _nota_ambiguidade(artigo),
    ]
    return " | ".join(parte for parte in partes if parte)


def _nota_ambiguidade(artigo: ArtigoConsulta) -> str:
    """Quando a tabela da' dois precos a` mesma coisa, a frase di-lo.

    Sem esta nota o indice ficava com dois artigos parecidos e precos
    diferentes, e a resposta citava o que calhasse. A regra -- vale o mais
    caro -- esta' em ``consulta._marcar_ambiguos``; aqui so' se escreve.
    """
    if len(artigo.precos_da_medida) < 2:
        return ""
    todos = ", ".join(_preco(valor) for valor in artigo.precos_da_medida)
    if artigo.preco_a_considerar:
        return (
            f"Atencao: a tabela da' {len(artigo.precos_da_medida)} precos a esta "
            f"referencia nesta medida ({todos} EUR). Este e' o mais alto e e' o "
            "preco a considerar"
        )
    return (
        f"Atencao: a tabela da' {len(artigo.precos_da_medida)} precos a esta "
        f"referencia nesta medida ({todos} EUR). Este NAO e' o preco a "
        f"considerar -- vale o mais alto, {_preco(artigo.precos_da_medida[-1])} EUR"
    )


def _chunks_base(session: Session) -> Iterator[tuple[str, dict]]:
    """Uma frase por artigo das tabelas ativas da base."""
    for artigo in listar_artigos(session):
        local = artigo.tabela
        if artigo.espessura:
            local = f"{artigo.tabela} · {artigo.espessura}"
        texto = _frase(artigo)
        yield texto, {
            "ficheiro": artigo.tabela,
            # Nao ha' ficheiro para abrir: o artigo esta' na base. O duplo
            # clique na tabela dos resultados nao faz nada, de proposito.
            "caminho": "",
            "fornecedor": artigo.fornecedor,
            "local": local,
            "referencia": artigo.referencia,
            "artigo_id": artigo.artigo_id,
        }


def _chunks_excel(caminho: Path) -> Iterator[tuple[str, dict]]:
    wb = load_workbook(caminho, read_only=True, data_only=True)
    try:
        for folha in wb.sheetnames:
            ws = wb[folha]
            cabecalho: list[str] | None = None
            for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
                valores = [
                    "" if celula is None else str(celula).strip() for celula in row
                ]
                nao_vazias = [valor for valor in valores if valor]
                if not nao_vazias:
                    continue
                if cabecalho is None:
                    if len(nao_vazias) >= 4:
                        cabecalho = valores
                    continue
                partes = [
                    f"{coluna}: {valor}" if coluna else valor
                    for coluna, valor in zip(cabecalho, valores)
                    if valor
                ]
                if partes:
                    yield " | ".join(partes), {"folha": folha, "linha": i}
    finally:
        wb.close()


def _chunks_pdf(caminho: Path) -> Iterator[tuple[str, dict]]:
    from io import BytesIO

    from pypdf import PdfReader

    # Ler para memória: um PdfReader por caminho ficava com o ficheiro aberto
    # enquanto o gerador estivesse vivo, e o PDF ficava preso pelo Windows.
    reader = PdfReader(BytesIO(caminho.read_bytes()))
    for i, page in enumerate(reader.pages, start=1):
        texto = (page.extract_text() or "").strip()
        if texto:
            yield texto, {"pagina": i}


def indexar(
    session: Session, progresso: Callable[[str], None] | None = None
) -> ResultadoIndexacao:
    catalogos, indice, modelo_nome = _config(session)
    if not catalogos:
        raise RuntimeError("A 'Pasta Pesquisa Profunda IA' nao esta configurada.")
    base = Path(catalogos)
    if not base.exists():
        raise RuntimeError(f"Pasta de catalogos nao acessivel: {catalogos}")
    if not indice:
        raise RuntimeError("A 'Pasta Embeddings IA' nao esta configurada.")
    destino = Path(indice)
    destino.mkdir(parents=True, exist_ok=True)

    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Faltam dependencias de IA. Instale: pip install sentence-transformers pypdf"
        ) from exc

    textos: list[str] = []
    metadados: list[dict] = []
    ficheiros = 0
    erros = 0

    for texto, extra in _chunks_base(session):
        textos.append(texto)
        metadados.append({"texto": texto[:600], **extra})
    artigos = len(textos)
    if progresso:
        progresso(f"Base de catalogos: {artigos} artigos")

    for caminho in sorted(base.rglob("*")):
        if not caminho.is_file() or caminho.suffix.lower() not in EXTENSOES:
            continue
        if caminho.name == FICHEIRO_REFERENCIAS:
            # Ja' entrou pela base, em melhor forma. Ver a docstring do modulo.
            continue
        if any(parte in PASTAS_IGNORADAS for parte in caminho.parts):
            continue
        fornecedor = caminho.parent.name
        try:
            gerador = (
                _chunks_excel(caminho)
                if caminho.suffix.lower() in (".xlsx", ".xlsm")
                else _chunks_pdf(caminho)
            )
            for texto, extra in gerador:
                textos.append(texto)
                metadados.append(
                    {
                        "ficheiro": caminho.name,
                        "caminho": str(caminho),
                        "fornecedor": fornecedor,
                        "texto": texto[:600],
                        **extra,
                    }
                )
            ficheiros += 1
            if progresso:
                progresso(f"{caminho.name}: {len(textos)} chunks acumulados")
        except Exception:  # noqa: BLE001
            erros += 1

    if not textos:
        raise RuntimeError(
            "Nenhum conteudo extraido: a base de catalogos esta vazia e nao ha' "
            "ficheiros legiveis na pasta."
        )

    if progresso:
        progresso(f"A gerar embeddings de {len(textos)} chunks (modelo {modelo_nome})...")
    modelo = SentenceTransformer(modelo_nome)
    vetores = modelo.encode(
        textos, normalize_embeddings=True, show_progress_bar=False, batch_size=64
    ).astype("float32")

    np.save(destino / EMBEDDINGS_FILENAME, vetores)
    with open(destino / META_FILENAME, "w", encoding="utf-8") as ficheiro_meta:
        for meta in metadados:
            ficheiro_meta.write(json.dumps(meta, ensure_ascii=False) + "\n")

    return ResultadoIndexacao(
        ficheiros=ficheiros,
        chunks=len(textos),
        erros=erros,
        pasta_indice=str(destino),
        artigos=artigos,
    )
