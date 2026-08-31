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
