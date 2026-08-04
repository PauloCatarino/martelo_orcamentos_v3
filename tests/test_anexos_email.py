"""As contas de tamanho dos anexos, feitas antes de tentar enviar."""

from __future__ import annotations

from pathlib import Path

from app.domain.anexos_email import (
    LIMITE_PADRAO_MB,
    formatar_tamanho,
    medir_anexo,
    resumir_anexos,
)


def _ficheiro(tmp_path: Path, nome: str, megabytes: float) -> Path:
    caminho = tmp_path / nome
    caminho.write_bytes(b"0" * int(megabytes * 1024 * 1024))
    return caminho


def test_formatar_tamanho_usa_virgula_e_escala() -> None:
    assert formatar_tamanho(0) == "0 bytes"
    assert formatar_tamanho(2048) == "2 KB"
    assert formatar_tamanho(int(23.1 * 1024 * 1024)) == "23,1 MB"


def test_anexo_que_nao_existe_fica_marcado(tmp_path: Path) -> None:
    medida = medir_anexo(tmp_path / "nao_existe.pdf")

    assert not medida.existe
    assert medida.bytes_ficheiro == 0
    assert "NÃO ENCONTRADO" in medida.etiqueta


def test_etiqueta_mostra_nome_e_tamanho(tmp_path: Path) -> None:
    caminho = _ficheiro(tmp_path, "2_Projeto_Producao.pdf", 1.5)

    medida = medir_anexo(caminho)

    assert medida.etiqueta == "2_Projeto_Producao.pdf — 1,5 MB"


def test_total_soma_todos_os_anexos_e_nao_so_o_primeiro(tmp_path: Path) -> None:
    # O que rebenta o email é a SOMA: três anexos de 8 MB passam o limite
    # mesmo com nenhum deles a chegar lá sozinho.
    anexos = [
        str(_ficheiro(tmp_path, f"anexo_{indice}.pdf", 8)) for indice in range(3)
    ]

    resumo = resumir_anexos(anexos, limite_mb=18)

    assert resumo.total_bytes == 24 * 1024 * 1024
    assert resumo.excede


def test_dentro_do_limite_nao_excede(tmp_path: Path) -> None:
    resumo = resumir_anexos([str(_ficheiro(tmp_path, "leve.pdf", 2))], limite_mb=18)

    assert not resumo.excede
    assert "2,0 MB de 18 MB" in resumo.texto_barra


def test_texto_barra_avisa_quando_passa_do_limite(tmp_path: Path) -> None:
    resumo = resumir_anexos([str(_ficheiro(tmp_path, "pesado.pdf", 23))], limite_mb=18)

    assert "demasiado grande" in resumo.texto_barra


def test_texto_barra_conta_os_ficheiros_em_falta(tmp_path: Path) -> None:
    resumo = resumir_anexos(
        [str(_ficheiro(tmp_path, "existe.pdf", 1)), str(tmp_path / "sumiu.pdf")]
    )

    assert "1 ficheiro não encontrado" in resumo.texto_barra


def test_sem_anexos_nao_excede_nada() -> None:
    resumo = resumir_anexos([])

    assert not resumo.excede
    assert resumo.texto_barra == "Sem anexos."


def test_mensagem_de_aviso_nomeia_os_maiores(tmp_path: Path) -> None:
    anexos = [
        str(_ficheiro(tmp_path, "pequeno.pdf", 1)),
        str(_ficheiro(tmp_path, "2_Projeto_Producao.pdf", 23)),
    ]

    mensagem = resumir_anexos(anexos, limite_mb=18).mensagem_aviso()

    assert "2_Projeto_Producao.pdf — 23,0 MB" in mensagem
    # O maior aparece primeiro, para se saber logo o que retirar.
    assert mensagem.index("2_Projeto_Producao.pdf") < mensagem.index("pequeno.pdf")
    assert "OneDrive" in mensagem


def test_limite_padrao_desconta_a_margem_da_codificacao() -> None:
    # 18 MB de ficheiro chegam ao servidor com ~25 MB, o limite habitual.
    assert LIMITE_PADRAO_MB == 18.0
