"""Tests for the production preparation panel service."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from app.services import producao_preparacao_service as svc
from app.services.system_setting_service import SystemSettingService


def _contexto(base: Path) -> svc.PreparacaoContexto:
    obra = base / "1319_01_01_JF_VIVA"
    obra.mkdir(parents=True, exist_ok=True)
    layouts = base / "layouts"
    nome_enc_imos = "1319_01_26_JF_VIVA"
    return svc.PreparacaoContexto(
        codigo_processo="26.1319_01_01_JF_VIVA",
        pasta_obra=obra,
        nome_enc_imos=nome_enc_imos,
        nome_plano_cut_rite="1319_01_01_26_JF_VIVA",
        pasta_layouts_pdf_imos=layouts,
        conj_pdf_origem=layouts / f"{nome_enc_imos}.pdf",
        pasta_origem_cnc=base / "cnc",
        pasta_origem_cnc_obra=base / "cnc" / nome_enc_imos,
        pasta_programas_obra=obra / nome_enc_imos,
        pasta_destino_cnc=base / "mpr",
        pasta_destino_cnc_ano=base / "mpr" / "2026_MPR",
        pasta_destino_cnc_obra=base / "mpr" / "2026_MPR" / nome_enc_imos,
        conj_pdf=obra / f"CONJ_{nome_enc_imos}.pdf",
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


def test_contexto_resolve_layout_imos_e_nome_conj_da_obra(
    session, tmp_path: Path
) -> None:
    layouts = tmp_path / "exports_imos"
    SystemSettingService(session).guardar_valor(
        svc.KEY_PASTA_LAYOUTS_PDF_IMOS, str(layouts)
    )

    contexto = svc.resolver_contexto(
        session,
        codigo_processo="26.1449_01_01_JF_VIVA",
        pasta_obra=tmp_path / "obra",
        nome_enc_imos="1449_01_26_JF_VIVA",
    )

    assert contexto.conj_pdf_origem == layouts / "1449_01_26_JF_VIVA.pdf"
    assert contexto.conj_pdf == tmp_path / "obra" / "CONJ_1449_01_26_JF_VIVA.pdf"


def test_mover_layout_imos_para_obra_renomeia_e_remove_origem(tmp_path: Path) -> None:
    contexto = _contexto(tmp_path)
    contexto.pasta_layouts_pdf_imos.mkdir(parents=True)
    contexto.conj_pdf_origem.write_bytes(b"layout real")

    antes = _estados_por_key(contexto)["conj_pdf"]
    destino = svc.mover_conj_para_obra(contexto)
    depois = _estados_por_key(contexto)["conj_pdf"]

    assert antes.acao == svc.ACAO_MOVER_CONJ_PDF
    assert antes.acao_label == "Mover"
    assert destino == contexto.conj_pdf
    assert destino.read_bytes() == b"layout real"
    assert not contexto.conj_pdf_origem.exists()
    assert depois.estado == svc.ESTADO_OK


def test_mover_conj_nao_substitui_destino_sem_confirmacao(tmp_path: Path) -> None:
    contexto = _contexto(tmp_path)
    contexto.pasta_layouts_pdf_imos.mkdir(parents=True)
    contexto.conj_pdf_origem.write_bytes(b"novo")
    contexto.conj_pdf.write_bytes(b"anterior")

    estado = _estados_por_key(contexto)["conj_pdf"]
    with pytest.raises(FileExistsError, match="confirmação"):
        svc.mover_conj_para_obra(contexto)

    assert estado.estado == svc.ESTADO_DESATUALIZADO
    assert estado.acao == svc.ACAO_MOVER_CONJ_PDF
    assert contexto.conj_pdf.read_bytes() == b"anterior"
    assert contexto.conj_pdf_origem.read_bytes() == b"novo"


def test_mover_conj_substitui_so_quando_confirmado(tmp_path: Path) -> None:
    contexto = _contexto(tmp_path)
    contexto.pasta_layouts_pdf_imos.mkdir(parents=True)
    contexto.conj_pdf_origem.write_bytes(b"novo")
    contexto.conj_pdf.write_bytes(b"anterior")

    svc.mover_conj_para_obra(contexto, substituir=True)

    assert contexto.conj_pdf.read_bytes() == b"novo"
    assert not contexto.conj_pdf_origem.exists()


def test_conj_pdf_legacy_continua_valido_para_obras_antigas(tmp_path: Path) -> None:
    contexto = _contexto(tmp_path)
    legado = contexto.pasta_obra / svc.CONJ_PDF_NOME_LEGACY
    legado.write_bytes(b"obra antiga")

    estado = _estados_por_key(contexto)["conj_pdf"]

    assert estado.estado == svc.ESTADO_OK
    assert estado.detalhe == str(legado)


def test_ficheiro_existente_fica_ok(tmp_path: Path) -> None:
    contexto = _contexto(tmp_path)
    (contexto.pasta_obra / "1_List_FerragensA4.pdf").write_bytes(b"")
    (contexto.pasta_obra / "Lista_Material_1319.pdf").write_bytes(b"")

    estados = _estados_por_key(contexto)

    assert estados["ferragens_a4_pdf"].estado == svc.ESTADO_OK
    assert estados["lista_material_pdf"].estado == svc.ESTADO_OK
    assert str(contexto.pasta_obra) in estados["ferragens_a4_pdf"].detalhe


def test_novos_nomes_pdf_do_centro_exportacao_ficam_ok(tmp_path: Path) -> None:
    contexto = _contexto(tmp_path)
    nome_enc = contexto.nome_enc_imos
    esperados = {
        "ferragens_a4_pdf": f"2_Lista_Ferragens_{nome_enc}.pdf",
        "resumo_ml_orlas_pdf": f"4_Resumo_Orlas_{nome_enc}.pdf",
        "etiqueta_palete_pdf": f"5_Etiqueta_Palete_{nome_enc}.pdf",
        "lista_material_pdf": f"6_Lista_Material_{nome_enc}.pdf",
    }
    for nome in esperados.values():
        (contexto.pasta_obra / nome).write_bytes(b"")

    estados = _estados_por_key(contexto)

    for key, nome in esperados.items():
        assert estados[key].estado == svc.ESTADO_OK
        assert estados[key].detalhe.endswith(nome)


def test_pdf_mais_antigo_que_o_excel_fica_desatualizado(tmp_path: Path) -> None:
    contexto = _contexto(tmp_path)
    pdf = contexto.pasta_obra / "5_Etiqueta_Palete_1319_01_26_JF_VIVA.pdf"
    excel = contexto.pasta_obra / "5_Etiqueta_Palete.xlsx"
    pdf.write_bytes(b"")
    excel.write_bytes(b"")
    import os

    os.utime(pdf, (1_700_000_000, 1_700_000_000))
    os.utime(excel, (1_700_000_900, 1_700_000_900))

    estados = _estados_por_key(contexto)

    assert estados["etiqueta_palete_pdf"].estado == svc.ESTADO_DESATUALIZADO


def test_resumo_geral_encomenda_foi_retirado_das_validacoes() -> None:
    assert "resumo_geral_pdf" not in svc.KEYS_FICHEIROS
    assert all(
        "3_Resumo_Geral_Encomenda" not in opcao["label"]
        for opcao in svc.listar_validacoes_configuraveis()
    )


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


def test_projeto_producao_pdf_sai_leve_o_bastante_para_email(tmp_path: Path) -> None:
    """Um CONJ.pdf pesado do iMos não pode dar um anexo impossível de enviar."""
    import random

    from PIL import Image
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    random.seed(3)
    render = Image.new("RGB", (3000, 2100))
    pixeis = render.load()
    for y in range(2100):
        base = 130 + int(80 * y / 2100)
        for x in range(3000):
            ruido = random.randint(-25, 25)
            pixeis[x, y] = (base + ruido, base - 20 + ruido, base - 45 + ruido)

    contexto = _contexto(tmp_path)
    desenho = canvas.Canvas(str(contexto.conj_pdf), pagesize=(1684, 1190))
    for _pagina in range(2):
        desenho.drawImage(ImageReader(render), 0, 0, 1684, 1190)
        desenho.showPage()
    desenho.save()
    assert contexto.conj_pdf.stat().st_size > 5 * 1024 * 1024

    saida = svc.gerar_projeto_producao_pdf(contexto)

    assert saida.stat().st_size < 5 * 1024 * 1024


def test_chave_e_serializacao_das_preferencias() -> None:
    # O utilizador vive na coluna `user_id` das `user_prefs`, nao na chave.
    assert svc.CHAVE_VALIDACOES == "producao_preparacao_validacoes"
    assert ":" not in svc.CHAVE_VALIDACOES

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
    assert "svc.ACAO_MOVER_CONJ_PDF" in fonte
    assert "svc.ACAO_COPIAR_PROGRAMAS_OBRA" in fonte
    assert "svc.ACAO_ENVIAR_PROGRAMAS_CNC" in fonte
    # Preferências por utilizador, não globais.
    assert "guardar_validacoes_utilizador" in fonte
    assert "setToolTip" in fonte
    assert "status_label" in fonte
    assert "WindowMaximized" in fonte
    assert "setRowHeight(linha, 40)" in fonte
    assert fonte.index("layout.addLayout(botoes)") < fonte.index(
        "layout.addWidget(self.tabela, stretch=1)"
    )


def test_pagina_producao_abre_a_preparacao() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    fonte = inspect.getsource(ProducaoPage)

    # A Preparação vive dentro do botão "Funções", como as ações do CUT-RITE.
    assert "self.funcoes_button.setMenu(self.funcoes_menu)" in fonte
    assert "self.preparacao_action.triggered.connect(self._abrir_preparacao)" in fonte
    assert "self.funcoes_menu.setToolTipsVisible(True)" in fonte
    assert "ProducaoPreparacaoDialog" in fonte
    assert hasattr(ProducaoPage, "_abrir_preparacao")
