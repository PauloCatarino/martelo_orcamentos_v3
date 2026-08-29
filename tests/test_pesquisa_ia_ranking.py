"""Como se ordenam os resultados da pesquisa nos catálogos.

O caso que motivou isto: o Paulo procurou `carvalho kendal H3170` e não veio
nada — a placa está no catálogo da EGGER, mas lá ela chama-se "Roble Kendal
natural", nunca "carvalho". Exigia-se que TODAS as palavras estivessem no
trecho, e bastava uma falhar para o resultado certo desaparecer.

Regra nova: cada palavra conta o que vale (uma referência vale muito mais do
que uma palavra comum) e há um prémio para o trecho que tem tudo o que foi
pedido.
"""

from __future__ import annotations

import numpy as np

from app.services.pesquisa_ia_search_service import (
    PesquisaCatalogosService,
    e_referencia,
)


class _ModeloFalso:
    """Devolve sempre o mesmo vetor: quem decide é a correspondência literal."""

    @staticmethod
    def encode(textos, normalize_embeddings=True):  # noqa: ARG004
        return np.zeros((len(textos), 2), dtype="float32")


class _ServicoFalso(PesquisaCatalogosService):
    """O motor de pesquisa com um índice de mentira, sem servidor nem modelo."""

    def __init__(self, trechos: list[str]) -> None:
        self._pasta = "C:/indice"
        self._modelo_nome = "modelo"
        self._meta = [
            {
                "texto": trecho,
                "ficheiro": "catalogo.pdf",
                "fornecedor": "Fornecedor",
                "caminho": "C:/catalogo.pdf",
                "pagina": 1,
            }
            for trecho in trechos
        ]
        # Semelhança semântica igual para todos: isola o efeito das palavras.
        self._matriz = np.zeros((len(trechos), 2), dtype="float32")
        self._modelo = _ModeloFalso()

    def disponivel(self) -> bool:
        return True

    def _carregar(self) -> None:
        return None

    def _get_modelo(self):
        return self._modelo


# ------------------------------------------------------ o que é uma referência


def test_referencia_distingue_se_de_palavra_comum() -> None:
    for codigo in ("B3768", "H3170", "ST12", "b3768"):
        assert e_referencia(codigo), codigo
    for palavra in ("carvalho", "kendal", "placa", "sc", "19"):
        assert not e_referencia(palavra), palavra


# --------------------------------------------------------------- a ordenação


def test_trecho_com_a_referencia_vem_primeiro_e_fica_marcado() -> None:
    servico = _ServicoFalso(
        [
            "Placa branca lisa sem referencia nenhuma",
            "Referencia: B3768 | Nome: Prime White | Textura: SC",
        ]
    )

    resultados = servico.pesquisar("B3768", top_n=2)

    assert resultados[0].trecho.startswith("Referencia: B3768")
    assert resultados[0].exato
    assert not resultados[1].exato
    assert resultados[0].score > resultados[1].score


def test_referencia_certa_ganha_mesmo_faltando_uma_palavra() -> None:
    """O caso do Paulo: o catálogo diz "Roble", ele escreveu "carvalho"."""
    servico = _ServicoFalso(
        [
            "Orlas Carvalho 1911E13 preco por metro",
            "Referencia: H3170 | ST12 | Nome Design: Roble Kendal natural",
        ]
    )

    resultados = servico.pesquisar("carvalho kendal H3170", top_n=2)

    assert "H3170" in resultados[0].trecho, "a placa certa tem de vir primeiro"
    assert resultados[0].exato, "a referencia pedida esta la': conta como exato"
    assert not resultados[1].exato


def test_pesquisa_so_por_palavras_tambem_premeia_quem_tem_tudo() -> None:
    """`dobradica blum` — sem referências, mas quem tem as duas palavras ganha."""
    servico = _ServicoFalso(
        [
            "Aglomerado melamina Timeless Oak Biscuit",
            "Dobradica para portas espessas CLIP top BLUMOTION da Blum",
            "Dobradica de canto sem marca indicada",
        ]
    )

    resultados = servico.pesquisar("dobradica blum", top_n=3)

    assert resultados[0].exato
    assert "BLUMOTION" in resultados[0].trecho
    # A que só tem "dobradica" ainda sobe acima da placa, mas não é exata.
    assert not resultados[1].exato
    assert resultados[1].score > resultados[2].score


def test_sem_correspondencia_nenhuma_nada_fica_marcado_como_exato() -> None:
    servico = _ServicoFalso(["Placa branca", "Perfil de aluminio"])

    resultados = servico.pesquisar("B9999", top_n=2)

    assert not any(resultado.exato for resultado in resultados)
