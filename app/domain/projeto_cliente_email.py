"""Email que avisa o cliente de que a obra dele entrou em produção.

Texto aprovado no mockup `docs/mockup_email_projeto_producao.html`. Regra que
atravessa tudo: **os campos que a obra não tem desaparecem** — nem no assunto
nem no corpo aparecem etiquetas vazias. O que o cliente recebe é o que lhe diz
respeito (referências, datas, materiais e descrição); notas internas, preços e
estados do Martelo ficam de fora.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path

#: O que o cliente lê no "Estado atual". Na obra o estado é sempre "Producao"
#: (é o único que o seletor tem), mas isso é linguagem interna do Martelo.
ESTADO_PARA_O_CLIENTE = "Em produção"


@dataclass(frozen=True)
class ProjetoParaCliente:
    """O que se conta ao cliente sobre a obra que vai entrar em produção."""

    processo: str = ""
    cliente: str = ""
    ref_cliente: str = ""
    obra: str = ""
    localizacao: str = ""
    data_entrada: str = ""
    data_entrega: str = ""
    materias_usados: str = ""
    descricao_producao: str = ""

    @property
    def referencias(self) -> tuple[str, ...]:
        """Ref./Obra/Localização, só as que existem — pela ordem acordada."""
        etiquetas = (
            ("Ref. Cliente", self.ref_cliente),
            ("Obra", self.obra),
            ("Localização", self.localizacao),
        )
        return tuple(f"{nome}: {valor}" for nome, valor in etiquetas if str(valor or "").strip())


def assunto_projeto_producao(dados: ProjetoParaCliente) -> str:
    """``Processo: X | Ref.Cliente: Y | Obra: Z`` — sem as partes que faltam."""
    partes = []
    if dados.processo:
        partes.append(f"Processo: {dados.processo}")
    if dados.ref_cliente:
        partes.append(f"Ref.Cliente: {dados.ref_cliente}")
    if dados.obra:
        partes.append(f"Obra: {dados.obra}")
    return " | ".join(partes) or "Projeto para produção"


def corpo_projeto_producao(
    dados: ProjetoParaCliente,
    *,
    saudacao: str = "Boa tarde",
    utilizador: str = "",
    imagem_path: str = "",
) -> str:
    """Corpo HTML do email. ``imagem_path`` vazio = email sem imagem."""
    linhas = [f"<p>{escape(saudacao)},</p>"]

    if dados.cliente:
        linhas.append(f"<p>Sr. Cliente: <b>{escape(dados.cliente)}</b></p>")

    if imagem_path:
        try:
            uri = Path(imagem_path).as_uri()
            linhas.append(f'<p><img src="{uri}" width="480" /></p>')
        except (ValueError, OSError):
            # Imagem ilegível não pode impedir o aviso ao cliente.
            pass

    referencias = dados.referencias
    if referencias:
        linhas.append(
            '<p style="font-size:14pt"><b>'
            + escape(" | ".join(referencias))
            + "</b></p>"
        )

    entrada = ["A sua obra vai entrar para produção"]
    if dados.data_entrada:
        entrada.append(f"no dia <b>{escape(dados.data_entrada)}</b>")
    if dados.data_entrega:
        entrada.append(
            f", com previsão de conclusão a <b>{escape(dados.data_entrega)}</b>"
        )
    linhas.append("<p>" + " ".join(entrada).replace(" ,", ",") + ".</p>")

    if dados.processo:
        linhas.append(f"<p>Processo: <b>{escape(dados.processo)}</b></p>")

    detalhes = []
    if dados.materias_usados:
        detalhes.append(("Matérias-primas usadas", dados.materias_usados))
    if dados.descricao_producao:
        detalhes.append(("Descrição dos produtos", dados.descricao_producao))
    detalhes.append(("Estado atual", ESTADO_PARA_O_CLIENTE))

    linhas.append("<p><b>Detalhes da sua obra</b></p>")
    for titulo, valor in detalhes:
        linhas.append(
            '<p style="margin:0 0 10px;padding:8px 12px;background:#F7F2EA;'
            'border-left:3px solid #8B6F4E">'
            f"<b>{escape(titulo)}:</b><br>{_multilinha(valor)}</p>"
        )

    linhas.append(
        f"<p>Com os melhores cumprimentos,<br>{escape(utilizador)}</p>"
    )
    linhas.append(
        '<p style="color:#8B6F4E;font-size:9pt">🔨 IA Martelo — mensagem '
        "preparada automaticamente pelo Martelo Orçamentos.</p>"
    )
    return "\n".join(linhas)


def _multilinha(valor: str) -> str:
    """Texto do Martelo (várias linhas) em HTML, sem deixar passar tags."""
    linhas = [escape(linha.strip()) for linha in str(valor or "").splitlines()]
    return "<br>".join(linha for linha in linhas if linha)
