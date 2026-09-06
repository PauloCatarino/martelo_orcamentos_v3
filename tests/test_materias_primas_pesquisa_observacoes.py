"""Referências agrupadas nas observações devem encontrar o material de preço."""

from app.models import DefMateriaPrima
from app.repositories.def_materia_prima_repository import DefMateriaPrimaRepository
from app.ui.pages.materias_primas_page import materia_matches_search


def test_referencia_nas_observacoes_encontra_as_duas_espessuras(session):
    session.add_all([
        DefMateriaPrima(ref_le="PLC0070", descricao="AGL MLM EGGER GRUPO 7 19MM",
                        observacoes="F186 | F187 | F206", ativo=True),
        DefMateriaPrima(ref_le="PLC0071", descricao="AGL MLM EGGER GRUPO 7 08MM",
                        observacoes="F186 | F187 | F206", ativo=True),
        DefMateriaPrima(ref_le="PLC0058", descricao="AGL MLM EGGER GRUPO 1 19MM",
                        observacoes=None, ativo=True),
        DefMateriaPrima(ref_le="ANTIGO", descricao="Grupo antigo",
                        observacoes="F186", ativo=False),
    ])
    session.flush()
    repository = DefMateriaPrimaRepository(session)
    encontrados = repository.pesquisar("f186")
    assert {m.ref_le for m in encontrados} == {"PLC0070", "PLC0071"}
    assert repository.pesquisar("F9999") == []
    assert {m.ref_le for m in encontrados if materia_matches_search(m, "f186 19mm")} == {"PLC0070"}
    assert {m.ref_le for m in encontrados if materia_matches_search(m, "F186 08MM")} == {"PLC0071"}
    assert not materia_matches_search(repository.get_by_ref_le("PLC0058"), "F186")
