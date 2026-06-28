from app.domain.descricao_format import (
    LinhaDescricao,
    descricao_para_html,
    descricao_para_reportlab,
    parse_descricao,
)


def test_parse_descricao_classifica_linhas() -> None:
    assert parse_descricao("Titulo\n  - traco\n\t* estrela\n\n") == [
        LinhaDescricao("titulo", "Titulo"),
        LinhaDescricao("traco", "traco"),
        LinhaDescricao("estrela", "estrela"),
        LinhaDescricao("vazia", ""),
        LinhaDescricao("vazia", ""),
    ]


def test_titulo_fica_bold() -> None:
    html = descricao_para_html("ROUPEIRO 3+3 PORTAS")
    assert "font-weight:bold" in html
    assert "ROUPEIRO 3+3 PORTAS" in html


def test_linha_marcador_fica_italico_indentado() -> None:
    html = descricao_para_html("\t- Puxador TIC-TAC")
    assert "font-style:italic" in html
    assert "margin-left:18px" in html
    assert "- Puxador TIC-TAC" in html


def test_linha_destaque_fica_verde() -> None:
    html = descricao_para_html("\t* Montado")
    assert "#0a5c0a" in html
    assert "Montado" in html


def test_variante_sem_cor_remove_verde_mas_mantem_italico() -> None:
    html = descricao_para_html("\t* Montado", com_cor=False)
    assert "#0a5c0a" not in html
    assert "font-style:italic" in html
    assert "Montado" in html


def test_escapa_html() -> None:
    html = descricao_para_html("A & B <x>")
    assert "&amp;" in html and "&lt;x&gt;" in html


def test_deteta_prefixo_escrito_a_mao_sem_tab() -> None:
    # o utilizador pode escrever à mão, sem o tab
    html = descricao_para_html("- Interiores AGL")
    assert "font-style:italic" in html


def test_descricao_para_reportlab_formata_e_escapa() -> None:
    markup = descricao_para_reportlab("Titulo & <x>\n- Puxador\n* Montado\n")

    assert "<b>Titulo &amp; &lt;x&gt;</b>" in markup
    assert "&nbsp;&nbsp;<i>- Puxador</i>" in markup
    assert '<font color="#0a5c0a">Montado</font>' in markup
    assert "<br/>" in markup
    assert markup.endswith("<br/>&nbsp;")


def test_descricao_para_reportlab_sem_cor() -> None:
    markup = descricao_para_reportlab("* Montado", com_cor=False)

    assert "<font" not in markup
    assert "&nbsp;&nbsp;<i>Montado</i>" in markup
