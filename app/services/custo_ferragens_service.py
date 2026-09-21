"""Preço das ferragens da obra: V3 primeiro, depois PHC, depois IMOS (provisório).

Ordem pedida pelo Paulo (21-09-2026): 1.º Matérias-Primas do V3; 2.º o preço
do PHC; 3.º o preço do IMOS, que não é atualizado com frequência e fica
sempre marcado como provisório.

O PHC é só leitura (SELECT) e os preços lá não vêm todos no mesmo formato.
Visto na obra 1610: parafusos à CENTENA (unidade «%»: 1,267 € por 100
unidades), corrediças por PAR, dobradiças por UN — e a cavilha FC00304 ao
QUILO (7,34 €/KG; tomada à unidade dava 606 × 7,34 = 4 448 € numa obra de
5 500 €). Por isso só UN e «%» entram sozinhos; qualquer outra unidade, ou um
preço mais de 10× longe do IMOS, fica «a confirmar» e só se usa à mão.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.services.phc_sql import build_connection_string, load_phc_config, run_select

REF_PHC = re.compile(r"^[A-Z]{2}\d{5}$")
CATEGORIAS_FERRAGENS = ("Ferragens", "SPP", "Comprados")
ESTADOS_FINAIS = ("finalizado", "arquivado")

FONTE_V3, FONTE_PHC, FONTE_IMOS = "V3", "PHC", "IMOS"


def _numero(valor) -> Decimal | None:
    try:
        numero = Decimal(str(valor).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    return numero if numero.is_finite() else None


def refs_validas(refs) -> list[str]:
    """Só referências no formato FFxxxxx/FCxxxxx entram na consulta (nada de SQL livre)."""
    return sorted({str(r).strip().upper() for r in refs if REF_PHC.match(str(r).strip().upper())})


def ler_precos_phc(session: Session, refs) -> dict[str, dict]:
    """Preços do PHC para estas referências. SÓ LEITURA."""
    wanted = refs_validas(refs)
    if not wanted:
        return {}
    lista = ", ".join(f"'{ref}'" for ref in wanted)
    query = (
        "SELECT ref AS Ref, design AS Descricao, epcusto AS Preco_Custo, "
        "epvultimo AS Preco_Ultimo, unidade AS Unidade, "
        "CONVERT(VARCHAR(10), udata, 104) AS Data_Preco "
        f"FROM ST WITH (NOLOCK) WHERE ref IN ({lista})"
    )
    rows = run_select(build_connection_string(load_phc_config(session)), query)
    return {str(row.get("Ref") or "").strip().upper(): row for row in rows}


def preco_phc(line: dict, artigo: dict | None) -> dict | None:
    """Preço por unidade da linha, a partir do artigo PHC; None se não houver preço."""
    if not artigo:
        return None
    custo, ultimo = _numero(artigo.get("Preco_Custo")), _numero(artigo.get("Preco_Ultimo"))
    base = custo if custo and custo > 0 else ultimo if ultimo and ultimo > 0 else None
    if base is None:
        return None
    unidade = str(artigo.get("Unidade") or "").strip().upper()
    confirmar = ""
    preco = base
    if unidade == "%":
        preco = base / Decimal(100)
        nota = f"PHC {base} € por 100 → {preco.normalize():f} € / un"
    elif unidade in ("", "UN", "UND", "UNI"):
        nota = f"PHC {base} € / un"
    else:
        confirmar = f"PHC em {unidade}, não por unidade: confirmar antes de usar"
        nota = f"PHC {base} € por {unidade}"
    imos = _numero(line.get("imos_price"))
    if not confirmar and imos and imos > 0 and not (imos / 10 <= preco <= imos * 10):
        confirmar = f"PHC {preco.normalize():f} € muito longe do IMOS {imos} €: confirmar"
    origem = "custo" if base == custo else "último preço"
    return {
        "id": None, "ref": str(artigo.get("Ref") or "").strip(),
        "description": str(artigo.get("Descricao") or "").strip(),
        "unit": line.get("unit") or "un", "net": str(preco),
        "date": str(artigo.get("Data_Preco") or ""),
        "fonte": FONTE_PHC, "confirmar": confirmar,
        "mapping_source": f"2.ª opção PHC ({origem}): {nota}" + (f" — {confirmar}" if confirmar else ""),
    }


def preco_imos(line: dict) -> dict | None:
    preco = _numero(line.get("imos_price"))
    if preco is None or preco <= 0:
        return None
    return {
        "id": None, "ref": line.get("ref_phc") or "", "description": line.get("description") or line["name"],
        "unit": line.get("unit") or "un", "net": str(preco), "date": "",
        "fonte": FONTE_IMOS, "confirmar": "",
        "mapping_source": "Preço IMOS — PROVISÓRIO (não atualizado com frequência)",
    }


def fonte(price: dict | None) -> str:
    if not price:
        return ""
    if price.get("fonte"):
        return price["fonte"]
    return FONTE_V3


def resolver_ferragem(line: dict, preco_v3: dict | None, phc: dict[str, dict]) -> dict | None:
    """V3 → PHC → IMOS; o primeiro que tiver preço."""
    if preco_v3:
        return preco_v3
    if line["kind"] not in CATEGORIAS_FERRAGENS:
        return None
    ref = str(line.get("ref_phc") or "").strip().upper()
    via_phc = preco_phc(line, phc.get(ref))
    if via_phc and not via_phc["confirmar"]:
        return via_phc
    # PHC por confirmar nunca entra sozinho: fica o IMOS provisório (ou nada).
    return preco_imos(line)


@dataclass
class EstadoCusto:
    final: bool
    titulo: str
    pontos: list[tuple[bool, str]] = field(default_factory=list)


def estado_do_custo(estado_obra: str, lines, prices, plans, production) -> EstadoCusto:
    """O custo só é «com rigor» no fim: obra Finalizada/Arquivada e tudo apurado."""
    pontos: list[tuple[bool, str]] = []
    estado = str(estado_obra or "").strip()
    fechada = estado.casefold() in ESTADOS_FINAIS
    pontos.append((fechada, f"Obra {estado or 'sem estado'}"
                   + ("" if fechada else " — o custo final fecha em Finalizado/Arquivado")))

    area = sum((Decimal(p["total"]) for p in plans), Decimal(0))
    pontos.append((bool(plans), f"Placas: {len(plans)} plano(s) Cut-Rite, {area:.2f} m² consumidos"
                   if plans else "Placas: sem plano de corte — consumo real por apurar"))

    for kind in ("Placas", "Orlas"):
        rows = [l for l in lines if l["kind"] == kind]
        if rows:
            ok = sum(1 for l in rows if prices.get(l["key"]))
            pontos.append((ok == len(rows), f"{kind}: {ok} de {len(rows)} com preço V3"))

    hardware = [l for l in lines if l["kind"] in CATEGORIAS_FERRAGENS]
    if hardware:
        contagem = {FONTE_V3: 0, FONTE_PHC: 0, FONTE_IMOS: 0, "": 0}
        confirmar = 0
        for line in hardware:
            price = prices.get(line["key"])
            contagem[fonte(price)] = contagem.get(fonte(price), 0) + 1
            confirmar += bool(price and price.get("confirmar"))
        ok = contagem[FONTE_IMOS] == 0 and contagem[""] == 0 and confirmar == 0
        texto = (f"Ferragens: V3 {contagem[FONTE_V3]} · PHC {contagem[FONTE_PHC]} · "
                 f"IMOS provisório {contagem[FONTE_IMOS]} · sem preço {contagem['']}")
        if confirmar:
            texto += f" · {confirmar} com unidade a confirmar"
        pontos.append((ok, texto))

    sectors = (production or {}).get("sectors") or []
    # «Não aplicável» (estado N no Streamlit) conta como fechado; «Concluído» com horas também.
    closed = sum(1 for s in sectors if s.get("state") in ("Concluído", "Não aplicável"))
    pontos.append((bool(sectors) and closed == len(sectors),
                   f"Tempos Streamlit: {closed} de {len(sectors)} setores concluídos com horas "
                   "(ou não aplicáveis)" if sectors else "Tempos Streamlit: ainda não consultados"))

    final = all(ok for ok, _ in pontos)
    titulo = ("Custo FINAL da obra — tudo apurado." if final else
              "Custo PROVISÓRIO — o custo com rigor fica fechado quando a obra estiver "
              "Finalizada/Arquivada e todos os pontos abaixo estiverem ✓.")
    return EstadoCusto(final, titulo, pontos)
