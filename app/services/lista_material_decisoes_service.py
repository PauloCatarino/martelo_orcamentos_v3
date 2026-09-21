"""Decisões sobre materiais que o Woodstore não conhece, por Lista Material.

Um material sem código no Woodstore não é cortado pelo Cut-Rite. Há três
saídas, todas decididas pelo utilizador na Análise da Lista Material:

* ``criar_woodstore`` — pedir às compras que o criem; as peças vão numa versão
  nova do plano de corte;
* ``temporario`` — nome temporário, para um material de uma ou duas vezes;
* ``fora_cutrite`` — peça comprada ou cortada à parte (ex.: tampo
  PostForming); não é para o Cut-Rite.

Ficam num JSON ao lado das análises da obra, para a verificação antes do envio
para o Cut-Rite não voltar a perguntar o que já foi decidido.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

CRIAR_WOODSTORE = "criar_woodstore"
TEMPORARIO = "temporario"
FORA_CUTRITE = "fora_cutrite"

ROTULOS = {
    CRIAR_WOODSTORE: "Pedir criação no Woodstore",
    TEMPORARIO: "Nome temporário",
    FORA_CUTRITE: "Fora do Cut-Rite (comprado / cortado à parte)",
}

EXPLICACOES = {
    CRIAR_WOODSTORE: "Pedido de criação às compras; estas peças vão numa versão nova do plano.",
    TEMPORARIO: "Nome temporário, só para esta obra.",
    FORA_CUTRITE: "Peça comprada ou cortada à parte; não vai ao Cut-Rite.",
}


def caminho(workbook_path: Path) -> Path:
    workbook_path = Path(workbook_path)
    return (
        workbook_path.parent / "Analise_Lista_Material" / "Decisoes"
        / f"{workbook_path.stem}_materiais.json"
    )


def ler(workbook_path: Path) -> dict[str, dict]:
    destino = caminho(workbook_path)
    if not destino.is_file():
        return {}
    try:
        dados = json.loads(destino.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    materiais = dados.get("materiais") if isinstance(dados, dict) else None
    return {
        str(nome): dict(valor)
        for nome, valor in (materiais or {}).items()
        if isinstance(valor, dict) and valor.get("acao") in ROTULOS
    }


def gravar(workbook_path: Path, novas: dict[str, dict], *, utilizador: str) -> dict[str, dict]:
    """Junta as decisões novas às existentes (a mais recente ganha)."""
    decisoes = ler(workbook_path)
    agora = datetime.now().isoformat(timespec="seconds")
    for material, decisao in novas.items():
        if decisao.get("acao") not in ROTULOS:
            raise ValueError(f"Decisão desconhecida para {material}.")
        decisoes[material] = {**decisao, "utilizador": utilizador, "data": agora}
    destino = caminho(workbook_path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".tmp")
    temporario.write_text(
        json.dumps(
            {"workbook": Path(workbook_path).name, "materiais": decisoes},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temporario.replace(destino)
    return decisoes


def descricao(decisao: dict) -> str:
    texto = ROTULOS.get(decisao.get("acao"), "")
    if decisao.get("acao") == TEMPORARIO and decisao.get("original"):
        texto += f" (em vez de {decisao['original']})"
    return texto
