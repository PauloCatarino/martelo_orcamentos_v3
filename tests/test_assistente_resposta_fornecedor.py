"""O assistente que lê a resposta do fornecedor (G8).

Três coisas, e nada mais do que estas três: encontrar as colunas quando o
fornecedor mexe no ficheiro, ler uma tabela de preços em PDF, e assinalar
valores estranhos antes de entrarem no catálogo.

O que o assistente **não** faz tem tanto peso como o que faz: nenhuma linha
destas grava seja o que for. Tudo o que sai daqui é uma proposta à espera de um
visto.
"""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app.domain.resposta_fornecedor import (
    ESTADO_ANOMALIA,
    ESTADO_ATUALIZA,
    ORIGEM_CONTEUDO,
    ORIGEM_PARECIDO,
    ORIGEM_TITULO,
    avisos_do_valor,
    ler_respostas,
    mapear_colunas,
)
from app.services.def_materia_prima_service import (
    CriarDefMateriaPrimaData,
    DefMateriaPrimaService,
)
from app.services.leitor_pdf_precos import e_pdf, interpretar_linha, ler_pdf
from app.services.resposta_fornecedor_service import RespostaFornecedorService
from app.ui.dialogs.resposta_fornecedor_dialog import RespostaFornecedorDialog

_app = QApplication.instance() or QApplication([])

HOJE = date(2026, 8, 25)


def _catalogo(**overrides):
    base = {
        "id": 1,
        "ref_le": "PLC0052",
        "descricao": "AGL TERM BEGE ARDENNE 19MM",
        "preco_tabela": Decimal("30.00"),
        "desconto": Decimal("18"),
        "margem": None,
        "referencia_fornecedor": "413/BRILHO",
    }
    base.update(overrides)
    return {base["ref_le"].upper(): SimpleNamespace(**base)}


# ----------------------------------------------------- encontrar as colunas


def test_titulo_parecido_e_reconhecido_e_dito_ao_utilizador() -> None:
    """«Preço tabela 2026» não é o nosso título, mas diz o mesmo."""
    cabecalhos = ["Ref. LE", "Descrição do artigo", "Preço tabela 2026", "Desconto"]

    mapa = mapear_colunas(cabecalhos, [("PLC0052", "AGL", 31.2, 20)])

    assert mapa["codigo"] == 0
    assert mapa["preco_novo"] == 2
    assert mapa["desconto"] == 3
    assert "preco_novo" in mapa.renomeados()
    assert any("Preço tabela 2026" in nota for nota in mapa.notas(cabecalhos))


def test_desconto_nao_rouba_a_coluna_da_descricao() -> None:
    """«desc» apanharia «descrição»: os títulos curtos só valem exatos."""
    mapa = mapear_colunas(["Descrição", "Desconto %"], [("AGL", 20)])

    assert mapa["designacao"] == 0
    assert mapa["desconto"] == 1


def test_coluna_sem_titulo_conhecido_e_reconhecida_pelos_valores() -> None:
    """O fornecedor refez a folha e pôs títulos que não dizem nada."""
    cabecalhos = ["A", "B", "C"]
    linhas = [("PLC0052", "AGL TERM BEGE", 31.2), ("PLC0053", "AGL BRANCO", 12.5)]

    mapa = mapear_colunas(cabecalhos, linhas)

    assert mapa["codigo"] == 0
    assert mapa["preco_novo"] == 2
    assert set(mapa.adivinhados()) == {"codigo", "preco_novo"}
    assert any("confirme" in nota for nota in mapa.notas(cabecalhos))


def test_nao_adivinha_o_preco_quando_ha_duas_colunas_de_numeros() -> None:
    """Entre duas colunas de números não se escolhe à sorte: fica por saber."""
    linhas = [("PLC0052", 31.2, 20), ("PLC0053", 12.5, 15)]

    mapa = mapear_colunas(["A", "B", "C"], linhas)

    assert mapa["codigo"] == 0
    assert mapa["preco_novo"] is None


def test_como_cada_coluna_foi_encontrada_fica_registado() -> None:
    mapa = mapear_colunas(
        ["Código", "Preço tabela 2026", "X"], [("PLC0052", 31.2, "nota")]
    )

    assert mapa.origens["codigo"] == ORIGEM_TITULO
    assert mapa.origens["preco_novo"] == ORIGEM_PARECIDO
    assert ORIGEM_CONTEUDO not in mapa.origens.values()


def test_reconhece_o_material_pela_referencia_do_fornecedor() -> None:
    """O fornecedor respondeu com a lista dele: só lá está a referência dele."""
    cabecalhos = ["Ref. fornecedor", "Designação", "Preço tabela"]
    linhas = [("413/BRILHO", "AGL TERM BEGE", 31.2)]
    catalogo = _catalogo()
    por_referencia = {"413/BRILHO": catalogo["PLC0052"]}

    propostas = ler_respostas(
        cabecalhos, linhas, {}, materias_por_referencia=por_referencia
    )

    assert propostas[0].estado == ESTADO_ATUALIZA
    assert propostas[0].materia_prima_id == 1
    assert propostas[0].codigo == "PLC0052"


