"""Menu Ajuda: que versão tenho eu, e já saiu uma correção?

O número da versão é a única forma de responder a "ele já tem a correção ou
não?". Até aqui isso vivia na cabeça de quem instala; agora o Martelo lê a
pasta do servidor de onde toda a gente instala e compara.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domain.versoes_instalador import (
    escolher_mais_recente,
    ha_versao_mais_recente,
    ler_versao_do_nome,
    versao_para_ordem,
)
from app.services import atualizacao_service as modulo
from app.services.atualizacao_service import AtualizacaoService

V3 = "Setup_Martelo_V3_{}.exe"


# ----- Ler a versão do nome do ficheiro -----


def test_le_a_versao_do_nome_do_instalador() -> None:
    assert ler_versao_do_nome("Setup_Martelo_V3_1.0.8.exe") == "1.0.8"
    assert ler_versao_do_nome("setup_martelo_v3_1.2.30.EXE") == "1.2.30"


def test_ignora_o_instalador_do_martelo_v2() -> None:
    """O V2 vive na MESMA pasta do servidor: 2.2.9 não pode ganhar ao V3."""
    assert ler_versao_do_nome("Setup_Martelo Orcamentos V2_2.2.9.exe") is None


def test_ignora_ficheiros_que_nao_sao_instaladores() -> None:
    for nome in ("Password_Instalador.txt", "Diagnostico_Email_Outlook.ps1", ""):
        assert ler_versao_do_nome(nome) is None


def test_ignora_betas_e_release_candidates() -> None:
    """Quem tem o oficial não deve ser convidado a instalar uma beta."""
    assert ler_versao_do_nome("Setup_Martelo_V3_0.9.7-beta.exe") is None
    assert ler_versao_do_nome("Setup_Martelo_V3_1.1.0-rc1.exe") is None


# ----- Comparar por número, não por texto -----


def test_compara_por_numero_e_nao_por_texto() -> None:
    """Em texto "1.0.10" < "1.0.9". Em número não — é aqui que se erra."""
    assert versao_para_ordem("1.0.10") > versao_para_ordem("1.0.9")
    assert ha_versao_mais_recente("1.0.9", "1.0.10") is True
    assert ha_versao_mais_recente("1.0.10", "1.0.9") is False


def test_versao_igual_nao_convida_a_atualizar() -> None:
    assert ha_versao_mais_recente("1.0.8", "1.0.8") is False


def test_versao_estragada_nao_rebenta() -> None:
    assert versao_para_ordem("nao-e-versao") == (0, 0, 0)
    assert versao_para_ordem("") == (0, 0, 0)


def test_escolhe_o_mais_recente_de_uma_pasta_a_serio() -> None:
    """A pasta real do servidor, com o V2 e a password lá dentro."""
    escolhido = escolher_mais_recente(
        [
            "Password_Instalador.txt",
            "Setup_Martelo Orcamentos V2_2.2.9.exe",
            V3.format("1.0.8"),
            V3.format("1.0.10"),
            V3.format("1.0.9"),
            "Setup_Martelo_V3_1.1.0-beta.exe",
        ]
    )

    assert escolhido is not None
    assert escolhido.versao == "1.0.10"
    assert escolhido.nome_ficheiro == V3.format("1.0.10")


def test_pasta_sem_instaladores_do_v3() -> None:
    assert escolher_mais_recente(["Password_Instalador.txt"]) is None
    assert escolher_mais_recente([]) is None


# ----- O serviço -----


def _servico(monkeypatch, *, pasta: str, instalada: str = "1.0.8"):
    monkeypatch.setattr(modulo, "version_completa", lambda: instalada)
    monkeypatch.setattr(
        modulo,
        "SystemSettingService",
        lambda _session: SimpleNamespace(obter_valor=lambda _chave: pasta),
    )
    return AtualizacaoService(session=object())


def test_avisa_quando_ha_versao_mais_recente(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / V3.format("1.0.8")).write_text("x")
    (tmp_path / V3.format("1.0.9")).write_text("x")

    estado = _servico(monkeypatch, pasta=str(tmp_path)).estado()

    assert estado.instalada == "1.0.8"
    assert estado.disponivel == "1.0.9"
    assert estado.ha_atualizacao is True
    assert estado.caminho_instalador == tmp_path / V3.format("1.0.9")
    assert estado.problema is None


def test_nao_avisa_quando_ja_esta_atualizado(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / V3.format("1.0.8")).write_text("x")

    estado = _servico(monkeypatch, pasta=str(tmp_path)).estado()

    assert estado.ha_atualizacao is False
    assert estado.disponivel == "1.0.8"


def test_versao_do_servidor_mais_antiga_nao_convida_a_recuar(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / V3.format("1.0.7")).write_text("x")

    estado = _servico(monkeypatch, pasta=str(tmp_path)).estado()

    assert estado.ha_atualizacao is False


def test_pasta_por_definir_diz_onde_se_define(monkeypatch) -> None:
    estado = _servico(monkeypatch, pasta="").estado()

    assert estado.ha_atualizacao is False
    assert estado.problema is not None
    assert "Caminhos do Sistema" in estado.problema
    assert modulo.CHAVE_PASTA_INSTALADORES in estado.problema


def test_servidor_inacessivel_nao_rebenta(monkeypatch) -> None:
    estado = _servico(
        monkeypatch, pasta=r"\\SERVER_QUE_NAO_EXISTE\seja_o_que_for"
    ).estado()

    assert estado.ha_atualizacao is False
    assert estado.problema is not None
    assert "servidor" in estado.problema.lower()


def test_pasta_sem_instalador_nenhum_explica_se(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "Password_Instalador.txt").write_text("x")

    estado = _servico(monkeypatch, pasta=str(tmp_path)).estado()

    assert estado.ha_atualizacao is False
    assert "não encontrei nenhum instalador" in estado.problema.lower()


@pytest.mark.parametrize("existe", [True, False])
def test_diz_se_o_instalador_pede_password(
    monkeypatch, tmp_path: Path, existe: bool
) -> None:
    """O instalador é cifrado; a password está num ficheiro ao lado dele."""
    (tmp_path / V3.format("1.0.9")).write_text("x")
    if existe:
        (tmp_path / modulo.NOME_FICHEIRO_PASSWORD).write_text("x")

    estado = _servico(monkeypatch, pasta=str(tmp_path)).estado()

    assert estado.pede_password is existe


def test_o_servico_nao_instala_nada_sozinho() -> None:
    """Uma versão com problema não pode entrar sozinha em todos os PCs."""
    import inspect

    fonte = inspect.getsource(modulo)
    for proibido in ("startfile", "subprocess", "Popen", "os.system"):
        assert proibido not in fonte
