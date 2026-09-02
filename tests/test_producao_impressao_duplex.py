"""Por que margem se vira a folha no duplex: A4 pela maior, A3 pela menor.

Dizer só «duplex» deixava a escolha ao driver da impressora, que virava tudo da
mesma maneira e punha o verso das folhas A3 de pernas para o ar.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.pdfgen import canvas

from app.services import producao_impressao_service as svc

NOME_PLANO = "1319_01_01_26_JF_VIVA"


def _pdf(pasta: Path, nome: str, tamanho=A4) -> Path:
    caminho = pasta / nome
    desenho = canvas.Canvas(str(caminho), pagesize=tamanho)
    desenho.drawString(50, 50, nome)
    desenho.save()
    return caminho


# ---- a regra, sozinha ------------------------------------------------------


def test_a4_vira_pela_margem_maior() -> None:
    assert svc.modo_duplex("A4") == "duplexlong"


def test_a3_vira_pela_margem_menor() -> None:
    assert svc.modo_duplex("A3") == "duplexshort"


def test_formato_desconhecido_deixa_a_decisao_ao_driver() -> None:
    """Sem saber o formato, mais vale o duplex genérico do que adivinhar."""
    assert svc.modo_duplex(None) == "duplex"
    assert svc.modo_duplex("") == "duplex"
    assert svc.modo_duplex(svc.DO_PDF) == "duplex"
    assert svc.modo_duplex("A5") == "duplex"


def test_o_formato_e_lido_sem_ligar_a_maiusculas() -> None:
    assert svc.modo_duplex(" a4 ") == "duplexlong"
    assert svc.modo_duplex("a3") == "duplexshort"


# ---- ligada à impressão ----------------------------------------------------


def _documento(tmp_path: Path, tamanho, *, papel=svc.DO_PDF) -> svc.DocumentoImpressao:
    obra = tmp_path / "obra"
    obra.mkdir(exist_ok=True)
    _pdf(obra, f"{NOME_PLANO}.pdf", tamanho)
    documento = svc.listar_documentos(obra, nome_plano_cut_rite=NOME_PLANO)[0]
    documento.duplex = True
    documento.papel = papel
    return documento


def test_sem_duplex_nada_muda(tmp_path: Path) -> None:
    documento = _documento(tmp_path, landscape(A3))
    documento.duplex = False

    definicoes = svc.definicoes_sumatra(documento)[0]

    assert "duplex" not in definicoes


def test_folha_a4_do_pdf_vai_pela_margem_maior(tmp_path: Path) -> None:
    documento = _documento(tmp_path, A4)

    assert svc.definicoes_sumatra(documento) == [
        "paperkind=9,portrait,shrink,disable-auto-rotation,duplexlong"
    ]


def test_folha_a3_do_pdf_vai_pela_margem_menor(tmp_path: Path) -> None:
    documento = _documento(tmp_path, landscape(A3))

    assert svc.definicoes_sumatra(documento) == [
        "paperkind=8,landscape,shrink,disable-auto-rotation,duplexshort"
    ]


def test_papel_forcado_segue_a_mesma_regra(tmp_path: Path) -> None:
    """A regra é do tamanho da folha, venha ele do PDF ou da coluna Papel."""
    documento = _documento(tmp_path, landscape(A3), papel="A4")
    assert "duplexlong" in svc.definicoes_sumatra(documento)[0]

    documento.papel = "A3"
    assert "duplexshort" in svc.definicoes_sumatra(documento)[0]


def test_plano_com_a3_e_a4_vira_cada_folha_a_sua_maneira(tmp_path: Path) -> None:
    """O plano CUT-RITE traz folhas A3 e, no fim, uma A4."""
    obra = tmp_path / "obra"
    obra.mkdir()
    caminho = obra / f"{NOME_PLANO}.pdf"
    desenho = canvas.Canvas(str(caminho), pagesize=landscape(A3))
    for pagina in range(2):
        desenho.drawString(50, 50, f"corte {pagina}")
        desenho.showPage()
    desenho.setPageSize(landscape(A4))
    desenho.drawString(50, 50, "resumo")
    desenho.showPage()
    desenho.save()

    documento = svc.listar_documentos(obra, nome_plano_cut_rite=NOME_PLANO)[0]
    documento.duplex = True

    assert svc.definicoes_sumatra(documento) == [
        "1-2,paperkind=8,landscape,shrink,disable-auto-rotation,duplexshort",
        "3,paperkind=9,landscape,shrink,disable-auto-rotation,duplexlong",
    ]


def test_pdf_ilegivel_mantem_o_duplex_generico(tmp_path: Path) -> None:
    documento = _documento(tmp_path, A4)
    # Sem geometria lida, não se sabe o formato de nenhuma página.
    documento.geometria_paginas = []

    assert svc.definicoes_sumatra(documento) == ["shrink,duplex"]


def test_o_preto_e_branco_continua_a_vir_a_seguir(tmp_path: Path) -> None:
    documento = _documento(tmp_path, landscape(A3))
    documento.cor = "pb"

    assert svc.definicoes_sumatra(documento) == [
        "paperkind=8,landscape,shrink,disable-auto-rotation,duplexshort,monochrome"
    ]
