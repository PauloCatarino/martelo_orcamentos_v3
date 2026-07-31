"""Preparar (e registar) o aviso ao cliente de que a obra entrou em produção.

O Martelo monta o email todo — destinatário, assunto, corpo, imagem e anexo —
mas **quem envia é o utilizador**, depois de o rever. Só quando o envio corre
bem é que fica o rasto na obra: é isso que a coluna "Projeto Cliente" mostra.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.domain.assistente_obra import saudacao_por_hora
from app.domain.projeto_cliente_email import (
    ProjetoParaCliente,
    assunto_projeto_producao,
    corpo_projeto_producao,
)
from app.models.cliente import Cliente
from app.models.producao import Producao
from app.models.user import User
from app.services.imos_imagem_service import resolver_imagem_imos
from app.services.producao_pastas_service import (
    caminho_versao_de_processo,
    caminho_versao_de_processo_existente,
)
from app.services.producao_service import gerar_nome_enc_imos_ix

#: Anexo por defeito: o PDF do projeto de produção, que existe para isto mesmo.
ANEXO_PROJETO = "2_Projeto_Producao.pdf"


@dataclass(frozen=True)
class EnvioProjetoCliente:
    """Tudo o que o diálogo do email precisa, já resolvido."""

    processo_id: int
    destino: str
    assunto: str
    corpo_html: str
    anexos: tuple[str, ...] = ()
    imagem_path: str = ""
    pasta_obra: str = ""
    avisos: tuple[str, ...] = field(default_factory=tuple)
    enviado_em: datetime | None = None
    enviado_para: str = ""
    enviado_por: str = ""

    @property
    def ja_enviado(self) -> bool:
        return self.enviado_em is not None


def preparar_envio(
    session: Session,
    processo_id: int,
    *,
    utilizador: str = "",
    agora: datetime | None = None,
) -> EnvioProjetoCliente:
    """Montar o email do projeto para o cliente, sem enviar nada."""
    processo = session.get(Producao, int(processo_id))
    if processo is None:
        raise ValueError("Processo de produção não encontrado.")

    momento = agora or datetime.now()
    avisos: list[str] = []

    cliente = _cliente_da_obra(session, processo)
    destino = _email_do_cliente(cliente)
    if not destino:
        avisos.append(
            "A ficha do cliente não tem email de envio do projeto de produção. "
            "Escreva o destinatário à mão antes de enviar."
        )

    pasta = _pasta_da_obra(session, processo)
    anexos: list[str] = []
    anexo = pasta / ANEXO_PROJETO if pasta else None
    if anexo is not None and anexo.is_file():
        anexos.append(str(anexo))
    else:
        avisos.append(
            f"Não encontrei o {ANEXO_PROJETO} na pasta da obra — o email vai sem "
            "ele. Pode gerá-lo na Preparação ou juntar outro anexo aqui."
        )

    imagem = _imagem_da_obra(session, processo)
    if not imagem:
        avisos.append("A obra não tem imagem do iMos — o email vai sem imagem.")

    dados = ProjetoParaCliente(
        processo=_texto(processo.codigo_processo),
        cliente=_texto(processo.nome_cliente),
        ref_cliente=_texto(processo.ref_cliente),
        obra=_texto(processo.obra),
        localizacao=_texto(processo.localizacao),
        data_entrada=momento.strftime("%d-%m-%Y"),
        data_entrega=_data(processo.data_entrega),
        materias_usados=_texto(processo.materias_usados),
        descricao_producao=_texto(processo.descricao_producao),
    )

    enviado_em = getattr(processo, "projeto_cliente_enviado_em", None)
    if enviado_em is not None:
        avisos.append(
            "O cliente já foi informado desta obra em "
            f"{enviado_em.strftime('%d-%m-%Y %H:%M')}. Se enviar outra vez, a "
            "data passa a ser a de hoje."
        )

    return EnvioProjetoCliente(
        processo_id=int(processo_id),
        destino=destino,
        assunto=assunto_projeto_producao(dados),
        corpo_html=corpo_projeto_producao(
            dados,
            saudacao=saudacao_por_hora(momento.hour),
            utilizador=utilizador,
            imagem_path=imagem,
        ),
        anexos=tuple(anexos),
        imagem_path=imagem,
        pasta_obra=str(pasta) if pasta else "",
        avisos=tuple(avisos),
        enviado_em=enviado_em,
        enviado_para=_texto(getattr(processo, "projeto_cliente_email", "")),
        enviado_por=_nome_utilizador(
            session, getattr(processo, "projeto_cliente_enviado_por_id", None)
        ),
    )


def registar_envio(
    session: Session,
    processo_id: int,
    *,
    destino: str,
    user_id: object = None,
    quando: datetime | None = None,
) -> None:
    """Guardar na obra que o cliente foi mesmo avisado (só após enviar)."""
    processo = session.get(Producao, int(processo_id))
    if processo is None:
        raise ValueError("Processo de produção não encontrado.")

    processo.projeto_cliente_enviado_em = quando or datetime.now()
    processo.projeto_cliente_email = _texto(destino)[:255]
    processo.projeto_cliente_enviado_por_id = int(user_id) if user_id else None
    session.commit()


# ---- peças ------------------------------------------------------------------
def _texto(valor: object) -> str:
    return str(valor or "").strip()


def _data(valor: object) -> str:
    try:
        return valor.strftime("%d-%m-%Y")  # type: ignore[union-attr]
    except AttributeError:
        return _texto(valor)


def _cliente_da_obra(session: Session, processo) -> Cliente | None:
    cliente_id = getattr(processo, "cliente_id", None)
    return session.get(Cliente, cliente_id) if cliente_id else None


def _email_do_cliente(cliente: Cliente | None) -> str:
    """Só a coluna de envio do projeto: o email do PHC serve para outra coisa."""
    if cliente is None:
        return ""
    return _texto(getattr(cliente, "email_projeto_producao", ""))


def _pasta_da_obra(session: Session, processo) -> Path | None:
    try:
        encontrada = caminho_versao_de_processo_existente(session, processo)
        if encontrada is not None:
            return Path(encontrada)
        return Path(caminho_versao_de_processo(session, processo))
    except (OSError, ValueError):
        pasta = _texto(getattr(processo, "pasta_servidor", ""))
        return Path(pasta) if pasta else None


def _imagem_da_obra(session: Session, processo) -> str:
    nome_enc = gerar_nome_enc_imos_ix(
        getattr(processo, "ano", ""),
        getattr(processo, "num_enc_phc", ""),
        getattr(processo, "versao_obra", ""),
        nome_cliente_simplex=getattr(processo, "nome_cliente_simplex", None),
        nome_cliente=getattr(processo, "nome_cliente", None),
        ref_cliente=getattr(processo, "ref_cliente", None),
    )
    if not nome_enc:
        return ""
    try:
        caminho = resolver_imagem_imos(session, nome_enc_imos=nome_enc)
    except (OSError, ValueError):
        return ""
    return str(caminho) if caminho else ""


def _nome_utilizador(session: Session, user_id) -> str:
    if not user_id:
        return ""
    utilizador = session.get(User, user_id)
    if utilizador is None:
        return ""
    return _texto(getattr(utilizador, "nome", "")) or _texto(
        getattr(utilizador, "username", "")
    )
