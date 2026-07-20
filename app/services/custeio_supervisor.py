"""Supervisor de custeio: transforma as observações de produção de uma linha
num diagnóstico acionável — o *porquê* do alerta, uma *sugestão* de correção e
as *origens* (onde o utilizador pode corrigir).

É o "cérebro" do assistente de resolução de erros que acompanha a coluna
"Observações produção" da tabela de custeio. Reaproveita a classificação da
auditoria financeira (severidade CRÍTICO/AVISO + categoria) para não haver duas
lógicas diferentes a decidir o que é grave.

Fase 1: as origens são DENTRO do orçamento (abrir as operações da linha, focar a
linha). A Fase 2 acrescentará saltos para menus externos (Matérias-Primas,
Máquinas/Tarifas, Ferragens) e a alternância entre várias origens.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.custeio_auditoria_service import (
    AVISO,
    CRITICO,
    classificar_observacoes_producao,
)

# Chaves de origem reconhecidas pela UI (a página liga cada chave a uma ação de
# navegação). Ficam aqui para o diálogo e a página falarem a mesma linguagem.
ORIGEM_OPERACOES = "operacoes"
ORIGEM_LINHA = "linha"
ORIGEM_MATERIAL = "material"


@dataclass(frozen=True)
class Origem:
    """Um sítio onde o problema pode ser corrigido."""

    chave: str
    titulo: str
    descricao: str


@dataclass(frozen=True)
class DiagnosticoLinha:
    """Diagnóstico de uma observação de produção de uma linha de custeio."""

    categoria: str
    severidade: str
    mensagem: str
    porque: str
    sugestao: str
    origens: tuple[Origem, ...]

    @property
    def grave(self) -> bool:
        return self.severidade == CRITICO


# Porquê do alerta, por categoria (o que o utilizador ganha em perceber).
_PORQUE = {
    "Material": (
        "O custeio da matéria-prima precisa da área da peça e do preço líquido; "
        "falta um deles, por isso o Custo MP fica a zero e o preço sai por baixo."
    ),
    "Orlagem": (
        "A orlagem está prevista mas falta máquina, tarifa ou tempo para a "
        "calcular, por isso o custo de orlagem não entra no preço."
    ),
    "CNC": (
        "A operação CNC está prevista mas falta máquina, geometria, tempo ou "
        "tarifa para a custear, por isso o custo CNC fica em falta."
    ),
    "Operação manual": (
        "Há tempo manual preenchido mas falta o custo horário do posto, por isso "
        "a mão de obra não é contabilizada no custo de produção."
    ),
    "Acabamento": (
        "O acabamento está previsto mas falta área, preço ou desperdício para o "
        "custear, por isso não entra no preço."
    ),
    "Ferragem": (
        "A ferragem está prevista mas falta referência, quantidade ou preço, por "
        "isso não é contabilizada no custo."
    ),
    "Quantidade": (
        "A quantidade da linha é nula ou inválida, o que faz o custo total da "
        "linha sair errado."
    ),
    "Tempos": (
        "Faltam tempos ou setup de produção, por isso o custo de produção fica "
        "incompleto."
    ),
}

# Sugestão de correção, por categoria (o passo concreto a dar).
_SUGESTAO = {
    "Material": "Escolher a matéria-prima correta ou corrigir o preço líquido; depois recalcular o item.",
    "Orlagem": "Validar orlas, máquina e tarifas de orlagem; depois recalcular.",
    "CNC": "Validar operação, máquina, geometria, tempo e tarifa CNC; depois recalcular.",
    "Operação manual": "Validar tempo e custo horário da operação manual; depois recalcular.",
    "Acabamento": "Completar acabamento, área, preço e desperdício; depois recalcular.",
    "Ferragem": "Completar referência, quantidade e preço da ferragem; depois recalcular.",
    "Quantidade": "Corrigir a regra ou a quantidade (QT módulo/QT unidade) e recalcular o item.",
    "Tempos": "Completar tempos e setup da produção e recalcular o item.",
}

_PORQUE_GENERICO = "Esta observação pode afetar o custo calculado da linha."
_SUGESTAO_GENERICA = (
    "Rever a observação de produção e completar os dados antes de aceitar o preço."
)

# Categorias cujo problema se resolve tipicamente nas operações da peça.
_CATEGORIAS_OPERACOES = {"Orlagem", "CNC", "Operação manual", "Tempos"}


def _origem_operacoes() -> Origem:
    return Origem(
        ORIGEM_OPERACOES,
        "Operações da linha",
        "Abrir as operações desta peça para validar máquina, tempo e tarifa.",
    )


def _origem_linha() -> Origem:
    return Origem(
        ORIGEM_LINHA,
        "Dados da linha",
        "Rever esta linha no custeio (material, medidas, quantidades) e recalcular.",
    )


def _origens(categoria: str) -> tuple[Origem, ...]:
    if categoria in _CATEGORIAS_OPERACOES:
        return (_origem_operacoes(), _origem_linha())
    if categoria == "Material":
        return (
            Origem(
                ORIGEM_MATERIAL,
                "Matéria-prima da linha",
                "Escolher a matéria-prima correta ou corrigir o preço líquido nesta linha.",
            ),
            _origem_linha(),
        )
    return (_origem_linha(),)


def diagnosticar_observacoes(observacoes: str | None) -> list[DiagnosticoLinha]:
    """Devolve os diagnósticos (graves primeiro) das observações de uma linha."""
    diagnosticos = [
        DiagnosticoLinha(
            categoria=categoria,
            severidade=severidade,
            mensagem=mensagem,
            porque=_PORQUE.get(categoria, _PORQUE_GENERICO),
            sugestao=_SUGESTAO.get(categoria, _SUGESTAO_GENERICA),
            origens=_origens(categoria),
        )
        for categoria, severidade, mensagem in classificar_observacoes_producao(observacoes)
    ]
    # Graves primeiro, mantendo a ordem original dentro de cada grupo.
    diagnosticos.sort(key=lambda d: 0 if d.severidade == CRITICO else 1)
    return diagnosticos


def tem_erro_grave(observacoes: str | None) -> bool:
    """True se alguma observação da linha for um erro grave (CRÍTICO)."""
    return any(
        severidade == CRITICO
        for _categoria, severidade, _mensagem in classificar_observacoes_producao(observacoes)
    )
