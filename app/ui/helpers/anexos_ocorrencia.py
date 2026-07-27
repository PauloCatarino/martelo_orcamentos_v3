"""Gravar na pasta da obra as fotos que o utilizador juntou ao ticket.

Faz a ponte entre a faixa de miniaturas (que só junta) e o disco + base de
dados. Vive nos helpers da interface porque precisa do Qt para gravar uma
imagem colada; a lógica de caminhos, essa, está em ``app/domain/ocorrencia_anexos``.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain.ocorrencia_anexos import (
    copiar_anexo,
    pasta_anexos_ticket,
    preparar_pasta,
    proximo_caminho,
)
from app.models.producao import Producao
from app.services.producao_ocorrencias_service import eliminar_anexo, registar_anexo
from app.services.producao_pastas_service import caminho_versao_de_processo


def resolver_pasta_obra(session: Session, processo: Producao) -> str | None:
    """Folder of this obra on the server — None when it cannot be resolved.

    Usa o caminho já gravado em ``pasta_servidor`` quando existe (é o que o
    utilizador vê no menu Produção) e só recalcula quando falta.
    """
    guardada = str(getattr(processo, "pasta_servidor", "") or "").strip()
    if guardada:
        return guardada
    try:
        return str(caminho_versao_de_processo(session, processo))
    except (SQLAlchemyError, OSError, ValueError):
        return None


def guardar_anexos(
    session: Session,
    *,
    ocorrencia,
    pasta_obra: str | None,
    pendentes,
    removidos=(),
    user_id: int | None = None,
) -> list[str]:
    """Save the new attachments, forget the removed ones; return warnings.

    Nunca levanta por causa de uma foto: se a rede estiver em baixo o ticket
    fica escrito na mesma e o utilizador vê o aviso.
    """
    avisos: list[str] = []

    for anexo_id in removidos or ():
        try:
            eliminar_anexo(session, int(anexo_id))
        except (ValueError, SQLAlchemyError):
            avisos.append("Não foi possível remover uma das fotos.")

    lista = list(pendentes or ())
    if not lista:
        return avisos

    numero = getattr(ocorrencia, "numero", None)
    pasta, aviso = preparar_pasta(pasta_anexos_ticket(pasta_obra, numero))
    if pasta is None:
        avisos.append(aviso or "Não foi possível guardar as fotos.")
        return avisos

    for anexo in lista:
        caminho, nome, problema = _gravar_um(anexo, pasta, numero)
        if problema:
            avisos.append(problema)
        if not caminho:
            continue
        try:
            registar_anexo(
                session,
                ocorrencia_id=ocorrencia.id,
                caminho=caminho,
                nome_original=nome,
                user_id=user_id,
            )
        except (ValueError, SQLAlchemyError):
            avisos.append(f"A foto '{nome}' foi copiada mas não ficou ligada ao ticket.")

    return avisos


def _gravar_um(anexo, pasta: Path, numero: int | None) -> tuple[str | None, str, str | None]:
    """Write one attachment to disk; return (caminho, nome, aviso)."""
    if getattr(anexo, "imagem", None) is not None:
        destino = proximo_caminho(pasta, numero, ".png")
        try:
            gravou = anexo.imagem.save(str(destino), "PNG")
        except OSError:
            gravou = False
        if not gravou:
            return None, anexo.nome, f"Não foi possível gravar a imagem colada ({anexo.nome})."
        return str(destino), anexo.nome, None

    resultado = copiar_anexo(getattr(anexo, "caminho", None), pasta, numero)
    return resultado.caminho, resultado.nome_original or anexo.nome, resultado.aviso