# ------------------------------------------------------ valores estranhos


def test_preco_a_zero_e_assinalado() -> None:
    avisos = avisos_do_valor(Decimal("30"), Decimal("0"), None, Decimal("-100"))

    assert any("zero" in aviso for aviso in avisos)


def test_desconto_escrito_em_fracao() -> None:
    """0,2 em vez de 20 — o erro que o Excel antigo deixava passar."""
    avisos = avisos_do_valor(Decimal("30"), Decimal("31"), Decimal("0.2"), None)

    assert any("20%" in aviso for aviso in avisos)


def test_desconto_impossivel() -> None:
    avisos = avisos_do_valor(Decimal("30"), Decimal("31"), Decimal("120"), None)

    assert any("fora do normal" in aviso for aviso in avisos)


def test_virgula_fora_do_sitio() -> None:
    """24,87 escrito 2487: a variação é enorme, mas a razão é outra."""
    avisos = avisos_do_valor(
        Decimal("24.87"), Decimal("2487"), None, Decimal("9900")
    )

    assert any("vírgula fora do sítio" in aviso for aviso in avisos)
    assert not any("Variação de" in aviso for aviso in avisos)


def test_variacao_grande_continua_a_ser_assinalada() -> None:
    avisos = avisos_do_valor(Decimal("30"), Decimal("48.9"), None, Decimal("63"))

    assert any("Variação de 63%" in aviso for aviso in avisos)


def test_valor_ilegivel_no_preco_nao_passa_por_linha_em_branco() -> None:
    cabecalhos = ["Código", "Preço tabela atualizado"]

    propostas = ler_respostas(cabecalhos, [("PLC0052", "sob consulta")], _catalogo())

    assert propostas[0].estado == ESTADO_ANOMALIA
    assert "sob consulta" in propostas[0].detalhe


def test_material_repetido_no_ficheiro_fica_por_confirmar() -> None:
    """A lista do fornecedor colada por baixo da nossa: o artigo vem duas vezes."""
    cabecalhos = ["Código", "Preço tabela atualizado"]
    linhas = [("PLC0052", 31.2), ("PLC0052", 32.5)]

    propostas = ler_respostas(cabecalhos, linhas, _catalogo())

    assert [p.estado for p in propostas] == [ESTADO_ANOMALIA, ESTADO_ANOMALIA]
    assert all("mais do que uma linha" in p.detalhe for p in propostas)
    assert not any(p.sugerido for p in propostas)


def test_linha_repetida_em_branco_nao_levanta_suspeita() -> None:
    cabecalhos = ["Código", "Preço tabela atualizado"]

    propostas = ler_respostas(cabecalhos, [("PLC0052", 31.2), ("PLC0052", None)], _catalogo())

    assert propostas[0].estado == ESTADO_ATUALIZA


def test_desconto_novo_com_preco_igual_continua_a_ser_uma_alteracao() -> None:
    """O preço mantém-se mas o desconto mudou: isso muda o líquido."""
    cabecalhos = ["Código", "Preço tabela atualizado", "Desconto %"]

    propostas = ler_respostas(cabecalhos, [("PLC0052", 30.00, 25)], _catalogo())

    assert propostas[0].estado == ESTADO_ATUALIZA
    assert propostas[0].desconto_novo == Decimal("25")


# --------------------------------------------------------- tabela em PDF


def test_le_uma_linha_de_pdf_com_a_nossa_referencia() -> None:
    linha = interpretar_linha("PLC0052 AGL TERM BEGE ARDENNE 19MM 31,20 €")

    assert linha[0] == "PLC0052"
    assert linha[1] == "AGL TERM BEGE ARDENNE 19MM"
    assert linha[2] == Decimal("31.20")


def test_le_o_desconto_do_pdf_quando_vem_com_o_sinal() -> None:
    linha = interpretar_linha("PLC0052 AGL TERM BEGE 31,20 € 20%")

    assert linha[2] == Decimal("31.20")
    assert linha[3] == Decimal("20")


def test_linha_de_pdf_sem_referencia_conhecida_e_ignorada() -> None:
    assert interpretar_linha("Condições de pagamento: 30 dias") is None
    assert interpretar_linha("Tabela de preços 2026") is None


def test_pdf_reconhece_a_referencia_do_proprio_fornecedor() -> None:
    """Sem uma Ref LE à vista, vale a referência dele — se a conhecermos."""
    conhecidas = {"413/BRILHO"}

    linha = interpretar_linha(
        "413/BRILHO AGLOMERADO BEGE 31,20", lambda p: p in conhecidas
    )

    assert linha[0] == "413/BRILHO"
    assert linha[2] == Decimal("31.20")


def test_guarda_a_linha_original_do_pdf_nas_observacoes() -> None:
    """Quem revê tem de poder comparar com o que estava escrito no PDF."""
    linha = interpretar_linha("PLC0052 AGL TERM BEGE 31,20")

    assert linha[4].startswith("Lido do PDF:")
    assert "31,20" in linha[4]


