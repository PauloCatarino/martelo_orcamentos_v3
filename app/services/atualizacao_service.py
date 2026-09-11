"""Saber se há uma versão mais recente do Martelo na pasta do servidor.

O número da versão é a única forma de responder a "ele já tem a correção ou
não?", e até aqui isso vivia todo na cabeça de quem instala. Este serviço olha
para a pasta onde os instaladores ficam (a mesma de onde toda a gente instala)
e diz o que lá está.

Deliberadamente NÃO instala nada sozinho: devolve o caminho do instalador e é a
pessoa que decide. Uma versão com um problema entrar em todos os PCs de uma vez,
sem ninguém carregar em nada, seria pior do que o problema que resolve.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.config.versao import version_completa
from app.domain.versoes_instalador import (
    escolher_mais_recente,
    ha_versao_mais_recente,
)
from app.services.system_setting_service import SystemSettingService

#: Chave em ``system_settings`` (Configurações → Caminhos do Sistema).
CHAVE_PASTA_INSTALADORES = "pasta_instaladores"


@dataclass(frozen=True)
class EstadoVersao:
    """O que dizer ao utilizador sobre a versão que tem."""

    instalada: str
    disponivel: str | None
    caminho_instalador: Path | None
    pasta: Path | None
    ha_atualizacao: bool
    problema: str | None = None


class AtualizacaoService:
    """Compara a versão instalada com a que está na pasta dos instaladores."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def estado(self) -> EstadoVersao:
        instalada = version_completa()
        caminho = (
            SystemSettingService(self.session).obter_valor(CHAVE_PASTA_INSTALADORES)
            or ""
        ).strip()

        if not caminho:
            return EstadoVersao(
                instalada=instalada,
                disponivel=None,
                caminho_instalador=None,
                pasta=None,
                ha_atualizacao=False,
                problema=(
                    "A pasta dos instaladores ainda não está definida. "
                    "Defina-a em Configurações → Caminhos do Sistema "
                    f"({CHAVE_PASTA_INSTALADORES})."
                ),
            )

        pasta = Path(caminho)
        try:
            nomes = [ficheiro.name for ficheiro in pasta.iterdir() if ficheiro.is_file()]
        except OSError:
            return EstadoVersao(
                instalada=instalada,
                disponivel=None,
                caminho_instalador=None,
                pasta=pasta,
                ha_atualizacao=False,
                problema=(
                    f"Não foi possível ler a pasta dos instaladores:\n{pasta}\n\n"
                    "Verifique a ligação ao servidor."
                ),
            )

        mais_recente = escolher_mais_recente(nomes)
        if mais_recente is None:
            return EstadoVersao(
                instalada=instalada,
                disponivel=None,
                caminho_instalador=None,
                pasta=pasta,
                ha_atualizacao=False,
                problema=(
                    f"Não encontrei nenhum instalador do Martelo V3 em:\n{pasta}"
                ),
            )

        return EstadoVersao(
            instalada=instalada,
            disponivel=mais_recente.versao,
            caminho_instalador=pasta / mais_recente.nome_ficheiro,
            pasta=pasta,
            ha_atualizacao=ha_versao_mais_recente(instalada, mais_recente.versao),
        )


class InstaladorIndisponivel(RuntimeError):
    """Nao foi possivel deixar o instalador pronto a correr neste PC."""


def _e_caminho_de_rede(caminho: Path) -> bool:
    r"""``\SERVER_LE\...`` ou uma letra de unidade mapeada a um servidor."""
    texto = str(caminho)
    if texto.startswith("\\\\") or texto.startswith("//"):
        return True
    letra = os.path.splitdrive(texto)[0]
    if len(letra) == 2 and letra.endswith(":"):
        try:
            import ctypes

            DRIVE_REMOTE = 4
            return ctypes.windll.kernel32.GetDriveTypeW(letra + "\\") == DRIVE_REMOTE
        except Exception:
            return False
    return False


def preparar_instalador_local(caminho: Path) -> Path:
    r"""Devolver um caminho LOCAL para o instalador, copiando-o se for preciso.

    PORQUE E' QUE ISTO EXISTE
    -------------------------
    Desde que a empresa passou a exigir uma conta de administrador propria para
    instalar (setembro de 2026), abrir o instalador diretamente de
    ``\SERVER_LE\...`` deixou de funcionar. O UAC eleva para a conta
    ``ADMIN_<pessoa>``, o instalador passa a correr COM ESSA CONTA, e essa
    conta nao tem sessao autenticada no servidor de ficheiros. O servidor
    recusa-a e o Windows mostra ``ShellExecuteEx falhou; codigo 1385``, que nao
    explica nada a ninguem -- e o Martelo, que ja' se tinha fechado, nao estava
    la' para traduzir.

    A volta e' a que o Paulo descobriu a testar a mao: copiar primeiro para o
    PC (com a conta normal, que TEM acesso ao servidor) e so' depois abrir. O
    UAC pede a password na mesma -- isto nao contorna permissao nenhuma; o que
    muda e' que o processo elevado deixa de precisar da rede.
    """
    if not _e_caminho_de_rede(caminho):
        return caminho

    if not caminho.exists():
        raise InstaladorIndisponivel(
            "O instalador nao esta' onde devia:\n" + str(caminho)
        )

    destino_pasta = Path(tempfile.gettempdir()) / "Martelo_Atualizacao"
    destino = destino_pasta / caminho.name
    try:
        tamanho = caminho.stat().st_size
        destino_pasta.mkdir(parents=True, exist_ok=True)
        livre = shutil.disk_usage(destino_pasta).free
        if livre < tamanho * 1.1:
            raise InstaladorIndisponivel(
                "Nao ha' espaco neste PC para copiar o instalador.\n"
                "Precisa de {} MB e so' ha' {} MB livres.".format(
                    tamanho // (1024 * 1024), livre // (1024 * 1024)
                )
            )
        # Se ficou inteiro de uma tentativa anterior, nao voltar a copiar 200 MB.
        if not (destino.exists() and destino.stat().st_size == tamanho):
            shutil.copy2(caminho, destino)
    except InstaladorIndisponivel:
        raise
    except OSError as erro:
        raise InstaladorIndisponivel(
            "Nao foi possivel copiar o instalador para este PC.\n\n"
            "De:   {}\nPara: {}\n\n{}".format(caminho, destino, erro)
        ) from erro
    return destino
