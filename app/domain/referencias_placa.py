"""Referências de decoração nos nomes das placas (B3768, H3710, M6305...).

A referência é o que identifica a placa a sério: o resto do nome muda de
sistema para sistema (IMOS, Woodstore, o texto que o utilizador escreve em
«Matérias usados»). Serve para dois avisos, ambos só de leitura:

* a referência de um material da lista não bate com as «Matérias usados» da
  obra — e, pior, bate com uma PARECIDA (M6305 na lista, M6307 pedida): troca
  provável ao escolher o material no IMOS;
* no Woodstore há referências parecidas com a escolhida. Mede-se que 195 das
  273 referências do Woodstore têm uma vizinha a um algarismo (21-09-2026), por
  isso isto é só informação, nunca alerta por si.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_REFERENCIA = re.compile(r"[A-Z]{1,2}\d{3,5}")
_SEPARADOR = re.compile(r"[^A-Z0-9]+")
_ESPESSURA = re.compile(r"(\d+(?:[.,]\d+)?)\s*MM\b")

# Palavras que aparecem em todos os nomes e não distinguem uma placa de outra.
_GENERICAS = frozenset({
    "AGL", "MDF", "MLM", "MR", "HID", "STD", "CRU", "FOLH", "HPL", "PL",
    "MM", "COM", "DE", "DA", "DO", "E", "C", "VEIO", "TXT", "FACE", "FACES",
})

OK, AVISO, ALERTA, INFO = "ok", "aviso", "alerta", "info"


def _tokens(texto: object) -> list[str]:
    return [t for t in _SEPARADOR.split(str(texto or "").upper()) if t]


def referencias(texto: object) -> set[str]:
    """As referências de decoração que aparecem no texto."""
    return {t for t in _tokens(texto) if _REFERENCIA.fullmatch(t)}


def palavras(texto: object) -> set[str]:
    """As palavras que distinguem a placa (cor, nome comercial...)."""
    return {
        t for t in _tokens(texto)
        if t.isalpha() and len(t) >= 3 and t not in _GENERICAS
    }


def espessura(texto: object) -> int | None:
    achada = _ESPESSURA.search(str(texto or "").upper())
    if not achada:
        return None
    return int(round(float(achada.group(1).replace(",", "."))))


def parecidas(a: str, b: str) -> bool:
    """Um algarismo/letra diferente, ou dois vizinhos trocados (M6305/M6307, H3710/H3170)."""
    if a == b or len(a) != len(b):
        return False
    diferentes = [i for i in range(len(a)) if a[i] != b[i]]
    if len(diferentes) == 1:
        return True
    return (
        len(diferentes) == 2
        and diferentes[1] == diferentes[0] + 1
        and a[diferentes[0]] == b[diferentes[1]]
        and a[diferentes[1]] == b[diferentes[0]]
    )


@dataclass(frozen=True)
class Comparacao:
    nivel: str
    mensagem: str
    sugeridas: tuple[str, ...] = ()  # refs das «Matérias usados» parecidas


def comparar_com_materiais_usados(material: str, materiais_usados: str) -> Comparacao:
    """Leitura superficial: o texto de «Matérias usados» é escrito à mão."""
    if not str(materiais_usados or "").strip():
        return Comparacao(INFO, "«Matérias usados» da obra vazio — sem comparação.")
    refs_material = referencias(material)
    refs_usados = referencias(materiais_usados)
    if refs_material:
        faltam = sorted(refs_material - refs_usados)
        if not faltam:
            return Comparacao(
                OK, f"Ref {', '.join(sorted(refs_material))} consta nas «Matérias usados»."
            )
        vizinhas = sorted(
            {u for r in faltam for u in refs_usados if parecidas(r, u)}
        )
        if vizinhas:
            return Comparacao(
                ALERTA,
                f"Ref {', '.join(faltam)} NÃO consta nas «Matérias usados», que "
                f"indicam {', '.join(vizinhas)} — referência parecida: confirmar "
                "se o material escolhido no IMOS é o certo.",
                tuple(vizinhas),
            )
        lista = ", ".join(sorted(refs_usados)) or "nenhuma ref"
        return Comparacao(
            AVISO,
            f"Ref {', '.join(faltam)} não consta nas «Matérias usados» "
            f"(lá estão: {lista}) — confirmar.",
        )
    distintas = palavras(material)
    if distintas and distintas <= palavras(materiais_usados):
        return Comparacao(
            OK, f"{' '.join(sorted(distintas))} consta nas «Matérias usados»."
        )
    return Comparacao(
        AVISO, "Não aparece nas «Matérias usados» da obra — confirmar."
    )


def referencias_esquecidas(materiais_lista: list[str], materiais_usados: str) -> list[str]:
    """Refs das «Matérias usados» que nenhuma peça da lista usa."""
    usadas = set().union(*(referencias(m) for m in materiais_lista)) if materiais_lista else set()
    return sorted(referencias(materiais_usados) - usadas)


def vizinhas_no_woodstore(material: str, codigos: list[str], limite: int = 4) -> list[str]:
    """Códigos do Woodstore com ref parecida e a mesma espessura (só informação)."""
    refs_material = referencias(material)
    if not refs_material:
        return []
    esp = espessura(material)
    achados = []
    for codigo in sorted(set(codigos)):
        if esp is not None and espessura(codigo) not in (None, esp):
            continue
        if any(parecidas(r, u) for r in refs_material for u in referencias(codigo)):
            achados.append(codigo)
    return achados[:limite]


def mesma_referencia_no_woodstore(material: str, codigos: list[str]) -> list[str]:
    """Códigos do Woodstore com a MESMA ref e espessura — o nome pode estar só escrito de outra forma."""
    refs_material = referencias(material)
    if not refs_material:
        return []
    esp = espessura(material)
    return sorted(
        codigo for codigo in set(codigos)
        if refs_material & referencias(codigo)
        and (esp is None or espessura(codigo) in (None, esp))
        and codigo != material
    )
