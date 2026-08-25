# 32 - O assistente que le a resposta do fornecedor (G8)

> Fecha o ciclo desenhado em `docs/31_plano_materias_primas_no_v3.md`:
> G5 (fornecedores) -> G6 (pedir precos) -> G7 (importar a resposta) -> **G8**.
> Estado: **FEITO** (2026-08-25). Suite: 3838 testes.

---

## 1. O problema que isto resolve

O G7 ja lia a resposta do fornecedor - **desde que ela voltasse como saiu**. Na
pratica raramente volta:

- o fornecedor apaga colunas, muda os titulos, ou refaz a folha a maneira dele;
- responde com a **lista de precos dele**, onde nao existe a nossa Ref LE;
- manda a tabela em **PDF**, que ninguem vai copiar a mao para dentro do V3;
- e engana-se: escreve `0,2` em vez de `20`, ou `2487` em vez de `24,87`.

Tudo isto acabava em trabalho manual ou, pior, num preco errado dentro do
catalogo - e um preco errado no catalogo entra em **todos os orcamentos feitos a
seguir**.

---

## 2. O que o assistente faz - e o que nao faz

**Faz tres coisas**, exatamente as tres que o plano previa:

1. **Encontra as colunas** mesmo quando o ficheiro vem mexido.
2. **Le uma tabela de precos em PDF** enviada em vez do anexo.
3. **Assinala valores estranhos** antes de entrarem na base de dados.

**Nao faz uma quarta**: nao decide o que fica gravado. Continua a ser preciso um
visto por linha, e o que o assistente teve de adivinhar vem escrito no ecra, em
vez de ficar escondido.

---

## 3. Encontrar as colunas (`app/domain/resposta_fornecedor.py`)

A procura passou a ter **tres passagens**, da mais fiavel para a menos:

| Passagem | Como | Exemplo |
|---|---|---|
| `titulo` | o titulo normalizado bate certo com um dos nossos | "Preco tabela atualizado" |
| `parecido` | o titulo contem (ou esta contido em) um dos nossos | "Preco tabela 2026" |
| `conteudo` | o titulo nao diz nada; olha-se para os **valores** | uma coluna "C" cheia de `PLC0052` |

Duas travoes para nao ser esperto de mais:

- na 2.a passagem so contam titulos com **6 caracteres ou mais** - senao `desc`
  (desconto) roubava a coluna `descricao`;
- na 3.a passagem o preco so e adivinhado quando ha **uma unica** coluna de
  numeros por explicar. Havendo duas, fica por saber: entre duas colunas nao se
  escolhe a sorte.

O que foi encontrado por `parecido` ou por `conteudo` sai numa **nota** para o
utilizador ("«Preco tabela 2026» foi lida como o preco novo"), que aparece numa
caixa ocre no topo da janela de revisao.

### Reconhecer o material sem a nossa referencia

O catalogo passou a ser indexado **duas vezes**: por Ref LE e pela **referencia
do fornecedor**. Quando a linha nao traz o nosso codigo, tenta-se a dele. Uma
referencia usada por **dois** materiais nossos e retirada do indice - deixou de
identificar seja qual for.

---

## 4. Ler o PDF (`app/services/leitor_pdf_precos.py`)

Um PDF nao tem colunas, tem linhas de texto. Le-se com `pypdf` e, em cada linha,
procura-se:

- uma **referencia que conhecamos** (a nossa ou a dele) - sem isso a linha e
  deitada fora em silencio;
- o **preco**, que e o ultimo numero da linha que nao seja a percentagem;
- o **desconto**, so quando vem escrito com o sinal `%`.

O resultado sai no mesmo formato de uma folha (cabecalhos + linhas), por isso
todo o resto do circuito - as regras de leitura, os avisos e o ecra de revisao -
funciona sem saber que veio de um PDF. A linha original fica guardada nas
observacoes ("Lido do PDF: ..."), para quem revê poder comparar.

**Limite honesto:** um PDF que seja uma **imagem digitalizada** nao tem texto
nenhum para ler. Nesse caso o V3 diz isso mesmo, em vez de fingir que leu.

---

## 5. Assinalar valores estranhos

Antes havia uma regra: variacao de 25% ou mais. Agora ha seis:

| Sinal | Aviso |
|---|---|
| preco a zero ou negativo | "o material sairia sem custo nos orcamentos" |
| desconto fora de 0-95% | "esta fora do normal" |
| desconto entre 0 e 1 | "escrito 0,2 - quis dizer 20%?" |
| preco ~100x ou ~1000x | "parece uma virgula fora do sitio" |
| variacao >= 25% | "variacao de 63% acima do preco atual" |
| o mesmo material duas vezes no ficheiro | "mais do que uma linha para este material" |

E ainda: um preco **ilegivel** ("sob consulta") deixou de passar por linha em
branco - fica **A CONFIRMAR** com o texto que la estava escrito.

Uma correcao de passagem: o preco manter-se mas **o desconto mudar** ja nao e
lido como "sem alteracao". Muda o liquido, logo e uma alteracao.

Tudo o que e assinalado fica **por marcar** no ecra de revisao. O utilizador ve
os avisos na coluna "O que o V3 assinala" e decide.

---

## 6. Guiao de teste

**Onde:** Menu **Matérias-Primas** -> botao **"Ler resposta…"**.

1. **O caminho normal.** Pedir precos a um fornecedor, preencher o anexo como
   ele o faria e ler de volta: deve funcionar como sempre, **sem caixa ocre**
   nenhuma (nada foi adivinhado).
2. **Ficheiro mexido.** No mesmo anexo, mudar o titulo "Preço tabela atualizado"
   para **"Preço tabela 2026"** e trocar as colunas de sitio. Ler outra vez:
   os precos continuam a ser lidos e aparece a nota a dizer como.
3. **Titulos que nao dizem nada.** Apagar os titulos todos e escrever `A`, `B`,
   `C`. Ler: a coluna dos codigos e reconhecida pelos valores e a caixa ocre diz
   "foi reconhecida pelos valores - confirme".
4. **PDF.** Guardar uma tabela de precos em PDF (ou imprimir uma folha para PDF)
   com linhas do tipo `PLC0052 AGL TERM BEGE 31,20`. Escolher o ficheiro no
   mesmo botao: o filtro ja aceita `*.pdf`. Confirmar que aparece o aviso
   "a leitura de um PDF e sempre um palpite".
5. **Erros de propósito.** No anexo, escrever num preco `0`, noutro `0,2` no
   desconto e noutro o preco multiplicado por 100. Ler: as tres linhas ficam
   **A CONFIRMAR**, **por marcar**, com a explicacao na coluna dos avisos.
6. **Repetido.** Colar a mesma linha duas vezes com precos diferentes: as duas
   ficam A CONFIRMAR.
7. **Aplicar.** Marcar so as linhas boas e aplicar. Confirmar no separador
   **Historico de precos** da ficha que o preco entrou com origem FORNECEDOR, e
   que um **orcamento antigo** com esse material **nao mudou**.

---

## 7. O que fica de fora

- **PDF digitalizado** (imagem) - precisaria de OCR, que nao existe no V3.
- As regras de validacao escritas para o Excel ainda nao foram viradas para
  validar o **catalogo do V3** (ponto que vem do documento 31).
- A auditoria de custeio continua a dar a mensagem generica para materiais de
  **preco livre** sem preco.
- A **beta** precisa das migracoes 95 e 96 quando la chegar.
