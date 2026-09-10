"""Secções estáveis e valores verificáveis, independentes da redação do LLM."""
from html import escape
import re
from app.utils.formatters import format_currency


def resumo_fontes(v3, phc, wood, placas, catalogos, estado=""):
    def texto(value):
        return escape(str(value if value is not None else "—"))
    def secao(n, titulo, linhas):
        # O limite só afeta a apresentação; os separadores mantêm os resultados.
        conteudo = "".join("<li>"+texto(l)+"</li>" for l in linhas[:40])
        if len(linhas)>40:
            conteudo += "<li>Mais resultados no separador desta fonte.</li>"
        return f'<h2 style="font-size:14pt;color:#5a3e2b">{n}. {titulo}</h2>' + ("<ul>"+conteudo+"</ul>" if linhas else "<p>Sem correspondências nos dados carregados. Consulte o estado da fonte.</p>")
    out=secao(1,"MATÉRIAS-PRIMAS V3",[
        f"{m.ref_le} — {m.descricao}: preço líquido {format_currency(m.preco_liquido)}/{m.unidade or 'unidade por confirmar'}."
        for m in v3])
    out+=secao(2,"PHC",[
        f"{r.get('Ref')} — {r.get('Descricao')}: custo {format_currency(r.get('Preco_Custo'))}/{r.get('Unidade')}; stock PHC {r.get('Stock')}; data do preço {r.get('Data_Preco')}."
        for r in phc])
    out+=secao(3,"WOODSTORE",[
        f"{r.get('Referencia')} — {r.get('Material')} | {r.get('Comprimento')} × {r.get('Largura')} × {r.get('Espessura')} mm: quantidade (Lagen) {r.get('Quantidade')}; reservas {r.get('Reservadas')}; saldo calculado {r.get('Disponivel')}."
        for r in wood])
    out+='<p>WoodStore: saldo por registo e dimensões. Um artigo sem saldo não elimina os restos disponíveis noutros registos. Saldos negativos exigem confirmação.</p>'
    # A comparação vai no topo da secção porque é a resposta à pergunta que
    # motivou isto tudo. O corte dos 40 é por baixo dela, de propósito.
    out+=secao(4,"REFERÊNCIAS DE CATÁLOGOS",[
        f"MAIS BARATO — {frase}" for frase in comparar_fornecedores(placas)
    ] + [
        # Uma ferragem nao tem acabamento nem grupo de preco: se estes campos
        # entrassem sempre, metade das linhas comecava por "22.8000/ — grupo ".
        "".join([
            r.referencia,
            f"/{r.st_acab}" if r.st_acab else "",
            f" — grupo {r.grupo}" if r.grupo else "",
            f"; {r.fornecedor or r.folha}; ",
            "; ".join(f"{e}: {p}" for e,p in r.precos.items()) or "sem preço na tabela",
            f". Origem: {r.folha}.",
        ])
        for r in placas])
    out+=secao(5,"CATÁLOGOS",[f"{r.ficheiro} — {r.local}: {r.trecho[:700]}" for r in catalogos if r.exato])
    return out+"<p><small>"+texto(estado)+"</small></p>"


def comentario_html(texto):
    """Formatar apenas negritos e parágrafos; nunca interpretar HTML do modelo."""
    safe=escape(texto or "")
    safe=re.sub(r"\*\*(.+?)\*\*",r"<strong>\1</strong>",safe)
    return '<h2 style="font-size:14pt;color:#5a3e2b">6. COMENTÁRIO IA</h2><p>'+safe.replace("\n","<br>")+"</p>"


def _valor(preco):
    """`9,32 €` -> 9.32. Devolve None ao que nao souber ler."""
    numero = re.sub(r"[^\d,.-]", "", str(preco or "")).replace(".", "").replace(",", ".")
    try:
        return float(numero)
    except ValueError:
        return None


def comparar_fornecedores(placas):
    """Onde a mesma referencia, na mesma medida, tem precos diferentes.

    Escrito aqui e nao pedido ao modelo porque e' a pergunta que motivou tudo
    isto -- «a quem compro isto mais barato» -- e um modelo pequeno responde-a
    com o primeiro preco que lhe aparece. O `W908` em 19 mm custa 9,32 EUR na
    Balbino & Faustino e 8,74 EUR na WoodSide, e a resposta dizia 9,32 sem
    mencionar a outra.

    Devolve uma linha por (referencia, medida) com mais do que um preco,
    ordenada do mais barato para o mais caro, com a diferenca no fim.
    """
    por_medida = {}
    for linha in placas:
        for etiqueta, preco in (linha.precos or {}).items():
            valor = _valor(preco)
            if valor is None:
                continue
            chave = (linha.referencia, etiqueta)
            origem = (linha.fornecedor or linha.folha or "").strip()
            por_medida.setdefault(chave, {}).setdefault((valor, preco), set()).add(origem)

    frases = []
    for (referencia, etiqueta), ofertas in sorted(por_medida.items()):
        if len(ofertas) < 2:
            continue
        ordenadas = sorted(ofertas.items())
        partes = "  ·  ".join(
            f"{preco} ({' / '.join(sorted(origens))})" for (_, preco), origens in ordenadas
        )
        diferenca = ordenadas[-1][0][0] - ordenadas[0][0][0]
        frases.append(
            f"{referencia} em {etiqueta}: {partes} — diferença de "
            f"{format_currency(diferenca)}"
        )
    return frases
