"""Tests for the pure PHC -> Martelo customer mapping (phase 10.5.1)."""

from __future__ import annotations

from app.domain.clientes_phc import normalizar_linha_phc


def _linha(**o):
    base = {
        "Num_PHC": 100, "Nome": "Moveis Silva", "Simplex": "MS Mob",
        "Morada": "Rua A", "Email": "a@b.pt", "WEB": "ms.pt",
        "Telemovel": "910000000", "Telefone": "210000000", "Info_1": "obs",
    }
    base.update(o)
    return base


def test_normaliza_linha_completa() -> None:
    d = normalizar_linha_phc(_linha())
    assert d.num_cliente_phc == "100"
    assert d.nome == "Moveis Silva"
    assert d.nome_simplex == "MS_MOB"  # de NOME2 (Simplex), upper + "_"
    assert d.pagina_web == "ms.pt"
    assert d.telemovel == "910000000"


def test_simplex_vazio_fica_vazio_e_nao_deriva_do_nome() -> None:
    """Sem NOME2 no PHC o Martelo não inventa: era assim que nasciam nomes
    de pasta como ``WERNAGEN__IMOB`` (nome completo cortado)."""
    assert normalizar_linha_phc(_linha(Simplex=None)).nome_simplex is None
    assert normalizar_linha_phc(_linha(Simplex="   ")).nome_simplex is None


def test_ignora_sem_num_ou_sem_nome() -> None:
    assert normalizar_linha_phc(_linha(Num_PHC=None)) is None
    assert normalizar_linha_phc(_linha(Nome="  ")) is None
