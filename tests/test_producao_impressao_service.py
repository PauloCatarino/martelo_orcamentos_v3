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

    plano = por_nome[f"{NOME_PLANO}.pdf"]
    assert plano.categoria == svc.CATEGORIA_CUT_RITE
    assert plano.papel == "A3"
    assert plano.orientacao == svc.ORIENTACAO_HORIZONTAL

    ferragens = por_nome["1_List_FerragensA4.pdf"]
    assert ferragens.categoria == svc.CATEGORIA_FERRAGENS
    assert ferragens.quantidade == 3

    material = por_nome[f"Lista_Material_{NOME_ENC}.pdf"]
    assert material.categoria == svc.CATEGORIA_MATERIAIS
    assert por_nome["qualquer_coisa.pdf"].categoria == svc.CATEGORIA_OUTROS


def test_papel_do_ficheiro_e_lido_do_pdf(tmp_path: Path) -> None:
    obra = _obra_com_documentos(tmp_path)

    por_nome = {documento.nome: documento for documento in _listar(obra)}

    assert por_nome[f"{NOME_PLANO}.pdf"].papel_ficheiro == "A3"
    assert por_nome["1_List_FerragensA4.pdf"].papel_ficheiro == "A4"
    # A3 impresso em A3 não precisa de ajuste.
    assert por_nome[f"{NOME_PLANO}.pdf"].papel_diferente is False


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


def test_chave_das_prioridades_e_por_utilizador() -> None:
    assert (
        svc.chave_prioridades_utilizador(4) == "producao_impressao_prioridades:4"
    )
    assert (
        svc.chave_prioridades_utilizador(None)
        == "producao_impressao_prioridades:default"
    )
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
    assert "paper=A3" in definicoes and "landscape" in definicoes


def test_impressao_sem_sumatra_avisa_quando_o_papel_e_diferente(
    tmp_path: Path, monkeypatch
) -> None:
    obra = tmp_path / "obra"
    obra.mkdir()
    _pdf(obra, "RP_01.pdf", landscape(A3))
    documentos = svc.listar_documentos(obra)
    assert documentos[0].papel == "A4"  # OUTROS imprime em A4

    monkeypatch.setattr(svc, "resolver_sumatra", lambda session: None)
    impressos: list[str] = []
    monkeypatch.setattr(
        svc.os, "startfile", lambda caminho, verbo: impressos.append(caminho)
    )

    avisos = svc.imprimir_documentos(None, documentos)

    assert impressos
    assert avisos and "SumatraPDF" in avisos[0]


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
