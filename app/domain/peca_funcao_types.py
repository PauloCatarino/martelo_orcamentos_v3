"""Controlled structural origins for reusable catalog pieces."""

TETO = "TETO"
FUNDO = "FUNDO"
PRATELEIRA_FIXA = "PRATELEIRA_FIXA"
PRATELEIRA_AMOVIVEL = "PRATELEIRA_AMOVIVEL"
LATERAL = "LATERAL"
DIVISORIA = "DIVISORIA"
COSTA = "COSTA"
PORTA = "PORTA"
PORTA_CORRER = "PORTA_CORRER"
GAVETA = "GAVETA"
REMATE = "REMATE"
FERRAGEM = "FERRAGEM"
ACESSORIO = "ACESSORIO"
SERVICO = "SERVICO"

PECA_FUNCAO_LABELS = {
    TETO: "Teto / topo (horizontal)",
    FUNDO: "Fundo (horizontal)",
    PRATELEIRA_FIXA: "Prateleira fixa (horizontal)",
    PRATELEIRA_AMOVIVEL: "Prateleira amovível (horizontal)",
    LATERAL: "Lateral (vertical)",
    DIVISORIA: "Divisória (vertical)",
    COSTA: "Costa",
    PORTA: "Porta de abrir",
    PORTA_CORRER: "Porta articulada / de correr",
    GAVETA: "Gaveta / componente de gaveta",
    REMATE: "Remate / guarnição",
    FERRAGEM: "Ferragem",
    ACESSORIO: "Acessório",
    SERVICO: "Serviço / operação",
}


def get_peca_funcao_options() -> tuple[tuple[str, str], ...]:
    return tuple(PECA_FUNCAO_LABELS.items())


def normalize_peca_funcao(value: str | None) -> str | None:
    normalized = " ".join(str(value or "").strip().upper().split())
    return normalized or None
