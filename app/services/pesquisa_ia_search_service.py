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
        self._modelo_nome = (
            (svc.obter_valor("modelo_embeddings_ia", "") or "").strip()
            or MODELO_EMBEDDINGS_DEFAULT
        )
        self._meta: list[dict] | None = None
        self._matriz = None
        self._modelo = None

    def disponivel(self) -> bool:
        base = Path(self._pasta)
        return (
            bool(self._pasta)
            and (base / EMBEDDINGS_FILENAME).exists()
            and (base / META_FILENAME).exists()
        )

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
