"""Read a supplier's price answer and apply what the user approves."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.domain.materia_prima_types import ORIGEM_PRECO_FORNECEDOR
from app.domain.resposta_fornecedor import (
    ESTADO_DESCONTINUADO,
    PropostaPreco,
    ler_respostas,
    mapear_colunas,
)
from app.services.def_materia_prima_service import (
    DefMateriaPrimaService,
    EditarDefMateriaPrimaData,
)
from app.services.leitor_pdf_precos import e_pdf, ler_pdf, resumo_da_leitura

#: Quantas linhas do topo procurar até encontrar o cabeçalho.
LIMITE_PROCURA_CABECALHO = 10


@dataclass(frozen=True)
class LeituraResposta:
    """What came out of the file, and how it was read.

    As notas são a parte honesta do assistente: dizem que colunas foram
    reconhecidas por adivinhação e que a leitura de um PDF é um palpite. Quem
    revê fica a saber onde olhar duas vezes.
    """

    propostas: tuple = ()
    notas: tuple = ()
    origem: str = "EXCEL"

    def __iter__(self):
        """Percorrer a leitura é percorrer as propostas."""
        return iter(self.propostas)

    def __len__(self) -> int:
        return len(self.propostas)


@dataclass(frozen=True)
class ResultadoAplicacao:
    """What actually changed after applying the approved lines."""

    atualizadas: int = 0
    desativadas: int = 0
    ignoradas: int = 0
    erros: tuple[str, ...] = ()


class RespostaFornecedorService:
    """Turn a returned workbook into proposals, then into catalog changes."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.materias = DefMateriaPrimaService(session)

    def ler_ficheiro(self, caminho: str | Path) -> list[PropostaPreco]:
        """Ler o ficheiro devolvido pelo fornecedor, sem gravar nada."""
        return list(self.ler_com_notas(caminho).propostas)

    def ler_com_notas(self, caminho: str | Path) -> LeituraResposta:
        """Ler o ficheiro e dizer também *como* foi lido.

        Aceita o anexo que mandámos, uma folha refeita à maneira do fornecedor
        ou uma tabela de preços em PDF. Em nenhum dos casos escreve seja o que
        for: só propõe.
        """
        catalogo, por_referencia = self._indices()

        if e_pdf(caminho):
            cabecalhos, linhas, primeira = ler_pdf(
                caminho, reconhecer=_reconhecedor(catalogo, por_referencia)
            )
            origem, notas = "PDF", [resumo_da_leitura(linhas)]
        else:
            cabecalhos, linhas, primeira = ler_folha(caminho)
            origem, notas = "EXCEL", []

        mapa = mapear_colunas(cabecalhos, linhas)
        notas.extend(mapa.notas(cabecalhos))

        propostas = ler_respostas(
            cabecalhos,
            linhas,
            catalogo,
            primeira_linha=primeira,
            materias_por_referencia=por_referencia,
            mapa=mapa,
        )

        return LeituraResposta(
            propostas=tuple(propostas), notas=tuple(notas), origem=origem
        )

    def _indices(self) -> tuple[dict, dict]:
        """O catálogo indexado pelas duas referências que o identificam."""
        catalogo: dict = {}
        por_referencia: dict = {}
        ambiguas: set = set()
        for materia in self.materias.listar_materias_primas():
            if materia.ref_le:
                catalogo[materia.ref_le.upper()] = materia
            referencia = (materia.referencia_fornecedor or "").strip().upper()
            if not referencia:
                continue
            if referencia in por_referencia:
                # Referência usada por dois materiais nossos: deixa de servir
                # para identificar seja qual for.
                ambiguas.add(referencia)
                continue
            por_referencia[referencia] = materia

        for referencia in ambiguas:
            por_referencia.pop(referencia, None)

        return catalogo, por_referencia

    def aplicar(
        self,
        propostas,
        hoje: date | None = None,
    ) -> ResultadoAplicacao:
        """Aplicar as propostas aprovadas ao catálogo.

        Cada preço aplicado fica no histórico com origem FORNECEDOR. Orçamentos
        já feitos não mudam: cada linha guarda a cópia com que foi calculada.
        """
        hoje = hoje or date.today()
        atualizadas = desativadas = ignoradas = 0
        erros: list[str] = []

        for proposta in propostas:
            if not proposta.aplicavel or proposta.materia_prima_id is None:
                ignoradas += 1
                continue

            materia = self.materias.obter_por_id(proposta.materia_prima_id)
            if materia is None:
                ignoradas += 1
                continue

            try:
                if proposta.estado == ESTADO_DESCONTINUADO:
                    self.materias.definir_ativo(materia.id, ativo=False)
                    desativadas += 1
                    continue

                self.materias.editar_materia_prima(
                    materia.id, _dados_atualizados(materia, proposta, hoje)
                )
                atualizadas += 1
            except ValueError as erro:
                erros.append(f"{proposta.codigo}: {erro}")

        return ResultadoAplicacao(
            atualizadas=atualizadas,
            desativadas=desativadas,
            ignoradas=ignoradas,
            erros=tuple(erros),
        )


