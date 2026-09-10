"""O vocabulário de substratos que todos os fornecedores partilham.

Cada fornecedor chama outra coisa ao mesmo núcleo de placa. O EGGER escreve
«Eurodekor Tableros de partículas revestidos», a Innovus escreve ``PB STD``, a
Finsa escreve ``AGL STD``. São a mesma coisa: aglomerado de partículas
standard. Enquanto cada um ficar com o seu nome, a pergunta que motivou este
trabalho todo — «quanto custa o 19 mm em aglomerado, em qualquer fornecedor» —
não tem resposta.

**A decisão:** o campo ``substrato`` do artigo guarda o **código canónico**
desta lista, que é o eixo pelo qual se compara. O nome que o fornecedor lhe dá
fica em ``atributos["substrato_origem"]`` e, quando distingue preços, entra
também na chave natural.

Isso significa que o canónico **perde de propósito** qualificadores que não
mudam o núcleo — o ``CARB2`` da Innovus (baixo formaldeído), o ``EZ`` da Finsa.
Um ``PB STD`` e um ``PB STD CARB2`` da Innovus ficam os dois como ``PB STD``,
com preços diferentes, porque são de facto dois produtos com o mesmo núcleo. É
por isso que o nome de origem tem de sobreviver: quem compara vê os dois e
escolhe; quem procura por «aglomerado standard» encontra-os aos dois.

Não se inventa nada: um texto que não se reconheça devolve ``None`` e quem
chama transforma isso num aviso. Um substrato errado é pior do que nenhum.
"""

from __future__ import annotations

import re

from app.services.catalogos.base import normalizar

# --- núcleos ---------------------------------------------------------------
PB = "PB"
"""Aglomerado de partículas — «tableros de partículas», «AGL», «PB»."""
MDF = "MDF"
SUPERPAN = "SUPERPAN"
"""Sandwich da Finsa: alma de aglomerado com faces de MDF. Não é nem um nem
outro, e tem preço próprio — por isso é núcleo e não qualificador."""
COMPACTO = "COMPACTO"

# --- qualificadores --------------------------------------------------------
STD = "STD"
HID = "HID"
"""Hidrófugo — «HID», «HYDRO X», «hidrófugo», «P3»/«P5»."""
IGN = "IGN"
"""Ignífugo."""
STAR = "STAR"
"""Só existe no SUPERPAN STAR da Finsa."""

#: Núcleos que levam um qualificador de núcleo em vez de STD/HID/IGN.
COR = "COLOR"
PINTADO = "PINTADO"

#: Todos os códigos que este módulo sabe produzir. Serve de contrato: uma
#: consulta pode contar com esta lista e um teste garante que não cresce por
#: acidente.
CANONICOS: frozenset[str] = frozenset(
    {
        "PB STD", "PB HID", "PB IGN",
        "MDF STD", "MDF HID", "MDF IGN", "MDF COLOR", "MDF PINTADO",
        "SUPERPAN STD", "SUPERPAN HID", "SUPERPAN STAR",
        "COMPACTO",
    }
)

_PALAVRAS = re.compile(r"[a-z0-9]+")


def _tokens(texto_norm: str) -> set[str]:
    return set(_PALAVRAS.findall(texto_norm))


def _qualificador(norm: str, tokens: set[str]) -> str:
    """STD, HID ou IGN, a partir do texto do fornecedor.

    Compara por palavras e não por pedaços de palavra: um ``in`` solto fazia
    qualquer texto com «hid» lá dentro passar por hidrófugo.
    """
    if tokens & {"ign", "ignifugo", "ignifuga", "fr", "b1"}:
        return IGN
    if tokens & {"hid", "hidrofugo", "hidrofuga", "hydro", "humidade", "p3", "p5"}:
        return HID
    if "hidrofug" in norm or "hydro x" in norm:
        return HID
    return STD


def canonico(designacao: object) -> str | None:
    """O código canónico do substrato, ou ``None`` se não se reconhecer.

    Aceita o que cada fornecedor escreve: ``AGL HID EZ`` (Finsa),
    ``PB STD CARB2`` (Innovus), ``Eurodekor Tableros de partículas revestidos
    E1E05 TSCA P2`` (EGGER).
    """
    if designacao is None:
        return None
    norm = normalizar(designacao)
    if not norm:
        return None
    tokens = _tokens(norm)

    if "superpan" in tokens:
        if "star" in tokens:
            return f"{SUPERPAN} {STAR}"
        return f"{SUPERPAN} {_qualificador(norm, tokens)}"

    if tokens & {"compacto", "compact"}:
        return COMPACTO

    e_mdf = bool(tokens & {"mdf", "fibras", "dm"})
    if e_mdf:
        # «COLOURED MDF PRETO», «MDF PINTADO DECORATIVOS» — o acabamento do
        # próprio núcleo, que na Innovus tem tabela de preços própria.
        if tokens & {"coloured", "colorido", "colorida", "color"}:
            return f"{MDF} {COR}"
        if tokens & {"pintado", "pintada", "lacado"}:
            return f"{MDF} {PINTADO}"
        return f"{MDF} {_qualificador(norm, tokens)}"

    e_pb = bool(
        tokens & {"pb", "agl", "aglomerado", "particulas", "particula", "eurodekor"}
    )
    if e_pb:
        return f"{PB} {_qualificador(norm, tokens)}"

    return None
