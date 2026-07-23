"""Envia (ou pre-visualiza) os questionarios da IA por Outlook, um por pessoa.

    python enviar_questionarios.py            -> so mostra o que ia enviar
    python enviar_questionarios.py --enviar   -> envia mesmo
"""

from __future__ import annotations

import sys
from pathlib import Path

from app.db.session import SessionLocal
from app.services.email_service import carregar_email_config, enviar_email

RAIZ = Path(__file__).resolve()
PASTA_DOCS = Path("docs/ia_questionarios")
EXEMPLO_PAULO = Path("docs/Ensinar_assistente_Martelo_Paulo_melhorado.docx")

REMETENTE = "projetos@lancaencanto.pt"
REMETENTE_NOME = "Paulo Catarino"

#: nome -> (email, frase personalizada)
PESSOAS = {
    "Pedro": (
        "desenhos2@lancaencanto.pt",
        "És das pessoas com mais obras no Martelo — só este ano tens 89 obras "
        "à tua responsabilidade. O assistente vai dar-te jeito sobretudo a "
        "encontrar trabalhos antigos parecidos com o que estás a fazer.",
    ),
    "Angela": (
        "projetos3@lancaencanto.pt",
        "Tens 70 obras tuas só este ano. Interessa-me sobretudo saber como "
        "descreves os móveis quando falas deles — é por aí que a pesquisa vai.",
    ),
    "Bruno": (
        "desenhos3@lancaencanto.pt",
        "Tens 52 obras tuas este ano. Os teus exemplos de ferragens e "
        "materiais são dos que mais vão ajudar.",
    ),
    "Dario": (
        "projetos2@lancaencanto.pt",
        "Tens 37 obras tuas este ano. Interessa-me sobretudo as palavras que "
        "usas para os móveis especiais e as formas fora do standard.",
    ),
    "Ana": (
        "desenhos4@lancaencanto.pt",
        "Tens 36 obras tuas este ano. As tuas perguntas do dia a dia são "
        "exatamente o que precisamos de recolher.",
    ),
    "Marcia": (
        "desenhos@lancaencanto.pt",
        "Tens 33 obras tuas este ano. Interessa-me sobretudo como tratas os "
        "clientes pelo nome curto quando falas deles.",
    ),
    "Andreia": (
        "orcamentos@lancaencanto.pt",
        "Estás nos orçamentos, por isso a parte que mais me interessa que "
        "preenchas é a dos avisos (Parte 5): o que te dava jeito o Martelo "
        "lembrar-te, sem teres de andar a verificar orçamento a orçamento.",
    ),
    "Catia": (
        "orcamentos2@lancaencanto.pt",
        "Estás nos orçamentos, por isso a parte que mais me interessa que "
        "preenchas é a dos avisos (Parte 5): o que te dava jeito o Martelo "
        "lembrar-te, sem teres de andar a verificar orçamento a orçamento.",
    ),
    "Elisabete": (
        "orcamentos3@lancaencanto.pt",
        "Estás nos orçamentos, por isso a parte que mais me interessa que "
        "preenchas é a dos avisos (Parte 5): o que te dava jeito o Martelo "
        "lembrar-te, sem teres de andar a verificar orçamento a orçamento.",
    ),
}

ASSUNTO = "Martelo V3 — ajuda-me a ensinar o novo assistente ({nome})"

CORPO = """\
<p>Olá {nome},</p>

<p>Estamos a preparar uma novidade no Martelo V3: um <b>assistente que responde a
perguntas escritas por palavras nossas</b>, do género <i>«que roupeiros meus estão
atrasados?»</i>, em vez de andarmos a mexer nos filtros um a um.</p>

<p>Para ele responder bem, precisa de aprender como cada um de nós fala. {frase}</p>

<p>Segue em anexo um documento com quadros para preencheres: as perguntas que
farias, as palavras que usas para os móveis e materiais, como tratas as pessoas e
os clientes, e os avisos que te dariam jeito. <b>Demora cerca de 20 minutos</b> e
não é preciso perceber nada de informática — escreve como falas.</p>

<p>Vai também o meu, já preenchido, só para veres o género de respostas. Não
copies o meu: o que interessa é como <i>tu</i> falas.</p>

<p><b>Não é preciso ter tudo decidido de uma vez.</b> O Martelo vai passar a ter
uma área da IA nas Configurações, onde cada um poderá ir acrescentando palavras e
avisos ao seu perfil à medida que se for lembrando. Quadros em branco não são
problema.</p>

<p><b>Não é obrigatório.</b> Mas sou honesto contigo: o assistente aprende com o
que estiver escrito, e quem não der exemplos vai ter respostas mais fracas às
suas próprias perguntas.</p>

<p>Há um quadro que te peço mesmo para não deixares em branco: o
<b>«o que NÃO queres ver»</b>, na Parte 5. É aí que dizes o que te iria irritar ou
o que te daria a sensação de estares a ser vigiado. O que escreveres aí passa a
ser regra do programa.</p>

<p>Quando acabares, devolve-me o ficheiro. Qualquer dúvida, aparece aí.</p>

<p>Obrigado,<br>Paulo</p>
"""


def main() -> int:
    enviar = "--enviar" in sys.argv
    if not EXEMPLO_PAULO.exists():
        print("FALTA o exemplo preenchido:", EXEMPLO_PAULO)
        return 2

    with SessionLocal() as session:
        config = carregar_email_config(session)

    print(f"Metodo de envio configurado: {config.metodo}")
    print(f"Remetente: {REMETENTE}")
    print()

    erros = 0
    for nome, (email, frase) in PESSOAS.items():
        anexo = PASTA_DOCS / f"Ensinar_assistente_Martelo_{nome}.docx"
        if not anexo.exists():
            print(f"[FALTA ANEXO] {nome}: {anexo}")
            erros += 1
            continue

        assunto = ASSUNTO.format(nome=nome)
        corpo = CORPO.format(nome=nome, frase=frase)
        anexos = [str(anexo.resolve()), str(EXEMPLO_PAULO.resolve())]

        if not enviar:
            print(f"[PRE-VISUALIZACAO] {nome:<10} -> {email}")
            print(f"    assunto: {assunto}")
            print(f"    anexos : {anexo.name}, {EXEMPLO_PAULO.name}")
            continue

        try:
            enviar_email(
                email,
                assunto,
                corpo,
                anexos,
                config=config,
                remetente_email=REMETENTE,
                remetente_nome=REMETENTE_NOME,
            )
            print(f"[ENVIADO] {nome:<10} -> {email}")
        except Exception as erro:  # noqa: BLE001 - reportado ao utilizador
            print(f"[ERRO] {nome:<10} -> {email}: {erro}")
            erros += 1

    print()
    print("Nada foi enviado (pre-visualizacao)." if not enviar else "Envio terminado.")
    return 1 if erros else 0


if __name__ == "__main__":
    raise SystemExit(main())
