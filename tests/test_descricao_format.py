from app.domain.descricao_format import descricao_para_html


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


def test_escapa_html() -> None:
    html = descricao_para_html("A & B <x>")
    assert "&amp;" in html and "&lt;x&gt;" in html


def test_deteta_prefixo_escrito_a_mao_sem_tab() -> None:
    # o utilizador pode escrever à mão, sem o tab
    html = descricao_para_html("- Interiores AGL")
    assert "font-style:italic" in html
