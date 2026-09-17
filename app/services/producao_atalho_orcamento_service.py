"""Atalho da pasta do orçamento dentro da pasta de produção da obra.

Quem está na produção abre ``Dep_Producao\\2026\\Encomenda de Cliente\\1597_CICOMOL``
e precisa muitas vezes de ir ao orçamento que deu origem à obra (o pedido do
cliente, o PDF enviado, as medidas). Até aqui o Paulo criava o atalho à mão:
``260906_CICOMOL - Atalho``, a apontar para ``Dep._Orcamentos\\2026\\260906_CICOMOL``.

Regras:

* só nas **Encomendas de Cliente** (nº PHC de 4 dígitos, ``1597``). As
  ``_111`` (Encomenda de Cliente Final) ainda não nascem de orçamentos do
  Martelo e o Paulo ainda não decidiu o que fazer com elas;
* o atalho vai para a pasta **principal** da obra (``1597_CICOMOL``), não para
  a pasta da versão, e aponta para a pasta **principal** do orçamento;
* se já existir, não se mexe; se a pasta do orçamento não for encontrada, não
  se cria nada. Um atalho que falha **nunca** impede a criação da pasta da
  obra -- é uma comodidade, não um passo obrigatório.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import Session

from app.core import diario_bordo
from app.models.orcamento import Orcamento
from app.models.producao import Producao
from app.services.orcamento_pasta_lookup_service import resolver_pasta_orcamento

SUFIXO_ATALHO = " - Atalho.lnk"


def e_encomenda_de_cliente(num_enc_phc: object, tipo_pasta: object = None) -> bool:
    """``1597`` sim; ``_111`` (Encomenda de Cliente Final) não."""
    numero = str(num_enc_phc or "").strip()
    if not numero or numero.startswith("_"):
        return False
    if "final" in str(tipo_pasta or "").casefold():
        return False
    return True


def nome_atalho(pasta_orcamento: Path) -> str:
    """``260906_CICOMOL`` -> ``260906_CICOMOL - Atalho.lnk`` (como o Paulo fazia)."""
    return f"{pasta_orcamento.name}{SUFIXO_ATALHO}"


def pasta_principal_da_obra(pasta_versao: Path) -> Path:
    """``...\\1597_CICOMOL\\1597_01_CICOMOL\\1597_01_01_CICOMOL`` -> ``...\\1597_CICOMOL``."""
    return Path(pasta_versao).parent.parent


def pasta_do_orcamento(session: Session, processo: Producao) -> Path | None:
    """A pasta principal do orçamento de onde a obra veio, se existir."""
    orcamento = (
        session.get(Orcamento, processo.orcamento_id)
        if processo.orcamento_id is not None
        else None
    )
    if orcamento is not None and orcamento.pasta_manual:
        pasta = Path(orcamento.pasta_manual)
        try:
            return pasta if pasta.is_dir() else None
        except OSError:
            return None

    num_orcamento = str(
        (orcamento.num_orcamento if orcamento is not None else None)
        or processo.num_orcamento
        or ""
    ).strip()
    if not num_orcamento:
        return None
    if orcamento is not None:
        ano = orcamento.ano
    elif len(num_orcamento) >= 2 and num_orcamento[:2].isdigit():
        # 260906 -> 2026: os dois primeiros dígitos do nº são o ano.
        ano = 2000 + int(num_orcamento[:2])
    else:
        return None
    # Sem versão: o atalho aponta para a pasta principal do orçamento.
    return resolver_pasta_orcamento(session, ano=ano, num_orcamento=num_orcamento)


def _criar_lnk_windows(atalho: Path, destino: Path) -> None:
    """Escrever o ``.lnk`` com o WScript.Shell (o mesmo que o Explorador usa)."""
    import win32com.client  # só existe no Windows; importado aqui de propósito

    shell = win32com.client.Dispatch("WScript.Shell")
    lnk = shell.CreateShortcut(str(atalho))
    lnk.TargetPath = str(destino)
    lnk.WorkingDirectory = str(destino)
    lnk.Description = f"Pasta do orçamento {destino.name}"
    lnk.Save()


def criar_atalho_orcamento(
    session: Session,
    processo: Producao,
    pasta_versao: Path | str | None,
    *,
    criar_lnk: Callable[[Path, Path], None] | None = None,
) -> Path | None:
    """Pôr na pasta principal da obra um atalho para a pasta do orçamento.

    Devolve o atalho (criado agora ou já existente), ou ``None`` quando não se
    aplica ou não foi possível. Nunca levanta exceção.
    """
    try:
        if not pasta_versao or not e_encomenda_de_cliente(
            processo.num_enc_phc, processo.tipo_pasta
        ):
            return None
        pasta_obra = pasta_principal_da_obra(Path(pasta_versao))
        if not pasta_obra.is_dir():
            return None
        pasta_orc = pasta_do_orcamento(session, processo)
        if pasta_orc is None:
            return None
        atalho = pasta_obra / nome_atalho(pasta_orc)
        if atalho.exists():
            return atalho
        (criar_lnk or _criar_lnk_windows)(atalho, pasta_orc)
        diario_bordo.registar_acao(
            "Atalho do orçamento na pasta da obra", f"{atalho} -> {pasta_orc}"
        )
        return atalho
    except Exception as erro:  # noqa: BLE001 - comodidade, nunca bloqueia
        diario_bordo.registar_aviso(
            "Não foi possível criar o atalho do orçamento na pasta da obra",
            f"{pasta_versao}: {erro}",
        )
        return None
