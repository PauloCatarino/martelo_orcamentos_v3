"""Pure rules for asking suppliers to update their prices.

The point of this is to stop chasing prices one by one: the V3 gathers what is
old, groups it by supplier and prepares one request per supplier.

What the supplier sees is deliberately narrow — their own reference, the
designation we know the material by, the unit, and the table price we have on
file. What they fill in is the **table price** and their **discount**, which are
the two numbers the Excel always had. The net price is ours to calculate and
never leaves the house, nor does the waste percentage, the stock, the edge
banding or which jobs the material goes into.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.materia_prima_types import (
    MESES_PRECO_DESATUALIZADO,
    meses_desde,
    preco_desatualizado,
)

#: Colunas do anexo. As marcadas para preencher vão destacadas no ficheiro.
COLUNA_CODIGO = "Código"
COLUNA_REF_FORNECEDOR = "Ref. fornecedor"
COLUNA_DESIGNACAO = "Designação"
COLUNA_UNIDADE = "Und"
COLUNA_PRECO_ATUAL = "Preço tabela atual"
COLUNA_PRECO_NOVO = "Preço tabela atualizado"
COLUNA_DESCONTO = "Desconto %"
COLUNA_NOVA_REF = "Nova referência"
COLUNA_NOVA_DESIGNACAO = "Nova designação"
COLUNA_OBSERVACOES = "Observações"

COLUNAS_ANEXO = (
    COLUNA_CODIGO,
    COLUNA_REF_FORNECEDOR,
    COLUNA_DESIGNACAO,
    COLUNA_UNIDADE,
    COLUNA_PRECO_ATUAL,
    COLUNA_PRECO_NOVO,
    COLUNA_DESCONTO,
    COLUNA_NOVA_REF,
    COLUNA_NOVA_DESIGNACAO,
    COLUNA_OBSERVACOES,
)

#: As que o fornecedor preenche (as outras vão só para ele se situar).
COLUNAS_A_PREENCHER = (
    COLUNA_PRECO_NOVO,
    COLUNA_DESCONTO,
    COLUNA_NOVA_REF,
    COLUNA_NOVA_DESIGNACAO,
    COLUNA_OBSERVACOES,
)


@dataclass(frozen=True)
class LinhaPedido:
    """One material inside a price request."""

    materia_prima_id: int
    codigo: str
    referencia_fornecedor: str | None
    designacao: str
    unidade: str | None
    preco_tabela: Decimal | None
    data_ultimo_preco: date | None
    meses: int | None

    def valores_do_anexo(self) -> dict:
        """A linha como vai para o ficheiro do fornecedor."""
        return {
            COLUNA_CODIGO: self.codigo,
            COLUNA_REF_FORNECEDOR: self.referencia_fornecedor or "",
            COLUNA_DESIGNACAO: self.designacao,
            COLUNA_UNIDADE: self.unidade or "",
            COLUNA_PRECO_ATUAL: self.preco_tabela,
            COLUNA_PRECO_NOVO: None,
            COLUNA_DESCONTO: None,
            COLUNA_NOVA_REF: None,
            COLUNA_NOVA_DESIGNACAO: None,
            COLUNA_OBSERVACOES: None,
        }


@dataclass(frozen=True)
class PedidoFornecedor:
    """Everything needed to ask one supplier for updated prices."""

    fornecedor_id: int | None
    fornecedor_nome: str
    email: str | None
    email_cc: str | None
    pessoa_contacto: str | None
    linhas: tuple[LinhaPedido, ...]

    @property
    def total(self) -> int:
        return len(self.linhas)

    @property
    def tem_email(self) -> bool:
        return bool((self.email or "").strip())

    @property
    def preco_mais_antigo(self) -> date | None:
        """A data mais antiga do lote, que é o que justifica o pedido."""
        datas = [linha.data_ultimo_preco for linha in self.linhas if linha.data_ultimo_preco]
        return min(datas) if datas else None


def materiais_a_rever(
    materias,
    hoje: date | None = None,
    meses_limite: int = MESES_PRECO_DESATUALIZADO,
) -> list:
    """As matérias-primas ativas cujo preço já pede revisão."""
    return [
        materia
        for materia in materias
        if getattr(materia, "ativo", True)
        and preco_desatualizado(materia, hoje, meses_limite)
    ]


def agrupar_por_fornecedor(
    materias,
    fornecedores,
    hoje: date | None = None,
    meses_limite: int = MESES_PRECO_DESATUALIZADO,
) -> list[PedidoFornecedor]:
    """Juntar os materiais a rever em um pedido por fornecedor.

    Os materiais sem fornecedor identificado ficam juntos num grupo próprio, sem
    email — aparecem na lista para se ver que existem, mas não se lhes pode
    escrever enquanto não tiverem ficha.
    """
    fichas = {fornecedor.id: fornecedor for fornecedor in fornecedores}
    grupos: dict[int | None, list[LinhaPedido]] = {}
    nomes: dict[int | None, str] = {}

    for materia in materiais_a_rever(materias, hoje, meses_limite):
        chave = getattr(materia, "fornecedor_id", None)
        ficha = fichas.get(chave)
        nomes.setdefault(
            chave,
            ficha.nome if ficha is not None else (materia.fornecedor or "(sem fornecedor)"),
        )
        grupos.setdefault(chave, []).append(_linha(materia, hoje))

    pedidos = [
        PedidoFornecedor(
            fornecedor_id=chave,
            fornecedor_nome=nomes[chave],
            email=getattr(fichas.get(chave), "email", None),
            email_cc=getattr(fichas.get(chave), "email_cc", None),
            pessoa_contacto=getattr(fichas.get(chave), "pessoa_contacto", None),
            linhas=tuple(linhas),
        )
        for chave, linhas in grupos.items()
    ]

    # Os que se conseguem enviar primeiro, e dentro desses os maiores lotes.
    return sorted(pedidos, key=lambda p: (not p.tem_email, -p.total, p.fornecedor_nome))


def _linha(materia, hoje: date | None) -> LinhaPedido:
    """Uma matéria-prima como linha de pedido."""
    return LinhaPedido(
        materia_prima_id=materia.id,
        codigo=materia.ref_le or "",
        referencia_fornecedor=materia.referencia_fornecedor,
        designacao=materia.descricao,
        unidade=materia.unidade,
        preco_tabela=materia.preco_tabela,
        data_ultimo_preco=materia.data_ultimo_preco,
        meses=meses_desde(materia.data_ultimo_preco, hoje),
    )


def assunto_do_email(pedido: PedidoFornecedor, empresa: str = "Lança Encanto") -> str:
    """Assunto do email do pedido de preços."""
    referencias = "referência" if pedido.total == 1 else "referências"
    return f"Atualização de preços — {empresa} ({pedido.total} {referencias})"


def corpo_do_email(
    pedido: PedidoFornecedor,
    nome_anexo: str,
    remetente: str | None = None,
    empresa: str = "Lança Encanto",
) -> str:
    """Corpo do email, em HTML.

    O tom é o de quem pede uma confirmação de rotina, não o de quem reclama:
    explica porque estamos a perguntar, diz exatamente o que é para preencher e
    avisa que a resposta entra direta na nossa base de dados — para o fornecedor
    perceber que não vale a pena mudar o formato do ficheiro.
    """
    saudacao = f"Bom dia, {pedido.pessoa_contacto}" if pedido.pessoa_contacto else "Bom dia"
    referencias = "referência" if pedido.total == 1 else "referências"
    assinatura = f"<b>{remetente}</b><br>" if remetente else ""

    return f"""
