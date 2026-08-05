"""Tests for the obra print manager service."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.pdfgen import canvas

from app.services import producao_impressao_service as svc


NOME_PLANO = "1319_01_01_26_JF_VIVA"
NOME_ENC = "1319_01_26_JF_VIVA"


def _pdf(pasta: Path, nome: str, tamanho=A4) -> Path:
    caminho = pasta / nome
    desenho = canvas.Canvas(str(caminho), pagesize=tamanho)
    desenho.drawString(50, 50, nome)
    desenho.save()
    return caminho


def _obra_com_documentos(tmp_path: Path) -> Path:
    obra = tmp_path / "1319_01_01_JF_VIVA"
    obra.mkdir()
    _pdf(obra, f"{NOME_PLANO}.pdf", landscape(A3))
    _pdf(obra, "1_List_FerragensA4.pdf")
    _pdf(obra, "2_Projeto_Producao.pdf", landscape(A4))
    _pdf(obra, "3_Resumo_Geral_Encomenda.pdf")
    _pdf(obra, f"Lista_Material_{NOME_ENC}.pdf", landscape(A3))
    _pdf(obra, "5_Etiqueta_Palete.pdf")
    _pdf(obra, "qualquer_coisa.pdf")
    (obra / "notas.txt").write_text("não é PDF", encoding="utf-8")
    return obra


def _listar(obra: Path, prioridades=None) -> list[svc.DocumentoImpressao]:
    return svc.listar_documentos(
        obra,
        nome_plano_cut_rite=NOME_PLANO,
        nome_enc_imos=NOME_ENC,
        prioridades=prioridades,
    )


def test_lista_so_pdfs_por_ordem_de_prioridade(tmp_path: Path) -> None:
    obra = _obra_com_documentos(tmp_path)

    documentos = _listar(obra)

    assert [documento.nome for documento in documentos] == [
        f"{NOME_PLANO}.pdf",
        "1_List_FerragensA4.pdf",
        "2_Projeto_Producao.pdf",
        "3_Resumo_Geral_Encomenda.pdf",
        f"Lista_Material_{NOME_ENC}.pdf",
        "5_Etiqueta_Palete.pdf",
        "qualquer_coisa.pdf",
    ]
    # Todos vêm marcados para imprimir, como no V2.
    assert all(documento.selecionado for documento in documentos)


def test_categorias_e_defaults_de_impressao(tmp_path: Path) -> None:
    obra = _obra_com_documentos(tmp_path)

    por_nome = {documento.nome: documento for documento in _listar(obra)}

    # O plano CUT-RITE sai como está gravado (folhas A3 e A4 no mesmo PDF).
    plano = por_nome[f"{NOME_PLANO}.pdf"]
    assert plano.categoria == svc.CATEGORIA_CUT_RITE
    assert plano.papel == svc.DO_PDF
    assert plano.orientacao == svc.DO_PDF
    assert plano.segue_o_pdf is True

    ferragens = por_nome["1_List_FerragensA4.pdf"]
    assert ferragens.categoria == svc.CATEGORIA_FERRAGENS
    assert ferragens.quantidade == 3
    assert ferragens.papel == svc.DO_PDF

    # Estas duas são sempre impressas num formato fixo, pedido pelo Paulo.
    projeto = por_nome["2_Projeto_Producao.pdf"]
    assert projeto.papel == "A4"
    assert projeto.orientacao == svc.ORIENTACAO_HORIZONTAL

    material = por_nome[f"Lista_Material_{NOME_ENC}.pdf"]
    assert material.categoria == svc.CATEGORIA_MATERIAIS
    assert material.papel == "A3"
    assert material.orientacao == svc.ORIENTACAO_HORIZONTAL

    assert por_nome["qualquer_coisa.pdf"].categoria == svc.CATEGORIA_OUTROS


def test_papel_e_orientacao_saem_do_proprio_pdf(tmp_path: Path) -> None:
    obra = _obra_com_documentos(tmp_path)

    por_nome = {documento.nome: documento for documento in _listar(obra)}

    plano = por_nome[f"{NOME_PLANO}.pdf"]
    assert plano.papel_ficheiro == "A3"
    assert plano.orientacao_ficheiro == svc.ORIENTACAO_HORIZONTAL

    ferragens = por_nome["1_List_FerragensA4.pdf"]
    assert ferragens.papel_ficheiro == "A4"
    assert ferragens.orientacao_ficheiro == svc.ORIENTACAO_VERTICAL

    projeto = por_nome["2_Projeto_Producao.pdf"]
    assert projeto.orientacao_ficheiro == svc.ORIENTACAO_HORIZONTAL
    # Forçado em A4 e o PDF também é A4: não há mudança de papel.
    assert projeto.papel_diferente is False


def test_paginas_de_tamanhos_diferentes_sao_todas_lidas(tmp_path: Path) -> None:
    """O plano CUT-RITE traz várias folhas A3 e, normalmente, uma A4."""
    obra = tmp_path / "obra"
    obra.mkdir()
    caminho = obra / "plano.pdf"
    desenho = canvas.Canvas(str(caminho), pagesize=landscape(A3))
    desenho.drawString(50, 50, "corte 1")
    desenho.showPage()
    desenho.drawString(50, 50, "corte 2")
    desenho.showPage()
    desenho.setPageSize(landscape(A4))
    desenho.drawString(50, 50, "resumo")
    desenho.showPage()
    desenho.save()

    paginas = svc.analisar_paginas(caminho)

    assert [pagina.papel for pagina in paginas] == ["A3", "A3", "A4"]
    assert all(
        pagina.orientacao == svc.ORIENTACAO_HORIZONTAL for pagina in paginas
    )
    dominante = svc.geometria_dominante(paginas)
    assert dominante == svc.GeometriaPagina("A3", svc.ORIENTACAO_HORIZONTAL)
    resumo = svc.resumo_paginas(paginas)
    assert "2 páginas A3 horizontal" in resumo
    assert "1 página A4 horizontal" in resumo


def test_pagina_rodada_conta_como_horizontal(tmp_path: Path) -> None:
    from pypdf import PdfReader, PdfWriter

    origem = tmp_path / "vertical.pdf"
    desenho = canvas.Canvas(str(origem), pagesize=A4)
    desenho.drawString(50, 50, "rodado")
    desenho.save()

    escritor = PdfWriter()
    pagina = PdfReader(str(origem)).pages[0]
    pagina.rotate(90)
    escritor.add_page(pagina)
    rodado = tmp_path / "rodado.pdf"
    with rodado.open("wb") as ficheiro:
        escritor.write(ficheiro)

    paginas = svc.analisar_paginas(rodado)

    assert paginas == [svc.GeometriaPagina("A4", svc.ORIENTACAO_HORIZONTAL)]


def test_prioridades_do_utilizador_mandam_na_ordem(tmp_path: Path) -> None:
    obra = _obra_com_documentos(tmp_path)
    minhas = svc.prioridades_default()
    minhas[svc.CATEGORIA_FERRAGENS] = 0
    minhas[svc.CATEGORIA_CUT_RITE] = 1

    documentos = _listar(obra, prioridades=minhas)

    assert documentos[0].nome == "1_List_FerragensA4.pdf"
    assert documentos[1].nome == f"{NOME_PLANO}.pdf"


def test_ordem_alterada_e_detetada(tmp_path: Path) -> None:
    obra = _obra_com_documentos(tmp_path)
    documentos = _listar(obra)
    guardadas = svc.prioridades_default()

    assert svc.ordem_foi_alterada(documentos, guardadas) is False

    documentos[0], documentos[1] = documentos[1], documentos[0]
    for posicao, documento in enumerate(documentos):
        documento.prioridade = posicao

    assert svc.ordem_foi_alterada(documentos, guardadas) is True
    novas = svc.prioridades_dos_documentos(documentos)
    assert novas[svc.CATEGORIA_FERRAGENS] == 0
    assert novas[svc.CATEGORIA_CUT_RITE] == 1
    # Categorias que não estão na pasta ficam como estavam.
    assert novas[svc.CATEGORIA_AUTOCAD] == svc.prioridades_default()[
        svc.CATEGORIA_AUTOCAD
    ]


def test_pasta_inexistente_devolve_lista_vazia(tmp_path: Path) -> None:
    assert svc.listar_documentos(tmp_path / "nao_existe") == []


def test_a_chave_das_prioridades_ja_nao_leva_o_utilizador() -> None:
    # Vive na coluna `user_id` das `user_prefs`.
    assert svc.CHAVE_PRIORIDADES == "producao_impressao_prioridades"
    assert ":" not in svc.CHAVE_PRIORIDADES
    assert json.dumps(svc.prioridades_default())


def test_impressao_usa_sumatra_quando_existe(tmp_path: Path, monkeypatch) -> None:
    obra = _obra_com_documentos(tmp_path)
    documentos = _listar(obra)[:2]
    documentos[1].quantidade = 2
    comandos: list[list[str]] = []

    monkeypatch.setattr(svc, "resolver_sumatra", lambda session: "SumatraPDF.exe")
    monkeypatch.setattr(
        svc.subprocess, "run", lambda cmd, check=False: comandos.append(list(cmd))
    )

    avisos = svc.imprimir_documentos(None, documentos)

    assert avisos == []
    # 1 cópia do plano + 2 cópias do segundo documento.
    assert len(comandos) == 3
    assert comandos[0][0] == "SumatraPDF.exe"
    assert "-print-to-default" in comandos[0]
    definicoes = comandos[0][comandos[0].index("-print-settings") + 1]
    # O plano segue o PDF: papel e orientação com que a página foi gravada.
    assert definicoes == "paperkind=8,landscape,shrink,disable-auto-rotation"


def test_definicoes_sumatra_por_modo(tmp_path: Path) -> None:
    obra = _obra_com_documentos(tmp_path)
    por_nome = {documento.nome: documento for documento in _listar(obra)}

    plano = por_nome[f"{NOME_PLANO}.pdf"]
    assert svc.definicoes_sumatra(plano) == ["paperkind=8,landscape,shrink,disable-auto-rotation"]

    ferragens = por_nome["1_List_FerragensA4.pdf"]
    assert svc.definicoes_sumatra(ferragens) == ["paperkind=9,portrait,shrink,disable-auto-rotation"]

    material = por_nome[f"Lista_Material_{NOME_ENC}.pdf"]
    assert svc.definicoes_sumatra(material) == ["paperkind=8,landscape,fit,disable-auto-rotation"]

    projeto = por_nome["2_Projeto_Producao.pdf"]
    assert svc.definicoes_sumatra(projeto) == ["paperkind=9,landscape,fit,disable-auto-rotation"]

    # Frente e verso e preto-e-branco entram no fim das definições.
    projeto.duplex = True
    projeto.cor = "pb"
    assert svc.definicoes_sumatra(projeto) == [
        "paperkind=9,landscape,fit,disable-auto-rotation,duplex,monochrome"
    ]

    # Forçar vertical continua possível para quem quiser.
    ferragens.papel = "A4"
    ferragens.orientacao = svc.ORIENTACAO_VERTICAL
    assert svc.definicoes_sumatra(ferragens) == ["paperkind=9,portrait,fit,disable-auto-rotation"]


def test_plano_com_folhas_a3_e_a4_imprime_cada_uma_no_seu_papel(
    tmp_path: Path, monkeypatch
) -> None:
    """O plano CUT-RITE traz folhas A3 e, no fim, uma A4 — todas horizontais."""
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

    documentos = svc.listar_documentos(obra, nome_plano_cut_rite=NOME_PLANO)

    assert svc.definicoes_sumatra(documentos[0]) == [
        "1-2,paperkind=8,landscape,shrink,disable-auto-rotation",
        "3,paperkind=9,landscape,shrink,disable-auto-rotation",
    ]

    comandos: list[list[str]] = []
    monkeypatch.setattr(svc, "resolver_sumatra", lambda session: "SumatraPDF.exe")
    monkeypatch.setattr(
        svc.subprocess, "run", lambda cmd, check=False: comandos.append(list(cmd))
    )
    svc.imprimir_documentos(None, documentos)

    # Um trabalho de impressão por bloco de páginas.
    assert len(comandos) == 2


def test_formato_da_impressora_resolve_nomes_com_medidas() -> None:
    """A EPSON ET-16650 chama "A3 297 x 420 mm" ao A3 — tem de ser aceite."""
    formatos_epson = [
        ("A4 210 x 297 mm", 9),
        ("A3 297 x 420 mm", 8),
        ("A3+ 329 x 483 mm", 258),
    ]

    assert svc._id_do_formato(formatos_epson, "A3", 8) == 8
    assert svc._id_do_formato(formatos_epson, "A4", 9) == 9
    # Nome exato ganha ao nome com medidas.
    assert svc._id_do_formato([("A3 extra", 63), ("A3", 8)], "A3", 8) == 8
    # Sem nenhum formato A3, não se inventa nenhum.
    assert svc._id_do_formato([("A4", 9)], "A3", 8) is None


def test_id_papel_usa_a_impressora_e_senao_o_standard() -> None:
    assert svc.id_papel("A3") == 8
    assert svc.id_papel("A4") == 9
    assert svc.id_papel("") is None
    # O número do driver manda sobre o standard do Windows.
    assert svc.id_papel("A3", {"A3": 258}) == 258


def test_aviso_quando_a_impressora_nao_tem_o_papel(tmp_path: Path) -> None:
    obra = _obra_com_documentos(tmp_path)
    documentos = _listar(obra)

    avisos = svc._avisos_de_papel(documentos, {"A4": 9})

    assert len(avisos) == 1
    assert "A3" in avisos[0]
    # Com A3 e A4 disponíveis não há nada a avisar.
    assert svc._avisos_de_papel(documentos, {"A4": 9, "A3": 8}) == []


def test_impressao_sem_sumatra_avisa_uma_vez(tmp_path: Path, monkeypatch) -> None:
    obra = _obra_com_documentos(tmp_path)
    documentos = _listar(obra)

    monkeypatch.setattr(svc, "resolver_sumatra", lambda session: None)
    impressos: list[str] = []
    monkeypatch.setattr(
        svc.os, "startfile", lambda caminho, verbo: impressos.append(caminho)
    )

    avisos = svc.imprimir_documentos(None, documentos)

    assert len(impressos) >= len(documentos)
    # Um aviso só, não um por documento.
    assert len(avisos) == 1
    assert "SumatraPDF" in avisos[0]


def test_dialogo_impressao_tem_as_pecas_esperadas() -> None:
    from app.ui.dialogs import producao_impressao_dialog as dialogo

    fonte = inspect.getsource(dialogo)

    assert "Imprimir Selecionados" in fonte
    assert "▲ Subir" in fonte and "▼ Descer" in fonte
    # A pergunta que decide se a nova ordem fica como modelo.
    assert "Gravar para as próximas obras" in fonte
    assert "Só nesta obra" in fonte
    assert "guardar_prioridades_utilizador" in fonte
    assert "setToolTip" in fonte
    assert "status_label" in fonte


def test_pagina_producao_abre_a_impressao() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    fonte = inspect.getsource(ProducaoPage)

    # Imprimir vive dentro do botão "Funções", como as ações do CUT-RITE.
    assert "self.funcoes_menu.addAction(self.imprimir_action)" in fonte
    assert "self.imprimir_action.triggered.connect(self._abrir_impressao)" in fonte
    assert "ProducaoImpressaoDialog" in fonte
    assert hasattr(ProducaoPage, "_abrir_impressao")
