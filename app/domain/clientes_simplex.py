"""Regras (puras) do nome abreviado do cliente — o "simplex".

O simplex é o que entra nos nomes que saem do Martelo para fora: pastas do
servidor (``0621_WERNAGEN``), plano CUT-RITE e encomenda iMos. Por isso tem de
ser curto e estável:

- **Vem do PHC** (campo ``NOME2``, "nome abreviado") ou do Streamlit; o Martelo
  nunca o inventa a partir do nome completo — era isso que criava disparates
  como ``WERNAGEN__IMOB`` (nome completo cortado por quem criou a pasta).
- **Máximo 19 caracteres**: o nome da encomenda iMos é
  ``NNNN_VV_AA_<SIMPLEX>`` = 11 caracteres + simplex, e o iMos não aceita mais
  de 30.

Sem DB nem Qt, para ser testável isolado.
"""

from __future__ import annotations

#: Limite do nome da encomenda iMos (iX Organizer).
MAX_NOME_ENC_IMOS = 30
#: ``NNNN_VV_AA_`` = 11 caracteres antes do nome do cliente.
PREFIXO_NOME_ENC_IMOS = 11
#: Máximo de caracteres do nome abreviado do cliente.
MAX_SIMPLEX = MAX_NOME_ENC_IMOS - PREFIXO_NOME_ENC_IMOS


def normalizar_simplex(valor: str | None) -> str | None:
    """Devolve o simplex pronto a usar em nomes de pasta, ou None se vazio.

    Maiúsculas e espaços trocados por ``_`` (como no V2); separadores a mais
    nas pontas são limpos. **Nunca** cai para o nome completo do cliente.
    """
    texto = str(valor or "").strip()
    if not texto:
        return None
    texto = texto.upper().replace(" ", "_").strip("_-")
    return texto or None


def simplex_demasiado_longo(simplex: str | None) -> bool:
    """True quando o simplex ultrapassa o que cabe no nome da encomenda iMos."""
    return len(str(simplex or "")) > MAX_SIMPLEX


def validar_simplex(
    simplex: str | None,
    *,
    nome_cliente: str | None = None,
    origem: str = "PHC",
) -> str | None:
    """Devolve a mensagem de erro a mostrar ao utilizador, ou None se está bem.

    ``origem`` é onde o utilizador tem de ir corrigir ("PHC" ou "Streamlit") —
    o Martelo lê esse campo, não o escreve.
    """
    cliente = str(nome_cliente or "").strip()
    identificacao = f" do cliente {cliente}" if cliente else ""

    texto = str(simplex or "").strip()
    if not texto:
        return (
            f"O nome abreviado{identificacao} está vazio.\n\n"
            f"Preencha o nome abreviado no {origem} e volte a sincronizar/pesquisar. "
            "É esse nome que dá o nome à pasta da obra, ao plano CUT-RITE e à "
            "encomenda iMos, por isso não pode ficar em branco."
        )

    if simplex_demasiado_longo(texto):
        return (
            f"O nome abreviado{identificacao} tem {len(texto)} caracteres "
            f"(máximo {MAX_SIMPLEX}):\n\n{texto}\n\n"
            f"Encurte o nome abreviado no {origem} e volte a sincronizar/pesquisar. "
            f"O nome da encomenda iMos é NNNN_VV_AA_<nome abreviado> e não pode "
            f"passar dos {MAX_NOME_ENC_IMOS} caracteres."
        )

    return None
