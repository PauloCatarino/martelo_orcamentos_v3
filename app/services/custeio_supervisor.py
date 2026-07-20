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
# Origens INTERNAS (dentro do orçamento):
ORIGEM_OPERACOES = "operacoes"
ORIGEM_LINHA = "linha"
ORIGEM_MATERIAL = "material"
# Fase 3A: resolver + recalcular SEM sair (a página de custeio trata da ação).
ORIGEM_RESOLVER_MATERIAL = "resolver_material"


def origem_resolver_material() -> "Origem":
    """Origem de resolução inline do material (Fase 3A): corrigir + recalcular aqui."""
    return Origem(
        ORIGEM_RESOLVER_MATERIAL,
        "Resolver aqui",
        "Corrigir o material/preço desta linha e recalcular — sem sair do custeio.",
    )

# Origens EXTERNAS (Fase 2): a chave "menu:<nome_da_pagina>" pede à app para
# abrir esse menu de topo. Os nomes têm de coincidir com os de
# ``MainWindow.show_page`` (materias_primas, operacoes_maquinas, …).
PREFIXO_MENU = "menu:"
PAGINA_MATERIAS_PRIMAS = "materias_primas"
PAGINA_MAQUINAS_TARIFAS = "operacoes_maquinas"


def chave_menu(nome_pagina: str) -> str:
    """Devolve a chave de origem externa para um menu de topo."""
    return f"{PREFIXO_MENU}{nome_pagina}"


def pagina_de_chave(chave: str) -> str | None:
    """Se ``chave`` for uma origem externa, devolve o nome da página; senão None."""
    if chave.startswith(PREFIXO_MENU):
        return chave[len(PREFIXO_MENU):]
    return None


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
_CATEGORIAS_OPERACOES = {"Corte", "Orlagem", "CNC", "Operação manual", "Tempos"}


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


def _origem_materias_primas() -> Origem:
    return Origem(
        chave_menu(PAGINA_MATERIAS_PRIMAS),
        "Matérias-Primas",
        "Abrir o menu Matérias-Primas para corrigir preço/área da matéria-prima.",
    )


def _origem_maquinas_tarifas() -> Origem:
    return Origem(
        chave_menu(PAGINA_MAQUINAS_TARIFAS),
        "Máquinas e Tarifas",
        "Abrir Máquinas/Operações para validar a máquina, o tempo e a tarifa.",
    )


def _origens(categoria: str) -> tuple[Origem, ...]:
    """Origens onde o problema pode ser corrigido (internas primeiro, depois menus).

    A alternância que o utilizador pediu faz-se por vários botões de origem: cada
    categoria oferece o(s) sítio(s) provável(is) do problema.
    """
    if categoria == "Orlagem":
        # A orlagem pode falhar por PREÇO (o preço da orla vive no material /
        # Matérias-Primas) ou por OPERAÇÃO (máquina/tarifa) — ofereço ambos.
        return (
            _origem_operacoes(),
            _origem_maquinas_tarifas(),
            _origem_materias_primas(),
            _origem_linha(),
        )
    if categoria in _CATEGORIAS_OPERACOES:
        return (_origem_operacoes(), _origem_maquinas_tarifas(), _origem_linha())
    if categoria == "Material":
        return (_origem_materias_primas(), _origem_linha())
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


CATEGORIA_OPERACOES = "Operações"


def diagnostico_de_operacao(estado: str, diagnostico: str) -> DiagnosticoLinha:
    """Diagnóstico para uma linha do audit de operações ("Auditar operações", 2B).

    ``estado`` é OK/ATENÇÃO/VERIFICAR; só faz sentido chamar para linhas não-OK.
    VERIFICAR (tem operações mas custo a zero) é grave; ATENÇÃO (sem operações)
    fica como aviso — pode ser intencional (ferragem comprada).
    """
    severidade = CRITICO if estado == "VERIFICAR" else AVISO
    return DiagnosticoLinha(
        categoria=CATEGORIA_OPERACOES,
        severidade=severidade,
        mensagem=diagnostico,
        porque=(
            "Uma peça/ferragem sem operações — ou com operações mas custo de "
            "produção a zero — pode sair com o custo de produção incompleto."
        ),
        sugestao=(
            "Abrir as operações desta linha e validar máquina, tempo e tarifa; "
            "se for intencional (ex.: ferragem comprada), pode ignorar."
        ),
        origens=(_origem_operacoes(), _origem_maquinas_tarifas()),
    )


def diagnostico_de_ocorrencia(
    categoria: str, severidade: str, problema: str, acao: str | None
) -> DiagnosticoLinha:
    """Constrói um diagnóstico a partir de uma ocorrência da Auditoria de Custeio.

    A auditoria já classificou (categoria/severidade) e traz o ``problema`` e a
    ``acao`` recomendada; o supervisor acrescenta o *porquê* e as *origens* para
    o mesmo assistente servir também a página de auditoria (Fase 2C).
    """
    return DiagnosticoLinha(
        categoria=categoria,
        severidade=severidade,
        mensagem=problema,
        porque=_PORQUE.get(categoria, _PORQUE_GENERICO),
        sugestao=acao or _SUGESTAO.get(categoria, _SUGESTAO_GENERICA),
        origens=_origens(categoria),
    )