<div style="font-family: Calibri, 'Segoe UI', Arial, sans-serif; font-size: 11pt; line-height: 1.5;">
  <p>{saudacao},</p>
  <p>
    Na preparação dos nossos orçamentos usamos uma base de dados própria com os
    preços dos materiais que nos fornecem. Alguns desses preços já têm mais de um
    ano e, para não orçamentarmos com valores desatualizados, gostaríamos de os
    confirmar convosco.
  </p>
  <p style="background:#F7F2EA; border-left:3px solid #8B6F4E; padding:10px 14px; margin:0 0 12px;">
    <b>O que pedimos:</b> que preencham as colunas <b>«{COLUNA_PRECO_NOVO}»</b> e
    <b>«{COLUNA_DESCONTO}»</b> da tabela em anexo e nos devolvam o ficheiro
    respondendo a este email. Se alguma referência ou designação tiver mudado, há
    colunas próprias para isso. Se algum artigo já não existir, basta escrever
    «descontinuado» nas observações.
  </p>
  <p>
    A tabela leva apenas as <b>{pedido.total} {referencias}</b> que precisamos de
    confirmar, com a vossa referência e a designação por que as conhecemos. O
    ficheiro que nos devolverem entra diretamente na nossa base de dados, por isso
    não é preciso mudarem o formato nem responderem com outra lista.
  </p>
  <p>Anexo: <b>{nome_anexo}</b></p>
  <p>Agradecemos desde já a colaboração.</p>
  <p style="color:#8B6F4E;">
    Com os melhores cumprimentos,<br>
    {assinatura}Departamento de Orçamentos · {empresa}
  </p>
</div>
""".strip()


def nome_do_anexo(pedido: PedidoFornecedor, hoje: date | None = None) -> str:
    """Nome do ficheiro que segue em anexo."""
    data = (hoje or date.today()).strftime("%Y-%m-%d")
    nome = "".join(
        caracter if caracter.isalnum() or caracter in "-_" else "_"
        for caracter in pedido.fornecedor_nome.strip()
    )
    return f"Precos_LancaEncanto_{nome}_{data}.xlsx"
