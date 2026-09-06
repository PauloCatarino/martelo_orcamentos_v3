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
    out+=secao(4,"REFERÊNCIAS DE PLACAS",[
        f"{r.referencia}/{r.st_acab} — grupo {r.grupo}; {r.fornecedor or r.folha}; " + "; ".join(f"{e}: {p}" for e,p in r.precos.items()) + f". Origem: {r.folha}."
        for r in placas])
    out+=secao(5,"CATÁLOGOS",[f"{r.ficheiro} — {r.local}: {r.trecho[:700]}" for r in catalogos if r.exato])
    return out+"<p><small>"+texto(estado)+"</small></p>"


def comentario_html(texto):
    """Formatar apenas negritos e parágrafos; nunca interpretar HTML do modelo."""
    safe=escape(texto or "")
    safe=re.sub(r"\*\*(.+?)\*\*",r"<strong>\1</strong>",safe)
    return '<h2 style="font-size:14pt;color:#5a3e2b">6. COMENTÁRIO IA</h2><p>'+safe.replace("\n","<br>")+"</p>"
