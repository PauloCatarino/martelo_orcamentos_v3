"""ValueSet key constants and helpers."""

from __future__ import annotations

MATERIAL_CAIXOTE = "MATERIAL_CAIXOTE"
MATERIAL_PORTAS = "MATERIAL_PORTAS"
MATERIAL_FRENTES = "MATERIAL_FRENTES"
MATERIAL_COSTAS = "MATERIAL_COSTAS"
MATERIAL_FUNDOS = "MATERIAL_FUNDOS"
MATERIAL_PRATELEIRAS = "MATERIAL_PRATELEIRAS"
MATERIAL_GAVETAS = "MATERIAL_GAVETAS"
MATERIAL_TAMPOS = "MATERIAL_TAMPOS"
MATERIAL_OUTROS = "MATERIAL_OUTROS"

FERRAGEM_DOBRADICA = "FERRAGEM_DOBRADICA"
FERRAGEM_CORREDICA = "FERRAGEM_CORREDICA"
FERRAGEM_PUXADOR = "FERRAGEM_PUXADOR"
FERRAGEM_VARAO = "FERRAGEM_VARAO"
FERRAGEM_SUPORTE_VARAO = "FERRAGEM_SUPORTE_VARAO"
FERRAGEM_PE_NIVELADOR = "FERRAGEM_PE_NIVELADOR"
SISTEMA_CORRER = "SISTEMA_CORRER"
ACESSORIO_OUTRO = "ACESSORIO_OUTRO"

ORLA_FINA = "ORLA_FINA"
ORLA_GROSSA = "ORLA_GROSSA"

ACABAMENTO_FACE_SUP = "ACABAMENTO_FACE_SUP"
ACABAMENTO_FACE_INF = "ACABAMENTO_FACE_INF"
ACABAMENTO_OUTRO = "ACABAMENTO_OUTRO"

DEFAULT_VALUESET_KEY = MATERIAL_OUTROS

VALUESET_KEY_LABELS = {
    MATERIAL_CAIXOTE: "Material caixote",
    MATERIAL_PORTAS: "Material portas",
    MATERIAL_FRENTES: "Material frentes",
    MATERIAL_COSTAS: "Material costas",
    MATERIAL_FUNDOS: "Material fundos",
    MATERIAL_PRATELEIRAS: "Material prateleiras",
    MATERIAL_GAVETAS: "Material gavetas",
    MATERIAL_TAMPOS: "Material tampos",
    MATERIAL_OUTROS: "Material outros",
    FERRAGEM_DOBRADICA: "Dobradiça",
    FERRAGEM_CORREDICA: "Corrediça",
    FERRAGEM_PUXADOR: "Puxador",
    FERRAGEM_VARAO: "Varão",
    FERRAGEM_SUPORTE_VARAO: "Suporte varão",
    FERRAGEM_PE_NIVELADOR: "Pé nivelador",
    SISTEMA_CORRER: "Sistema correr",
    ACESSORIO_OUTRO: "Acessório outro",
    ORLA_FINA: "Orla fina",
    ORLA_GROSSA: "Orla grossa",
    ACABAMENTO_FACE_SUP: "Acabamento face superior",
    ACABAMENTO_FACE_INF: "Acabamento face inferior",
    ACABAMENTO_OUTRO: "Acabamento outro",
}


def get_valueset_key_label(chave: str | None) -> str:
    """Return the friendly label for a ValueSet key."""
    return VALUESET_KEY_LABELS[normalize_valueset_key(chave)]


def get_valueset_key_options() -> tuple[tuple[str, str], ...]:
    """Return ValueSet key options as code/label pairs."""
    return tuple(VALUESET_KEY_LABELS.items())


def normalize_valueset_key(chave: str | None) -> str:
    """Normalize a ValueSet key, falling back to MATERIAL_OUTROS."""
    if chave is None:
        return DEFAULT_VALUESET_KEY

    normalized = chave.strip().upper()
    if not normalized:
        return DEFAULT_VALUESET_KEY

    return normalized if normalized in VALUESET_KEY_LABELS else DEFAULT_VALUESET_KEY
