"""Orquestração de "registar o orçamento no PHC" — criar + confirmar o número.

Junta as duas metades do processo:

* ``phc_automation_service`` — conduz a janela do PHC pelo teclado;
* ``phc_propostas_service`` — lê da base de dados do PHC (SÓ ``SELECT``) o
  número que foi atribuído e confirma que ficou tudo nos campos certos.

O resultado (``RegistoPropostaResultado``) diz sempre o que aconteceu, para a
interface poder ser honesta: número confirmado, número por confirmar à mão,
avisos de campos trocados, ou um dossier criado com o tipo errado.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.services.phc_automation_service import (
    PhcAutomationService,
    construir_designacao,
    formatar_num_cliente_phc,
)
from app.services.phc_propostas_service import (
    PropostaPhc,
    ler_designacoes_proposta,
    ler_max_obrano,
    localizar_proposta_criada,
    procurar_dossier_tipo_errado,
    verificar_proposta_gravada,
)


@dataclass(frozen=True)
class RegistoPropostaResultado:
    """O que aconteceu ao tentar registar a proposta no PHC."""

    proposta: PropostaPhc | None = None
    avisos: list[str] = field(default_factory=list)
    tipo_errado: str | None = None
    erro_leitura: str | None = None

    @property
    def numero_confirmado(self) -> int | None:
        """Número da proposta, quando foi possível confirmá-lo por SQL."""
        return self.proposta.numero if self.proposta else None

    @property
    def codigo_v3(self) -> str | None:
        """Código do orçamento no V3 (``<ano2><nº4>``, ex.: ``260806``)."""
        if self.proposta is None:
            return None
        return formatar_codigo_v3(self.proposta.ano, self.proposta.numero)

    @property
    def precisa_confirmacao_manual(self) -> bool:
        """A proposta foi criada mas o número não pôde ser lido."""
        return self.proposta is None


def _hoje_iso() -> str:
    """Data de hoje em ``YYYYMMDD`` (formato aceite pelo SQL Server)."""
    from datetime import date

    return date.today().strftime("%Y%m%d")


def formatar_codigo_v3(ano: int, numero: int) -> str:
    """Código do orçamento no V3 a partir do ano e do nº da proposta PHC.

    2026 + 806 -> ``260806``. Os dois primeiros dígitos são o ano; é isso que
    torna o número não-ambíguo, já que no PHC o ``OBRANO`` reinicia todos os
    anos.
    """
    return f"{int(ano) % 100:02d}{int(numero):04d}"


def designacao_sugerida(ref_cliente: str | None) -> str:
    """Designação inicial: ``Obra: <ref>`` com ref, vazio sem ela.

    Com ref. cliente há uma convenção clara (é o que o Paulo escreve à mão);
    sem ref não há nada sensato a sugerir, e o utilizador escreve o que
    precisar.
    """
    ref = (ref_cliente or "").strip()
    return construir_designacao(ref) if ref else ""


def registar_proposta_no_phc(
    session: Session,
    *,
    ano: int,
    num_cliente_phc: str,
    ref_cliente: str | None,
    designacao: str,
    data_iso: str | None = None,
    nome_cliente: str | None = None,
    automation: PhcAutomationService | None = None,
) -> RegistoPropostaResultado:
    """Criar a proposta no PHC e confirmar o número atribuído.

    Levanta ``PhcAutomationError`` se não conseguir conduzir o PHC (nesse caso
    nada foi criado). Se a criação correr mas a leitura falhar, devolve um
    resultado com ``erro_leitura`` — a proposta existe e o número tem de ser
    confirmado por uma pessoa.

    ``nome_cliente`` só é usado nos **clientes temporários**: aí o
    ``num_cliente_phc`` é o do cliente genérico (063) e o nome verdadeiro é
    escrito na janela que o PHC abre a seguir. É também esse nome que depois
    identifica a proposta na base de dados do PHC, já que o número de cliente
    é o mesmo em todas elas.
    """
    # Marca de água ANTES: o maior nº de PROPOSTA do ano. Tem de ser só de
    # propostas — cada tipo de dossier tem a sua própria série de OBRANO (as
    # Encomendas de Cliente já vão em 1329 enquanto as Propostas vão em 805),
    # por isso uma marca "de qualquer tipo" tornaria a proposta invisível.
    obrano_base: int | None = None
    erro_leitura: str | None = None
    try:
        obrano_base = ler_max_obrano(session, ano=ano)
    except Exception as exc:  # noqa: BLE001 - SQL/PowerShell/config do PHC
        erro_leitura = str(exc)

    servico = automation or PhcAutomationService()
    servico.criar_proposta(
        num_cliente_phc=num_cliente_phc,
        ref_cliente=ref_cliente,
        designacao=designacao,
        nome_cliente=nome_cliente,
    )

    if obrano_base is None:
        return RegistoPropostaResultado(erro_leitura=erro_leitura)

    try:
        proposta = localizar_proposta_criada(
            session,
            ano=ano,
            obrano_base=obrano_base,
            num_cliente=num_cliente_phc,
            ref_cliente=ref_cliente,
            nome_cliente=nome_cliente,
        )
    except Exception as exc:  # noqa: BLE001
        return RegistoPropostaResultado(erro_leitura=str(exc))

    if proposta is None:
        # Nenhuma proposta nova: o seletor do PHC podia estar noutro tipo.
        # A busca é por DATA, não por número — as séries são por tipo.
        try:
            tipo_errado = procurar_dossier_tipo_errado(
                session,
                data_iso=data_iso or _hoje_iso(),
                num_cliente=num_cliente_phc,
                ref_cliente=ref_cliente,
            )
        except Exception:  # noqa: BLE001
            tipo_errado = None
        return RegistoPropostaResultado(tipo_errado=tipo_errado)

    try:
        designacoes = ler_designacoes_proposta(
            session, ano=proposta.ano, numero=proposta.numero
        )
        avisos = verificar_proposta_gravada(
            proposta,
            designacoes,
            ref_cliente=ref_cliente,
            designacao=designacao,
            nome_cliente=nome_cliente,
        )
    except Exception:  # noqa: BLE001 - a verificação é uma rede de segurança
        avisos = []

    return RegistoPropostaResultado(proposta=proposta, avisos=avisos)


def descrever_resultado(
    resultado: RegistoPropostaResultado,
    *,
    num_cliente_phc: str,
    nome_cliente: str | None = None,
) -> str:
    """Texto para mostrar ao utilizador, honesto sobre o que se sabe."""
    cliente = formatar_num_cliente_phc(num_cliente_phc)
    if (nome_cliente or "").strip():
        cliente = f"{cliente} (genérico) com o nome «{nome_cliente.strip()}»"

    if resultado.tipo_errado:
        return (
            "A proposta NÃO foi criada — em vez dela ficou um "
            f"{resultado.tipo_errado} no PHC.\n\n"
            "O seletor da janela Dossiers Internos não estava em 'Proposta'. "
            "Abre o PHC, apaga esse documento, escolhe 'Proposta' no seletor "
            "e tenta de novo."
        )

    if resultado.proposta is None:
        texto = (
            "O documento foi gravado no PHC, mas não consegui confirmar o "
            "número na base de dados."
        )
        if resultado.erro_leitura:
            texto += f"\n\nMotivo: {resultado.erro_leitura}"
        return texto

    proposta = resultado.proposta
    texto = (
        f"Proposta PHC nº {proposta.numero} ({proposta.ano}) criada para o "
        f"cliente {cliente}.\n\n"
    )
    if (nome_cliente or "").strip():
        texto += f"  Nome no PHC:         {proposta.nome or '(vazio)'}\n"
    texto += (
        f"  Ref. cliente no PHC: {proposta.ref_cliente or '(vazio)'}\n"
        f"  Data:                {proposta.data or '—'}\n"
        f"  Nº do orçamento V3:  {resultado.codigo_v3}"
    )

    if resultado.avisos:
        texto += "\n\nMas o que ficou gravado não é exatamente o pedido:\n"
        texto += "\n".join(f"  • {aviso}" for aviso in resultado.avisos)
        texto += (
            "\n\nIsto costuma significar que a grelha do PHC neste computador "
            "tem as colunas noutra ordem. Confirma a proposta no PHC."
        )
    elif (nome_cliente or "").strip():
        texto += "\n\n✅ Nome, ref. cliente e designação verificados no PHC."
    else:
        texto += "\n\n✅ Ref. cliente e designação verificadas no PHC."

    return texto
