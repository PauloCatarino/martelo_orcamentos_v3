"""Pesquisa local, tolerante a acentos, nas linhas de um modelo ValueSet."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


def normalizar_pesquisa_valueset_modelo(valor: object) -> str:
    """Normaliza texto para pesquisa sem diferenças de acentos ou maiúsculas."""
    if valor is None:
        return ""

    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", texto.casefold()).strip()


def linha_valueset_modelo_corresponde(
    linha, pesquisa: str | None, operacoes: str = ""
) -> bool:
    """True quando todos os termos aparecem em algum campo da linha."""
    tokens = normalizar_pesquisa_valueset_modelo(
        (pesquisa or "").replace("%", " ")
    ).split()
    if not tokens:
        return True

    estado = "ativo sim" if getattr(linha, "ativo", False) else "inativo nao"
    texto = normalizar_pesquisa_valueset_modelo(
        " ".join(
            str(valor)
            for valor in (
                getattr(linha, "chave", None),
                getattr(linha, "codigo_opcao", None),
                getattr(linha, "nome_opcao", None),
                getattr(linha, "ref_materia_prima", None),
                getattr(linha, "descricao_materia_prima", None),
                getattr(linha, "valor_texto", None),
                getattr(linha, "ref_le", None),
                getattr(linha, "descricao_no_orcamento", None),
                getattr(linha, "unidade", None),
                getattr(linha, "tipo_materia_prima", None),
                getattr(linha, "familia_materia_prima", None),
                getattr(linha, "prioridade", None),
                getattr(linha, "ordem", None),
                getattr(linha, "observacoes", None),
                operacoes,
                estado,
            )
            if valor
        )
    )
    return all(token in texto for token in tokens)


def filtrar_linhas_valueset_modelo(
    linhas: Iterable,
    pesquisa: str | None,
    operacoes_por_linha: dict[int, str] | None = None,
) -> list:
    """Filtra linhas preservando a ordem apresentada pelo serviço."""
    operacoes_por_linha = operacoes_por_linha or {}
    return [
        linha
        for linha in linhas
        if linha_valueset_modelo_corresponde(
            linha, pesquisa, operacoes_por_linha.get(linha.id, "")
        )
    ]
