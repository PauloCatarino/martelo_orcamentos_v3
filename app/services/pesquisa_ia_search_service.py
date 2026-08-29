"""Retrieval hibrido sobre o indice dos catalogos da Pesquisa IA."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.services.system_setting_service import SystemSettingService

EMBEDDINGS_FILENAME = "embeddings.npy"
META_FILENAME = "meta.jsonl"
MODELO_EMBEDDINGS_DEFAULT = "paraphrase-multilingual-MiniLM-L12-v2"

#: Subpasta, ao lado do indice, onde o modelo vive no servidor.
SUBPASTA_MODELOS = "ia_models"


def resolver_modelo(pasta_indice: str, escolhido: str = "") -> str:
    """Onde ir buscar o modelo da pesquisa por IA.

    O modelo sao 458 MB. Se aqui ficasse so' o NOME dele
    (``paraphrase-multilingual-MiniLM-L12-v2``), a biblioteca ia descarrega-lo
    da internet na primeira pesquisa -- em cada PC, e a pedir acesso ao
    huggingface.co que a rede da empresa pode nem permitir.

    Por isso procura-se primeiro no servidor, na pasta ``ia_models`` ao lado do
    indice: uma copia so', que toda a gente le'. O nome fica como ultimo
    recurso, para a maquina de quem faz manutencao (que tem internet e ja' o
    tem em cache).

    Ordem: o que estiver configurado (se for uma pasta que existe) ->
    ``<indice>/ia_models/<nome>`` -> o nome do modelo.
    """
    escolhido = (escolhido or "").strip()
    if escolhido:
        # Um caminho que existe ganha sempre. Se for so' um nome de modelo,
        # continua a servir de nome no fim.
        if Path(escolhido).is_dir():
            return escolhido

    nome = escolhido or MODELO_EMBEDDINGS_DEFAULT
    pasta_indice = (pasta_indice or "").strip()
    if pasta_indice:
        no_servidor = Path(pasta_indice) / SUBPASTA_MODELOS / nome
        if no_servidor.is_dir():
            return str(no_servidor)

    return nome


@dataclass(frozen=True)
class ResultadoCatalogo:
    score: float
    fornecedor: str
    ficheiro: str
    caminho: str
    local: str
    trecho: str


class PesquisaCatalogosService:
    """Carrega o indice e faz pesquisa semantica + palavra-chave."""

    def __init__(self, session: Session) -> None:
        svc = SystemSettingService(session)
        self._pasta = (svc.obter_valor("pasta_embeddings_ia", "") or "").strip()
        self._modelo_nome = resolver_modelo(
            self._pasta,
            (svc.obter_valor("modelo_embeddings_ia", "") or "").strip(),
        )
        self._meta: list[dict] | None = None
        self._matriz = None
        self._modelo = None

    def disponivel(self) -> bool:
        return self.motivo_indisponivel() is None

    def motivo_indisponivel(self) -> str | None:
        """Porque e' que a pesquisa por IA nao da' para usar, em portugues.

        Sao duas coisas diferentes, e antes so' se olhava para uma:

        1. O INDICE -- os ficheiros que descrevem os catalogos. Vivem numa pasta
           do servidor, por isso ou existem para toda a gente ou para ninguem.
        2. A BIBLIOTECA que le' o indice (sentence-transformers). Essa vive
           dentro da aplicacao, e o executavel normal NAO a leva: sao centenas
           de MB que so' servem para esta funcionalidade.

        Como o indice esta' no servidor, ele existe em todos os PCs -- e sem
        esta verificacao a aplicacao dizia "disponivel" e depois estoirava com
        "No module named 'sentence_transformers'", uma frase que nao ajuda
        ninguem a perceber o que se passa.
        """
        if not self._pasta:
            return (
                "A pesquisa por IA ainda nao esta' configurada: falta indicar a "
                "pasta dos catalogos em Configuracoes."
            )

        base = Path(self._pasta)
        if not (base / EMBEDDINGS_FILENAME).exists() or not (base / META_FILENAME).exists():
            return (
                "Nao encontrei o indice dos catalogos em:\n"
                f"{self._pasta}\n\n"
                "Confirme que tem acesso a essa pasta do servidor."
            )

        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            return (
                "Esta instalacao do Martelo nao inclui a pesquisa por IA.\n\n"
                "E' a unica funcionalidade que fica de fora: ocupa centenas de "
                "MB e tornava a instalacao muito mais pesada para toda a gente. "
                "O resto do Martelo funciona na mesma."
            )

        return None

    def _carregar(self) -> None:
        if self._meta is not None:
            return
        import numpy as np

        base = Path(self._pasta)
        self._matriz = np.load(base / EMBEDDINGS_FILENAME)
        with open(base / META_FILENAME, encoding="utf-8") as ficheiro:
            self._meta = [json.loads(linha) for linha in ficheiro if linha.strip()]

    def _get_modelo(self):
        if self._modelo is None:
            from sentence_transformers import SentenceTransformer

            self._modelo = SentenceTransformer(self._modelo_nome)
        return self._modelo

    def pesquisar(self, texto: str, top_n: int = 30) -> list[ResultadoCatalogo]:
        texto = (texto or "").strip()
        if not texto or not self.disponivel():
            return []
        import numpy as np

        self._carregar()
        modelo = self._get_modelo()
        q = modelo.encode([texto], normalize_embeddings=True).astype("float32")[0]
        score = self._matriz @ q

        tokens = _normalizar(texto).split()
        if tokens:
            boost = np.array(
                [
                    0.3
                    if all(
                        token in _normalizar(meta.get("texto", ""))
                        for token in tokens
                    )
                    else 0.0
                    for meta in self._meta
                ],
                dtype="float32",
            )
            score = score + boost

        ordem = np.argsort(-score)[:top_n]
        resultados: list[ResultadoCatalogo] = []
        for i in ordem:
            meta = self._meta[int(i)]
            if meta.get("folha") is not None:
                local = f"Folha {meta.get('folha')} / linha {meta.get('linha')}"
            else:
                local = f"P\u00e1gina {meta.get('pagina')}"
            resultados.append(
                ResultadoCatalogo(
                    score=round(float(score[int(i)]), 3),
                    fornecedor=str(meta.get("fornecedor") or ""),
                    ficheiro=str(meta.get("ficheiro") or ""),
                    caminho=str(meta.get("caminho") or ""),
                    local=local,
                    trecho=str(meta.get("texto") or ""),
                )
            )
        return resultados


def _normalizar(value: object) -> str:
    if value is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(value))
    texto = "".join(
        caractere for caractere in texto if not unicodedata.combining(caractere)
    )
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()