def test_e_pdf_olha_para_a_extensao() -> None:
    assert e_pdf("tabela.PDF") is True
    assert e_pdf("resposta.xlsx") is False


def test_ler_pdf_de_verdade(tmp_path) -> None:
    """Um PDF escrito por nós, lido de volta pelo assistente."""
    reportlab = pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    caminho = tmp_path / "tabela.pdf"
    folha = canvas.Canvas(str(caminho))
    folha.drawString(60, 800, "TABELA DE PRECOS 2026")
    folha.drawString(60, 780, "PLC0052 AGL TERM BEGE ARDENNE 19MM 31,20")
    folha.drawString(60, 760, "PLC0099 ARTIGO QUE NAO TEMOS 10,00")
    folha.drawString(60, 740, "Condicoes de pagamento 30 dias")
    folha.save()

    cabecalhos, linhas, primeira = ler_pdf(caminho)

    assert cabecalhos[0] == "Código"
    assert primeira == 1
    assert [linha[0] for linha in linhas] == ["PLC0052", "PLC0099"]
    assert linhas[0][2] == Decimal("31.20")
    assert reportlab is not None


# ---------------------------------------------- ciclo, serviço e diálogo


@pytest.fixture()
def service(session) -> RespostaFornecedorService:
    return RespostaFornecedorService(session)


def _material(session, **overrides):
    dados = {
        "descricao": "AGL TERM BEGE ARDENNE 19MM",
        "ref_le": "PLC0052",
        "familia_original_excel": "PLACAS",
        "unidade": "M2",
        "preco_tabela": Decimal("30.00"),
        "desconto": Decimal("18"),
        "preco_liquido": Decimal("24.60"),
        "referencia_fornecedor": "413/BRILHO",
        "data_ultimo_preco": date(2025, 7, 23),
    }
    dados.update(overrides)
    return DefMateriaPrimaService(session).criar_materia_prima(
        CriarDefMateriaPrimaData(**dados)
    )


def test_servico_le_um_pdf_e_propoe_sem_gravar(session, service, tmp_path) -> None:
    pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    materia = _material(session)
    caminho = tmp_path / "tabela.pdf"
    folha = canvas.Canvas(str(caminho))
    folha.drawString(60, 800, "413/BRILHO AGLOMERADO TERMOLAMINADO BEGE 33,00")
    folha.save()

    leitura = service.ler_com_notas(caminho)

    assert leitura.origem == "PDF"
    assert any("palpite" in nota for nota in leitura.notas)
    assert [p.materia_prima_id for p in leitura.propostas] == [materia.id]
    # Nada mudou: ler é ler.
    assert DefMateriaPrimaService(session).obter_por_id(
        materia.id
    ).preco_tabela == Decimal("30.00")


def test_referencia_do_fornecedor_repetida_deixa_de_identificar(session, service) -> None:
    """Duas matérias-primas com a mesma referência: nenhuma pode ser escolhida."""
    _material(session)
    _material(session, ref_le="PLC0053", descricao="AGL TERM BEGE OUTRO 19MM")

    _, por_referencia = service._indices()

    assert "413/BRILHO" not in por_referencia


def test_ler_com_notas_aceita_o_anexo_de_sempre(session, service, tmp_path) -> None:
    """O caminho normal continua igual, e sem notas nenhumas a assustar."""
    import openpyxl

    materia = _material(session)
    livro = openpyxl.Workbook()
    folha = livro.active
    folha.append(["Código", "Designação", "Preço tabela atual", "Preço tabela atualizado"])
    folha.append([materia.ref_le, materia.descricao, 30.00, 31.00])
    caminho = tmp_path / "resposta.xlsx"
    livro.save(caminho)

    leitura = service.ler_com_notas(caminho)

    assert leitura.origem == "EXCEL"
    assert leitura.notas == ()
    assert [p.estado for p in leitura.propostas] == [ESTADO_ATUALIZA]


def test_dialogo_mostra_as_notas_e_os_avisos() -> None:
    propostas = ler_respostas(
        ["Código", "Preço tabela atualizado"], [("PLC0052", 3000)], _catalogo()
    )

    dialogo = RespostaFornecedorDialog(
        propostas, notas=["«C» foi reconhecida pelos valores — confirme."],
    )

    assert dialogo.notas_label.isVisibleTo(dialogo) is True
    assert "confirme" in dialogo.notas_label.text()
    avisos = dialogo.table.item(0, RespostaFornecedorDialog.COLUNA_AVISOS)
    assert "vírgula" in avisos.text()
    # Assinalado é assinalado: não vem marcado para aplicar.
    assert dialogo.table.item(0, 0).checkState().value == 0


def test_dialogo_sem_notas_nao_mostra_a_caixa() -> None:
    propostas = ler_respostas(
        ["Código", "Preço tabela atualizado"], [("PLC0052", 31.2)], _catalogo()
    )

    dialogo = RespostaFornecedorDialog(propostas)

    assert dialogo.notas_label.isVisibleTo(dialogo) is False