def _reconhecedor(catalogo: dict, por_referencia: dict):
    """Uma função que diz se um pedaço de texto é referência conhecida.

    É o que permite ler o PDF do fornecedor: no meio da linha, a palavra que
    bate certo com o nosso código ou com a referência dele é o artigo.
    """

    def reconhecer(palavra: str) -> bool:
        chave = (palavra or "").strip().upper()
        return bool(chave) and (chave in catalogo or chave in por_referencia)

    return reconhecer


def _dados_atualizados(materia, proposta: PropostaPreco, hoje: date):
    """A matéria-prima como fica depois de aceitar a resposta.

    O preço líquido é recalculado aqui: o fornecedor manda o preço de tabela e o
    desconto dele, a margem continua a ser nossa.
    """
    preco_tabela = (
        proposta.preco_novo if proposta.preco_novo is not None else materia.preco_tabela
    )
    desconto = (
        proposta.desconto_novo
        if proposta.desconto_novo is not None
        else materia.desconto
    )
    margem = materia.margem

    preco_liquido = materia.preco_liquido
    if preco_tabela is not None:
        preco_liquido = (
            preco_tabela
            * (Decimal(1) - (desconto or Decimal(0)) / Decimal(100))
            * (Decimal(1) + (margem or Decimal(0)) / Decimal(100))
        )

    return EditarDefMateriaPrimaData(
        descricao=proposta.nova_designacao or materia.descricao,
        ref_le=materia.ref_le,
        referencia_fornecedor=proposta.nova_referencia or materia.referencia_fornecedor,
        tipo_original_excel=materia.tipo_original_excel,
        familia_original_excel=materia.familia_original_excel,
        tipo_martelo=materia.tipo_martelo,
        familia_martelo=materia.familia_martelo,
        coresp_orla_0_4=materia.coresp_orla_0_4,
        coresp_orla_1_0=materia.coresp_orla_1_0,
        unidade=materia.unidade,
        preco_tabela=preco_tabela,
        desconto=desconto,
        margem=margem,
        desperdicio_percentagem=materia.desperdicio_percentagem,
        preco_liquido=preco_liquido,
        comprimento=materia.comprimento,
        largura=materia.largura,
        espessura=materia.espessura,
        fornecedor=materia.fornecedor,
        fornecedor_id=materia.fornecedor_id,
        tipo_preco=materia.tipo_preco,
        data_ultimo_preco=hoje,
        stock=materia.stock,
        cor=materia.cor,
        nome_fabricante=materia.nome_fabricante,
        ref_phc=materia.ref_phc,
        ativo=materia.ativo,
        observacoes=materia.observacoes,
        origem_dados=ORIGEM_PRECO_FORNECEDOR,
    )


def ler_folha(caminho: str | Path) -> tuple[list, list, int]:
    """Ler o ficheiro e devolver (cabeçalhos, linhas, número da primeira linha).

    O cabeçalho é procurado nas primeiras linhas em vez de assumido na primeira:
    há quem responda com o logótipo da casa por cima da tabela.
    """
    import openpyxl

    livro = openpyxl.load_workbook(caminho, data_only=True)
    try:
        folha = livro.worksheets[0]
        todas = [tuple(linha) for linha in folha.iter_rows(values_only=True)]
    finally:
        livro.close()

    if not todas:
        return [], [], 2

    indice = _linha_do_cabecalho(todas)
    cabecalhos = list(todas[indice])
    linhas = [
        linha
        for linha in todas[indice + 1 :]
        if any(valor not in (None, "") for valor in linha)
    ]

    return cabecalhos, linhas, indice + 2


def _linha_do_cabecalho(todas: list) -> int:
    """A primeira linha que pareça um cabeçalho (tem a coluna do código)."""
    from app.domain.resposta_fornecedor import ALIASES, normalizar_cabecalho

    codigos = set(ALIASES["codigo"])
    for indice, linha in enumerate(todas[:LIMITE_PROCURA_CABECALHO]):
        titulos = {normalizar_cabecalho(valor) for valor in linha if valor}
        if codigos & titulos:
            return indice

    return 0
