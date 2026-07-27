"""Tests for the production preparation panel service."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from app.services import producao_preparacao_service as svc


def _contexto(base: Path) -> svc.PreparacaoContexto:
    obra = base / "1319_01_01_JF_VIVA"
    obra.mkdir(parents=True, exist_ok=True)
    return svc.PreparacaoContexto(
        codigo_processo="26.1319_01_01_JF_VIVA",
        pasta_obra=obra,
        nome_enc_imos="1319_01_26_JF_VIVA",
        nome_plano_cut_rite="1319_01_01_26_JF_VIVA",
        pasta_origem_cnc=base / "cnc",
        pasta_origem_cnc_obra=base / "cnc" / "1319_01_26_JF_VIVA",
        pasta_programas_obra=obra / "1319_01_26_JF_VIVA",
        pasta_destino_cnc=base / "mpr",
        pasta_destino_cnc_ano=base / "mpr" / "2026_MPR",
        pasta_destino_cnc_obra=base / "mpr" / "2026_MPR" / "1319_01_26_JF_VIVA",
        conj_pdf=obra / svc.CONJ_PDF_NOME,
        projeto_pdf=obra / svc.PROJETO_PRODUCAO_PDF_NOME,
    )


def _estados_por_key(contexto, keys=None) -> dict[str, svc.PreparacaoEstado]:
    return {
        estado.key: estado
        for estado in svc.recolher_estados(contexto, keys_obrigatorias=keys)
    }


def test_pasta_vazia_marca_tudo_pendente(tmp_path: Path) -> None:
    contexto = _contexto(tmp_path)

    estados = _estados_por_key(contexto)

    assert estados["conj_pdf"].estado == svc.ESTADO_PENDENTE
    assert estados["lista_material_pdf"].estado == svc.ESTADO_PENDENTE
    # Sem origem IMOS os passos seguintes ficam bloqueados, não pendentes.
    assert estados["cnc_origem"].estado == svc.ESTADO_PENDENTE
    assert estados["cnc_obra"].estado == svc.ESTADO_BLOQUEADO
    assert estados["obra_pronta"].estado == svc.ESTADO_BLOQUEADO


def test_ficheiro_existente_fica_ok(tmp_path: Path) -> None:
    contexto = _contexto(tmp_path)
    (contexto.pasta_obra / "1_List_FerragensA4.pdf").write_bytes(b"")
    (contexto.pasta_obra / "Lista_Material_1319.pdf").write_bytes(b"")

    estados = _estados_por_key(contexto)

    assert estados["ferragens_a4_pdf"].estado == svc.ESTADO_OK
    assert estados["lista_material_pdf"].estado == svc.ESTADO_OK
    assert str(contexto.pasta_obra) in estados["ferragens_a4_pdf"].detalhe


def test_pdf_mais_antigo_que_o_excel_fica_desatualizado(tmp_path: Path) -> None:
    contexto = _contexto(tmp_path)
    pdf = contexto.pasta_obra / "3_Resumo_Geral_Encomenda.pdf"
    excel = contexto.pasta_obra / "3_Resumo_Geral_Encomenda.xlsx"
    pdf.write_bytes(b"")
    excel.write_bytes(b"")
    import os

    os.utime(pdf, (1_700_000_000, 1_700_000_000))
    os.utime(excel, (1_700_000_900, 1_700_000_900))

    estados = _estados_por_key(contexto)

    assert estados["resumo_geral_pdf"].estado == svc.ESTADO_DESATUALIZADO


def test_plano_cutrite_sem_nome_fica_bloqueado(tmp_path: Path) -> None:
    contexto = _contexto(tmp_path)
    sem_plano = svc.PreparacaoContexto(
        **{**contexto.__dict__, "nome_plano_cut_rite": ""}
    )

    estados = _estados_por_key(sem_plano)

    assert estados["cutrite_pdf"].estado == svc.ESTADO_BLOQUEADO
    assert "Nome Plano CUT-RITE" in estados["cutrite_pdf"].detalhe


def test_preferencias_do_utilizador_escondem_validacoes(tmp_path: Path) -> None:
    contexto = _contexto(tmp_path)

    estados = _estados_por_key(
        contexto, keys={"conj_pdf", *svc.KEYS_SEMPRE_OBRIGATORIAS}
    )

    assert "conj_pdf" in estados
    assert "etiqueta_palete_pdf" not in estados
    # As validações dos programas CNC nunca desaparecem.
    assert "cnc_enviado" in estados


def test_copiar_e_enviar_programas_cnc(tmp_path: Path) -> None:
    contexto = _contexto(tmp_path)
    contexto.pasta_origem_cnc_obra.mkdir(parents=True)
    (contexto.pasta_origem_cnc_obra / "peca.mpr").write_text("programa", encoding="utf-8")

    destino_obra = svc.copiar_programas_para_obra(contexto)
    destino_maquinas = svc.enviar_programas_para_cnc(contexto)

    assert (destino_obra / "peca.mpr").is_file()
    assert (destino_maquinas / "peca.mpr").is_file()
    estados = _estados_por_key(contexto)
    assert estados["cnc_obra"].estado == svc.ESTADO_OK
    assert estados["cnc_enviado"].estado == svc.ESTADO_OK


def test_enviar_sem_programas_na_obra_da_erro(tmp_path: Path) -> None:
    contexto = _contexto(tmp_path)

    try:
        svc.enviar_programas_para_cnc(contexto)
    except ValueError as erro:
        assert "Pasta de programas na obra em falta" in str(erro)
    else:  # pragma: no cover - o erro tem mesmo de acontecer
        raise AssertionError("enviar_programas_para_cnc devia falhar sem programas")


def test_gerar_projeto_producao_pdf_em_a4_horizontal(tmp_path: Path) -> None:
    from pypdf import PdfReader
    from reportlab.pdfgen import canvas

    contexto = _contexto(tmp_path)
    desenho = canvas.Canvas(str(contexto.conj_pdf), pagesize=(1684, 1190))
    for pagina in range(3):
        desenho.drawString(100, 600, f"pagina {pagina}")
        desenho.showPage()
    desenho.save()

    saida = svc.gerar_projeto_producao_pdf(contexto)

    leitor = PdfReader(str(saida))
    # Só as duas primeiras páginas do CONJ.pdf vão para produção.
    assert len(leitor.pages) == svc.MAX_PAGINAS_PROJETO_PDF
    assert round(float(leitor.pages[0].mediabox.width)) == 842
    assert round(float(leitor.pages[0].mediabox.height)) == 595
    assert _estados_por_key(contexto)["projeto_pdf"].estado == svc.ESTADO_OK


def test_chave_e_serializacao_das_preferencias() -> None:
    assert (
        svc.chave_validacoes_utilizador(7) == "producao_preparacao_validacoes:7"
    )
    assert (
        svc.chave_validacoes_utilizador(None)
        == "producao_preparacao_validacoes:default"
    )

    fonte = inspect.getsource(svc.guardar_validacoes_utilizador)
    assert "json.dumps" in fonte
    # Chaves desconhecidas não podem ir para a base de dados.
    assert "KEYS_FICHEIROS" in fonte

    opcoes = svc.listar_validacoes_configuraveis()
    assert {opcao["key"] for opcao in opcoes} == set(svc.KEYS_FICHEIROS)
    assert json.dumps(opcoes)  # serializável para o diálogo


def test_dialogo_preparacao_tem_as_pecas_esperadas() -> None:
    from app.ui.dialogs import producao_preparacao_dialog as dialogo

    fonte = inspect.getsource(dialogo)

    assert "Preparação de Produção" in fonte
    assert "Preferências..." in fonte
    assert '"Ação", "Validação", "Estado", "Detalhe"' in fonte
    assert "svc.ACAO_GERAR_PROJETO_PDF" in fonte
    assert "svc.ACAO_COPIAR_PROGRAMAS_OBRA" in fonte
    assert "svc.ACAO_ENVIAR_PROGRAMAS_CNC" in fonte
    # Preferências por utilizador, não globais.
    assert "guardar_validacoes_utilizador" in fonte
    assert "setToolTip" in fonte
    assert "status_label" in fonte


def test_pagina_producao_abre_a_preparacao() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    fonte = inspect.getsource(ProducaoPage)

    assert "self.preparacao_button" in fonte
    assert "ProducaoPreparacaoDialog" in fonte
    assert hasattr(ProducaoPage, "_abrir_preparacao")
